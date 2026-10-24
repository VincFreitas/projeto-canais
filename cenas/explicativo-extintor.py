"""Cena do extintor (palco em pixel art, em corte): triângulo do fogo, pó, gás apertado, pino, rótulo e uso."""
import math
import random

from darkops.palco import (brilhos, circulo, linha, luz, moldura, poeira, polilinha, ret, suave, vapor)

SERIE = "PULGA DO SABER · EXTINTOR"
MUNDO = (216, 384)

PECAS = {
    "fogo": {"titulo": "Fogo", "caixa": (10, 220, 90, 300), "ancora": (40, 262), "conta": False},
    "cilindro": {"titulo": "Cilindro com pó", "caixa": (110, 110, 170, 296), "ancora": (140, 240)},
    "gas": {"titulo": "Gás apertado", "caixa": (110, 96, 172, 170), "ancora": (140, 140)},
    "pino": {"titulo": "Pino de trava", "caixa": (110, 90, 160, 126), "ancora": (128, 108)},
    "rotulo": {"titulo": "Rótulo ABC", "caixa": (110, 170, 170, 240), "ancora": (140, 204)},
}

PAREDE, PISO, CONTORNO = (220, 226, 236), (170, 176, 190), (26, 24, 32)
VERMELHO, PO, GAS = (210, 40, 40), (250, 214, 60), (120, 190, 255)


def _cenario(img, T):
    ret(img, 0, 0, 216, 296, PAREDE)
    for x in range(0, 216, 30):
        ret(img, x, 0, x + 1, 296, (206, 212, 224))
    ret(img, 0, 296, 216, 384, PISO)
    for x in range(0, 216, 24):
        ret(img, x, 296, x + 1, 384, (150, 156, 170))
    poeira(img, T, n=16)


