"""Cena da caneta esferográfica (palco em pixel art): da pena ao tubo de tinta com a bolinha na ponta."""
import math

from darkops.palco import (brilhos, circulo, linha, luz, moldura, poeira, polilinha, ret, suave, vaivem)

SERIE = "PULGA DO SABER · CANETA"
MUNDO = (216, 384)

PECAS = {
    "tubo": {"titulo": "Tubo de tinta", "caixa": (80, 70, 136, 240), "ancora": (108, 150)},
    "ponta": {"titulo": "Ponta", "caixa": (88, 210, 128, 250), "ancora": (108, 238), "conta": False},
    "esfera": {"titulo": "Esfera", "caixa": (88, 210, 128, 250), "ancora": (108, 240)},
    "jornal": {"titulo": "Jornal", "caixa": (20, 70, 120, 170), "ancora": (70, 110), "conta": False},
    "tinta": {"titulo": "Tinta grossa", "caixa": (80, 70, 136, 240), "ancora": (108, 120)},
    "corpo": {"titulo": "Caneta", "caixa": (70, 40, 146, 250), "ancora": (108, 90)},
}

PAREDE, MESA, PAPEL = (90, 110, 160), (160, 110, 70), (250, 248, 240)
TINTA, TINTA_CLARA, CONTORNO = (40, 80, 200), (120, 160, 240), (24, 24, 34)
PLASTICO = (230, 236, 244)


def _cenario(img, T):
    ret(img, 0, 0, 216, 230, PAREDE)
    circulo(img, 180, 40, 30, (255, 230, 160), 0.12)
    ret(img, 168, 0, 172, 30, (40, 40, 50))  # luminária
    ret(img, 156, 30, 188, 40, (240, 200, 80))
    ret(img, 0, 230, 216, 384, MESA)
    for y in range(240, 384, 16):
        ret(img, 0, y, 216, y + 1, (130, 86, 54))
    ret(img, 24, 244, 192, 300, PAPEL)  # folha
    moldura(img, 24, 244, 192, 300, (200, 196, 186))
    for y in range(256, 300, 8):
        ret(img, 28, y, 188, y + 1, (190, 210, 240))
    poeira(img, T, n=20)


def _pena(img, ctx, T):
    if ctx.cena > 2:
        return
    ret(img, 150, 222, 176, 240, (40, 40, 50))  # tinteiro
    ret(img, 154, 216, 172, 222, (60, 60, 70))
    moldura(img, 150, 222, 176, 240, CONTORNO)
    mergulha = 0.5 + 0.5 * math.sin(T * 2.4) if ctx.acao("pena") is not None else 0
    x, y = 150 - 40 * (1 - mergulha), 120 + 90 * mergulha
    for k in range(18):  # pena
        ret(img, x + k * 2, y - k * 4, x + k * 2 + 6, y - k * 4 + 3, (245, 245, 250))
    linha(img, (x, y), (x + 36, y - 72), (200, 200, 210), esp=1)
    if ctx.cena == 2 and ctx.acao("mancha") is not None:
        r = 4 + 14 * suave(ctx.acao("mancha") / 2.0)
        circulo(img, 80, 272, r, TINTA)
        circulo(img, 92, 280, r * 0.5, TINTA)


