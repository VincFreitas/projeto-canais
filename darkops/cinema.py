"""Cena viva: câmera que corta e se aproxima, partículas, antes/depois e etiquetas presas ao objeto.

Recebe a ilustração da cena já reduzida à grade de pixel art (visuais.ilustracao_local) e devolve um clipe mp4
sem áudio, do tamanho da tela, que o render usa como o visual da cena. Tudo acontece na grade de pixels e só
no fim é ampliado sem suavizar, então câmera e partículas continuam com cara de videogame 16 bits.

Campos da cena (posições de 0 a 1 no quadro aberto, como nas etiquetas):
  "focos": [{"x": 0.5, "y": 0.6, "zoom": 2, "em": "palavra"}]   closes da câmera (sem focos, ela escolhe sozinha)
  "efeitos": [{"tipo": "fluxo", "caminho": [[0.5, 0.2], [0.5, 0.8]]}, {"tipo": "vapor", "x": 0.5, "y": 0.4}]
      tipos: poeira, brilhos, fluxo, eletricidade, faiscas, vapor, bolhas, calor, frio, ondas
  "ilustracao_depois" + "depois_em": segunda imagem (o mesmo objeto depois da mudança), trocada na palavra
  "rotulos": [{"texto": "motor", "x": 0.5, "y": 0.3, "em": "motor", "alvo": [0.5, 0.6]}]   alvo = ponta da linha
"""
import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .render import FFMPEG, FPS

VERSAO = 3
FONTE = "C:/Windows/Fonts/ariblk.ttf"
CORES_ROTULO = [(255, 90, 125), (40, 200, 255), (110, 230, 140), (255, 206, 40)]
TIPOS = ("poeira", "brilhos", "fluxo", "eletricidade", "faiscas", "vapor", "bolhas", "calor", "frio", "ondas")


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _pulso(t: float, subida: float = 0.07, descida: float = 0.35) -> float:
    """0 -> 1 -> 0: impacto rápido que some devagar."""
    if t < 0:
        return 0.0
    if t < subida:
        return t / subida
    return max(0.0, 1 - (t - subida) / descida)


# ---------- desenho na grade (img: float32 H x W x 3) ----------

def _ponto(img, x, y, cor, alfa=1.0, lado=1):
    h, w = img.shape[:2]
    x0, y0 = int(round(x)), int(round(y))
    for dy in range(lado):
        for dx in range(lado):
            xx, yy = x0 + dx, y0 + dy
            if 0 <= xx < w and 0 <= yy < h:
                img[yy, xx] = img[yy, xx] * (1 - alfa) + np.asarray(cor, np.float32) * alfa


def _luz(img, x, y, cor, alfa=1.0, lado=2):
    """Partícula que brilha: miolo de lado x lado com um halo de 1 pixel em volta."""
    for dx in range(-1, lado + 1):
        for dy in range(-1, lado + 1):
            borda = dx in (-1, lado) or dy in (-1, lado)
            if borda and (dx, dy) in ((-1, -1), (-1, lado), (lado, -1), (lado, lado)):
                continue
            _ponto(img, x + dx, y + dy, cor, alfa * (0.35 if borda else 1.0))


def _linha(img, a, b, cor, alfa=1.0):
    passos = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
    for k in range(passos):
        f = k / max(passos - 1, 1)
        _ponto(img, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, cor, alfa)


def _anel(img, cx, cy, r, cor, alfa):
    voltas = max(int(2 * math.pi * r), 6)
    for k in range(voltas):
        ang = 2 * math.pi * k / voltas
        _ponto(img, cx + r * math.cos(ang), cy + r * math.sin(ang), cor, alfa)


