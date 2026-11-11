"""Palco 3D: a cena é um módulo JavaScript (Three.js + GSAP) desenhado num Chromium sem janela, quadro a quadro.

O módulo (ex.: cenas/explicativo-geladeira.3d.js) exporta SERIE, PECAS e criar({THREE, gsap, renderer, largura,
altura}), que devolve {scene, camera, quadro(estado)}. O Python manda o estado de cada quadro (tempo, peças montadas,
ações, câmera) e recebe a imagem já em 1080x1920 (antialias, sombras, JPEG) e onde cada peça está na tela. Depois
põe por cima as etiquetas e a barra de peças, iguais às do palco 2D.

Com VISUAL = "pixel" (campo "visual_3d" do perfil ou do roteiro), usa web/palco_pixel.html: a cena sai na grade de
pixels (largura / pixel) com contorno, pontilhado e paleta curta, e aqui é ampliada sem suavizar.

Precisa de: pip install playwright; python -m playwright install chromium; npm install em web/ (gsap e three).
"""
import base64
import hashlib
import io
import json
import mimetypes
import subprocess
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw

from . import config

# o Chromium fica na pasta do projeto (apps.instalar_playwright), visível para o n8n e para o terminal do agente
import os as _os  # noqa: E402
from .apps import env_playwright  # noqa: E402
_os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", env_playwright()["PLAYWRIGHT_BROWSERS_PATH"])
from .palco import _foco, _historia, _hud, _sprite_rotulo, rotulo_na_tela, vaivem
from .render import FFMPEG, FPS

VERSAO = 3
ORIGEM = "http://palco.local"
VISUAL = "liso"  # "liso" ou "sombrio" (palco.html) ou "pixel" (palco_pixel.html); a produção troca conforme o roteiro


def _servir(rota):
    """Entrega os arquivos do projeto ao Chromium sem subir um servidor."""
    caminho = (config.RAIZ / rota.request.url[len(ORIGEM) + 1:].split("?")[0]).resolve()
    if not caminho.is_relative_to(config.RAIZ) or not caminho.is_file():
        return rota.fulfill(status=404, body="")
    tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
    if caminho.suffix in (".js", ".mjs"):
        tipo = "text/javascript"
    rota.fulfill(status=200, body=caminho.read_bytes(), headers={"Content-Type": tipo})


# Quem desenha o 3D, do mais rápido ao mais lento. Medido numa cena sombria em 1080x1920, por quadro: placa de vídeo
# dedicada 82 ms, placa integrada 96 ms, WARP (o desenho por processador do próprio Windows) 330 ms, SwiftShader (o do
# Chromium) 1200 ms. Ou seja: PC sem placa dedicada desenha quase igual, e PC sem placa nenhuma usa o WARP.
MOTORES = {
    "gpu": ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--force_high_performance_gpu"],
    "warp": ["--use-angle=d3d11-warp", "--enable-gpu", "--ignore-gpu-blocklist"],
    "swiftshader": ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
}
_PROCESSADOR = ("swiftshader", "basic render", "llvmpipe", "software")  # nomes de desenho sem placa de vídeo
_PLACA_JS = """() => { const g = document.createElement('canvas').getContext('webgl2');
  if (!g) return ''; const e = g.getExtension('WEBGL_debug_renderer_info');
  return e ? String(g.getParameter(e.UNMASKED_RENDERER_WEBGL)) : 'webgl'; }"""
_motor: str | None = None  # escolhido na primeira cena e reaproveitado até o programa fechar

# Qualidade do desenho: resolução interna (ampliada para a tela com suavização) e o que fica ligado. Vale só quando a
# máquina é lenta; em PC com placa de vídeo é sempre "alta". DARKOPS_3D_QUALIDADE no .env fixa um nível.
QUALIDADES = {
    "alta": (1.0, {}),
    "media": (0.75, {}),
    "leve": (2 / 3, {"sombra": 1024}),
    "minima": (0.5, {"sombra": 1024, "bloom": False}),
}
ALVO_MS = 200  # tempo por quadro que a qualidade automática procura (vídeo de 90 s: uns 9 min de 3D)
_qualidade: dict[str, str] = {}  # por visual, medida na primeira cena


