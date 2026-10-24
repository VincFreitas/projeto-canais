"""Cena da geladeira (palco em pixel art): a caixa de gelo vira geladeira, peça por peça.

Ordem do roteiro: caixa com gelo, entregador, gelo derrete, calor sai, álcool na mão, evaporador, gás ferve,
compressor, condensador, parte de trás quente, tubo capilar, termostato, vedação com ímã, geladeira pronta.
"""
import math

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ondas_calor, ponto, poeira, polilinha,
                           ret, suave, vaivem, vapor)

SERIE = "PULGA DO SABER · GELADEIRA"
MUNDO = (216, 384)

PECAS = {
    "caixa": {"titulo": "Caixa", "caixa": (36, 100, 152, 296), "ancora": (92, 112)},
    "gelo": {"titulo": "Gelo", "caixa": (64, 130, 132, 192), "ancora": (98, 150), "conta": False},
    "entregador": {"titulo": "Entregador", "caixa": (118, 180, 216, 296), "ancora": (170, 205), "conta": False},
    "bolha": {"titulo": "Álcool", "caixa": (66, 44, 170, 142), "ancora": (116, 98), "conta": False},
    "evaporador": {"titulo": "Evaporador", "caixa": (48, 116, 136, 172), "ancora": (92, 144)},
    "compressor": {"titulo": "Compressor", "caixa": (146, 244, 206, 294), "ancora": (175, 270)},
    "condensador": {"titulo": "Condensador", "caixa": (150, 116, 212, 254), "ancora": (182, 180)},
    "termometro": {"titulo": "Termômetro", "caixa": (150, 40, 216, 130), "ancora": (204, 84), "conta": False},
    "capilar": {"titulo": "Tubo capilar", "caixa": (48, 92, 172, 134), "ancora": (110, 104)},
    "termostato": {"titulo": "Termostato", "caixa": (96, 188, 142, 232), "ancora": (124, 208)},
    "vedacao": {"titulo": "Vedação", "caixa": (34, 104, 154, 296), "ancora": (142, 200)},
}

PAREDE, REJUNTE = (46, 86, 150), (60, 104, 170)
PISO, PISO_LINHA = (150, 96, 58), (120, 74, 44)
MADEIRA, MADEIRA_ESC = (164, 108, 60), (110, 68, 34)
CREME, CREME_ESC, INTERIOR = (236, 226, 196), (190, 176, 140), (212, 202, 170)
CONTORNO = (34, 28, 30)
COBRE, COBRE_CLARO = (196, 112, 52), (240, 170, 100)
GELO, GELO_CLARO = (150, 210, 245), (230, 248, 255)
FRIO, QUENTE = (150, 220, 255), (255, 130, 40)

EVAPORADOR = [(56, 124), (128, 124), (128, 133), (56, 133), (56, 142), (128, 142), (128, 151), (56, 151),
              (56, 160), (128, 160)]
SAIDA_EVAP = [(128, 160), (148, 160), (148, 262), (156, 262)]
COMP_COND = [(198, 268), (206, 268), (206, 248)]
CONDENSADOR = [(206, 248), (158, 248), (158, 238), (206, 238), (206, 228), (158, 228), (158, 218), (206, 218),
               (206, 208), (158, 208), (158, 198), (206, 198), (206, 188), (158, 188), (158, 178), (206, 178),
               (206, 168), (158, 168), (158, 158), (206, 158), (206, 148), (158, 148), (158, 138), (206, 138),
               (206, 128), (162, 128)]
CAPILAR = [(162, 128), (162, 100), (56, 100), (56, 124)]