class _Efeito:
    """Um sistema de partículas: desenha no quadro da imagem em função do tempo (sem estado)."""

    def __init__(self, spec: dict, ox: float, oy: float, gw: int, gh: int, w: int, h: int, semente: int):
        self.tipo = spec.get("tipo", "poeira")
        self.rng = random.Random(semente)
        self.w, self.h = w, h
        self.px = lambda fx, fy: (ox + fx * gw, oy + fy * gh)
        self.cx, self.cy = self.px(float(spec.get("x", 0.5)), float(spec.get("y", 0.5)))
        self.raio = float(spec.get("raio", 0.12)) * gw
        self.cor = tuple(spec["cor"]) if spec.get("cor") else None
        self.caminho = [self.px(float(p[0]), float(p[1])) for p in spec.get("caminho", [])]
        if len(self.caminho) < 2:
            self.caminho = [(self.cx, self.cy - self.raio), (self.cx, self.cy + self.raio)]
        self.trechos = [math.dist(a, b) for a, b in zip(self.caminho, self.caminho[1:])]
        self.total = sum(self.trechos) or 1.0
        n = {"poeira": 34, "brilhos": 14, "vapor": 16, "bolhas": 14, "frio": 30, "faiscas": 12}.get(self.tipo, 0)
        r = self.rng
        self.p = [(r.random(), r.random(), r.random(), r.random()) for _ in range(n)]

    def _no_caminho(self, s):
        for (a, b), comp in zip(zip(self.caminho, self.caminho[1:]), self.trechos):
            if s <= comp:
                f = s / (comp or 1)
                return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            s -= comp
        return self.caminho[-1]

    def desenhar(self, img, t):
        getattr(self, "_" + self.tipo, self._poeira)(img, t)

    def _poeira(self, img, t):
        for a, b, c, d in self.p:
            y = (b * self.h - (2 + 4 * c) * t) % self.h
            x = a * self.w + math.sin(t * (0.6 + d) + a * 9) * 3
            _luz(img, x, y, self.cor or (255, 240, 200), 0.3 + 0.35 * (0.5 + 0.5 * math.sin(t * 3 + d * 7)),
                 lado=1 + (c > 0.7))

    def _brilhos(self, img, t):
        for a, b, c, d in self.p:
            x, y = self.cx + (a - 0.5) * self.raio * 4, self.cy + (b - 0.5) * self.raio * 4
            v = max(0.0, math.sin(t * (2 + 3 * c) + d * 6)) ** 4
            if v > 0.05:
                cor = self.cor or (255, 255, 220)
                _luz(img, x, y, cor, v, lado=2)
                for k in (2, 3):  # raios da estrela
                    for dx, dy in ((k, 0), (-k + 1, 0), (0, k), (0, -k + 1)):
                        _ponto(img, x + dx, y + dy, cor, v * (0.7 if k == 2 else 0.35))

    def _fluxo(self, img, t):
        cor, passo = self.cor or (255, 214, 40), 9.0
        for a, b in zip(self.caminho, self.caminho[1:]):  # trilho apagado por onde a luz corre
            _linha(img, a, b, cor, 0.25)
        s = (t * 30) % passo
        while s < self.total:
            x, y = self._no_caminho(s)
            _luz(img, x - 1, y - 1, cor, 0.9, lado=3)
            _ponto(img, x, y, (255, 255, 255), 0.95)
            s += passo

    def _eletricidade(self, img, t):
        rng = random.Random(int(t / 0.09))
        cor = self.cor or (170, 220, 255)
        pontos, n = [], max(int(self.total / 5), 3)
        for k in range(n + 1):
            x, y = self._no_caminho(self.total * k / n)
            jit = 0 if k in (0, n) else rng.uniform(-3, 3)
            pontos.append((x + jit, y + rng.uniform(-3, 3) * (0 < k < n)))
        alfa = 0.6 + 0.4 * rng.random()
        for a, b in zip(pontos, pontos[1:]):
            for dx, dy, f, c2 in ((-1, 0, 0.5, cor), (1, 0, 0.5, cor), (0, 1, 0.5, cor), (0, 0, 1.0, (255, 255, 255))):
                _linha(img, (a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), c2, alfa * f)

    def _faiscas(self, img, t):
        periodo = 0.55
        rajada = int(t / periodo)
        tt = t - rajada * periodo
        rng = random.Random(rajada * 31 + 7)
        for _ in range(12):
            ang, vel = rng.uniform(0, 2 * math.pi), rng.uniform(18, 42)
            x = self.cx + math.cos(ang) * vel * tt
            y = self.cy + math.sin(ang) * vel * tt + 55 * tt * tt
            vida = 1 - tt / periodo
            _luz(img, x, y, (255, int(140 + 110 * vida), 40), max(vida, 0), lado=2)

    def _vapor(self, img, t):
        for a, b, c, d in self.p:
            vida = (t / 1.6 + a) % 1.0
            x = self.cx + (b - 0.5) * self.raio + math.sin(vida * 6 + d * 5) * 3
            y = self.cy - vida * 32
            _luz(img, x, y, self.cor or (240, 245, 255), 0.7 * (1 - vida), lado=2 + int(vida * 4))

    def _bolhas(self, img, t):
        for a, b, c, d in self.p:
            vida = (t / 1.5 + a) % 1.0
            x = self.cx + (b - 0.5) * self.raio * 1.6 + math.sin(vida * 8 + d * 4) * 2
            _anel(img, x, self.cy - vida * 34, 2 + c * 2.5, self.cor or (190, 235, 255), 0.9 * (1 - vida))

    def _calor(self, img, t):
        cor = self.cor or (255, 140, 40)
        for k in range(5):
            base = self.cx + (k - 2) * self.raio * 0.35
            for j in range(26):
                vida = j / 26
                y = self.cy - j * 1.3
                x = base + math.sin(j * 0.45 - t * 7 + k) * 2.2
                _ponto(img, x, y, cor, 0.85 * (1 - vida) * (0.6 + 0.4 * math.sin(t * 5 + k)), lado=2)

    def _frio(self, img, t):
        for a, b, c, d in self.p:
            y = (b * self.h + (8 + 8 * c) * t) % self.h
            x = a * self.w + math.sin(t * 1.5 + d * 6) * 4
            cor = self.cor or (210, 235, 255)
            _luz(img, x, y, cor, 0.85, lado=1 + (c > 0.5))
            if c > 0.6:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    _ponto(img, x + dx, y + dy, cor, 0.4)

    def _ondas(self, img, t):
        for k in range(4):
            vida = (t / 1.2 + k / 4) % 1.0
            r = 2 + vida * self.raio * 1.6
            for dr in (0, 1):
                _anel(img, self.cx, self.cy, r + dr, self.cor or (150, 255, 200), 0.85 * (1 - vida))


