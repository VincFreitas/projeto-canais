"""Cena do elevador (palco em pixel art, prédio em corte): polia, motor, contrapeso, freio de segurança e limitador."""
import math

from darkops.palco import (brilhos, circulo, linha, luz, moldura, poeira, ret, suave, vaivem)

SERIE = "PULGA DO SABER · ELEVADOR"
MUNDO = (216, 384)

PECAS = {
    "cabine": {"titulo": "Cabine", "caixa": (60, 150, 160, 260), "ancora": (110, 200), "conta": False},
    "motor": {"titulo": "Motor", "caixa": (90, 20, 170, 70), "ancora": (146, 42)},
    "contrapeso": {"titulo": "Contrapeso", "caixa": (110, 60, 160, 300), "ancora": (134, 180)},
    "freio": {"titulo": "Freio de segurança", "caixa": (56, 140, 164, 260), "ancora": (68, 200)},
    "limitador": {"titulo": "Limitador de velocidade", "caixa": (56, 26, 110, 90), "ancora": (76, 48)},
}

CEU, PREDIO, PREDIO_ESC = (30, 34, 80), (220, 120, 120), (180, 90, 96)
POCO, TRILHO, CONTORNO = (60, 56, 70), (150, 156, 170), (24, 22, 30)
CABINE, ACO = (240, 230, 210), (190, 196, 206)


def _cenario(img, T):
    ret(img, 0, 0, 216, 384, CEU)
    for k in range(14):
        luz(img, (k * 53) % 216, (k * 37) % 120, (255, 255, 220), 0.3 + 0.3 * math.sin(T * 2 + k), lado=1)
    ret(img, 30, 20, 190, 310, PREDIO)
    for y in range(80, 300, 60):  # andares e janelas
        ret(img, 30, y, 190, y + 3, PREDIO_ESC)
        for x in (36, 168):
            ret(img, x, y + 14, x + 14, y + 34, (255, 230, 140))
    ret(img, 56, 26, 164, 304, POCO)  # poço do elevador em corte
    moldura(img, 56, 26, 164, 304, CONTORNO, 2)
    ret(img, 62, 60, 65, 304, TRILHO)  # trilhos-guia
    ret(img, 155, 60, 158, 304, TRILHO)
    ret(img, 0, 310, 216, 384, (70, 70, 80))
    poeira(img, T, n=18)


def _polia(img, T, girando):
    a = T * 3 * girando
    circulo(img, 110, 48, 14, (110, 110, 120))
    circulo(img, 110, 48, 14, CONTORNO, cheio=False)
    for k in range(4):
        b = a + k * math.pi / 2
        linha(img, (110, 48), (110 + math.cos(b) * 12, 48 + math.sin(b) * 12), (70, 70, 80), esp=2)


