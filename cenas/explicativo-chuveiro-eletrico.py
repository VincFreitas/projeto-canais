"""Cena do chuveiro elétrico (palco em pixel art): da panela de água quente ao chuveiro com diafragma e chave."""
import math
import random

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ondas_calor, ponto, poeira, polilinha,
                           ret, suave, vaivem, vapor)

SERIE = "PULGA DO SABER · CHUVEIRO"
MUNDO = (216, 384)

PECAS = {
    "panela": {"titulo": "Panela", "caixa": (10, 220, 100, 298), "ancora": (46, 246), "conta": False},
    "chuveiro": {"titulo": "Chuveiro", "caixa": (60, 50, 160, 200), "ancora": (108, 90)},
    "resistencia": {"titulo": "Resistência", "caixa": (76, 136, 140, 172), "ancora": (108, 154)},
    "diafragma": {"titulo": "Diafragma", "caixa": (76, 96, 140, 134), "ancora": (100, 118)},
    "chave": {"titulo": "Chave verão/inverno", "caixa": (130, 96, 176, 140), "ancora": (156, 116)},
}

AZULEJO, REJUNTE = (120, 200, 200), (150, 222, 220)
PISO = (230, 236, 240)
METAL, METAL_ESC, CONTORNO = (220, 224, 232), (150, 156, 170), (34, 36, 48)
AGUA, AGUA_CLARA = (90, 170, 240), (190, 230, 255)
QUENTE, BRASA = (255, 120, 40), (255, 210, 90)
COBRE = (196, 112, 52)


def _cenario(img, T):
    ret(img, 0, 0, 216, 300, AZULEJO)
    for y in range(10, 300, 14):
        ret(img, 0, y, 216, y + 1, REJUNTE)
    for x in range(6, 216, 14):
        ret(img, x, 0, x + 1, 300, REJUNTE)
    ret(img, 0, 300, 216, 384, PISO)
    for x in range(0, 216, 18):
        ret(img, x, 300, x + 1, 384, (200, 206, 214))
    ret(img, 150, 300, 190, 304, (150, 156, 170))  # ralo
    poeira(img, T, n=20, cor=(255, 255, 255))


def _gotas(img, x0, x1, y0, y1, T, cor, n=10, vel=90, semente=5):
    rng = random.Random(semente)
    for _ in range(n):
        x, fase = rng.uniform(x0, x1), rng.random()
        y = y0 + ((T * vel / (y1 - y0) + fase) % 1.0) * (y1 - y0)
        ret(img, x, y, x + 1, y + 4, cor, 0.9)


def _panela(img, ctx, T):
    if ctx.cena > 2:
        return
    esfria = ctx.acao("esfria")
    ret(img, 14, 280, 92, 298, (60, 60, 70))  # fogão
    for x in (24, 60):
        ret(img, x, 276, x + 16, 280, (40, 40, 48))
    chama = 0 if esfria is not None else 1
    for k in range(5):
        if chama:
            luz(img, 26 + k * 7, 272 - (int(T * 12 + k) % 3), (80, 150, 255), 0.9)
    ret(img, 20, 240, 60, 272, METAL)  # panela
    ret(img, 14, 244, 20, 248, METAL_ESC)
    moldura(img, 20, 240, 60, 272, CONTORNO)
    ret(img, 22, 242, 58, 246, AGUA)
    if esfria is None:
        vapor(img, 40, 238, T, n=12, subida=40, espalha=30, semente=2)
    else:
        brilhos(img, 16, 220, 66, 270, T, n=6, cor=(190, 230, 255), semente=3)
    ret(img, 140, 262, 176, 298, (80, 160, 220))  # balde
    moldura(img, 140, 262, 176, 298, CONTORNO)
    ret(img, 142, 264, 174, 270, AGUA_CLARA)


def _chuveiro(img, ctx, T):
    p = ctx.peca("chuveiro")
    if p <= 0:
        return 0
    cair = (1 - p) * -80
    ret(img, 104, 0, 112, 70 + cair, METAL_ESC)  # cano da parede
    moldura(img, 104, 0, 112, 70 + cair, CONTORNO)
    y = cair
    ret(img, 70, 70 + y, 146, 180 + y, METAL)  # corpo em corte
    moldura(img, 70, 70 + y, 146, 180 + y, CONTORNO, 2)
    ret(img, 76, 76 + y, 140, 174 + y, (200, 214, 226))  # câmara de dentro
    ret(img, 60, 180 + y, 156, 190 + y, METAL)  # crivo
    moldura(img, 60, 180 + y, 156, 190 + y, CONTORNO)
    for x in range(66, 152, 8):
        ret(img, x, 187 + y, x + 2, 190 + y, CONTORNO)
    return cair


def _resistencia(img, ctx, T, estado):
    """estado: 0 apagada, 1 morna, 2 quente, 3 rompida."""
    if ctx.peca("chuveiro") <= 0:
        return
    pontos = [(80 + k * 3, 154 + (6 if k % 2 else -6)) for k in range(20)]
    cor = {0: (110, 90, 80), 1: QUENTE, 2: BRASA, 3: (60, 40, 40)}[estado]
    destaque = ctx.peca("resistencia")
    if estado == 3:
        polilinha(img, pontos[:9], cor, esp=2)
        polilinha(img, pontos[11:], cor, esp=2)
        return
    polilinha(img, pontos, CONTORNO, esp=3)
    polilinha(img, pontos, cor, esp=2)
    if estado >= 1:
        ondas_calor(img, 108, 150, ctx.T, largura=40, altura=18, alfa=0.6 if estado == 1 else 0.9)
    if 0 < destaque < 1:
        brilhos(img, 76, 136, 140, 172, T, n=8, semente=4)


def _diafragma(img, ctx, T, empurrado):
    p = ctx.peca("diafragma")
    if p <= 0:
        return
    sobe = 10 * empurrado
    for x in range(78, 126):  # pele de borracha que se curva quando a água empurra
        curva = math.sin((x - 78) / 48 * math.pi) * sobe
        ret(img, x, 124 - curva, x + 1, 128 - curva, (60, 60, 70), p)
    ret(img, 96, 104, 112, 108, (230, 180, 60), p)  # contato elétrico
    moldura(img, 96, 104, 112, 108, CONTORNO)
    ret(img, 103, 96, 105, 104, CONTORNO)
    if empurrado > 0.9:
        brilhos(img, 96, 104, 112, 112, T, n=5, cor=(255, 255, 160), semente=7)


def _chave(img, ctx, T):
    p = ctx.peca("chave")
    if p <= 0:
        return 0
    inverno = ctx.acao("inverno") is not None
    circulo(img, 156, 116, 11 * p, (245, 245, 250))
    circulo(img, 156, 116, 11 * p, CONTORNO, cheio=False)
    ang = (-2.4 if not inverno else -0.7) + 0.05 * math.sin(T * 4)
    linha(img, (156, 116), (156 + math.cos(ang) * 9, 116 + math.sin(ang) * 9), CONTORNO, esp=2)
    circulo(img, 144, 98, 4, (255, 200, 40))  # sol (verão)
    for k in range(4):  # floco (inverno)
        a = k * math.pi / 4
        linha(img, (170 - math.cos(a) * 4, 98 - math.sin(a) * 4), (170 + math.cos(a) * 4, 98 + math.sin(a) * 4),
              (120, 200, 255))
    return 1 if inverno else 0


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _panela(img, ctx, T)
    cair = _chuveiro(img, ctx, T)
    if ctx.peca("chuveiro") <= 0:
        return
    rompida = c == 5 and ctx.acao("romper") is not None and ctx.acao("romper") > 1.5
    ligar = ctx.acao("ligar")
    pouca = c == 8
    agua = c in (3, 4, 9, 10, 11) or (c == 7 and ligar is not None) or pouca
    empurrado = 0.0
    if c == 7 and ligar is not None:
        empurrado = suave(ligar / 0.6)
    elif c in (9, 10, 11):
        empurrado = 1.0
    elif pouca:
        empurrado = 0.3
    estado = 0
    if c in (3, 4):
        estado = 2
    elif c == 5:
        estado = 3 if rompida else 2
    elif empurrado >= 0.95:
        estado = 2
    inverno = _chave(img, ctx, T)
    if agua:  # água entrando pelo cano e saindo pelo crivo
        fluxo(img, [(108, 0), (108, 90), (108, 170)], ctx.T, AGUA_CLARA, velocidade=50, passo=6)
        quente = estado == 2
        _gotas(img, 64, 152, 192, 298, T, BRASA if quente and c != 8 else AGUA, n=4 if pouca else 26, semente=c)
        if quente:
            vapor(img, 108, 260, T, n=14, subida=70, espalha=80, semente=9)
    _diafragma(img, ctx, T, empurrado)
    _resistencia(img, ctx, T, estado)
    if c == 5 and ctx.acao("romper") is not None:
        r = ctx.acao("romper")
        if r < 1.8:  # sem água: esquenta até romper
            ondas_calor(img, 108, 150, T, largura=50, altura=26, cor=(255, 60, 40))
        if 1.3 < r < 2.4:
            for k in range(14):
                a = k * 0.45
                luz(img, 108 + math.cos(a) * (r - 1.3) * 40, 154 + math.sin(a) * (r - 1.3) * 30, BRASA,
                    1 - (r - 1.3))
    if c == 7 and empurrado > 0.95:  # contato fechado: corrente passando
        fluxo(img, [(104, 96), (104, 108), (82, 140), (134, 168)], ctx.T, (255, 255, 140), velocidade=60, passo=6)
    if c == 10 or (c >= 10 and inverno):  # inverno: corrente num pedaço menor, que brilha mais
        fluxo(img, [(150, 120), (120, 150), (100, 150)], ctx.T, (255, 255, 160), velocidade=70, passo=5)
        brilhos(img, 96, 140, 124, 168, T, n=8, cor=(255, 240, 160), semente=12)
    if c == 11:
        brilhos(img, 40, 60, 200, 290, T, n=16, semente=13)