# ---------- onde está o objeto ----------

def objeto(img: np.ndarray, ox: float, oy: float, gw: int, gh: int) -> tuple[float, float, float, float, float, float]:
    """Centro e caixa (frações do quadro aberto) da parte mais desenhada da imagem: onde há mais bordas e
    detalhes. O desenho é imprevisível, então closes, partículas e etiquetas miram aqui em vez de chutar."""
    cinza = img[int(oy):int(oy) + gh, int(ox):int(ox) + gw].mean(axis=2)
    borda = np.abs(np.diff(cinza, axis=0))[:, :-1] + np.abs(np.diff(cinza, axis=1))[:-1, :]
    k = 9  # espalha as bordas para achar regiões, não linhas soltas
    soma = np.cumsum(np.cumsum(np.pad(borda, ((1, 0), (1, 0))), 0), 1)
    dens = soma[k:, k:] - soma[:-k, k:] - soma[k:, :-k] + soma[:-k, :-k]
    dens[: gh // 12] = 0  # ignora o topo (selo e termo) e a faixa de baixo (legenda e pulga)
    dens[-gh // 5:] = 0
    limite = np.quantile(dens, 0.85)
    ys, xs = np.nonzero(dens >= limite)
    if len(xs) == 0:
        return 0.5, 0.48, 0.3, 0.3, 0.7, 0.7
    pesos = dens[ys, xs]
    cx, cy = (np.average(xs, weights=pesos) + k / 2) / gw, (np.average(ys, weights=pesos) + k / 2) / gh
    x0, x1 = np.quantile(xs, [0.1, 0.9]) / gw
    y0, y1 = np.quantile(ys, [0.1, 0.9]) / gh
    return float(cx), float(cy), float(x0), float(y0), float(x1), float(y1)


def _no_objeto(spec: dict, alvo) -> dict:
    """Efeito sem posição definida no roteiro vai para o objeto achado na imagem."""
    cx, cy, x0, y0, x1, y1 = alvo
    spec = dict(spec)
    if spec.get("tipo") in ("fluxo", "eletricidade") and not spec.get("caminho"):
        # desce pelo objeto, de cima para baixo, passando pelo centro
        spec["caminho"] = [[(x0 + cx) / 2, y0], [cx, cy], [(x1 + cx) / 2, y1]]
    elif spec.get("tipo") not in ("poeira", "frio") and "x" not in spec:
        spec["x"], spec["y"] = cx, cy + (0.08 if spec.get("tipo") in ("vapor", "calor", "bolhas") else 0)
        spec.setdefault("raio", max(x1 - x0, 0.15) / 2)
    return spec


# ---------- câmera ----------

def _planos(cena: dict, dur: float, palavras, ox, oy, gw, gh, w, h, indice, alvo) -> list[tuple]:
    """Lista de (início, cx, cy, zoom, direção da deriva). Corta entre quadro aberto e closes."""
    from .sincronia import momento
    meio = (w / 2, h / 2)
    planos = [(0.0, *meio, 1.0, 1 if indice % 2 else -1)]
    focos = cena.get("focos")
    if not focos:  # escolhe sozinha: o objeto achado na imagem, depois um detalhe dele
        cx, cy, x0, y0, x1, y1 = alvo
        focos = []
        if dur >= 3.2:
            focos.append({"x": cx, "y": cy, "zoom": 1.7, "t": dur * 0.42})
        if dur >= 6.5:  # segundo close: a metade de cima ou de baixo do objeto, alternando
            focos.append({"x": cx, "y": y0 + (y1 - y0) * (0.3 if indice % 2 else 0.7), "zoom": 2.2, "t": dur * 0.72})
    ultimo = 0.0
    for k, f in enumerate(focos):
        t = f.get("t")
        if t is None and f.get("em"):
            t = momento(palavras, f["em"])
        if t is None:
            t = dur * (k + 1) / (len(focos) + 1)
        t = max(t, ultimo + 1.1)
        if t > dur - 0.6:
            break
        cx, cy = ox + float(f.get("x", 0.5)) * gw, oy + float(f.get("y", 0.5)) * gh
        planos.append((t, cx, cy, float(f.get("zoom", 2)), -planos[-1][4]))
        ultimo = t
    return planos


def _camera(planos, t, impactos, indice, w, h, gw, gh):
    inicio, cx, cy, z, direcao = next(p for p in reversed(planos) if p[0] <= t)
    dentro = t - inicio
    cx += direcao * dentro * 1.6 / z  # deriva lenta: a imagem nunca para
    cy += math.sin(t * 0.8 + indice) * 1.2 / z
    if inicio > 0:  # cada corte entra com um pequeno empurrão
        z *= 1 + 0.06 * (1 - _suave(dentro / 0.18))
    if indice % 3 == 0:  # entrada da cena: zoom rápido para dentro
        z *= 1 + 0.35 * (1 - _suave(t / 0.3))
    elif indice % 3 == 1:  # entrada: chicote lateral
        cx += gw * 0.35 * (1 - _suave(t / 0.3)) / z
    tremor = 0.0
    for ti in impactos:  # termo e palavra-herói: soco de câmera e tremor
        p = _pulso(t - ti)
        z *= 1 + 0.12 * p
        tremor = max(tremor, p)
    rng = random.Random(int(t * FPS))
    cx += rng.uniform(-2, 2) * tremor / z
    cy += rng.uniform(-2, 2) * tremor / z
    cw, ch = gw / z, gh / z
    x0 = min(max(cx - cw / 2, 0), w - cw)
    y0 = min(max(cy - ch / 2, 0), h - ch)
    return x0, y0, cw, ch


# ---------- etiquetas ----------

def _sprite_rotulo(texto: str, k: int, largura: int, pixel: int) -> Image.Image:
    fonte = ImageFont.truetype(FONTE, int(largura * 0.036))
    caixa = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto.upper(), font=fonte)
    tw, th = caixa[2] - caixa[0], caixa[3] - caixa[1]
    pad, bolinha = int(largura * 0.014), int(largura * 0.016)
    img = Image.new("RGBA", (tw + bolinha + pad * 3, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width - 1, img.height - 1], fill=(255, 255, 255, 255), outline=(32, 32, 32, 255),
                width=max(pixel // 2, 2))
    y = (img.height - bolinha) // 2
    d.rectangle([pad, y, pad + bolinha, y + bolinha], fill=CORES_ROTULO[k % 4] + (255,))
    d.text((pad * 2 + bolinha - caixa[0], pad - caixa[1]), texto.upper(), font=fonte, fill=(32, 32, 32, 255))
    return img


# ---------- vídeo ----------

def gerar(base: Path, depois: Path | None, t_depois: float | None, dur: float, largura: int, altura: int,
          pixel: int, indice: int, cena: dict, palavras: list, rotulos: list[tuple], impactos: list[float],
          destino: Path) -> Path:
    """Grava o clipe da cena viva (mp4 sem áudio). Reaproveita se nada mudou.

    rotulos = [(texto, x, y, segundo, alvo ou None)]; impactos = segundos do termo e da palavra-herói."""
    destino = destino.with_suffix(".mp4")
    assinatura = {"versao": VERSAO, "base": [str(base), base.stat().st_mtime],
                  "depois": [str(depois), depois.stat().st_mtime] if depois else None,
                  "t_depois": round(t_depois or 0, 2), "dur": round(dur, 2), "tela": [largura, altura, pixel],
                  "indice": indice, "rotulos": [[r[0], r[1], r[2], round(r[3], 2), r[4]] for r in rotulos],
                  "impactos": [round(t, 2) for t in impactos],
                  "cena": hashlib.md5(json.dumps({k: cena.get(k) for k in ("focos", "efeitos")},
                                                 sort_keys=True).encode()).hexdigest()}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    gw, gh = largura // pixel, altura // pixel
    imagens = [np.asarray(Image.open(p).convert("RGB"), np.float32) for p in [base] + ([depois] if depois else [])]
    if len(imagens) == 2 and imagens[1].shape != imagens[0].shape:
        imagens[1] = np.asarray(Image.open(depois).convert("RGB").resize(imagens[0].shape[1::-1], Image.NEAREST),
                                np.float32)
    h, w = imagens[0].shape[:2]
    ox, oy = (w - gw) / 2, (h - gh) / 2
    alvo = objeto(imagens[0], ox, oy, gw, gh)
    specs = [_no_objeto(e, alvo) for e in cena.get("efeitos", [])]
    if not any(e.get("tipo") in ("poeira", "frio") for e in specs):
        specs.append({"tipo": "poeira"})  # nenhuma cena fica parada
    sistemas = [_Efeito(e, ox, oy, gw, gh, w, h, indice * 100 + k) for k, e in enumerate(specs) if e.get("tipo") in TIPOS]
    planos = _planos(cena, dur, palavras, ox, oy, gw, gh, w, h, indice, alvo)
    # etiqueta sem alvo no roteiro: fica em cima ou embaixo do objeto, com a linha apontando para ele
    cx, cy, bx0, by0, bx1, by1 = alvo
    ajustados = []
    for k, (texto, fx, fy, ti, ponta) in enumerate(rotulos):
        if not ponta:
            em_cima = k % 2 == 0
            fy = max(by0 - 0.06 - 0.05 * (k // 2), 0.14) if em_cima else min(by1 + 0.06 + 0.05 * (k // 2), 0.72)
            fx = min(max(cx + (-0.12 if k % 3 == 1 else 0.12 if k % 3 == 2 else 0), 0.22), 0.78)
            ponta = [cx + (k - len(rotulos) / 2) * 0.05, by0 + 0.08 if em_cima else by1 - 0.08]
        ajustados.append((texto, fx, fy, ti, ponta))
    rotulos = ajustados
    sprites = [_sprite_rotulo(r[0], k, largura, pixel) for k, r in enumerate(rotulos)]

    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{largura}x{altura}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
                             "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(destino)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(max(int(round(dur * FPS)), 1)):
            t = q / FPS
            depois_ativo = len(imagens) == 2 and t_depois is not None and t >= t_depois
            img = imagens[1 if depois_ativo else 0].copy()
            for s in sistemas:
                s.desenhar(img, t)
            x0, y0, cw, ch = _camera(planos, t, impactos, indice, w, h, gw, gh)
            xs = np.clip((x0 + (np.arange(gw) + 0.5) * cw / gw).astype(int), 0, w - 1)
            ys = np.clip((y0 + (np.arange(gh) + 0.5) * ch / gh).astype(int), 0, h - 1)
            grade = img[ys][:, xs]
            flash = 0.0
            if indice % 3 == 2:  # entrada da cena: clarão
                flash = 0.85 * (1 - _suave(t / 0.22))
            if depois_ativo:
                flash = max(flash, 0.7 * (1 - _suave((t - t_depois) / 0.2)))
            if flash > 0.01:
                grade = grade * (1 - flash) + 255 * flash
            quadro = np.repeat(np.repeat(np.clip(grade, 0, 255).astype(np.uint8), pixel, 0), pixel, 1)
            visiveis = [(k, r) for k, r in enumerate(rotulos) if t >= r[3]]
            if visiveis:
                tela = Image.fromarray(quadro)
                d = ImageDraw.Draw(tela)
                escala = largura / cw

                def na_tela(fx, fy):
                    return ((ox + fx * gw - x0) * escala, (oy + fy * gh - y0) * escala)

                for k, (texto, fx, fy, ti, alvo) in visiveis:
                    lx, ly = na_tela(fx, fy)
                    if not (0 <= lx <= largura and 0 <= ly <= altura):
                        continue
                    # fica entre o termo (topo) e a legenda (baixo), sem sair pelas laterais
                    meia = sprites[k].width / 2 + pixel * 2
                    lx = min(max(lx, meia), largura - meia)
                    ly = min(max(ly, altura * 0.21), altura * 0.6)
                    if alvo:  # linha da etiqueta até a peça, com um ponto que pulsa
                        ax, ay = na_tela(float(alvo[0]), float(alvo[1]))
                        crescer = _suave((t - ti) / 0.25)
                        bx, by = lx + (ax - lx) * crescer, ly + (ay - ly) * crescer
                        d.line([(lx, ly), (bx, by)], fill=(32, 32, 32), width=pixel + 4)
                        d.line([(lx, ly), (bx, by)], fill=(255, 255, 255), width=pixel)
                        r = pixel * (1.6 + 0.5 * math.sin(t * 8))
                        d.rectangle([bx - r, by - r, bx + r, by + r], fill=CORES_ROTULO[k % 4], outline=(32, 32, 32))
                    sprite = sprites[k]
                    e = 0.3 + 0.8 * _suave((t - ti) / 0.12) - 0.1 * _suave((t - ti - 0.12) / 0.1)
                    if abs(e - 1) > 0.01:
                        sprite = sprite.resize((max(int(sprite.width * e), 1), max(int(sprite.height * e), 1)))
                    tela.paste(sprite, (int(lx - sprite.width / 2), int(ly - sprite.height / 2)), sprite)
                quadro = np.asarray(tela)
            proc.stdin.write(quadro.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar a cena viva {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino
