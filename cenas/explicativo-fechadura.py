"""Cena da fechadura (palco em pixel art, em corte): tranca, lingueta, cilindro, pinos com mola e a chave."""
import math

from darkops.palco import (brilhos, circulo, linha, luz, moldura, poeira, ret, suave, vaivem)

SERIE = "PULGA DO SABER · FECHADURA"
MUNDO = (216, 384)

PECAS = {
    "porta": {"titulo": "Porta", "caixa": (10, 60, 206, 300), "ancora": (108, 120), "conta": False},
    "lingueta": {"titulo": "Lingueta e cilindro", "caixa": (40, 170, 210, 220), "ancora": (190, 197)},
    "pinos": {"titulo": "Pinos", "caixa": (56, 120, 164, 216), "ancora": (110, 150)},
    "chave": {"titulo": "Chave", "caixa": (0, 170, 170, 230), "ancora": (40, 205)},
}

PAREDE, MADEIRA, MADEIRA_ESC = (230, 200, 160), (170, 110, 60), (120, 74, 40)
LATAO, LATAO_ESC, CONTORNO = (230, 190, 90), (180, 140, 60), (30, 26, 24)
ACO, MOLA, VERMELHO = (200, 204, 214), (120, 130, 150), (230, 60, 60)
COLUNAS = [70, 90, 110, 130, 150]
DENTES = [8, 14, 10, 16, 12]  # tamanho de cada pino de baixo
LINHA_Y, FUNDO_Y = 180, 214


def _cenario(img, T):
    ret(img, 0, 0, 216, 384, PAREDE)
    ret(img, 14, 56, 202, 310, MADEIRA)  # porta
    moldura(img, 14, 56, 202, 310, CONTORNO, 2)
    for x in range(30, 200, 24):
        ret(img, x, 60, x + 1, 306, MADEIRA_ESC)
    ret(img, 0, 310, 216, 384, (150, 110, 80))
    poeira(img, T, n=20)


def _tranca(img, ctx):
    if ctx.cena > 2:
        return
    f = suave(ctx.acao("tranca") / 0.8) if ctx.acao("tranca") is not None else 0
    for x in (40, 176):
        ret(img, x - 6, 170, x + 6, 196, (60, 60, 70))
    ret(img, 230 - 210 * f, 176, 230 - 210 * f + 180, 190, MADEIRA_ESC)
    moldura(img, 230 - 210 * f, 176, 230 - 210 * f + 180, 190, CONTORNO)
    if ctx.cena == 2 and ctx.acao("fora") is not None:
        circulo(img, 108, 110, 16, (250, 250, 250))
        circulo(img, 108, 110, 16, CONTORNO, cheio=False)
        ret(img, 104, 100, 112, 104, CONTORNO)  # interrogação
        ret(img, 110, 104, 114, 110, CONTORNO)
        ret(img, 106, 110, 110, 114, CONTORNO)
        ret(img, 106, 118, 110, 121, CONTORNO)


