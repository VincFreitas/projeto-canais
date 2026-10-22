"""Animações programadas (motion graphics) desenhadas quadro a quadro com Pillow.

Uma cena do roteiro ganha uma animação com o campo "animacao":

  {"tipo": "contador", "ate": 243, "sufixo": " dias", "rotulo": "1 dia em Vênus"}
  {"tipo": "comparacao", "itens": [{"rotulo": "Dia", "valor": 243}, {"rotulo": "Ano", "valor": 225}],
   "unidade": "dias", "titulo": "Vênus"}
  {"tipo": "linha_do_tempo", "marcos": [{"valor": -2560, "texto": "2560 a.C.", "rotulo": "Pirâmide"}, ...]}
  {"tipo": "icones", "simbolo": "coracao", "quantidade": 3, "rotulo": "3 corações"}

O conteúdo fica entre 12% e 62% da altura; a legenda da cena vai para baixo.
O vídeo sai com fundo próprio (gradiente escuro com partículas), sem banco de imagens.
"""
import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .render import FFMPEG, FPS

AMARELO = (255, 212, 0)
BRANCO = (245, 245, 245)
CINZA = (150, 150, 165)
CORES = [(255, 212, 0), (0, 200, 255), (255, 95, 120), (120, 230, 140)]
FONTE_FORTE = "C:/Windows/Fonts/ariblk.ttf"
FONTE = "C:/Windows/Fonts/arialbd.ttf"
VERSAO = 3  # mude para refazer as animações em cache


def _fonte(caminho: str, tamanho: int):
    try:
        return ImageFont.truetype(caminho, tamanho)
    except OSError:
        return ImageFont.load_default()


def _suave(x: float) -> float:
    """Ease-out cúbico de 0 a 1."""
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _mola(x: float) -> float:
    """Entrada com leve exagero (passa de 1 e volta), para os elementos 'pularem'."""
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


def _numero(v: float, casas: int = 0) -> str:
    texto = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def _centralizar(d: ImageDraw.ImageDraw, texto: str, fonte, cx: float, y: float, cor, sombra=True,
                 max_largura: float | None = None) -> None:
    """Texto centrado em cx; encolhe a fonte até caber (padrão: 90% da tela) e não sai pela borda."""
    largura_tela = d._image.size[0]
    limite = max_largura or largura_tela * 0.9
    caixa = d.textbbox((0, 0), texto, font=fonte)
    while caixa[2] - caixa[0] > limite and getattr(fonte, "size", 0) > 12:
        fonte = _fonte(fonte.path, int(fonte.size * 0.92))
        caixa = d.textbbox((0, 0), texto, font=fonte)
    largura = caixa[2] - caixa[0]
    margem = largura_tela * 0.05  # só a tela limita a posição; max_largura limita o tamanho
    x = min(max(cx - largura / 2, margem), largura_tela - margem - largura)
    if sombra:
        d.text((x + 4, y + 5), texto, font=fonte, fill=(0, 0, 0))
    d.text((x, y), texto, font=fonte, fill=cor)


class _Fundo:
    """Gradiente escuro azulado + partículas que sobem devagar (pré-calculado)."""

    def __init__(self, largura: int, altura: int, semente: int):
        self.base = Image.new("RGB", (largura, altura))
        d = ImageDraw.Draw(self.base)
        for y in range(altura):
            k = y / altura
            d.line([(0, y), (largura, y)], fill=(int(14 + 18 * k), int(16 + 10 * k), int(38 + 22 * (1 - k))))
        rng = random.Random(semente)
        self.particulas = [(rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(2, 6),
                            rng.uniform(15, 45)) for _ in range(40)]
        self.altura = altura

    def quadro(self, t: float) -> Image.Image:
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, r, vel in self.particulas:
            yy = (y - vel * t) % self.altura
            d.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 255, 255, 40))
        return img


def _contador(d, w, h, t, dur, a):
    ate, de = float(a.get("ate", 100)), float(a.get("de", 0))
    casas = int(a.get("casas", 0))
    p = _suave(t / max(dur * 0.55, 0.6))
    valor = de + (ate - de) * p
    escala = 1 + 0.06 * math.sin(min(t / 0.25, 1) * math.pi)
    _centralizar(d, a.get("prefixo", "") + _numero(valor, casas) + a.get("sufixo", ""),
                 _fonte(FONTE_FORTE, int(w * 0.19 * escala)), w / 2, h * 0.27, AMARELO)
    if a.get("rotulo"):
        _centralizar(d, a["rotulo"], _fonte(FONTE, int(w * 0.065)), w / 2, h * 0.43, BRANCO)


def _comparacao(d, w, h, t, dur, a):
    itens = a.get("itens", [])[:3]
    if not itens:
        return
    maior = max(float(i["valor"]) for i in itens) or 1
    if a.get("titulo"):
        _centralizar(d, a["titulo"], _fonte(FONTE_FORTE, int(w * 0.075)), w / 2, h * 0.12, BRANCO)
    base_y, topo_max = h * 0.56, h * 0.30
    largura_barra = w * 0.62 / len(itens)
    espaco = (w - largura_barra * len(itens)) / (len(itens) + 1)
    for k, item in enumerate(itens):
        p = _suave((t - 0.25 * k) / max(dur * 0.45, 0.6))
        alto = (base_y - topo_max) * float(item["valor"]) / maior * p
        x0 = espaco + k * (largura_barra + espaco)
        cor = CORES[k % len(CORES)]
        d.rounded_rectangle([x0, base_y - alto, x0 + largura_barra, base_y], radius=18, fill=cor)
        cx = x0 + largura_barra / 2
        rotulo_valor = (_numero(float(item["valor"]) * p, int(a.get("casas", 0)))
                        + (f" {a['unidade']}" if a.get("unidade") else ""))
        coluna = largura_barra + espaco * 0.8
        _centralizar(d, rotulo_valor, _fonte(FONTE_FORTE, int(w * 0.052)), cx, base_y - alto - w * 0.08, BRANCO,
                     max_largura=coluna)
        _centralizar(d, item["rotulo"], _fonte(FONTE, int(w * 0.06)), cx, base_y + h * 0.015, cor,
                     max_largura=coluna)


