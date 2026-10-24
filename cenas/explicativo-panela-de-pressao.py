"""Cena da panela de pressão (palco em pixel art, em corte): tampa, borracha, peso, válvula de segurança e trava."""
import math
import random

from darkops.palco import (brilhos, circulo, linha, luz, moldura, ondas_calor, poeira, ret, suave, vapor)

SERIE = "PULGA DO SABER · PANELA DE PRESSÃO"
MUNDO = (216, 384)

PECAS = {
    "panela": {"titulo": "Panela", "caixa": (40, 150, 180, 300), "ancora": (108, 200), "conta": False},
    "tampa": {"titulo": "Tampa presa", "caixa": (40, 140, 180, 180), "ancora": (108, 160)},
    "borracha": {"titulo": "Borracha de vedação", "caixa": (40, 150, 100, 186), "ancora": (52, 170)},
    "valvula": {"titulo": "Peso (válvula)", "caixa": (88, 116, 128, 160), "ancora": (108, 142)},
    "seguranca": {"titulo": "Válvula de segurança", "caixa": (126, 136, 160, 166), "ancora": (142, 156)},
    "trava": {"titulo": "Trava", "caixa": (150, 140, 200, 186), "ancora": (176, 164)},
}

PAREDE, FOGAO = (240, 214, 170), (70, 70, 80)
ALUMINIO, ALUMINIO_ESC, CONTORNO = (210, 214, 222), (150, 156, 170), (30, 30, 40)
AGUA, FEIJAO = (110, 170, 230), (110, 50, 40)