def _mecanismo(img, ctx, T, levanta, gira, errada):
    p = ctx.peca("lingueta")
    if p <= 0:
        return
    a = p
    ret(img, 40, 120, 178, 228, LATAO, a)  # corpo da fechadura em corte
    moldura(img, 40, 120, 178, 228, CONTORNO, 2)
    ret(img, 52, LINHA_Y, 166, FUNDO_Y, LATAO_ESC, a)  # cilindro (miolo)
    for k in range(6):  # listras que andam quando o cilindro gira
        y = LINHA_Y + ((k * 6 + gira * 60) % 34)
        ret(img, 52, y, 166, y + 1, (150, 110, 40), a)
    moldura(img, 52, LINHA_Y, 166, FUNDO_Y, CONTORNO)
    recolhe = 22 * gira
    ret(img, 176 - recolhe, 190, 210 - recolhe, 204, ACO, a)  # lingueta entrando no batente
    moldura(img, 176 - recolhe, 190, 210 - recolhe, 204, CONTORNO)
    ret(img, 200, 180, 216, 214, (90, 70, 50))  # batente
    pinos = ctx.peca("pinos")
    if pinos <= 0:
        return
    for k, x in enumerate(COLUNAS):
        ret(img, x - 5, 128, x + 5, FUNDO_Y, (100, 80, 40), pinos)  # furo da coluna
        sobe = (34 - DENTES[k] - (FUNDO_Y - LINHA_Y)) * 0 + (FUNDO_Y - DENTES[k] - LINHA_Y) * levanta
        if errada and k == 2:
            sobe -= 5
        topo_baixo = FUNDO_Y - DENTES[k] - sobe
        ret(img, x - 4, topo_baixo, x + 4, topo_baixo + DENTES[k], (240, 200, 110), pinos)  # pino de baixo
        moldura(img, x - 4, topo_baixo, x + 4, topo_baixo + DENTES[k], CONTORNO)
        ret(img, x - 4, topo_baixo - 12, x + 4, topo_baixo, ACO, pinos)  # pino de cima
        moldura(img, x - 4, topo_baixo - 12, x + 4, topo_baixo, CONTORNO)
        for y in range(130, int(topo_baixo - 12), 3):  # mola
            ret(img, x - 4 + (y // 3 % 2) * 2, y, x + 2 + (y // 3 % 2) * 2, y + 1, MOLA, pinos)
        atravessado = topo_baixo - 12 < LINHA_Y < topo_baixo - 0.5
        if atravessado and ctx.cena in (6, 10):
            ret(img, x - 6, LINHA_Y - 1, x + 6, LINHA_Y + 1, VERMELHO, 0.6 + 0.4 * math.sin(T * 8))
    if ctx.cena in (6, 8, 9):  # a linha de corte
        for x in range(52, 166, 4):
            ret(img, x, LINHA_Y, x + 2, LINHA_Y + 1, (255, 255, 255) if levanta >= 1 else VERMELHO)


def _chave(img, ctx, entra, errada):
    p = ctx.peca("chave")
    if p <= 0 and not errada:
        return
    desloca = -186 * (1 - entra)  # a chave entra da esquerda
    x_ponta = 166 + desloca
    cor = (200, 204, 214) if not errada else (210, 160, 160)
    ret(img, x_ponta - 186, 204, x_ponta, 212, cor)  # lâmina
    moldura(img, x_ponta - 186, 204, x_ponta, 212, CONTORNO)
    for k, x in enumerate(COLUNAS):  # cada dente sobe até encostar no seu pino
        topo = LINHA_Y + DENTES[k] + (5 if errada and k == 2 else 0)
        xd = x + desloca
        ret(img, xd - 5, topo, xd + 5, 204, cor)
        moldura(img, xd - 5, topo, xd + 5, 205, CONTORNO)
    circulo(img, x_ponta - 196, 208, 12, cor)
    circulo(img, x_ponta - 196, 208, 12, CONTORNO, cheio=False)


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _tranca(img, ctx)
    levanta, gira, entra, errada = 0.0, 0.0, 0.0, False
    if c == 4 and ctx.acao("chave_fenda") is not None:
        gira = vaivem(ctx.acao("chave_fenda") / 1.0)
        ret(img, 0, 198, 60, 206, (60, 60, 70))  # chave de fenda
        ret(img, 0, 194, 24, 210, (220, 60, 60))
    if c == 8:
        a = ctx.acao("alinha")
        entra = suave(ctx.peca("chave"))
        levanta = suave(a / 1.0) if a is not None else 0.0
    elif c == 9:
        entra, levanta = 1.0, 1.0
        gira = vaivem((ctx.acao("gira") or 0) / 1.0)
    elif c == 10:
        entra, levanta, errada = 1.0, 1.0, ctx.acao("errada") is not None
    elif c >= 11:
        entra, levanta, gira = 1.0, 1.0, 1.0 if c == 12 else 0.0
    _mecanismo(img, ctx, T, levanta, gira, errada)
    _chave(img, ctx, entra, errada)
    if c == 10 and errada:
        linha(img, (96, 140), (124, 168), VERMELHO, esp=3)
        linha(img, (124, 140), (96, 168), VERMELHO, esp=3)
    if c == 9 and gira > 0:
        for k in range(10):
            a = -math.pi * 0.9 + k * 0.2
            luz(img, 110 + math.cos(a) * 30, 197 + math.sin(a) * 30, (255, 240, 160), gira)
    if c in (11, 12):
        brilhos(img, 40, 110, 200, 240, T, n=14, semente=c)
