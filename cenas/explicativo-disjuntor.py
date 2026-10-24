"""Cena do disjuntor (palco em pixel art, em corte): fusível, lâmina bimetálica, eletroímã e alavanca."""
import math

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ondas_calor, poeira, polilinha, ret,
                           suave, vaivem)

SERIE = "PULGA DO SABER · DISJUNTOR"
MUNDO = (216, 384)

PECAS = {
    "tomada": {"titulo": "Tomada", "caixa": (10, 220, 90, 300), "ancora": (40, 262), "conta": False},
    "fio": {"titulo": "Fio", "caixa": (10, 40, 120, 300), "ancora": (24, 120), "conta": False},
    "fusivel": {"titulo": "Fusível", "caixa": (10, 120, 60, 190), "ancora": (24, 152)},
    "lamina": {"titulo": "Lâmina bimetálica", "caixa": (72, 120, 150, 210), "ancora": (96, 166)},
    "eletroima": {"titulo": "Eletroímã", "caixa": (110, 140, 170, 220), "ancora": (142, 180)},
    "disjuntor": {"titulo": "Disjuntor", "caixa": (60, 90, 180, 240), "ancora": (120, 100)},
}

PAREDE, CONTORNO = (210, 200, 230), (26, 24, 34)
FIO, COBRE, CAIXA = (40, 40, 48), (210, 120, 60), (60, 60, 70)
CORRENTE = (255, 230, 90)
CAMINHO = [(24, 40), (24, 120), (24, 200), (40, 240)]
DENTRO = [(24, 110), (100, 110), (100, 126), (96, 140), (96, 190), (140, 196), (140, 226), (110, 236), (40, 250)]


def _cenario(img, T):
    ret(img, 0, 0, 216, 384, PAREDE)
    for y in range(0, 384, 20):
        ret(img, 0, y, 216, y + 1, (196, 186, 220))
    ret(img, 0, 300, 216, 384, (150, 130, 110))
    poeira(img, T, n=18)