def _abrir(p):
    """Chromium para desenhar o 3D, com o motor mais rápido que a máquina tiver: placa de vídeo (dedicada ou
    integrada), depois WARP, depois SwiftShader. Confere o que o Chromium ligou de verdade, porque sem placa ele cai
    sozinho no SwiftShader, que é 3,6 vezes mais lento que o WARP. DARKOPS_3D_GPU=0 no .env pula a placa de vídeo;
    DARKOPS_3D_MOTOR=gpu|warp|swiftshader fixa um."""
    global _motor
    import os
    if _motor:
        return p.chromium.launch(args=MOTORES[_motor])
    fixo = os.getenv("DARKOPS_3D_MOTOR", "").strip().lower()
    ordem = [fixo] if fixo in MOTORES else [m for m in MOTORES if m != "gpu" or os.getenv("DARKOPS_3D_GPU", "1") != "0"]
    for motor in ordem:
        navegador = None
        try:
            navegador = p.chromium.launch(args=MOTORES[motor])
            pagina = navegador.new_page()
            placa = pagina.evaluate(_PLACA_JS).lower()
            pagina.close()
        except Exception:  # noqa: BLE001
            placa = ""
        if placa and (motor != "gpu" or not any(n in placa for n in _PROCESSADOR)) or motor == ordem[-1]:
            if navegador is None:
                navegador = p.chromium.launch(args=MOTORES[motor])
            _motor = motor
            print(f"  3D desenhado por: {motor}" + (f" ({placa[:70]})" if placa else ""), flush=True)
            return navegador
        if navegador is not None:
            navegador.close()
    raise RuntimeError("não consegui abrir o Chromium para o 3D")


def _nivel(ms: float) -> str:
    """Nível de qualidade para a máquina que levou `ms` por quadro na resolução cheia (o custo cai com a área)."""
    import os
    fixo = os.getenv("DARKOPS_3D_QUALIDADE", "").strip().lower()
    if fixo in QUALIDADES:
        return fixo
    for nome, (escala, _) in QUALIDADES.items():
        if ms * escala * escala <= ALVO_MS:
            return nome
    return "minima"


