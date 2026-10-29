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
from .palco import _foco, _historia, _hud, _sprite_rotulo, rotulo_na_tela, vaivem
from .render import FFMPEG, FPS

VERSAO = 2
ORIGEM = "http://palco.local"
VISUAL = "liso"  # "liso" (palco.html) ou "pixel" (palco_pixel.html); a produção troca conforme o roteiro


def _servir(rota):
    """Entrega os arquivos do projeto ao Chromium sem subir um servidor."""
    caminho = (config.RAIZ / rota.request.url[len(ORIGEM) + 1:].split("?")[0]).resolve()
    if not caminho.is_relative_to(config.RAIZ) or not caminho.is_file():
        return rota.fulfill(status=404, body="")
    tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
    if caminho.suffix in (".js", ".mjs"):
        tipo = "text/javascript"
    rota.fulfill(status=200, body=caminho.read_bytes(), headers={"Content-Type": tipo})


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
    if pixelado:  # só entra na assinatura no pixel, para não refazer as cenas lisas já gravadas
        assinatura["visual"] = "pixel"
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    gw, gh = largura, altura  # o 3D é desenhado na resolução cheia, com bordas suavizadas
    antes, entradas, acoes = _historia(cenas, i, palavras, dur)
    de = _foco(cenas[i - 2]) if i > 1 else "tudo"
    para = _foco(c)
    t_foco = momento(palavras, c["foco_em"]) if c.get("foco_em") else None
    if t_foco is None:
        t_foco = entradas.get(c.get("nova_peca"), 0.15) - 0.3 if c.get("nova_peca") else 0.15
    t_foco = max(t_foco, 0.0)

    with sync_playwright() as p:
        navegador = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                            "--ignore-gpu-blocklist"])
        pagina = navegador.new_page(viewport={"width": gw, "height": gh})
        erros = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.route(f"{ORIGEM}/**", _servir)
        pagina.goto(f"{ORIGEM}/web/{html}")
        pagina.wait_for_function("window.__pronto === true", timeout=20000)
        url = "/" + modulo.resolve().relative_to(config.RAIZ).as_posix()
        info = pagina.evaluate("([u, w, h, p]) => window.__palco.iniciar(u, w, h, p)", [url, gw, gh, pixel])
        if erros:
            raise RuntimeError(f"cena 3D com erro: {erros[0]}")
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
                    if ponta is None and r.get("ponto"):  # "ponto" vem na grade 216x384 do palco 2D
                        ponta = [r["ponto"][0] / 216 * largura, r["ponto"][1] / 384 * altura]
                    if ponta is None:
                        continue
                    rotulo_na_tela(tela, d, spr, ponta[0], ponta[1], ti, t, largura, altura, pixel)
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