def _tomada(img, ctx, T, aparelhos):
    ret(img, 20, 236, 60, 276, (245, 245, 250))
    moldura(img, 20, 236, 60, 276, CONTORNO, 2)
    for k in range(aparelhos):  # um monte de plugues e fios
        x = 26 + (k % 3) * 11
        ret(img, x, 248 + (k // 3) * 12, x + 8, 256 + (k // 3) * 12, (40, 40, 50))
        polilinha(img, [(x + 4, 256 + (k // 3) * 12), (x + 4 + k * 8, 300), (x + 4 + k * 14, 330)],
                  ((220, 60, 60), (60, 120, 220), (60, 180, 90), (230, 180, 40))[k % 4], esp=2)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    aparelhos = 6 if c in (1, 2, 11) else 2
    _tomada(img, ctx, T, aparelhos)
    disj = ctx.peca("lamina") > 0  # a partir da lâmina, a corrente passa por dentro do disjuntor
    caminho = DENTRO if disj else CAMINHO
    aberto = False
    entorta = 0.0
    if c == 6 and ctx.acao("entorta") is not None:
        entorta = suave(ctx.acao("entorta") / 1.5)
        aberto = entorta > 0.8
    puxa = 0.0
    if c == 8 and ctx.acao("puxa") is not None:
        puxa = suave(ctx.acao("puxa") / 0.25)
        aberto = puxa > 0.8
    if c == 7 and ctx.acao("curto") is not None and ctx.acao("curto") > 1.2:
        aberto = False
    if c == 10:
        aberto = ctx.acao("rearma") is None or ctx.acao("rearma") < 0.6
    if c == 11:
        aberto = int(T * 1.2) % 2 == 0  # cai, rearma, cai de novo
    fusivel_queimado = c == 3 and ctx.acao("derrete") is not None and ctx.acao("derrete") > 0.8
    corrente_alta = c in (1, 2, 7, 11)
    polilinha(img, caminho, FIO, esp=4)
    polilinha(img, caminho, COBRE, esp=2)
    corta = aberto or fusivel_queimado or c == 4
    if not corta:
        fluxo(img, caminho, ctx.T, CORRENTE, velocidade=60 if corrente_alta else 30, passo=5 if corrente_alta else 9)
    if c == 2 and ctx.acao("fogo") is not None:  # fio esquentando, derretendo a capa e pegando fogo
        f = suave(ctx.acao("fogo") / 2.0)
        polilinha(img, CAMINHO[:3], (255, 80, 40), alfa=f, esp=4)
        ondas_calor(img, 24, 130, T, largura=16, altura=40, alfa=f)
        if f > 0.6:
            for k in range(8):
                fase = (T * 3 + k / 8) % 1.0
                luz(img, 20 + (k % 3) * 4, 180 - fase * 30, (255, int(200 - 120 * fase), 40), 1 - fase, lado=3)
    fus = ctx.peca("fusivel")
    if fus > 0 and c in (3, 4):
        voa = suave((ctx.acao("lixo") or 0) / 1.0) if c == 4 else 0
        x, y = 14 + voa * 160, 140 - voa * 60
        ret(img, x, y, x + 20, y + 30, (200, 230, 240), 0.8 * fus)
        moldura(img, x, y, x + 20, y + 30, CONTORNO)
        ret(img, x + 2, y - 4, x + 18, y, (180, 180, 190))
        ret(img, x + 2, y + 30, x + 18, y + 34, (180, 180, 190))
        if fusivel_queimado or c == 4:
            ret(img, x + 9, y + 4, x + 11, y + 12, (60, 60, 60))
            ret(img, x + 9, y + 18, x + 11, y + 26, (60, 60, 60))
            ret(img, x + 4, y + 12, x + 16, y + 18, (80, 70, 60), 0.6)
        else:
            ret(img, x + 9, y + 4, x + 11, y + 26, COBRE)
    if disj:  # o disjuntor em corte
        caixa = max(ctx.peca("disjuntor"), 0.35)
        moldura(img, 64, 96, 176, 240, CONTORNO, 2)
        ret(img, 66, 98, 174, 238, CAIXA, 0.25 * caixa)
        alav = -0.9 if aberto else 0.9  # alavanca em cima
        linha(img, (110, 98), (110 + math.sin(alav) * 18, 98 - math.cos(alav) * 18), (40, 40, 48), esp=5)
        ret(img, 104, 92, 116, 100, (90, 90, 100))
        abre = 8 if aberto else 0  # contato
        ret(img, 92, 124, 104, 130, (220, 200, 80))
        ret(img, 100 + abre, 120 - abre, 112 + abre, 126 - abre, (220, 200, 80))
        for k in range(26):  # lâmina de dois metais, entortando
            y = 140 + k * 2
            dx = entorta * 10 * (k / 26) ** 2
            ret(img, 92 + dx, y, 95 + dx, y + 2, (210, 120, 60))
            ret(img, 95 + dx, y, 98 + dx, y + 2, (170, 176, 190))
        for k in range(8):  # mola
            ret(img, 120 + (k % 2) * 3, 120 + k * 3 - (6 if aberto else 0), 128 + (k % 2) * 3, 121 + k * 3, (150, 150, 165))
        if ctx.peca("eletroima") > 0:
            ret(img, 132, 156, 140, 206, (90, 90, 100))  # núcleo de ferro
            for y in range(158, 204, 3):
                ret(img, 128, y, 144, y + 2, COBRE, ctx.peca("eletroima"))
            if puxa > 0 or (c == 7 and ctx.acao("curto") is not None):
                circulo(img, 136, 180, 24, (150, 200, 255), 0.15 + 0.1 * math.sin(T * 20))
                brilhos(img, 120, 150, 156, 210, T, n=6, cor=(170, 210, 255), semente=8)
    if c == 7 and ctx.acao("curto") is not None:  # curto-circuito: faísca grande
        for k in range(14):
            a = k * 0.45 + T * 3
            r = 6 + (T * 40 + k * 7) % 20
            luz(img, 40 + math.cos(a) * r, 250 + math.sin(a) * r, (255, 255, 200), 0.9, lado=2)
    if c == 11:
        y = 60
        for k in range(12):  # triângulo de aviso piscando
            linha(img, (180 - k, y + k * 2), (180 + k, y + k * 2), (250, 200, 40), 0.6 + 0.4 * math.sin(T * 8))
        ret(img, 179, y + 6, 181, y + 16, CONTORNO)
        ret(img, 179, y + 19, 181, y + 21, CONTORNO)
    if c == 12:
        brilhos(img, 60, 80, 190, 250, T, n=16, semente=12)