def _cenario(img, T):
    ret(img, 0, 0, 216, 300, PAREDE)
    for y in range(0, 300, 14):
        for x in range((y // 14 % 2) * 7, 216, 14):
            ret(img, x, y, x + 13, y + 13, (246, 224, 186))
    ret(img, 0, 280, 216, 384, FOGAO)
    ret(img, 0, 280, 216, 284, (40, 40, 48))
    for x in range(20, 216, 40):
        circulo(img, x, 320, 8, (50, 50, 58))
    poeira(img, T, n=20)


def _fogo(img, T):
    for k in range(9):
        luz(img, 66 + k * 10, 276 - (int(T * 14 + k) % 4), (80, 150, 255), 0.95)


def _panela(img, ctx, T, pressao, tremor):
    dx = math.sin(T * 40) * tremor
    ret(img, 50 + dx, 176, 166 + dx, 270, ALUMINIO)
    ret(img, 56 + dx, 182, 160 + dx, 264, (60, 64, 76))  # dentro (em corte)
    moldura(img, 50 + dx, 176, 166 + dx, 270, CONTORNO, 2)
    ret(img, 30 + dx, 190, 50 + dx, 196, (40, 40, 48))  # cabo
    ret(img, 56 + dx, 226, 160 + dx, 264, AGUA)
    rng = random.Random(3)
    for _ in range(26):  # feijões balançando na água
        x, y = rng.uniform(60, 156), rng.uniform(234, 260)
        ret(img, x + dx + math.sin(T * 3 + x) * 1.5, y, x + dx + 4 + math.sin(T * 3 + x) * 1.5, y + 3, FEIJAO)
    for k in range(int(6 + 10 * pressao)):  # bolhas subindo
        fase = (T * (1 + pressao) + k / 10) % 1.0
        circulo(img, 62 + (k * 13) % 94 + dx, 262 - fase * 34, 1.5, (220, 240, 255), cheio=False)
    if pressao > 0:  # vapor preso dentro, cada vez mais denso
        for k in range(int(30 * pressao)):
            x, y = rng.uniform(58, 158), rng.uniform(184, 224)
            luz(img, x + dx + math.sin(T * 4 + k) * 2, y, (240, 245, 255), 0.5 + 0.3 * pressao, lado=2)


def _tampa(img, ctx, T, tremor):
    p = ctx.peca("tampa")
    if p <= 0:
        return
    dx = math.sin(T * 40) * tremor
    y = 162 + (1 - p) * -60
    ret(img, 44 + dx, y, 172 + dx, y + 14, ALUMINIO_ESC)
    moldura(img, 44 + dx, y, 172 + dx, y + 14, CONTORNO, 2)
    ret(img, 166 + dx, y + 2, 196 + dx, y + 8, (40, 40, 48))  # cabo da tampa
    if ctx.peca("borracha") > 0:  # anel de borracha na beirada
        ret(img, 48 + dx, y + 12, 168 + dx, y + 16, (40, 40, 40), ctx.peca("borracha"))


def _valvula(img, ctx, T, levanta):
    p = ctx.peca("valvula")
    if p <= 0:
        return
    sobe = 6 * levanta + (math.sin(T * 30) * 2 if levanta > 0.5 else 0)
    ret(img, 104, 154, 112, 162, (60, 60, 70))  # pino com o furinho
    ret(img, 98, 140 - sobe - (1 - p) * 40, 118, 154 - sobe - (1 - p) * 40, (60, 60, 70))
    moldura(img, 98, 140 - sobe - (1 - p) * 40, 118, 154 - sobe - (1 - p) * 40, CONTORNO)
    if levanta > 0.3:
        for k in range(10):  # jato de vapor
            fase = (T * 3 + k / 10) % 1.0
            luz(img, 108 + math.sin(k) * 4 * fase, 138 - sobe - fase * 50, (250, 250, 255), 1 - fase,
                lado=2 + int(fase * 3))


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    _fogo(img, T)
    pressao = 0.0
    if c == 3 and ctx.acao("pressao") is not None:
        pressao = suave(ctx.acao("pressao") / 2.0)
    elif c >= 4:
        pressao = 1.0
    tremor = 0.0
    if c == 6 and ctx.acao("treme") is not None:
        tremor = 1.5 * suave(ctx.acao("treme") / 1.0)
    _panela(img, ctx, T, pressao, tremor)
    if c == 6 and tremor > 0:
        ret(img, 50, 176, 166, 270, (255, 60, 40), 0.15 + 0.1 * math.sin(T * 12))
    if c == 2 and ctx.acao("ferve") is not None:  # termômetro travado nos 100 graus e relógio
        ret(img, 186, 120, 194, 200, (245, 245, 250))
        moldura(img, 186, 120, 194, 200, CONTORNO)
        ret(img, 188, 150, 192, 200, (220, 40, 40))
        circulo(img, 190, 204, 6, (220, 40, 40))
        circulo(img, 30, 120, 16, (250, 250, 250))
        circulo(img, 30, 120, 16, CONTORNO, cheio=False)
        linha(img, (30, 120), (30 + math.cos(T * 5) * 12, 120 + math.sin(T * 5) * 12), CONTORNO, esp=2)
    if c <= 2:
        vapor(img, 108, 176, T, n=14, subida=50, espalha=90, semente=2)
    _tampa(img, ctx, T, tremor)
    if c == 5 and ctx.acao("escapa") is not None and ctx.peca("borracha") < 1:  # vapor escapando pela beirada
        for lado in (44, 172):
            for k in range(6):
                fase = (T * 3 + k / 6) % 1.0
                luz(img, lado + (fase * 20 if lado > 100 else -fase * 20), 168 - fase * 10, (250, 250, 255),
                    1 - fase)
    levanta = 0.0
    if c == 7 and ctx.acao("levanta") is not None:
        levanta = suave(ctx.acao("levanta") / 0.4)
    elif c in (8, 12):
        levanta = 1.0
    _valvula(img, ctx, T, levanta)
    seg = ctx.peca("seguranca")
    if seg > 0:
        pula = c == 9 and ctx.acao("emergencia") is not None
        y = 156 - (10 * suave(ctx.acao("emergencia") / 0.3) if pula else 0)
        ret(img, 136, y, 148, y + 6, (220, 60, 60), seg)
        moldura(img, 136, y, 148, y + 6, CONTORNO)
        if pula:
            vapor(img, 142, y, T, n=12, subida=60, espalha=10, semente=9)
    trava = ctx.peca("trava")
    if trava > 0:
        ret(img, 170, 152, 186, 160, (240, 180, 40), trava)  # pino amarelo da trava
        moldura(img, 170, 152, 186, 160, CONTORNO)
        if c == 10:  # mão tentando abrir e sendo barrada
            puxa = math.sin(T * 6) * 3
            ret(img, 186 + puxa, 150, 206 + puxa, 170, (240, 196, 150))
            brilhos(img, 166, 144, 192, 166, T, n=5, cor=(255, 120, 120), semente=10)
    if pressao > 0:
        ondas_calor(img, 108, 140, T, largura=80, altura=20, alfa=0.3 * pressao)
    if c == 12:
        brilhos(img, 30, 100, 200, 290, T, n=16, semente=12)