def _cabine(img, x0, y, gente, plataforma=False):
    if plataforma:  # plataforma aberta de 1854
        ret(img, x0, y + 44, x0 + 72, y + 50, (140, 100, 60))
        moldura(img, x0, y + 44, x0 + 72, y + 50, CONTORNO)
        ret(img, x0 + 30, y + 6, x0 + 42, y + 12, (30, 30, 30))  # cartola
        ret(img, x0 + 32, y + 12, x0 + 40, y + 20, (240, 196, 150))
        ret(img, x0 + 30, y + 20, x0 + 42, y + 44, (40, 40, 60))
        return
    ret(img, x0, y, x0 + 72, y + 50, CABINE)
    moldura(img, x0, y, x0 + 72, y + 50, CONTORNO, 2)
    ret(img, x0 + 4, y + 4, x0 + 68, y + 8, (255, 240, 180))  # luz da cabine
    for k in range(gente):
        x = x0 + 10 + k * 18
        circulo(img, x + 4, y + 20, 4, (240, 196, 150))
        ret(img, x, y + 25, x + 9, y + 46, ((60, 110, 210), (210, 70, 90), (70, 170, 110))[k % 3])


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    ciclo = 0.5 - 0.5 * math.cos(T * 0.6)  # a cabine sobe e desce sozinha
    car_y = 250 - 150 * ciclo
    gente = 3 if c >= 2 else 0
    plataforma = c in (10, 11)
    girando = 1.0
    caindo = 0.0
    cortado = False
    if c == 1:
        car_y = 250 - 120 * suave((ctx.acao("corda") or 0) / 3.0) if ctx.acao("corda") is not None else 250
    if c == 2 and ctx.acao("pesado") is not None:
        car_y = 230 + math.sin(T * 6) * 3
        girando = 0.1
    if c == 4 and ctx.acao("esforco") is not None:
        car_y, girando = 230 - 20 * suave(ctx.acao("esforco") / 3.0), 0.3
    if c == 7 and ctx.acao("arrebenta") is not None:
        a = ctx.acao("arrebenta")
        cortado = True
        caindo = min(a * a * 30, 60)
        car_y = 120 + caindo
    if c == 8:
        a = ctx.acao("agarra")
        cortado = True
        car_y = 180 if a is not None else 120 + 60
    if c == 10 and ctx.acao("otis") is not None:
        a = ctx.acao("otis")
        cortado = a > 0.6
        car_y = 120 + (min((a - 0.6) * 40, 14) if cortado else 0)
    if c == 11:
        cortado, car_y = True, 134
    if c == 9:
        car_y = 160
    x0 = 74
    _polia(img, T, girando)
    mot = ctx.peca("motor")
    if mot > 0:
        ret(img, 130, 34 + (1 - mot) * -40, 162, 60 + (1 - mot) * -40, (70, 90, 160))
        moldura(img, 130, 34 + (1 - mot) * -40, 162, 60 + (1 - mot) * -40, CONTORNO)
        linha(img, (124, 48), (130, 48), (70, 70, 80), esp=3)
        if c == 4 and ctx.acao("esforco") is not None:  # motor sofrendo
            for k in range(4):
                luz(img, 140 + k * 6, 30 - (T * 20 + k * 5) % 14, (150, 200, 255), 0.8)
    if not cortado:
        linha(img, (110, 34), (110, car_y), (40, 40, 48), esp=2)  # cabo até a cabine
    else:
        linha(img, (110, 34), (110, 90 + math.sin(T * 8) * 4), (40, 40, 48), esp=2)  # ponta solta balançando
    cp = ctx.peca("contrapeso")
    if cp > 0 and not cortado:
        cw_y = 300 - (car_y - 60) - 40
        linha(img, (124, 48), (134, cw_y), (40, 40, 48), esp=2)
        ret(img, 126, cw_y, 142, cw_y + 40 * cp, (90, 90, 100))
        moldura(img, 126, cw_y, 142, cw_y + 40 * cp, CONTORNO)
    _cabine(img, x0, car_y, gente, plataforma)
    fr = ctx.peca("freio")
    if fr > 0:  # garras dos dois lados da cabine
        aperto = 1.0 if cortado else 0.0
        for xg, sinal in ((x0 - 8, -1), (x0 + 72, 1)):
            ret(img, xg + (2 * aperto * sinal if False else 0), car_y + 10, xg + 8, car_y + 22, (220, 60, 60), fr)
            moldura(img, xg, car_y + 10, xg + 8, car_y + 22, CONTORNO)
        if cortado and c in (8, 11):
            for k in range(8):
                fase = (T * 2 + k / 8) % 1.0
                luz(img, x0 - 6 + (k % 2) * 82, car_y + 16 + fase * 10, (255, 220, 80), 1 - fase)
    lim = ctx.peca("limitador")
    if lim > 0:
        circulo(img, 76, 48, 9 * lim, (220, 200, 60))
        circulo(img, 76, 48, 9 * lim, CONTORNO, cheio=False)
        a = T * 5
        for k in range(2):
            b = a + k * math.pi
            ret(img, 76 + math.cos(b) * 5 - 1, 48 + math.sin(b) * 5 - 1, 76 + math.cos(b) * 5 + 2,
                48 + math.sin(b) * 5 + 2, CONTORNO)
        linha(img, (68, 48), (68, car_y + 16), (60, 60, 70))  # cabo do limitador até a cabine
    if c == 7 and caindo > 0:
        ret(img, x0, car_y - 20, x0 + 72, car_y - 2, (255, 255, 255), 0.25)  # rastro de queda
    if c == 12:
        brilhos(img, 40, 30, 190, 300, T, n=16, semente=12)
