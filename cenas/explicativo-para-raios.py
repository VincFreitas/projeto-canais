"""Cena do para-raios (palco em pixel art): raio, captor no alto, cabo de descida e aterramento."""
import math
import random

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, poeira, polilinha, ret, suave)

SERIE = "PULGA DO SABER · PARA-RAIOS"
MUNDO = (216, 384)

PECAS = {
    "predio": {"titulo": "Prédio", "caixa": (50, 50, 160, 300), "ancora": (105, 160), "conta": False},
    "captor": {"titulo": "Captor (ponta)", "caixa": (90, 30, 120, 70), "ancora": (105, 44)},
    "cabo": {"titulo": "Cabo de descida", "caixa": (130, 50, 180, 300), "ancora": (154, 180)},
    "aterramento": {"titulo": "Aterramento", "caixa": (120, 290, 200, 360), "ancora": (160, 330)},
}

CEU, NUVEM, NUVEM_ESC = (24, 26, 50), (90, 94, 120), (60, 62, 84)
PAREDE, TELHADO, CONTORNO = (200, 150, 110), (150, 70, 60), (24, 20, 26)
TERRA, GRAMA, RAIO = (110, 76, 50), (70, 140, 70), (230, 240, 255)


def _cenario(img, T, clarao):
    ret(img, 0, 0, 216, 300, CEU)
    if clarao > 0:
        ret(img, 0, 0, 216, 300, (200, 210, 255), 0.35 * clarao)
    for k in range(5):  # nuvens carregadas
        circulo(img, 20 + k * 44, 26 + (k % 2) * 6, 26, NUVEM_ESC)
        circulo(img, 30 + k * 44, 20, 20, NUVEM)
    rng = random.Random(4)
    for _ in range(40):  # chuva
        x, f = rng.uniform(0, 216), rng.random()
        y = 50 + ((T * 160 / 250 + f) % 1.0) * 250
        ret(img, x, y, x + 1, y + 5, (140, 160, 210), 0.6)
    ret(img, 0, 296, 216, 302, GRAMA)
    ret(img, 0, 302, 216, 384, TERRA)
    for y in range(310, 384, 12):
        ret(img, 0, y, 216, y + 1, (96, 66, 44))
    poeira(img, T, n=10, cor=(200, 200, 220))


def _predio(img, fogo, T):
    ret(img, 60, 140, 150, 296, PAREDE)
    moldura(img, 60, 140, 150, 296, CONTORNO, 2)
    ret(img, 88, 74, 122, 140, PAREDE)  # torre
    moldura(img, 88, 74, 122, 140, CONTORNO, 2)
    for k in range(18):  # telhado pontudo
        ret(img, 105 - k, 56 + k, 105 + k, 57 + k, TELHADO)
    for x, y in ((72, 170), (120, 170), (72, 230), (120, 230), (98, 96)):
        ret(img, x, y, x + 14, y + 22, (255, 220, 120))
        moldura(img, x, y, x + 14, y + 22, CONTORNO)
    ret(img, 96, 256, 114, 296, (100, 60, 40))
    if fogo > 0:
        for k, (x, y) in enumerate(((78, 150), (130, 200), (100, 260))):
            for j in range(6):
                fase = (T * 3 + j / 6 + k * 0.3) % 1.0
                luz(img, x + math.sin(j * 2) * 4, y - fase * 16, (255, int(220 - 140 * fase), 40),
                    fogo * (1 - fase), lado=3)


def _raio(img, alvo, T, semente):
    """Zigue-zague da nuvem até o alvo, sorteado de novo a cada décimo de segundo."""
    rng = random.Random(int(T * 10) + semente)
    pontos = [(alvo[0] + rng.uniform(-40, 40), 36)]
    n = 7
    for k in range(1, n):
        f = k / n
        pontos.append((pontos[0][0] + (alvo[0] - pontos[0][0]) * f + rng.uniform(-8, 8), 36 + (alvo[1] - 36) * f))
    pontos.append(alvo)
    polilinha(img, pontos, (150, 170, 255), esp=4)
    polilinha(img, pontos, RAIO, esp=2)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    pisca = (T * 2.2) % 1.0 < 0.18  # o raio cai em pulsos
    clarao = 1.0 if pisca and c in (1, 5, 6, 9, 10) else 0.0
    _cenario(img, T, clarao)
    fogo = 1.0 if c == 2 or (c == 10 and ctx.acao("ruim") is not None) else 0.0
    _predio(img, fogo, T)
    cap = ctx.peca("captor")
    if cap > 0:
        ret(img, 104, 34 + (1 - cap) * -40, 107, 58, (200, 204, 214))
        luz(img, 104, 32 + (1 - cap) * -40, (255, 255, 255), 0.9)
    cabo = ctx.peca("cabo")
    if cabo > 0:
        polilinha(img, [(106, 50), (154, 72), (154, 296), (160, 312)], (180, 120, 60), esp=3, progresso=cabo)
    ater = ctx.peca("aterramento")
    if ater > 0:
        for x in (144, 160, 176):
            ret(img, x, 312, x + 3, 312 + 40 * ater, (200, 204, 214))
        polilinha(img, [(144, 312), (178, 312)], (180, 120, 60), esp=3)
    if c == 1 and pisca:  # sem para-raios: o raio entra pelo prédio
        _raio(img, (105, 58), T, 1)
        polilinha(img, [(105, 58), (96, 140), (110, 200), (92, 296)], (255, 255, 200), esp=2)
    if c in (5, 6) and pisca:
        _raio(img, (105, 34), T, 2)
    if c == 4 and ctx.acao("franklin") is not None:  # Franklin achava que a ponta descarregava a nuvem aos poucos
        for k in range(10):
            fase = (T * 0.8 + k / 10) % 1.0
            luz(img, 105 + math.sin(k) * 10, 36 + fase * -20 + 20, (180, 200, 255), 0.6 * (1 - fase))
        ret(img, 20, 270, 26, 296, (60, 60, 80))  # Franklin pequeno com a pipa
        circulo(img, 23, 266, 4, (240, 196, 150))
        linha(img, (26, 272), (50, 200), (230, 230, 230))
        ret(img, 46, 192, 56, 202, (220, 60, 60))
    if c in (9, 12, 11) and cabo > 0 and ater > 0:
        if pisca:
            _raio(img, (105, 34), T, 3)
        fluxo(img, [(106, 40), (154, 72), (154, 296), (160, 312)], ctx.T, (255, 255, 180), velocidade=120, passo=8)
        for k in range(12):  # a energia se espalha na terra
            a = math.pi * (0.05 + 0.9 * k / 11)
            fase = (T * 1.5 + k / 12) % 1.0
            luz(img, 160 + math.cos(a) * fase * 50, 330 + math.sin(a) * fase * 30, (255, 240, 140), 1 - fase)
    if c == 10 and ctx.acao("ruim") is not None:  # cabo partido: o raio pula para dentro do prédio
        ret(img, 150, 200, 160, 214, CEU)
        if pisca:
            _raio(img, (105, 34), T, 4)
            polilinha(img, [(154, 200), (140, 206), (120, 214)], (255, 255, 200), esp=2)
    if c == 11:
        brilhos(img, 50, 40, 200, 300, T, n=16, semente=11)