def _caneta(img, ctx, T, px, py, invertida=False):
    tubo = ctx.peca("tubo")
    if tubo <= 0:
        return
    corpo = ctx.peca("corpo")
    tinta = ctx.peca("tinta")
    s = -1 if invertida else 1
    ponta_y = py + s * 2
    if corpo > 0:  # corpo transparente, tampa e clipe
        ret(img, px - 12, py - 160 * s if not invertida else py + 20, px + 12, py - 20 if not invertida else py + 160,
            PLASTICO, 0.55 * corpo)
        ret(img, px - 12, py - 176 if not invertida else py + 160, px + 12, py - 160 if not invertida else py + 176,
            (40, 80, 200), corpo)
        ret(img, px + 12, py - 176 if not invertida else py + 130, px + 16, py - 130 if not invertida else py + 176,
            (180, 180, 190), corpo)
    y0, y1 = (py - 150, py - 18) if not invertida else (py + 18, py + 150)
    ret(img, px - 5, y0, px + 5, y1, (240, 240, 245), tubo)  # tubinho
    moldura(img, px - 5, y0, px + 5, y1, CONTORNO)
    cheio = 0.7
    cor = tuple(int(TINTA_CLARA[k] + (TINTA[k] - TINTA_CLARA[k]) * tinta) for k in range(3))
    if not invertida:
        ret(img, px - 4, y1 - (y1 - y0) * cheio, px + 4, y1, cor, tubo)
    else:  # de cabeça para baixo a tinta escorre para longe da ponta
        ret(img, px - 4, y1 - (y1 - y0) * cheio, px + 4, y1, cor, tubo)
    for k in range(10):  # cone da ponta
        a = 6 - k * 0.5
        yy = (py - 18 + k) if not invertida else (py + 18 - k)
        ret(img, px - a, yy, px + a, yy + 1, (190, 194, 204))
    esf = ctx.peca("esfera")
    if esf > 0:
        circulo(img, px, ponta_y, 3 * esf, (230, 230, 240))
        circulo(img, px, ponta_y, 3 * esf, CONTORNO, cheio=False)
    elif ctx.cena == 3 and ctx.acao("vaza") is not None:  # furo sem bolinha: vaza tudo
        r = 4 + 16 * suave(ctx.acao("vaza") / 2.0)
        circulo(img, px, py + 12, r, TINTA)
        for k in range(4):
            fase = (T * 2 + k / 4) % 1.0
            ret(img, px - 1, py - 4 + fase * 14, px + 2, py - 1 + fase * 14, TINTA)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _pena(img, ctx, T)
    px, py = 108, 238
    if c == 5 and ctx.acao("escreve") is not None:  # escrevendo: a caneta anda e deixa a linha
        f = vaivem(ctx.acao("escreve") / 3.0)
        px = 50 + 120 * f
        for x in range(50, int(px)):
            ret(img, x, 262 + math.sin(x * 0.3) * 3, x + 1, 264 + math.sin(x * 0.3) * 3, TINTA)
        a = T * 8  # bolinha girando com tinta
        luz(img, px + math.cos(a) * 2, py + math.sin(a) * 2, TINTA_CLARA, 0.9, lado=1)
        py = 262
    if c in (6,):
        rala = ctx.acao("rala")
        if rala is not None and rala < 2.4:  # tinta rala escorrendo
            for k in range(5):
                fase = (T * 2 + k / 5) % 1.0
                ret(img, px - 6 + k * 3, py + 4 + fase * 20, px - 4 + k * 3, py + 8 + fase * 20, TINTA_CLARA)
        elif rala is not None:  # tinta grossa demais: ponta seca
            brilhos(img, px - 10, py - 10, px + 10, py + 10, T, n=4, cor=(255, 200, 200), semente=6)
    if c >= 7 and c <= 8:
        j = ctx.acao("jornal") if c == 7 else 99
        if j is not None:
            f = suave(j / 0.5)
            ret(img, 20, 70 + (1 - f) * -60, 92, 170 + (1 - f) * -60, (236, 232, 220))
            moldura(img, 20, 70 + (1 - f) * -60, 92, 170 + (1 - f) * -60, CONTORNO)
            ret(img, 26, 76 + (1 - f) * -60, 86, 86 + (1 - f) * -60, CONTORNO)
            for y in range(92, 164, 6):
                ret(img, 26, y + (1 - f) * -60, 86, y + 2 + (1 - f) * -60, (120, 120, 120))
            brilhos(img, 20, 70, 92, 170, T, n=6, semente=7)
    if c == 8 and ctx.peca("tinta") >= 1:  # carimbo da patente
        ret(img, 140, 90, 200, 120, (200, 50, 50), 0.85)
        moldura(img, 140, 90, 200, 120, CONTORNO, 2)
    invertida = c == 10 and ctx.acao("virar") is not None and ctx.acao("virar") > 0.6
    if invertida:
        py = 120
        for x in range(40, 180):  # linha falhando no papel do teto
            if math.sin(x * 0.7 + T) > 0.3:
                ret(img, x, 100, x + 1, 102, TINTA, max(0.0, 1 - (x - 40) / 140))
    _caneta(img, ctx, T, px, py, invertida)
    if c == 4 and ctx.peca("esfera") > 0:
        brilhos(img, 96, 226, 120, 250, T, n=6, semente=4)
    if c == 11:
        for x in range(40, 180):
            ret(img, x, 280 + math.sin(x * 0.2) * 4, x + 1, 282 + math.sin(x * 0.2) * 4, TINTA)
        brilhos(img, 30, 60, 190, 300, T, n=16, semente=11)