def _cenario(img, T):
    ret(img, 0, 0, 216, 296, PAREDE)
    for y in range(8, 296, 16):  # azulejos
        ret(img, 0, y, 216, y + 1, REJUNTE)
    for x in range(8, 216, 16):
        ret(img, x, 0, x + 1, 296, REJUNTE)
    ret(img, 8, 36, 44, 84, (20, 26, 60))  # janela à noite
    moldura(img, 7, 35, 45, 85, (230, 220, 200), 2)
    ret(img, 25, 36, 27, 84, (230, 220, 200))
    for k, (x, y) in enumerate(((14, 44), (34, 52), (18, 68), (38, 74), (30, 42))):
        v = 0.5 + 0.5 * math.sin(T * 2 + k * 1.7)
        ponto(img, x, y, (255, 255, 220), 0.4 + 0.6 * v)
    circulo(img, 36, 46, 4, (250, 240, 200))
    ret(img, 107, 0, 109, 26, (40, 34, 30))  # lâmpada
    ret(img, 101, 26, 115, 32, (90, 70, 50))
    for r, a in ((26, 0.06), (18, 0.08), (10, 0.12)):
        circulo(img, 108, 36, r, (255, 220, 140), a)
    circulo(img, 108, 35, 4, (255, 236, 170))
    ret(img, 0, 296, 216, 384, PISO)
    for y in range(302, 384, 12):
        ret(img, 0, y, 216, y + 1, PISO_LINHA)
    ret(img, 0, 294, 216, 297, (90, 56, 34))
    poeira(img, T, n=26)


def _caixa(img, ctx, T):
    p = ctx.peca("caixa")
    if p <= 0:
        return 0
    cair = (1 - p) * -70  # a caixa desce e encaixa no chão
    moderna = ctx.peca("evaporador")
    cor = tuple(int(MADEIRA[k] + (CREME[k] - MADEIRA[k]) * moderna) for k in range(3))
    esc = tuple(int(MADEIRA_ESC[k] + (CREME_ESC[k] - MADEIRA_ESC[k]) * moderna) for k in range(3))
    dentro = tuple(int((MADEIRA_ESC[k] * 0.8) + (INTERIOR[k] - MADEIRA_ESC[k] * 0.8) * moderna) for k in range(3))
    y0 = 108 + cair
    ret(img, 44, y0, 146, 292 + cair, cor)
    ret(img, 40, y0 - 6, 150, y0 + 2, esc)  # tampa
    ret(img, 50, y0 + 8, 140, 286 + cair, dentro)
    ret(img, 50, y0 + 8, 54, 286 + cair, esc)  # sombra da lateral de dentro
    for ys in (186, 236):
        ret(img, 50, ys + cair, 140, ys + 3 + cair, (200, 200, 205) if moderna > 0.5 else esc)
    moldura(img, 44, y0, 146, 292 + cair, CONTORNO)
    ret(img, 48, 292 + cair, 58, 296 + cair, CONTORNO)  # pés
    ret(img, 132, 292 + cair, 142, 296 + cair, CONTORNO)
    if moderna < 0.5:  # tábuas da caixa de madeira
        for x in range(60, 140, 20):
            ret(img, x, y0 + 2, x + 1, y0 + 8, MADEIRA_ESC)
    return cair


def _porta(img, ctx, T):
    fechar = ctx.acao("fechar")
    reabrir = ctx.acao("pronto")
    f = vaivem(fechar / 1.1) if fechar is not None else 0.0
    if reabrir is not None:
        f *= 1 - vaivem(reabrir / 0.9)
    if f < 0.05:  # porta aberta, vista de lado, à esquerda
        ret(img, 30, 108, 44, 292, CREME if ctx.peca("evaporador") else MADEIRA)
        moldura(img, 30, 108, 44, 292, CONTORNO)
        ret(img, 32, 190, 34, 214, (140, 140, 150))
        return
    larg = 102 * f
    ret(img, 44, 108, 44 + larg, 292, CREME)
    moldura(img, 44, 108, 44 + larg, 292, CONTORNO)
    if f > 0.9:
        ret(img, 132, 180, 136, 220, (150, 150, 160))  # puxador
        # borracha com ímã: brilha em volta da porta
        v = 0.6 + 0.4 * math.sin(T * 6)
        for a, b in (((45, 109), (145, 109)), ((45, 291), (145, 291)), ((45, 109), (45, 291)), ((145, 109), (145, 291))):
            linha(img, a, b, (230, 90, 220), 0.8 * v, esp=2)
        brilhos(img, 44, 108, 148, 292, T, n=12, cor=(255, 170, 255), semente=21)


