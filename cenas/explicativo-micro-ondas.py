"""Cena do micro-ondas (palco em pixel art): do fogo às moléculas de água girando, e a caixa montada em volta do prato."""
import math
import random

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ondas_calor, ponto, poeira, ret, suave,
                           vapor)

SERIE = "PULGA DO SABER · MICRO-ONDAS"
MUNDO = (216, 384)

PECAS = {
    "fogao": {"titulo": "Fogão", "caixa": (10, 220, 100, 300), "ancora": (50, 250), "conta": False},
    "comida": {"titulo": "Comida", "caixa": (70, 210, 150, 262), "ancora": (110, 236), "conta": False},
    "molecula": {"titulo": "Molécula", "caixa": (60, 70, 160, 170), "ancora": (110, 120), "conta": False},
    "magnetron": {"titulo": "Magnetron", "caixa": (150, 170, 210, 270), "ancora": (180, 214)},
    "caixa": {"titulo": "Caixa de metal", "caixa": (30, 160, 210, 290), "ancora": (40, 200)},
    "porta": {"titulo": "Porta com grade", "caixa": (34, 166, 150, 286), "ancora": (92, 226)},
    "prato": {"titulo": "Prato giratório", "caixa": (60, 230, 160, 280), "ancora": (110, 262)},
}

PAREDE, BANCADA = (232, 196, 140), (150, 96, 60)
METAL, METAL_ESC, CONTORNO = (210, 214, 222), (140, 146, 160), (30, 30, 40)
QUENTE, AZUL = (255, 120, 40), (90, 170, 240)


def _cenario(img, T):
    ret(img, 0, 0, 216, 296, PAREDE)
    for y in range(0, 296, 12):
        for x in range((y // 12 % 2) * 6, 216, 12):
            ret(img, x, y, x + 11, y + 11, (240, 208, 156))
    ret(img, 0, 290, 216, 300, (200, 140, 90))
    ret(img, 0, 300, 216, 384, BANCADA)
    for y in range(312, 384, 14):
        ret(img, 0, y, 216, y + 1, (120, 74, 44))
    poeira(img, T, n=20)


def _prato_comida(img, ctx, T, quente, giro):
    cx, cy = 110, 268
    ret(img, cx - 46, cy - 4, cx + 46, cy + 6, (245, 245, 250))  # prato visto de lado
    moldura(img, cx - 46, cy - 4, cx + 46, cy + 6, CONTORNO)
    if giro is not None:  # marquinha que gira com o prato
        x = cx + math.cos(giro) * 40
        ret(img, x - 2, cy - 2, x + 2, cy + 4, (220, 60, 60))
    ret(img, cx - 30, cy - 22, cx + 30, cy - 4, (200, 110, 60))  # comida
    ret(img, cx - 26, cy - 26, cx + 20, cy - 20, (230, 160, 80))
    moldura(img, cx - 30, cy - 22, cx + 30, cy - 4, CONTORNO)
    if quente:
        vapor(img, cx, cy - 26, T, n=10, subida=36, espalha=50, semente=4)


def _fogo(img, ctx, T):
    if ctx.cena > 2:
        return False
    ret(img, 14, 286, 96, 300, (60, 60, 70))
    for k in range(6):
        luz(img, 22 + k * 11, 280 - (int(T * 14 + k) % 4), (80, 150, 255), 0.95)
    ret(img, 24, 262, 86, 278, (60, 60, 66))  # frigideira
    ret(img, 86, 266, 112, 270, (60, 60, 66))
    ret(img, 32, 254, 78, 262, (200, 110, 60))
    if ctx.cena == 2 and ctx.acao("espera") is not None:
        circulo(img, 170, 120, 18, (250, 250, 250))  # relógio girando
        circulo(img, 170, 120, 18, CONTORNO, cheio=False)
        a = T * 6
        linha(img, (170, 120), (170 + math.cos(a) * 14, 120 + math.sin(a) * 14), CONTORNO, esp=2)
        ondas_calor(img, 54, 252, T, largura=40, altura=20)
    return True


def _molecula(img, x, y, ang, r, cor_o=(220, 60, 60)):
    for s in (-1, 1):  # dois hidrogênios
        a = ang + s * 0.9
        circulo(img, x + math.cos(a) * r * 1.3, y + math.sin(a) * r * 1.3, r * 0.6, (245, 245, 250))
        circulo(img, x + math.cos(a) * r * 1.3, y + math.sin(a) * r * 1.3, r * 0.6, CONTORNO, cheio=False)
    circulo(img, x, y, r, cor_o)
    circulo(img, x, y, r, CONTORNO, cheio=False)


def _bolha_molecula(img, ctx, T):
    c = ctx.cena
    if c not in (3, 4, 5, 6):
        return
    abre = ctx.acao({3: "agua", 4: "molecula", 5: "onda", 6: "giram"}[c])
    if c == 3 and abre is None:
        return
    r = 50 * (suave(abre / 0.35) if c == 3 and abre is not None else 1.0)
    circulo(img, 110, 130, r + 2, CONTORNO)
    circulo(img, 110, 130, r, (230, 244, 255))
    linha(img, (96, 180), (106, 216), (230, 244, 255), esp=3)
    if r < 44:
        return
    if c in (3,):
        for k in range(8):
            fase = (T * 0.6 + k / 8) % 1.0
            luz(img, 80 + (k * 7) % 60, 100 + (k * 13) % 60 - math.sin(fase * 6) * 3, AZUL, 0.9, lado=4)
    elif c == 4:
        _molecula(img, 110, 130, -math.pi / 2 + 0.1 * math.sin(T * 2), 12)
        ret(img, 104, 108, 116, 111, (255, 220, 60))  # sinal de menos em cima? (lado negativo)
        ret(img, 90, 150, 96, 152, CONTORNO)
        ret(img, 124, 150, 130, 152, CONTORNO)
        ret(img, 126, 148, 128, 154, CONTORNO)
    else:
        rng = random.Random(5)
        for k in range(7):
            x, y = 80 + rng.random() * 60, 104 + rng.random() * 52
            if c == 5:
                ang = math.pi / 2 * (1 if math.sin(T * 18) > 0 else -1)  # viram juntas com a onda
            else:
                ang = T * (6 + k) + k
            calor = suave((abre or 0) / 3.0) if c == 6 else 0
            cor = tuple(int((220, 60, 60)[j] + ((255, 140, 40)[j] - (220, 60, 60)[j]) * calor) for j in range(3))
            _molecula(img, x, y, ang, 5, cor)
        if c == 6:
            ondas_calor(img, 110, 160, T, largura=60, altura=20, alfa=0.6)


def _magnetron(img, ctx, T, ligado):
    p = ctx.peca("magnetron")
    if p <= 0:
        return
    y = 190 + (1 - p) * -80
    ret(img, 160, y, 200, y + 50, (90, 90, 100))
    for k in range(6):  # aletas
        ret(img, 156, y + 4 + k * 8, 204, y + 7 + k * 8, (130, 130, 140))
    circulo(img, 180, y + 25, 9, (190, 120, 60))
    moldura(img, 160, y, 200, y + 50, CONTORNO)
    ret(img, 146, y + 20, 160, y + 30, METAL_ESC)  # guia de ondas
    if ligado:
        for k in range(4):
            fase = (T * 1.4 + k / 4) % 1.0
            x = 146 - fase * 100
            for dy in range(-12, 13, 3):
                ponto(img, x + math.sin(dy * 0.5 + T * 10) * 2, y + 25 + dy, (150, 255, 200), 0.8 * (1 - fase),
                      lado=2)


def _caixa(img, ctx, T, ligado):
    p = ctx.peca("caixa")
    if p <= 0:
        return
    for k, (a, b) in enumerate((((36, 170), (206, 170)), ((36, 170), (36, 288)), ((206, 170), (206, 288)),
                                ((36, 288), (206, 288)))):
        f = min(max(p * 4 - k, 0), 1)
        linha(img, a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), METAL, esp=6)
    moldura(img, 33, 167, 209, 291, CONTORNO)
    if p >= 1 and ligado and ctx.cena == 8:  # ondas batendo nas paredes e voltando
        fluxo(img, [(150, 200), (40, 230), (150, 280), (40, 190), (150, 240)], ctx.T, (150, 255, 200),
              velocidade=60, passo=10)


def _porta(img, ctx, T):
    p = ctx.peca("porta")
    if p <= 0:
        return
    ret(img, 40, 174, 150 * p + 40 * (1 - p), 284, (40, 44, 54), 0.55)  # vidro escuro
    for y in range(178, 282, 4):  # grade de furinhos
        for x in range(44, int(146 * p + 44 * (1 - p)), 4):
            ponto(img, x, y, (20, 22, 30), 0.8)
    moldura(img, 38, 172, int(152 * p + 38 * (1 - p)), 286, CONTORNO, 2)
    ret(img, 156, 180, 202, 280, (60, 64, 74))  # painel
    for k in range(6):
        ret(img, 164 + (k % 2) * 18, 196 + (k // 2) * 18, 176 + (k % 2) * 18, 206 + (k // 2) * 18, (200, 200, 210))
    ret(img, 162, 184, 196, 192, (30, 200, 120))  # visor


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    fogo = _fogo(img, ctx, T)
    ligado = c >= 7
    giro = T * 2 if ctx.peca("prato") > 0 else None
    if not fogo:
        _prato_comida(img, ctx, T, quente=c >= 10, giro=giro)
    if c >= 10:  # luz acesa lá dentro
        ret(img, 40, 174, 150, 284, (255, 236, 160), 0.18 + 0.04 * math.sin(T * 4))
    _magnetron(img, ctx, T, ligado)
    _caixa(img, ctx, T, ligado)
    _porta(img, ctx, T)
    if c == 11:  # pontos quentes e frios que o prato giratório espalha
        for k, (x, cor) in enumerate(((80, QUENTE), (110, AZUL), (140, QUENTE))):
            luz(img, x + math.sin(T * 2 + k) * 10, 244, cor, 0.9, lado=3)
    _bolha_molecula(img, ctx, T)
    if c == 12:
        brilhos(img, 30, 150, 210, 300, T, n=16, semente=12)
