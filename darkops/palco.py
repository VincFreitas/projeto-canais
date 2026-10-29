"""Palco: animação explicativa feita em código, em pixel art. O mecanismo funciona de verdade na tela.

Cada vídeo tem um módulo de cena (ex.: cenas/explicativo-geladeira.py) que desenha o mundo na grade de pixels a
cada quadro: as peças, o que elas fazem e as partículas. O palco cuida do resto: câmera que segue a peça da vez,
montagem peça por peça, barra "PEÇAS 3/7", aviso "NOVA PEÇA!" e etiquetas com linha presas exatamente na peça.

Módulo de cena:
  SERIE = "COMO FUNCIONA · GELADEIRA"
  MUNDO = (216, 384)                      tamanho do mundo em pixels da grade
  PECAS = {"compressor": {"titulo": "Compressor", "caixa": (x0, y0, x1, y1), "ancora": (x, y), "conta": True}}
  def desenhar(ctx): ...                  desenha o quadro em ctx.img (float32, altura x largura x 3)

Campos de cada cena no roteiro:
  "nova_peca": "compressor", "nova_em": "motor"     a peça entra (encaixa) quando a palavra é falada
  "acao": "derreter", "acao_em": "derrete"          liga um comportamento do módulo (ctx.acao("derreter"))
  "foco": "compressor" | "tudo", "foco_em": "..."   para onde a câmera vai (padrão: a peça nova)
  "rotulos": [{"texto": "motor", "peca": "compressor", "em": "motor"}]   ou "ponto": [x, y] no mundo
"""
import hashlib
import importlib.util
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .render import FFMPEG, FPS

VERSAO = 2
FONTE_FORTE = "C:/Windows/Fonts/ariblk.ttf"
FONTE_MONO = "C:/Windows/Fonts/consolab.ttf"
OURO = (255, 206, 40)
TINTA = (24, 22, 30)


def suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def vaivem(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------- desenho na grade ----------

def _cor(c):
    return np.asarray(c[:3], np.float32)


def ret(img, x0, y0, x1, y1, cor, alfa=1.0):
    h, w = img.shape[:2]
    a, b = int(max(round(x0), 0)), int(min(round(x1), w))
    c, d = int(max(round(y0), 0)), int(min(round(y1), h))
    if a < b and c < d:
        img[c:d, a:b] = img[c:d, a:b] * (1 - alfa) + _cor(cor) * alfa


def moldura(img, x0, y0, x1, y1, cor, esp=1):
    ret(img, x0, y0, x1, y0 + esp, cor)
    ret(img, x0, y1 - esp, x1, y1, cor)
    ret(img, x0, y0, x0 + esp, y1, cor)
    ret(img, x1 - esp, y0, x1, y1, cor)


def ponto(img, x, y, cor, alfa=1.0, lado=1):
    ret(img, x, y, x + lado, y + lado, cor, alfa)


def linha(img, a, b, cor, alfa=1.0, esp=1):
    passos = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
    for k in range(passos):
        f = k / max(passos - 1, 1)
        ret(img, a[0] + (b[0] - a[0]) * f - esp // 2, a[1] + (b[1] - a[1]) * f - esp // 2,
            a[0] + (b[0] - a[0]) * f - esp // 2 + esp, a[1] + (b[1] - a[1]) * f - esp // 2 + esp, cor, alfa)


def polilinha(img, pontos, cor, alfa=1.0, esp=1, progresso=1.0):
    """Linha por vários pontos; progresso < 1 desenha só o começo (peça sendo montada)."""
    comp = [math.dist(a, b) for a, b in zip(pontos, pontos[1:])]
    falta = sum(comp) * progresso
    for (a, b), c in zip(zip(pontos, pontos[1:]), comp):
        if falta <= 0:
            break
        f = min(falta / c, 1.0) if c else 1.0
        linha(img, a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), cor, alfa, esp)
        falta -= c


def circulo(img, cx, cy, r, cor, alfa=1.0, cheio=True):
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if (d <= r) if cheio else (r - 1 < d <= r):
                ponto(img, x, y, cor, alfa)


def luz(img, x, y, cor, alfa=1.0, lado=2):
    """Partícula que brilha: miolo com halo de 1 pixel."""
    ret(img, x - 1, y, x + lado + 1, y + lado, cor, alfa * 0.35)
    ret(img, x, y - 1, x + lado, y + lado + 1, cor, alfa * 0.35)
    ret(img, x, y, x + lado, y + lado, cor, alfa)


def sprite(img, arte: list[str], x, y, paleta: dict, escala: int = 1):
    """Desenha arte em texto: cada caractere é um pixel da paleta ('.' ou ' ' = transparente)."""
    for j, linha_arte in enumerate(arte):
        for i, ch in enumerate(linha_arte):
            if ch in paleta:
                ret(img, x + i * escala, y + j * escala, x + (i + 1) * escala, y + (j + 1) * escala, paleta[ch])


def no_caminho(pontos, s):
    for a, b in zip(pontos, pontos[1:]):
        c = math.dist(a, b)
        if s <= c:
            f = s / (c or 1)
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        s -= c
    return pontos[-1]


def fluxo(img, pontos, T, cor, velocidade=28.0, passo=8.0, alfa=1.0, cor_fim=None):
    """Pontos de luz correndo por um cano; cor_fim faz a cor mudar ao longo do caminho."""
    total = sum(math.dist(a, b) for a, b in zip(pontos, pontos[1:]))
    s = (T * velocidade) % passo
    while s < total:
        x, y = no_caminho(pontos, s)
        f = s / total
        c = tuple(int(cor[k] + (cor_fim[k] - cor[k]) * f) for k in range(3)) if cor_fim else cor
        luz(img, x - 1, y - 1, c, alfa, lado=2)
        s += passo


def ondas_calor(img, x, y, T, largura=20, altura=26, cor=(255, 140, 40), alfa=0.8):
    for k in range(4):
        base = x - largura / 2 + k * largura / 3
        for j in range(int(altura)):
            v = j / altura
            ponto(img, base + math.sin(j * 0.45 - T * 7 + k) * 2, y - j, cor, alfa * (1 - v), lado=2)


def vapor(img, x, y, T, n=10, cor=(240, 245, 255), alfa=0.7, subida=30, espalha=10, semente=1):
    rng = random.Random(semente)
    for _ in range(n):
        a, b = rng.random(), rng.random()
        v = (T / 1.6 + a) % 1.0
        luz(img, x + (b - 0.5) * espalha + math.sin(v * 6 + b * 5) * 3, y - v * subida, cor, alfa * (1 - v),
            lado=2 + int(v * 3))


def brilhos(img, x0, y0, x1, y1, T, n=10, cor=(255, 255, 220), semente=3):
    rng = random.Random(semente)
    for _ in range(n):
        x, y, c, d = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.random(), rng.random()
        v = max(0.0, math.sin(T * (2 + 3 * c) + d * 6)) ** 4
        if v > 0.05:
            luz(img, x, y, cor, v)
            for k in (2, 3):
                for dx, dy in ((k, 0), (-k + 1, 0), (0, k), (0, -k + 1)):
                    ponto(img, x + dx, y + dy, cor, v * (0.6 if k == 2 else 0.3))


def poeira(img, T, n=30, cor=(255, 240, 200), semente=7):
    h, w = img.shape[:2]
    rng = random.Random(semente)
    for _ in range(n):
        a, b, c, d = rng.random(), rng.random(), rng.random(), rng.random()
        ponto(img, a * w + math.sin(T * (0.6 + d) + a * 9) * 3, (b * h - (2 + 4 * c) * T) % h, cor,
              0.2 + 0.25 * (0.5 + 0.5 * math.sin(T * 3 + d * 7)))


# ---------- contexto que o módulo de cena recebe ----------

class Contexto:
    def __init__(self, img, t, T, cena, entradas, acoes, presentes_antes):
        self.img, self.t, self.T, self.cena = img, t, T, cena
        self._entradas, self._acoes, self._antes = entradas, acoes, presentes_antes

    def peca(self, nome: str) -> float:
        """0 = ainda não existe; de 0 a 1 enquanto encaixa; 1 = montada."""
        if nome in self._antes:
            return 1.0
        if nome in self._entradas:
            return suave((self.t - self._entradas[nome]) / 0.7)
        return 0.0

    def acao(self, nome: str) -> float | None:
        """Segundos desde que a ação começou (cenas anteriores contam como muito tempo); None = não começou."""
        if nome in self._acoes:
            dt = self.t - self._acoes[nome]
            return dt if dt >= 0 else None
        return None


def _carregar(modulo: Path):
    spec = importlib.util.spec_from_file_location(f"cena_{modulo.stem.replace('-', '_')}", modulo)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _historia(cenas: list[dict], i: int, palavras, dur):
    """Peças e ações já feitas antes da cena i, e as que acontecem nela (com o segundo)."""
    from .sincronia import momento
    antes, acoes_antes = set(), {}
    for c in cenas[: i - 1]:
        if c.get("nova_peca"):
            antes.add(c["nova_peca"])
        if c.get("acao"):
            acoes_antes[c["acao"]] = -99.0
    c = cenas[i - 1]
    entradas, acoes = {}, dict(acoes_antes)
    if c.get("nova_peca"):
        t = momento(palavras, c.get("nova_em") or c["nova_peca"])
        entradas[c["nova_peca"]] = t if t is not None else min(0.4, dur * 0.2)
    if c.get("acao"):
        t = momento(palavras, c.get("acao_em") or "") if c.get("acao_em") else None
        acoes[c["acao"]] = t if t is not None else 0.2
    return antes, entradas, acoes


def _alvo(mod, nome: str | None, mundo):
    """Centro e zoom da câmera para enquadrar a peça (ou o mundo todo)."""
    w, h = mundo
    if not nome or nome == "tudo" or nome not in mod.PECAS:
        return w / 2, h / 2, 1.0
    x0, y0, x1, y1 = mod.PECAS[nome]["caixa"]
    z = min(w / max((x1 - x0) * 1.5, 1), h / max((y1 - y0) * 2.2, 1))
    return (x0 + x1) / 2, (y0 + y1) / 2, min(max(z, 1.0), 2.6)


def _foco(cena: dict) -> str | None:
    return cena.get("foco") or cena.get("nova_peca") or "tudo"


def _sprite_rotulo(texto: str, k: int, largura: int) -> Image.Image:
    fonte = ImageFont.truetype(FONTE_FORTE, int(largura * 0.034))
    cx = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto.upper(), font=fonte)
    tw, th = cx[2] - cx[0], cx[3] - cx[1]
    pad, b = int(largura * 0.013), int(largura * 0.015)
    img = Image.new("RGBA", (tw + b + pad * 3, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width - 1, img.height - 1], fill=(255, 255, 255, 255), outline=TINTA + (255,), width=4)
    cores = [(255, 90, 125), (40, 200, 255), (110, 230, 140), OURO]
    y = (img.height - b) // 2
    d.rectangle([pad, y, pad + b, y + b], fill=cores[k % 4] + (255,))
    d.text((pad * 2 + b - cx[0], pad - cx[1]), texto.upper(), font=fonte, fill=TINTA + (255,))
    return img