def _chamas(img, x, y, T, forca, larg=30):
    if forca <= 0:
        return
    rng = random.Random(int(T * 12))
    for k in range(int(18 * forca)):
        f = rng.random()
        h = rng.uniform(6, 34) * forca
        xx = x + rng.uniform(-larg / 2, larg / 2) * (1 - f * 0.5)
        cor = (255, int(240 - 160 * f), 40)
        ret(img, xx, y - h * f, xx + 3, y - h * f + 4, cor, 0.9)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    ret(img, 20, 266, 60, 296, (90, 90, 100))  # lixeira
    moldura(img, 20, 266, 60, 296, CONTORNO)
    forca = 1.0
    if c == 2 and ctx.acao("agua") is not None:
        forca = 1 - suave(ctx.acao("agua") / 1.2)
        polilinha(img, [(90, 200), (60, 240), (40, 262)], (100, 170, 240), esp=4)
        if forca < 0.5:
            vapor(img, 40, 262, T, n=12, subida=40, espalha=30, semente=2)
    if c == 3 and ctx.acao("oleo") is not None:  # óleo: a água espalha o fogo
        ret(img, 14, 252, 70, 262, (60, 60, 66))
        forca = 1 + suave(ctx.acao("oleo") / 0.5)
        for k in range(6):
            luz(img, 80 + k * 6, 200 + math.sin(T * 20 + k) * 6, (255, 255, 140), 0.8)  # choque
    if c == 10 and ctx.acao("usar") is not None:
        forca = 1 - suave((ctx.acao("usar") - 1.0) / 2.5)
    if c in (11, 12):
        forca = 0.0
    _chamas(img, 40, 266, T, forca, larg=36 if forca <= 1 else 60)
    if c == 1 and ctx.acao("triangulo") is not None:  # triângulo do fogo
        f = suave(ctx.acao("triangulo") / 0.6)
        pts = [(40, 150), (10, 210), (70, 210), (40, 150)]
        polilinha(img, pts, (255, 160, 40), esp=3, progresso=f)
    cil = ctx.peca("cilindro")
    if cil > 0:
        y = (1 - cil) * -80
        ret(img, 116, 126 + y, 164, 292 + y, VERMELHO)
        moldura(img, 116, 126 + y, 164, 292 + y, CONTORNO, 2)
        ret(img, 122, 170 + y, 158, 286 + y, PO)  # o pó (em corte)
        for k in range(30):
            ret(img, 124 + (k * 7) % 32, 176 + (k * 13) % 104 + y, 126 + (k * 7) % 32, 178 + (k * 13) % 104 + y,
                (230, 180, 40))
        ret(img, 128, 112 + y, 152, 126 + y, (60, 60, 70))  # cabeça com o gatilho
        polilinha(img, [(152, 116 + y), (176, 120 + y), (180, 160 + y), (100, 190 + y)], (40, 40, 48), esp=4)
        ret(img, 94, 186 + y, 104, 194 + y, (40, 40, 48))  # bico
    gas = ctx.peca("gas")
    if gas > 0:
        for k in range(18):  # gás apertado em cima do pó, empurrando
            x = 124 + (k * 11) % 34 + math.sin(T * 8 + k) * 1.5
            yy = 132 + (k * 7) % 34 + math.cos(T * 9 + k) * 1.5
            luz(img, x, yy, GAS, gas, lado=2)
        circulo(img, 158, 106, 9 * gas, (245, 245, 250))  # manômetro
        circulo(img, 158, 106, 9 * gas, CONTORNO, cheio=False)
        linha(img, (158, 106), (164, 102), (60, 160, 60), esp=2)
    pino = ctx.peca("pino")
    if pino > 0 and not (c == 10 and ctx.acao("usar") is not None and ctx.acao("usar") > 0.3):
        ret(img, 120, 106, 134, 110, (220, 220, 230), pino)
        circulo(img, 116, 108, 5 * pino, (220, 220, 230))
        circulo(img, 116, 108, 3 * pino, PAREDE)
        ret(img, 132, 104, 136, 112, (240, 200, 60), pino)  # lacre
    rot = ctx.peca("rotulo")
    if rot > 0:
        ret(img, 120, 196, 160, 232, (250, 250, 250), rot)
        moldura(img, 120, 196, 160, 232, CONTORNO)
        for k, cor in enumerate(((60, 160, 60), (220, 60, 60), (60, 110, 220))):  # A, B, C
            ret(img, 124 + k * 12, 202, 134 + k * 12, 214, cor, rot)
            ret(img, 126 + k * 12, 204, 132 + k * 12, 212, (255, 255, 255), rot * 0.6)
    if c == 8 and ctx.acao("co2") is not None:  # extintor de gás carbônico: nuvem branca gelada
        ret(img, 176, 160, 204, 292, (40, 40, 48))
        moldura(img, 176, 160, 204, 292, CONTORNO)
        vapor(img, 170, 170, T, n=20, subida=60, espalha=40, cor=(240, 250, 255), semente=8)
        brilhos(img, 150, 100, 210, 180, T, n=8, cor=(200, 230, 255), semente=8)
    if c == 10 and ctx.acao("usar") is not None and ctx.acao("usar") > 0.8:  # jato varrendo a base do fogo
        ang = math.sin(T * 3) * 0.25
        for k in range(30):
            f = ((T * 2 + k / 30) % 1.0)
            x = 96 - f * 70
            y = 190 + f * (76 + math.sin(ang) * 40)
            luz(img, x + math.sin(k) * f * 8, y, PO, 0.9 * (1 - f * 0.5), lado=2 + int(f * 3))
    if c == 11 and ctx.acao("saida") is not None:  # placa de saída acendendo
        ret(img, 20, 60, 80, 84, (40, 170, 90), 0.6 + 0.4 * math.sin(T * 5))
        moldura(img, 20, 60, 80, 84, CONTORNO)
        ret(img, 28, 66, 40, 78, (255, 255, 255))
        polilinha(img, [(46, 72), (70, 72)], (255, 255, 255), esp=3)
    if c == 12:
        brilhos(img, 20, 90, 200, 290, T, n=16, semente=12)