def _linha_do_tempo(d, w, h, t, dur, a):
    marcos = a.get("marcos", [])[:5]
    if len(marcos) < 2:
        return
    valores = [float(m["valor"]) for m in marcos]
    vmin, vmax = min(valores), max(valores)
    x0, x1, y = w * 0.14, w * 0.86, h * 0.38
    revelar = max(dur * 0.7, 0.8)
    p = min(t / revelar, 1.0)
    d.line([(x0, y), (x0 + (x1 - x0) * p, y)], fill=CINZA, width=10)
    fonte_texto = _fonte(FONTE_FORTE, int(w * 0.05))
    fonte_rotulo = _fonte(FONTE, int(w * 0.042))
    for k, m in enumerate(marcos):
        pos = (float(m["valor"]) - vmin) / ((vmax - vmin) or 1)
        if pos > p + 1e-6:
            continue
        cx = x0 + (x1 - x0) * pos
        e = _mola((t - pos * revelar) / 0.3)
        r = w * 0.028 * e
        cor = CORES[k % len(CORES)]
        d.ellipse([cx - r, y - r, cx + r, y + r], fill=cor)
        acima = k % 2 == 0
        ty = y - h * 0.11 if acima else y + h * 0.04
        cx_texto = min(max(cx, w * 0.18), w * 0.82)  # texto nunca sai da tela
        _centralizar(d, m.get("texto", ""), fonte_texto, cx_texto, ty, cor)
        _centralizar(d, m.get("rotulo", ""), fonte_rotulo, cx_texto, ty + w * 0.065, BRANCO)


def _forma(d, simbolo: str, cx: float, cy: float, r: float, cor) -> None:
    if simbolo == "coracao":
        d.ellipse([cx - r, cy - r * 0.75, cx, cy + r * 0.25], fill=cor)
        d.ellipse([cx, cy - r * 0.75, cx + r, cy + r * 0.25], fill=cor)
        d.polygon([(cx - r * 0.97, cy - r * 0.1), (cx + r * 0.97, cy - r * 0.1), (cx, cy + r)], fill=cor)
    elif simbolo == "estrela":
        pontos = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            raio = r if i % 2 == 0 else r * 0.45
            pontos.append((cx + raio * math.cos(ang), cy + raio * math.sin(ang)))
        d.polygon(pontos, fill=cor)
    elif simbolo == "cubo":
        d.rounded_rectangle([cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8], radius=r * 0.15, fill=cor)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)


def _icones(d, w, h, t, dur, a):
    n = max(1, min(int(a.get("quantidade", 3)), 12))
    simbolo = a.get("simbolo", "circulo")
    cor = tuple(a["cor"]) if a.get("cor") else (235, 60, 80) if simbolo == "coracao" else AMARELO
    colunas = min(n, 4)
    linhas = math.ceil(n / colunas)
    r = w * (0.11 if n <= 4 else 0.075)
    for k in range(n):
        lin, col = divmod(k, colunas)
        nesta = min(colunas, n - lin * colunas)
        cx = w / 2 + (col - (nesta - 1) / 2) * r * 2.6
        cy = h * 0.32 + (lin - (linhas - 1) / 2) * r * 2.5
        entrada = _mola((t - 0.18 * k) / 0.35)
        if entrada <= 0:
            continue
        batida = 1 + 0.08 * max(0.0, math.sin((t - 0.18 * k) * 2 * math.pi * 1.2)) ** 6
        _forma(d, simbolo, cx, cy, r * entrada * batida, cor)
    if a.get("rotulo"):
        _centralizar(d, a["rotulo"], _fonte(FONTE_FORTE, int(w * 0.075)), w / 2, h * 0.52, BRANCO)


TIPOS = {"contador": _contador, "comparacao": _comparacao, "linha_do_tempo": _linha_do_tempo,
         "icones": _icones}


def gerar(animacao: dict, duracao: float, largura: int, altura: int, destino: Path) -> Path:
    """Desenha a animação e grava um mp4 sem áudio. Reaproveita se nada mudou."""
    tipo = animacao.get("tipo")
    if tipo not in TIPOS:
        raise SystemExit(f"animação '{tipo}' não existe. Opções: {', '.join(TIPOS)}")
    assinatura = {"animacao": animacao, "duracao": round(duracao, 2), "tamanho": [largura, altura],
                  "versao": VERSAO}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    fundo = _Fundo(largura, altura, hash(json.dumps(animacao, sort_keys=True)) & 0xFFFF)
    quadros = max(int(duracao * FPS), 1)
    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-s", f"{largura}x{altura}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                             str(destino)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(quadros):
            t = q / FPS
            img = fundo.quadro(t)
            TIPOS[tipo](ImageDraw.Draw(img, "RGBA"), largura, altura, t, duracao, animacao)
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar a animação {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino
