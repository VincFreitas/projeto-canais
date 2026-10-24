"""Cena do zíper (palco em pixel art): dos botões ao zíper que fecha e abre com o cursor e a cunha."""
import math

from darkops.palco import (brilhos, circulo, linha, luz, moldura, poeira, polilinha, ret, suave, vaivem)

SERIE = "PULGA DO SABER · ZÍPER"
MUNDO = (216, 384)

PECAS = {
    "jaqueta": {"titulo": "Jaqueta", "caixa": (24, 80, 192, 300), "ancora": (108, 120), "conta": False},
    "dentes": {"titulo": "Dentes", "caixa": (88, 110, 128, 290), "ancora": (104, 200)},
    "dente": {"titulo": "Dente", "caixa": (110, 120, 196, 210), "ancora": (152, 150), "conta": False},
    "cursor": {"titulo": "Cursor", "caixa": (90, 230, 126, 290), "ancora": (108, 262)},
    "cunha": {"titulo": "Cunha", "caixa": (90, 150, 126, 230), "ancora": (108, 190)},
}

PAREDE, MESA = (200, 150, 110), (150, 96, 60)
JEANS, JEANS_ESC, COSTURA = (60, 110, 190), (40, 80, 150), (230, 180, 80)
METAL, METAL_ESC, CONTORNO = (220, 220, 228), (150, 150, 165), (30, 30, 40)


def _cenario(img, T):
    ret(img, 0, 0, 216, 384, PAREDE)
    for y in range(0, 384, 24):
        ret(img, 0, y, 216, y + 1, (186, 136, 98))
    ret(img, 0, 300, 216, 384, MESA)
    ret(img, 0, 300, 216, 303, (110, 70, 40))
    circulo(img, 190, 30, 16, (255, 230, 160), 0.15)
    poeira(img, T, n=22)


def _jaqueta(img):
    ret(img, 30, 96, 186, 300, JEANS)
    ret(img, 30, 96, 60, 300, JEANS_ESC)  # mangas dobradas para dentro
    ret(img, 156, 96, 186, 300, JEANS_ESC)
    ret(img, 84, 84, 132, 100, JEANS_ESC)  # gola
    moldura(img, 30, 96, 186, 300, CONTORNO)
    for x in (70, 146):  # bolsos com costura
        ret(img, x - 12, 150, x + 12, 176, JEANS_ESC)
        moldura(img, x - 12, 150, x + 12, 176, COSTURA)
    for y in range(104, 296, 6):
        ret(img, 96, y, 97, y + 3, COSTURA)
        ret(img, 119, y, 120, y + 3, COSTURA)


def _botoes(img, ctx, T):
    if ctx.cena > 2:
        return
    for y in range(120, 290, 34):
        circulo(img, 104, y, 4, (200, 170, 120))
        circulo(img, 104, y, 4, CONTORNO, cheio=False)
        ret(img, 108, y - 2, 114, y + 2, (40, 40, 50))  # casa do botão
    if ctx.cena == 2 and ctx.acao("vento") is not None:
        for k in range(5):  # vento passando pelas frestas
            fase = (ctx.T * 0.9 + k / 5) % 1.0
            y = 136 + k * 34
            linha(img, (40 + fase * 150, y), (60 + fase * 150, y), (230, 240, 255), 0.8 * (1 - fase), esp=2)


def _dentes(img, ctx, T, fechado_ate, densidade):
    """fechado_ate: y do cursor; abaixo dele os dentes estão encaixados, acima abrem em V."""
    p = ctx.peca("dentes")
    if p <= 0:
        return
    passo = 6 if densidade < 0.5 else 4
    topo = 290 - 180 * p
    for y in range(110, 290, passo):
        if y < topo:
            continue
        abre = max(0.0, (fechado_ate - y) / 180) if fechado_ate is not None else 1.0
        sep = 3 + 10 * abre
        lado = (y // passo) % 2
        for sinal in (-1, 1):  # um dente de cada lado, alternados
            x = 108 + sinal * sep + (2 if (lado == (sinal > 0)) else 0) * (1 - abre) * -sinal
            ret(img, x - 3, y, x + 3, y + passo - 2, METAL)
            ret(img, x - 3, y, x + 3, y + 1, (255, 255, 255))
            moldura(img, x - 3, y, x + 3, y + passo - 2, METAL_ESC)


def _dente_grande(img, ctx, T):
    zoom = ctx.acao("zoom_dente")
    if ctx.cena not in (4, 5) or zoom is None:
        return
    r = 42 * suave(zoom / 0.35)
    circulo(img, 152, 166, r + 2, CONTORNO)
    circulo(img, 152, 166, r, (248, 248, 250))
    if r < 36:
        return
    ret(img, 134, 150, 170, 186, METAL)  # o dente, bem grande
    moldura(img, 134, 150, 170, 186, CONTORNO, 2)
    ret(img, 144, 140, 160, 150, METAL)  # calombo em cima
    moldura(img, 144, 140, 160, 151, CONTORNO, 2)
    ret(img, 145, 176, 159, 186, (90, 90, 100))  # buraco embaixo
    ret(img, 136, 152, 140, 182, (255, 255, 255))
    brilhos(img, 130, 136, 176, 190, T, n=6, semente=3)
    if ctx.cena == 5 and ctx.acao("mao") is not None:  # dedos tentando encaixar
        tremor = math.sin(T * 30) * 2
        ret(img, 168 + tremor, 186, 196 + tremor, 204, (240, 196, 150))
        ret(img, 160 + tremor, 182, 172 + tremor, 190, (240, 196, 150))


def _cursor(img, ctx, T, y):
    p = ctx.peca("cursor")
    if p <= 0:
        return
    y = y + (1 - p) * 60
    ret(img, 96, y, 120, y + 16, METAL)  # corpo em Y
    ret(img, 100, y + 16, 116, y + 22, METAL)
    moldura(img, 96, y, 120, y + 16, CONTORNO, 2)
    ret(img, 98, y + 2, 102, y + 14, (255, 255, 255))
    ret(img, 104, y + 22, 112, y + 40, METAL_ESC)  # puxador
    moldura(img, 104, y + 22, 112, y + 40, CONTORNO)
    if ctx.peca("cunha") > 0:  # vista por dentro: a cunha no meio do canal em Y
        a = ctx.peca("cunha")
        for k in range(8):
            ret(img, 108 - k * 0.6 * a, y + 2 + k, 108 + k * 0.6 * a + 1, y + 3 + k, (220, 60, 60))
        polilinha(img, [(98, y + 2), (106, y + 10), (106, y + 15)], CONTORNO)
        polilinha(img, [(118, y + 2), (110, y + 10), (110, y + 15)], CONTORNO)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _jaqueta(img)
    _botoes(img, ctx, T)
    y_cursor = 270
    fechado = None
    if c in (6, 7):
        subir = ctx.acao("subir")
        y_cursor = 270 - (150 * vaivem(subir / 2.5) if subir is not None else 0)
        fechado = y_cursor + 10
    elif c == 8:
        descer = ctx.acao("descer")
        y_cursor = 120 + (150 * vaivem(descer / 2.5) if descer is not None else 0)
        fechado = y_cursor + 10
    elif c == 9:
        y_cursor, fechado = 200, 210
    elif c >= 10:
        fechar = ctx.acao("fechar2") if c == 10 else 99
        y_cursor = 270 - 166 * vaivem((fechar or 0) / 1.6)
        fechado = y_cursor + 10
    densa = 1.0 if (c > 9 or (c == 9 and ctx.acao("densa") is not None)) else 0.0
    _dentes(img, ctx, T, fechado, densa)
    _cursor(img, ctx, T, y_cursor)
    _dente_grande(img, ctx, T)
    if c in (7, 10) and fechado is not None:  # cliques de encaixe logo abaixo do cursor
        luz(img, 106, y_cursor + 22 + (int(T * 20) % 4), (255, 255, 200), 0.9)
    if c == 11:
        brilhos(img, 30, 90, 186, 300, T, n=18, semente=11)