def rotulo_na_tela(tela, d, spr, ax, ay, ti, t, largura, altura, pixel):
    """Etiqueta que pula na tela, com a linha crescendo até a peça (ax, ay em pixels da tela)."""
    lx = min(max(ax + (largura * 0.18 if ax < largura / 2 else -largura * 0.18), spr.width / 2 + 20),
             largura - spr.width / 2 - 20)
    ly = min(max(ay - altura * 0.09, altura * 0.21), altura * 0.6)
    cresce = suave((t - ti) / 0.25)
    bx, by = lx + (ax - lx) * cresce, ly + (ay - ly) * cresce
    d.line([(lx, ly), (bx, by)], fill=TINTA, width=pixel + 6)
    d.line([(lx, ly), (bx, by)], fill=(255, 255, 255), width=pixel)
    r = pixel * (1.6 + 0.5 * math.sin(t * 8))
    d.rectangle([bx - r, by - r, bx + r, by + r], fill=OURO, outline=TINTA, width=3)
    e = 0.3 + 0.8 * suave((t - ti) / 0.12) - 0.1 * suave((t - ti - 0.12) / 0.1)
    s = spr if abs(e - 1) < 0.01 else spr.resize((max(int(spr.width * e), 1), max(int(spr.height * e), 1)))
    tela.paste(s, (int(lx - s.width / 2), int(ly - s.height / 2)), s)