def gerar(modulo: Path, cenas: list[dict], i: int, dur: float, palavras: list, largura: int, altura: int,
          pixel: int, T0: float, impactos: list[float], destino: Path) -> Path:
    from playwright.sync_api import sync_playwright

    from .sincronia import momento
    destino = destino.with_suffix(".mp4")
    c = cenas[i - 1]
    pixelado = VISUAL == "pixel" and pixel > 1
    html = "palco_pixel.html" if pixelado else "palco.html"
    assinatura = {"versao": VERSAO, "modulo": hashlib.md5(modulo.read_bytes()).hexdigest(),
                  "pagina": hashlib.md5((config.RAIZ / "web" / html).read_bytes()).hexdigest(),
                  "cenas": hashlib.md5(json.dumps([{k: x.get(k) for k in ("nova_peca", "nova_em", "acao", "acao_em",
                                                                          "foco", "foco_em", "rotulos")}
                                                   for x in cenas[:i]], sort_keys=True,
                                                  ensure_ascii=False).encode()).hexdigest(),
                  "dur": round(dur, 2), "T0": round(T0, 2), "tela": [largura, altura, pixel],
                  "impactos": [round(x, 2) for x in impactos],
                  "palavras": hashlib.md5(json.dumps(palavras, sort_keys=True).encode()).hexdigest()}
    sombrio = VISUAL == "sombrio" and not pixelado
    if pixelado or sombrio:  # só entra na assinatura fora do liso, para não refazer as cenas lisas já gravadas
        assinatura["visual"] = VISUAL
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    # o 3D é desenhado na resolução cheia, com bordas suavizadas; só máquina lenta desenha menor (QUALIDADES)
    import os
    medir = not pixelado
    nivel = _qualidade.get(VISUAL) or (os.getenv("DARKOPS_3D_QUALIDADE", "").strip().lower() if medir else "")
    if pixelado or nivel not in QUALIDADES:
        nivel = "alta"
    else:
        medir = False
    antes, entradas, acoes = _historia(cenas, i, palavras, dur)
    de = _foco(cenas[i - 2]) if i > 1 else "tudo"
    para = _foco(c)
    t_foco = momento(palavras, c["foco_em"]) if c.get("foco_em") else None
    if t_foco is None:
        t_foco = entradas.get(c.get("nova_peca"), 0.15) - 0.3 if c.get("nova_peca") else 0.15
    t_foco = max(t_foco, 0.0)

    with sync_playwright() as p:
        navegador = _abrir(p)
        erros = []
        url = "/" + modulo.resolve().relative_to(config.RAIZ).as_posix()

        def montar(nivel: str):
            escala, opcoes = QUALIDADES[nivel]
            gw, gh = int(largura * escala) // 2 * 2, int(altura * escala) // 2 * 2
            pagina = navegador.new_page(viewport={"width": gw, "height": gh})
            pagina.on("pageerror", lambda e: erros.append(str(e)))
            pagina.route(f"{ORIGEM}/**", _servir)
            pagina.goto(f"{ORIGEM}/web/{html}")
            pagina.wait_for_function("window.__pronto === true", timeout=20000)
            info = pagina.evaluate("([u, w, h, p, v, q]) => window.__palco.iniciar(u, w, h, p, v, q)",
                                   [url, gw, gh, pixel, "sombrio" if sombrio else VISUAL, opcoes])
            if erros:
                raise RuntimeError(f"cena 3D com erro: {erros[0]}")
            return pagina, info, largura / gw

        pagina, info, amplia = montar(nivel)
        if medir and _motor != "gpu":  # com placa de vídeo é sempre a qualidade cheia; sem ela, mede e decide
            import time
            parado = {"t": 0.0, "T": T0, "cena": i, "pecas": {n: 1.0 for n in info["PECAS"]}, "acoes": {},
                      "camera": {"de": "tudo", "para": "tudo", "f": 1.0}, "impacto": 0.0}
            tempos = []
            for _ in range(4):  # o primeiro quadro compila os shaders e não conta
                ini = time.perf_counter()
                pagina.evaluate("e => window.__palco.quadro(e)", parado)
                tempos.append((time.perf_counter() - ini) * 1000)
            ms = sum(tempos[1:]) / 3
            nivel = _nivel(ms)
            print(f"  3D sem placa de vídeo: {ms:.0f} ms por quadro, qualidade {nivel}", flush=True)
            if nivel != "alta":
                pagina.close()
                pagina, info, amplia = montar(nivel)
        if medir:
            _qualidade[VISUAL] = nivel
        mod = SimpleNamespace(PECAS=info["PECAS"], SERIE=info.get("SERIE", "COMO FUNCIONA"))
        rotulos = []
        for k, r in enumerate(c.get("rotulos", [])):
            t = momento(palavras, r.get("em") or r["texto"])
            rotulos.append((r, t if t is not None else 0.3, _sprite_rotulo(r["texto"], k, largura)))

        proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt",
                                 "rgb24", "-s", f"{largura}x{altura}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                                 "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(destino)],
                                stdin=subprocess.PIPE)
        assert proc.stdin is not None
        try:
            for q in range(max(int(round(dur * FPS)), 1)):
                t = q / FPS
                pecas = {}
                for nome in mod.PECAS:
                    if nome in antes:
                        pecas[nome] = 1.0
                    elif nome in entradas:
                        pecas[nome] = max(0.0, min((t - entradas[nome]) / 0.7, 1.0))
                    else:
                        pecas[nome] = 0.0
                estado = {"t": t, "T": T0 + t, "cena": i, "pecas": pecas,
                          "acoes": {k: (t - v if t >= v else None) for k, v in acoes.items()},
                          "camera": {"de": de, "para": para, "f": vaivem((t - t_foco) / 1.1)},
                          "impacto": max([max(0.0, 1 - abs(t - ti - 0.05) / 0.35) for ti in impactos if t >= ti - 0.05]
                                         or [0.0])}
                resposta = pagina.evaluate("e => window.__palco.quadro(e)", estado)
                if erros:
                    raise RuntimeError(f"cena 3D com erro na cena {i}, {t:.2f}s: {erros[0]}")
                tela = Image.open(io.BytesIO(base64.b64decode(resposta["png"].split(",", 1)[1]))).convert("RGB")
                if tela.size != (largura, altura):
                    tela = tela.resize((largura, altura), Image.NEAREST if pixelado else Image.LANCZOS)
                d = ImageDraw.Draw(tela)
                for r, ti, spr in rotulos:  # etiquetas presas onde a peça está na tela
                    if t < ti:
                        continue
                    ponta = resposta["ancoras"].get(r.get("peca")) if r.get("peca") else None
                    if ponta is not None:  # a âncora vem na resolução em que o 3D foi desenhado
                        ponta = [ponta[0] * amplia, ponta[1] * amplia]
                    if ponta is None and r.get("ponto"):  # "ponto" vem na grade 216x384 do palco 2D
                        ponta = [r["ponto"][0] / 216 * largura, r["ponto"][1] / 384 * altura]
                    if ponta is None:
                        continue
                    rotulo_na_tela(tela, d, spr, ponta[0], ponta[1], ti, t, largura, altura, pixel)
                if sombrio:  # no sombrio o cabeçalho do dossiê já diz o assunto; a cena nasce do escuro
                    if t < 0.35 and i > 1:
                        tela = Image.blend(tela, Image.new("RGB", tela.size, (0, 0, 0)), 0.85 * (1 - t / 0.35) ** 2)
                else:
                    _hud(tela, mod, cenas, i, t, entradas, antes, largura, altura)
                    if t < 0.12 and i > 1:
                        tela = Image.blend(tela, Image.new("RGB", tela.size, (255, 255, 255)), 0.5 * (1 - t / 0.12))
                proc.stdin.write(tela.tobytes())
        finally:
            proc.stdin.close()
            proc.wait()
            navegador.close()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar o palco 3D {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino


def testar(modulo: Path, cenas: list[dict], largura: int = 1080, altura: int = 1920) -> list[str]:
    """Desenha 3 quadros de cada cena sem gravar vídeo e devolve os erros: erro de JavaScript, peça que o roteiro cita
    e o módulo não tem, e etiqueta presa numa âncora que fica fora da tela. É o teste que a leva roda antes de produzir."""
    from playwright.sync_api import sync_playwright
    problemas = []
    with sync_playwright() as p:
        navegador = _abrir(p)
        try:
            pagina = navegador.new_page(viewport={"width": largura, "height": altura})
            erros = []
            pagina.on("pageerror", lambda e: erros.append(str(e)))
            pagina.route(f"{ORIGEM}/**", _servir)
            pagina.goto(f"{ORIGEM}/web/palco.html")
            pagina.wait_for_function("window.__pronto === true", timeout=20000)
            url = "/" + modulo.resolve().relative_to(config.RAIZ).as_posix()
            info = pagina.evaluate("([u, w, h, p]) => window.__palco.iniciar(u, w, h, p)", [url, largura, altura, 1])
            if erros:
                return [f"módulo com erro: {erros[0]}"]
            pecas_modulo = set(info["PECAS"])
            for i, c in enumerate(cenas, 1):
                for nome in (c.get("nova_peca"), c.get("foco")):
                    if nome and nome != "tudo" and nome not in pecas_modulo:
                        problemas.append(f"cena {i}: a peça '{nome}' não existe no módulo")
                antes, entradas, acoes = _historia(cenas, i, [], 4.0)
                de, para = (_foco(cenas[i - 2]) if i > 1 else "tudo"), _foco(c)
                for t in (0.0, 1.5, 3.5):
                    pecas = {n: 1.0 if n in antes else (min(max((t - entradas[n]) / 0.7, 0.0), 1.0)
                                                        if n in entradas else 0.0) for n in info["PECAS"]}
                    estado = {"t": t, "T": t, "cena": i, "pecas": pecas,
                              "acoes": {k: (t - v if t >= v else None) for k, v in acoes.items()},
                              "camera": {"de": de, "para": para, "f": vaivem(t / 1.1)}, "impacto": 0.0}
                    resposta = pagina.evaluate("e => window.__palco.quadro(e)", estado)
                    if erros:
                        problemas.append(f"cena {i}, {t:.1f}s: erro de JavaScript: {erros.pop()}")
                        break
                if t < 3.5:
                    continue
                for r in c.get("rotulos", []):  # no fim da cena a câmera já chegou: a etiqueta precisa caber na tela
                    ponta = resposta["ancoras"].get(r.get("peca")) if r.get("peca") else None
                    if ponta is None and not r.get("ponto"):
                        problemas.append(f"cena {i}: a etiqueta '{r['texto']}' não aparece: '{r.get('peca')}' "
                                         "não é uma âncora do módulo")
                    elif ponta and not (0 <= ponta[0] <= largura and 0 <= ponta[1] <= altura):
                        problemas.append(f"cena {i}: a etiqueta '{r['texto']}' aponta para '{r['peca']}', "
                                         f"que fica fora da tela ({ponta[0]:.0f}, {ponta[1]:.0f})")
        finally:
            navegador.close()
    return problemas