def _comida(img, cair):
    ret(img, 60, 248 + cair, 70, 284 + cair, (245, 245, 250))  # leite
    ret(img, 62, 242 + cair, 68, 248 + cair, (60, 120, 220))
    moldura(img, 60, 248 + cair, 70, 284 + cair, CONTORNO)
    circulo(img, 86, 278 + cair, 6, (220, 50, 60))  # maçã
    ret(img, 86, 270 + cair, 87, 273 + cair, (60, 120, 40))
    ret(img, 100, 272 + cair, 120, 284 + cair, (250, 210, 60))  # queijo
    moldura(img, 100, 272 + cair, 120, 284 + cair, CONTORNO)
    for k in range(3):
        circulo(img, 104 + k * 6, 278 + cair, 1, (220, 170, 40))
    ret(img, 64, 222, 84, 236, (120, 200, 90))  # verduras na prateleira do meio
    ret(img, 92, 226, 128, 236, (240, 140, 70))


def _gelo(img, ctx, T):
    if ctx.cena > 3:
        return
    derrete = ctx.acao("derreter")
    m = suave(derrete / 4.0) if derrete is not None else 0.0
    altura = 38 * (1 - 0.85 * m)
    y1 = 186
    y0 = y1 - altura
    ret(img, 72, y0, 122, y1, GELO)
    ret(img, 74, y0 + 2, 84, y0 + 6, GELO_CLARO)
    ret(img, 74, y0 + 2, 77, y1 - 4, GELO_CLARO)
    moldura(img, 72, y0, 122, y1, (60, 120, 170))
    brilhos(img, 66, y0 - 8, 128, y1, T, n=6, cor=(220, 245, 255), semente=4)
    if m > 0:  # gotas e poça
        for k in range(6):
            fase = (T * 1.4 + k / 6) % 1.0
            luz(img, 76 + k * 8, y1 + fase * 104, (120, 190, 240), 0.9, lado=2)
        larg = 30 + 60 * m
        ret(img, 96 - larg / 2, 292, 96 + larg / 2, 295, (110, 180, 230))
        ret(img, 96 - larg / 3, 291, 96 + larg / 3, 292, (170, 220, 250))


def _entregador(img, ctx, T):
    entrega = ctx.acao("entregar")
    if ctx.cena != 2 or entrega is None:
        return
    x = 236 - 70 * suave(entrega / 2.4)
    passo = int(T * 7) % 2 if entrega < 2.4 else 0
    y = 236
    ret(img, x + 4, y, x + 18, y + 6, (40, 90, 200))  # boné
    ret(img, x + 2, y + 5, x + 20, y + 7, (30, 70, 170))
    ret(img, x + 5, y + 7, x + 17, y + 18, (240, 196, 150))  # rosto
    ponto(img, x + 8, y + 11, CONTORNO, lado=2)
    ret(img, x + 3, y + 18, x + 19, y + 38, (50, 110, 210))  # camisa
    ret(img, x + 4, y + 38, x + 18, y + 48, (40, 40, 60))  # calça
    ret(img, x + 4 + passo * 3, y + 48, x + 9 + passo * 3, y + 58, (30, 30, 40))
    ret(img, x + 13 - passo * 3, y + 48, x + 18 - passo * 3, y + 58, (30, 30, 40))
    ret(img, x - 16, y + 20, x + 4, y + 36, GELO)  # o bloco de gelo nos braços
    moldura(img, x - 16, y + 20, x + 4, y + 36, (60, 120, 170))
    ret(img, x - 14, y + 22, x - 10, y + 25, GELO_CLARO)
    ret(img, x - 2, y + 24, x + 6, y + 28, (240, 196, 150))


def _calor_sai(img, ctx, T):
    if ctx.cena != 4 or ctx.acao("calor_sai") is None:
        return
    a = suave(ctx.acao("calor_sai") / 0.6)
    fluxo(img, [(92, 230), (92, 150), (92, 96), (140, 70), (200, 60)], ctx.T, QUENTE, velocidade=40, passo=9,
          alfa=a)
    for x in (70, 92, 114):
        ondas_calor(img, x, 200, ctx.T, largura=14, altura=40, alfa=0.7 * a)