def _hud(tela: Image.Image, mod, cenas, i, t, entradas, antes, largura, altura):
    """Série, barra de peças e o aviso de peça nova."""
    d = ImageDraw.Draw(tela)
    contam = [n for n, p in mod.PECAS.items() if p.get("conta", True)]
    feitas = [n for n in contam if n in antes or (n in entradas and t >= entradas[n])]
    mono = ImageFont.truetype(FONTE_MONO, int(largura * 0.034))
    y = int(altura * 0.05)
    x0, x1 = int(largura * 0.06), int(largura * 0.94)
    faixa = Image.new("RGBA", (largura, int(altura * 0.058)), (12, 10, 24, 170))  # fundo escuro para ler
    tela.paste(faixa, (0, y - int(altura * 0.012)), faixa)
    d.text((x0, y), getattr(mod, "SERIE", "COMO FUNCIONA"), font=mono, fill=(255, 255, 255))
    texto = f"PEÇAS {len(feitas)}/{len(contam)}"
    cx = d.textbbox((0, 0), texto, font=mono)
    d.text((x1 - (cx[2] - cx[0]), y), texto, font=mono, fill=OURO)
    yb, n = y + int(altura * 0.022), max(len(contam), 1)
    larg = (x1 - x0 - (n - 1) * 8) / n
    for k, nome in enumerate(contam):
        a = x0 + k * (larg + 8)
        cheia = nome in feitas
        nova = nome in entradas and 0 <= t - entradas[nome] < 1.2
        cor = (255, 255, 255) if nova and int(t * 8) % 2 else OURO if cheia else (70, 70, 90)
        d.rectangle([a, yb, a + larg, yb + 12], fill=TINTA, outline=TINTA)
        d.rectangle([a + 3, yb + 3, a + larg - 3, yb + 9], fill=cor)
    for nome, te in entradas.items():  # aviso NOVA PEÇA! por 1,6 s
        dt = t - te
        if 0 <= dt < 1.6 and mod.PECAS.get(nome, {}).get("conta", True):
            titulo = mod.PECAS[nome].get("titulo", nome).upper()
            e = 0.4 + 0.75 * suave(dt / 0.15) - 0.15 * suave((dt - 0.15) / 0.12)
            e *= 1 - 0.25 * suave((dt - 1.3) / 0.3)
            grande = ImageFont.truetype(FONTE_FORTE, int(largura * 0.07 * e))
            peq = ImageFont.truetype(FONTE_MONO, int(largura * 0.032 * e))
            gb = d.textbbox((0, 0), titulo, font=grande)
            pb = d.textbbox((0, 0), "NOVA PEÇA!", font=peq)
            w = max(gb[2] - gb[0], pb[2] - pb[0]) + 60
            h = (gb[3] - gb[1]) + (pb[3] - pb[1]) + 50
            cx0, cy0 = largura / 2 - w / 2, altura * 0.29 - h / 2
            alfa = 1 - suave((dt - 1.35) / 0.25)
            if alfa <= 0.02:
                continue
            caixa = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
            dc = ImageDraw.Draw(caixa)
            dc.rectangle([0, 0, w - 1, h - 1], fill=(20, 18, 34, int(235 * alfa)), outline=OURO + (int(255 * alfa),),
                         width=6)
            dc.text((w / 2 - (pb[2] - pb[0]) / 2 - pb[0], 18 - pb[1]), "NOVA PEÇA!", font=peq,
                    fill=(255, 255, 255, int(255 * alfa)))
            dc.text((w / 2 - (gb[2] - gb[0]) / 2 - gb[0], 26 + (pb[3] - pb[1]) - gb[1]), titulo, font=grande,
                    fill=OURO + (int(255 * alfa),))
            tela.paste(caixa, (int(cx0), int(cy0)), caixa)


