"""Cena da descarga (palco em pixel art, vista em corte): balde, caixa, sifão, água parada e boia."""
import math

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ponto, poeira, polilinha, ret, suave,
                           vaivem)

SERIE = "PULGA DO SABER · DESCARGA"
MUNDO = (216, 384)

PECAS = {
    "vaso": {"titulo": "Vaso", "caixa": (50, 200, 170, 300), "ancora": (110, 230), "conta": False},
    "caixa": {"titulo": "Caixa acoplada", "caixa": (24, 110, 100, 210), "ancora": (62, 130)},
    "sifao": {"titulo": "Sifão", "caixa": (80, 240, 190, 330), "ancora": (140, 296)},
    "boia": {"titulo": "Boia", "caixa": (24, 120, 100, 210), "ancora": (72, 160)},
}

AZULEJO, REJUNTE = (150, 214, 180), (176, 230, 200)
LOUCA, LOUCA_ESC, CONTORNO = (248, 248, 252), (200, 206, 214), (34, 36, 48)
AGUA, AGUA_CLARA = (90, 170, 240), (180, 225, 255)
CANO = (170, 176, 186)
SIFAO = [(104, 278), (112, 300), (128, 312), (148, 306), (160, 290), (172, 300), (182, 330)]


def _cenario(img, T):
    ret(img, 0, 0, 216, 300, AZULEJO)
    for y in range(8, 300, 14):
        ret(img, 0, y, 216, y + 1, REJUNTE)
    for x in range(8, 216, 14):
        ret(img, x, 0, x + 1, 300, REJUNTE)
    ret(img, 0, 300, 216, 384, (200, 200, 206))
    for y in range(300, 384, 10):  # chão em corte: terra e cano do esgoto
        ret(img, 0, y, 216, y + 1, (180, 180, 186))
    ret(img, 176, 326, 216, 340, CANO)
    poeira(img, T, n=18, cor=(255, 255, 255))


def _vaso(img):
    ret(img, 66, 216, 160, 236, LOUCA)  # borda (tampa do assento)
    for y in range(236, 296):  # bacia que afina para baixo
        aperto = (y - 236) * 0.45
        ret(img, 70 + aperto, y, 156 - aperto, y + 1, LOUCA)
    ret(img, 92, 290, 134, 300, LOUCA_ESC)  # pé
    moldura(img, 66, 216, 160, 236, CONTORNO)
    ret(img, 64, 212, 162, 216, LOUCA_ESC)


def _agua_bacia(img, nivel, T, rodando):
    if nivel <= 0:
        return
    topo = 284 - 40 * nivel
    for y in range(int(topo), 286):
        aperto = (y - 236) * 0.45 if y > 236 else 0
        ret(img, 74 + aperto, y, 152 - aperto, y + 1, AGUA, 0.85)
    if rodando:  # redemoinho
        for k in range(10):
            a = T * 8 + k * 0.6
            luz(img, 113 + math.cos(a) * (18 - k), topo + 6 + k * 2, AGUA_CLARA, 0.9)


def _caixa(img, ctx, T, nivel):
    p = ctx.peca("caixa")
    if p <= 0:
        return
    y = (1 - p) * -90
    ret(img, 28, 120 + y, 98, 206 + y, (230, 236, 244))
    moldura(img, 28, 120 + y, 98, 206 + y, CONTORNO, 2)
    if nivel > 0:
        ret(img, 30, 204 - 80 * nivel + y, 96, 204 + y, AGUA, 0.85)
        ret(img, 30, 204 - 80 * nivel + y, 96, 205 - 80 * nivel + y, AGUA_CLARA)
    ret(img, 92, 206 + y, 100, 214 + y, CANO)  # saída para a bacia
    ret(img, 94, 110 + y, 108, 116 + y, (210, 210, 220))  # botão
    moldura(img, 94, 110 + y, 108, 116 + y, CONTORNO)


def _tampa(img, ctx, levantada):
    if ctx.peca("caixa") < 1:
        return
    ang = levantada * 1.1
    x0, y0 = 54, 200
    linha(img, (x0, y0), (x0 + math.cos(-ang) * 18, y0 + math.sin(-ang) * 18), (40, 40, 50), esp=3)
    linha(img, (x0 + 9, y0 - 2), (x0 + 9, 128), (90, 90, 100))  # correntinha até o botão