def _bolha(img, ctx, T):
    alcool = ctx.acao("alcool")
    if ctx.cena != 5 or alcool is None:
        return
    r = 48 * suave(alcool / 0.35)
    if r < 4:
        return
    circulo(img, 116, 94, r + 2, CONTORNO)
    circulo(img, 116, 94, r, (250, 250, 252))
    for k in range(3):  # rabinho da bolha
        circulo(img, 100 - k * 8, 150 + k * 9, 4 - k, (250, 250, 252))
    if r < 40:
        return
    ret(img, 92, 100, 140, 124, (240, 196, 150))  # mão aberta
    for k in range(4):
        ret(img, 96 + k * 11, 82, 104 + k * 11, 102, (240, 196, 150))
    ret(img, 84, 104, 94, 116, (240, 196, 150))
    moldura(img, 92, 100, 140, 124, (180, 130, 100))
    for k in range(4):  # gotas de álcool que viram vapor
        fase = (T * 0.8 + k * 0.25) % 1.0
        if fase < 0.4:
            luz(img, 100 + k * 10, 96, (150, 210, 255), 1 - fase, lado=3)
    vapor(img, 116, 92, T, n=12, cor=(220, 240, 255), subida=36, espalha=34, semente=8)
    brilhos(img, 92, 100, 140, 124, T, n=6, cor=(190, 230, 255), semente=9)


def _evaporador(img, ctx, T):
    p = ctx.peca("evaporador")
    if p <= 0:
        return
    polilinha(img, EVAPORADOR, CONTORNO, esp=4, progresso=p)
    polilinha(img, EVAPORADOR, COBRE, esp=2, progresso=p)
    if p >= 1 and ctx.cena >= 7:
        gelado = suave(ctx.acao("evapora") / 1.0) if ctx.acao("evapora") is not None else 1.0
        for k, (a, b) in enumerate(zip(EVAPORADOR, EVAPORADOR[1:])):  # gelo em volta do cano
            for f in (0.2, 0.5, 0.8):
                ponto(img, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f - 2, (235, 248, 255), 0.7 * gelado)
        fluxo(img, EVAPORADOR, ctx.T, (200, 240, 255), velocidade=30, passo=7, alfa=gelado)
        brilhos(img, 54, 118, 132, 168, T, n=8, cor=FRIO, semente=11)
        if ctx.cena == 7:  # o calor da comida sobe e entra no cano
            for k in range(8):
                fase = (T * 0.7 + k / 8) % 1.0
                x = 64 + k * 9
                c = tuple(int(QUENTE[j] + (FRIO[j] - QUENTE[j]) * fase) for j in range(3))
                luz(img, x, 270 - fase * 110, c, 0.9)


def _compressor(img, ctx, T, ligado):
    p = ctx.peca("compressor")
    if p <= 0:
        return
    polilinha(img, SAIDA_EVAP, CONTORNO, esp=4, progresso=p)
    polilinha(img, SAIDA_EVAP, COBRE, esp=2, progresso=p)
    cair = (1 - p) * -60
    vibra = (int(T * 30) % 2) if ligado else 0
    x, y = 154 + vibra, 252 + cair
    ret(img, x, y + 8, x + 44, y + 40, (40, 40, 48))
    circulo(img, x + 22, y + 10, 20, (40, 40, 48))
    ret(img, x + 4, y + 10, x + 10, y + 34, (80, 80, 92))  # brilho
    ret(img, x + 12, y + 22, x + 32, y + 30, (200, 200, 60))  # plaquinha
    ret(img, x - 2, y + 38, x + 46, y + 42, CONTORNO)
    for bx in (x + 2, x + 40):
        ret(img, bx, y + 36, bx + 3, y + 39, (160, 160, 170))
    if ligado:
        circulo(img, x + 22, y + 18, 26, QUENTE, 0.08 + 0.05 * math.sin(T * 9))
        fluxo(img, SAIDA_EVAP, ctx.T, (150, 220, 255), velocidade=30, passo=8)


def _condensador(img, ctx, T, ligado):
    p = ctx.peca("condensador")
    if p <= 0:
        return
    polilinha(img, COMP_COND, CONTORNO, esp=4, progresso=p)
    polilinha(img, COMP_COND, COBRE, esp=2, progresso=p)
    polilinha(img, CONDENSADOR, CONTORNO, esp=3, progresso=p)
    polilinha(img, CONDENSADOR, (70, 70, 80), esp=1, progresso=p)
    for x in (166, 182, 198):  # arames verticais da grade
        ret(img, x, 126, x + 1, 250 * p + 126 * (1 - p), (60, 60, 70))
    if p >= 1 and ligado:
        quente = 0.6 + 0.4 * math.sin(T * 4)
        polilinha(img, CONDENSADOR, QUENTE, alfa=0.5 * quente, esp=1)
        fluxo(img, COMP_COND + CONDENSADOR[1:], ctx.T, (255, 90, 60), cor_fim=(255, 200, 90), velocidade=34, passo=9)
        for y in (150, 190, 230):
            ondas_calor(img, 210, y, ctx.T, largura=10, altura=24, alfa=0.6)


def _termometro(img, ctx, T):
    if ctx.cena < 10:
        return
    sobe = suave(ctx.acao("termometro") / 2.0) if ctx.acao("termometro") is not None else 1.0
    ret(img, 200, 46, 208, 112, (240, 240, 245))
    moldura(img, 200, 46, 208, 112, CONTORNO)
    circulo(img, 204, 116, 6, (220, 40, 40))
    nivel = 108 - 50 * sobe
    ret(img, 202, nivel, 206, 112, (220, 40, 40))
    for y in range(52, 108, 8):
        ret(img, 198, y, 200, y + 1, CONTORNO)


def _capilar(img, ctx, T):
    p = ctx.peca("capilar")
    if p <= 0:
        return
    pontos = []  # tubinho fino em mola
    for (a, b) in zip(CAPILAR, CAPILAR[1:]):
        n = int(math.dist(a, b) / 2)
        for k in range(n):
            f = k / max(n, 1)
            dx, dy = b[0] - a[0], b[1] - a[1]
            comp = math.hypot(dx, dy) or 1
            onda = math.sin(k * 1.4) * 1.5
            pontos.append((a[0] + dx * f - dy / comp * onda, a[1] + dy * f + dx / comp * onda))
    pontos.append(CAPILAR[-1])
    polilinha(img, pontos, CONTORNO, esp=2, progresso=p)
    polilinha(img, pontos, COBRE_CLARO, esp=1, progresso=p)
    if p >= 1:
        fluxo(img, CAPILAR, ctx.T, (255, 170, 80), cor_fim=(150, 230, 255), velocidade=26, passo=7)


def _termostato(img, ctx, T):
    p = ctx.peca("termostato")
    if p <= 0:
        return 1
    ciclo = 1 if ctx.cena != 12 else int(ctx.T / 1.6) % 2  # na cena dele: liga e desliga
    circulo(img, 124, 208, 9 * p, (245, 245, 250))
    circulo(img, 124, 208, 9 * p, CONTORNO, cheio=False)
    ang = -2.2 + (2.0 if ciclo else 0.6) + 0.1 * math.sin(T * 3)
    linha(img, (124, 208), (124 + math.cos(ang) * 7 * p, 208 + math.sin(ang) * 7 * p), (220, 40, 40))
    luz(img, 120, 194, (80, 230, 110) if ciclo else (230, 60, 60), 1.0, lado=3)
    return ciclo


def desenhar(ctx):
    img, T = ctx.img, ctx.T
    _cenario(img, T)
    cair = _caixa(img, ctx, T)
    if ctx.peca("caixa") > 0:
        _comida(img, cair)
        if ctx.cena >= 14:  # luz de dentro acesa
            ret(img, 50, 116, 140, 286, (255, 240, 180), 0.18 + 0.05 * math.sin(T * 3))
    _gelo(img, ctx, T)
    _evaporador(img, ctx, T)
    ligado = _termostato(img, ctx, T) == 1 and ctx.cena >= 8
    _capilar(img, ctx, T)
    _compressor(img, ctx, T, ligado)
    _condensador(img, ctx, T, ligado)
    _termometro(img, ctx, T)
    _calor_sai(img, ctx, T)
    _porta(img, ctx, T)
    _entregador(img, ctx, T)
    _bolha(img, ctx, T)
    if ctx.cena == 1:
        brilhos(img, 60, 120, 132, 196, T, n=8, cor=(220, 245, 255), semente=2)
    if ctx.cena >= 14:
        brilhos(img, 30, 90, 210, 300, T, n=16, semente=31)
