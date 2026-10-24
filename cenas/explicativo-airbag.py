"""Cena do airbag (palco em pixel art, carro por dentro): saco, sensor, cápsula, gás e furinhos."""
import math

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, poeira, polilinha, ret, suave, vapor)

SERIE = "PULGA DO SABER · AIRBAG"
MUNDO = (216, 384)

PECAS = {
    "boneco": {"titulo": "Motorista", "caixa": (30, 100, 130, 260), "ancora": (80, 130), "conta": False},
    "saco": {"titulo": "Saco dobrado", "caixa": (106, 140, 160, 210), "ancora": (128, 176)},
    "sensor": {"titulo": "Sensor", "caixa": (130, 220, 190, 270), "ancora": (160, 244)},
    "capsula": {"titulo": "Cápsula", "caixa": (110, 160, 150, 196), "ancora": (130, 178)},
    "furos": {"titulo": "Furinhos", "caixa": (80, 120, 160, 220), "ancora": (106, 160)},
}

FUNDO, BANCO, PAINEL = (40, 60, 110), (60, 60, 70), (80, 84, 100)
AMARELO, PRETO, CONTORNO = (250, 200, 40), (30, 30, 36), (20, 20, 26)
TECIDO = (245, 245, 250)


def _cenario(img, T, tremor):
    dx = math.sin(T * 50) * tremor
    ret(img, 0, 0, 216, 384, FUNDO)
    for k in range(10):
        luz(img, (k * 61) % 216, 40 + (k * 29) % 60, (255, 255, 220), 0.3 + 0.3 * math.sin(T * 2 + k), lado=1)
    ret(img, 0, 90 + dx, 216, 96 + dx, (150, 160, 180))  # teto
    polilinha(img, [(150, 96), (206, 150)], (150, 160, 180), esp=4)  # coluna do para-brisa
    ret(img, 140 + dx, 196, 216 + dx, 220, PAINEL)  # painel
    ret(img, 0, 260, 216, 384, (50, 50, 60))  # assoalho
    ret(img, 30 + dx, 150, 64 + dx, 262, BANCO)  # banco
    ret(img, 20 + dx, 110, 44 + dx, 160, BANCO)
    poeira(img, T, n=14)


def _boneco(img, x, inclina, cabeca_extra=0.0):
    ombro_x = x + 20 * inclina
    ret(img, x, 200, x + 30, 220, AMARELO)  # quadril
    polilinha(img, [(x + 15, 205), (ombro_x + 15, 150)], AMARELO, esp=16)  # tronco
    hx, hy = ombro_x + 16 + 14 * cabeca_extra, 134 + 6 * cabeca_extra
    circulo(img, hx, hy, 11, AMARELO)
    circulo(img, hx, hy, 11, CONTORNO, cheio=False)
    for sx in (-4, 4):  # marcas de boneco de teste
        circulo(img, hx + sx, hy - 2, 2, PRETO)
    polilinha(img, [(x + 26, 216), (x + 70, 226), (x + 74, 258)], AMARELO, esp=8)  # perna
    polilinha(img, [(ombro_x + 20, 156), (x + 66 + 6 * inclina, 172)], AMARELO, esp=6)  # braço no volante
    return hx, hy


def _volante(img):
    polilinha(img, [(124, 176), (150, 206)], (60, 60, 70), esp=6)  # coluna
    for y in range(146, 206):  # volante visto de lado
        ret(img, 118, y, 126, y + 1, PRETO)
    ret(img, 116, 168, 128, 184, (70, 70, 80))


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    tremor = 2.0 * max(0.0, 1 - (ctx.acao("bate") or 9) / 0.5) if c == 1 else 0.0
    _cenario(img, T, tremor)
    inclina, cabeca = 0.0, 0.0
    if c == 1 and ctx.acao("bate") is not None:
        inclina = suave(ctx.acao("bate") / 0.4) * 1.4
    elif c == 2 and ctx.acao("cabeca") is not None:
        inclina, cabeca = 0.6, suave(ctx.acao("cabeca") / 0.5) * 1.6
    elif c in (8,):
        d = ctx.acao("duro")
        if d is not None:  # bate no saco duro e volta
            inclina, cabeca = 0.6, 1.0 - abs(math.sin(min(d, 1.2) * 5)) * 0.8
    elif c in (9, 11):
        inclina, cabeca = 0.6, 0.6
    _volante(img)
    hx, hy = _boneco(img, 40, inclina, cabeca)
    if c >= 2:  # cinto de segurança
        cor = (255, 120, 60) if c == 11 else (90, 90, 100)
        polilinha(img, [(44, 118), (60 + 20 * inclina, 160), (78, 210)], cor, esp=4)
    saco = ctx.peca("saco")
    cheio = 0.0
    if c == 7 and ctx.acao("enche") is not None:
        cheio = suave(ctx.acao("enche") / 0.15)
    elif c == 8:
        cheio = 1.0
    elif c == 9:
        cheio = 1.0 - 0.6 * suave((ctx.acao("murcha") or 0) / 2.5)
    elif c in (10, 11, 12):
        cheio = 0.5
    if saco > 0 and cheio <= 0.02:  # saco dobrado dentro do volante (em corte)
        for k in range(4):
            ret(img, 118, 158 + k * 6, 126, 162 + k * 6, TECIDO, saco)
    if cheio > 0.02:
        r = 32 * cheio
        circulo(img, 104, 162, r, TECIDO)
        circulo(img, 104, 162, r, CONTORNO, cheio=False)
        if ctx.peca("furos") > 0:
            for k in range(6):
                a = k * 1.05
                ret(img, 104 + math.cos(a) * r * 0.8, 162 + math.sin(a) * r * 0.8,
                    106 + math.cos(a) * r * 0.8, 164 + math.sin(a) * r * 0.8, (120, 120, 130))
            if c == 9:
                for k in range(6):
                    a = k * 1.05
                    vapor(img, 104 + math.cos(a) * r, 162 + math.sin(a) * r, T, n=3, subida=12, espalha=4,
                          semente=k)
    sen = ctx.peca("sensor")
    if sen > 0:
        ret(img, 140, 228, 182, 254, (40, 120, 70), sen)  # placa do sensor
        moldura(img, 140, 228, 182, 254, CONTORNO)
        ag = -2.6 + (1.8 if c in (1, 6, 7) else 0.6 + 0.2 * math.sin(T * 2))
        circulo(img, 161, 246, 8, (245, 245, 250))
        linha(img, (161, 246), (161 + math.cos(ag) * 7, 246 + math.sin(ag) * 7), (220, 40, 40), esp=2)
    cap = ctx.peca("capsula")
    if cap > 0:
        ret(img, 126, 172, 136, 182, (200, 80, 60), cap)
        moldura(img, 126, 172, 136, 182, CONTORNO)
        if c == 6:  # choquinho do sensor até a cápsula
            fluxo(img, [(150, 228), (150, 200), (131, 182)], ctx.T, (255, 255, 160), velocidade=70, passo=5)
        if c == 7 and cheio < 1:  # queima e vira gás
            for k in range(10):
                a = k * 0.63 + T * 6
                luz(img, 131 + math.cos(a) * 8, 177 + math.sin(a) * 8, (255, 200, 80), 0.9)
    if c == 4 and ctx.acao("piscar") is not None:  # olho piscando
        fecha = abs(math.sin(T * 4))
        circulo(img, 170, 120, 14, (250, 250, 250))
        ret(img, 156, 120 - 14 * (1 - fecha), 184, 120 + 14 * (1 - fecha) * 0, (240, 196, 150))
        circulo(img, 170, 120, 5, (60, 120, 200))
    if c in (10, 12):
        brilhos(img, 60, 120, 160, 210, T, n=12, semente=c)