def _sifao(img, ctx, T, cheio, ar):
    p = ctx.peca("sifao")
    if p <= 0:
        return
    polilinha(img, SIFAO, CONTORNO, esp=12, progresso=p)
    polilinha(img, SIFAO, LOUCA_ESC, esp=9, progresso=p)
    if p >= 1:
        polilinha(img, SIFAO[:3], AGUA, esp=7)  # a água parada que fica na curva (selo)
        if cheio:
            polilinha(img, SIFAO, AGUA, esp=7)
            fluxo(img, SIFAO, ctx.T, AGUA_CLARA, velocidade=60, passo=6)
        if ar:
            for k in range(6):
                fase = (T * 1.5 + k / 6) % 1.0
                circulo(img, 150 + math.sin(k) * 6, 300 - fase * 10, 2, (230, 245, 255), cheio=False)


def _boia(img, ctx, T, nivel, abrindo):
    p = ctx.peca("boia")
    if p <= 0:
        return
    ret(img, 34, 130, 40, 204, CANO)  # cano da torneirinha
    ret(img, 30, 126, 46, 134, (110, 110, 120))
    by = 204 - 80 * nivel - 6
    linha(img, (42, 130), (74, by), (110, 110, 120), esp=2)  # haste
    circulo(img, 78, by, 8 * p, (240, 120, 60))
    circulo(img, 78, by, 8 * p, CONTORNO, cheio=False)
    if abrindo:  # água entrando pela torneirinha
        fluxo(img, [(38, 134), (38, 200)], ctx.T, AGUA_CLARA, velocidade=50, passo=5)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _vaso(img)
    nivel_caixa = 0.0
    levantada = 0.0
    bacia, rodando = 0.35, False
    if c == 3:
        nivel_caixa = 1.0
    elif c == 4:
        d = ctx.acao("descarga")
        f = suave(d / 1.6) if d is not None else 0
        nivel_caixa, levantada = 1 - f, (1.0 if d is not None and f < 1 else 0.0)
        bacia, rodando = 0.35 + 0.5 * f, d is not None
    elif c == 5:
        bacia, rodando = 0.8 - 0.5 * suave((ctx.acao("puxa") or 0) / 2.5), True
    elif c == 9:
        d = ctx.acao("enche")
        nivel_caixa = 0.4 * suave(d / 2.5) if d is not None else 0.0
    elif c == 10:
        d = ctx.acao("fecha")
        nivel_caixa = 0.4 + 0.6 * suave((d or 0) / 2.0)
    elif c == 11:
        nivel_caixa = 1.0
    if c == 1 and ctx.acao("balde") is not None:  # balde despejando
        incl = suave(ctx.acao("balde") / 0.8)
        ret(img, 150 - incl * 20, 150, 186 - incl * 20, 186, (80, 160, 220))
        moldura(img, 150 - incl * 20, 150, 186 - incl * 20, 186, CONTORNO)
        fluxo(img, [(150 - incl * 20, 160), (130, 220), (114, 260)], ctx.T, AGUA_CLARA, velocidade=70, passo=4,
              alfa=incl)
        bacia, rodando = 0.35 + 0.4 * incl, True
    if c == 2:
        ret(img, 160, 260, 196, 298, (80, 160, 220))  # balde vazio no chão
        moldura(img, 160, 260, 196, 298, CONTORNO)
    _agua_bacia(img, bacia, T, rodando)
    _caixa(img, ctx, T, nivel_caixa)
    _tampa(img, ctx, levantada)
    if c == 4 and levantada:
        fluxo(img, [(54, 204), (96, 210), (110, 236)], ctx.T, AGUA_CLARA, velocidade=70, passo=4)
    _sifao(img, ctx, T, cheio=c == 5, ar=c == 6)
    if c == 7 and ctx.acao("selo") is not None:  # cheiro do esgoto barrado pela água parada
        for k in range(5):
            fase = (T * 0.8 + k / 5) % 1.0
            luz(img, 186 - fase * 20, 334 - fase * 12, (150, 170, 60), 0.8 * (1 - fase), lado=3)
        ret(img, 104, 284, 122, 304, (120, 255, 140), 0.18 + 0.1 * math.sin(T * 6))
    _boia(img, ctx, T, nivel_caixa, abrindo=c in (9,) or (c == 10 and nivel_caixa < 0.97))
    if c == 11:
        brilhos(img, 40, 120, 180, 290, T, n=16, semente=11)