def gerar(modulo: Path, cenas: list[dict], i: int, dur: float, palavras: list, largura: int, altura: int,
          pixel: int, T0: float, impactos: list[float], destino: Path) -> Path:
    """Grava o clipe da cena i (mp4 sem áudio). Reaproveita se nada mudou."""
    if modulo.suffix == ".js":  # cena 3D (Three.js + GSAP) desenhada pelo Chromium sem janela
        from .palco_web import gerar as gerar_web
        return gerar_web(modulo, cenas, i, dur, palavras, largura, altura, pixel, T0, impactos, destino)
    from .sincronia import momento
    destino = destino.with_suffix(".mp4")
    c = cenas[i - 1]
    assinatura = {"versao": VERSAO, "modulo": hashlib.md5(modulo.read_bytes()).hexdigest(),
                  "cenas": hashlib.md5(json.dumps([{k: x.get(k) for k in ("nova_peca", "nova_em", "acao", "acao_em",
                                                                          "foco", "foco_em", "rotulos")}
                                                   for x in cenas[:i]], sort_keys=True,
                                                  ensure_ascii=False).encode()).hexdigest(),
                  "dur": round(dur, 2), "T0": round(T0, 2), "tela": [largura, altura, pixel],
                  "impactos": [round(x, 2) for x in impactos],
                  "palavras": hashlib.md5(json.dumps(palavras, sort_keys=True).encode()).hexdigest()}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    mod = _carregar(modulo)
    mundo = tuple(getattr(mod, "MUNDO", (largura // pixel, altura // pixel)))
    gw, gh = largura // pixel, altura // pixel
    antes, entradas, acoes = _historia(cenas, i, palavras, dur)
    de = _alvo(mod, _foco(cenas[i - 2]) if i > 1 else "tudo", mundo)
    para = _alvo(mod, _foco(c), mundo)
    t_foco = momento(palavras, c["foco_em"]) if c.get("foco_em") else None
    if t_foco is None:
        t_foco = entradas.get(c.get("nova_peca"), 0.15) - 0.3 if c.get("nova_peca") else 0.15
    t_foco = max(t_foco, 0.0)
    rotulos = []
    for k, r in enumerate(c.get("rotulos", [])):
        t = momento(palavras, r.get("em") or r["texto"])
        if r.get("peca") in mod.PECAS:
            ancora = mod.PECAS[r["peca"]].get("ancora") or [
                (mod.PECAS[r["peca"]]["caixa"][0] + mod.PECAS[r["peca"]]["caixa"][2]) / 2,
                (mod.PECAS[r["peca"]]["caixa"][1] + mod.PECAS[r["peca"]]["caixa"][3]) / 2]
        else:
            ancora = r.get("ponto") or [mundo[0] / 2, mundo[1] / 2]
        rotulos.append((r["texto"], ancora, t if t is not None else 0.3, _sprite_rotulo(r["texto"], k, largura)))

    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{largura}x{altura}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
                             "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(destino)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(max(int(round(dur * FPS)), 1)):
            t = q / FPS
            img = np.zeros((mundo[1], mundo[0], 3), np.float32)
            mod.desenhar(Contexto(img, t, T0 + t, i, entradas, acoes, antes))
            # câmera: viaja do enquadramento anterior até o da peça da vez, respira e dá um soco nos impactos
            f = vaivem((t - t_foco) / 0.9)
            cx = de[0] + (para[0] - de[0]) * f
            cy = de[1] + (para[1] - de[1]) * f
            z = de[2] + (para[2] - de[2]) * f
            z *= 1 + 0.025 * math.sin(T0 + t * 0.7)
            tremor = 0.0
            for ti in impactos:
                p = max(0.0, 1 - abs(t - ti - 0.05) / 0.35) if t >= ti - 0.05 else 0.0
                z *= 1 + 0.1 * p
                tremor = max(tremor, p)
            rng = random.Random(q)
            cx += rng.uniform(-1.5, 1.5) * tremor
            cy += rng.uniform(-1.5, 1.5) * tremor
            cw, ch = gw / z, gh / z
            x0 = min(max(cx - cw / 2, 0), max(mundo[0] - cw, 0))
            y0 = min(max(cy - ch / 2, 0), max(mundo[1] - ch, 0))
            xs = np.clip((x0 + (np.arange(gw) + 0.5) * cw / gw).astype(int), 0, mundo[0] - 1)
            ys = np.clip((y0 + (np.arange(gh) + 0.5) * ch / gh).astype(int), 0, mundo[1] - 1)
            grade = np.clip(img[ys][:, xs], 0, 255).astype(np.uint8)
            tela = Image.fromarray(np.repeat(np.repeat(grade, pixel, 0), pixel, 1))
            d = ImageDraw.Draw(tela)
            escala = largura / cw
            for texto, ancora, ti, spr in rotulos:  # etiqueta com linha até a peça
                if t >= ti:
                    rotulo_na_tela(tela, d, spr, (ancora[0] - x0) * escala, (ancora[1] - y0) * escala, ti, t,
                                   largura, altura, pixel)
            _hud(tela, mod, cenas, i, t, entradas, antes, largura, altura)
            if t < 0.12 and i > 1:  # corte entre cenas com um clarão curto
                tela = Image.blend(tela, Image.new("RGB", tela.size, (255, 255, 255)), 0.5 * (1 - t / 0.12))
            proc.stdin.write(tela.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar o palco {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino
