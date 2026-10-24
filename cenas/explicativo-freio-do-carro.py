"""Cena do freio do carro (palco em pixel art): da mão na roda ao freio hidráulico com pinça."""
import math

from darkops.palco import (brilhos, circulo, fluxo, linha, luz, moldura, ondas_calor, poeira, polilinha, ret,
                           suave)

SERIE = "PULGA DO SABER · FREIO"
MUNDO = (216, 384)

PECAS = {
    "roda": {"titulo": "Roda", "caixa": (96, 176, 206, 286), "ancora": (150, 230), "conta": False},
    "disco": {"titulo": "Disco e pastilhas", "caixa": (112, 190, 188, 270), "ancora": (150, 210)},
    "pedal": {"titulo": "Pedal", "caixa": (10, 190, 90, 290), "ancora": (40, 240), "conta": False},
    "fluido": {"titulo": "Fluido de freio", "caixa": (40, 160, 170, 220), "ancora": (110, 172)},
    "cilindro": {"titulo": "Cilindro mestre", "caixa": (30, 190, 100, 224), "ancora": (66, 206)},
    "pistao_roda": {"titulo": "Pistão largo", "caixa": (126, 168, 176, 206), "ancora": (150, 186)},
    "pinca": {"titulo": "Pinça", "caixa": (120, 166, 182, 214), "ancora": (162, 182)},
}

FUNDO, CHAO = (60, 64, 84), (90, 90, 100)
PNEU, ARO, METAL, CONTORNO = (34, 34, 40), (180, 184, 196), (200, 204, 214), (20, 20, 28)
FLUIDO, VERMELHO = (250, 210, 60), (210, 50, 50)
CX, CY = 150, 230


def _cenario(img, T):
    ret(img, 0, 0, 216, 286, FUNDO)
    for x in range(0, 216, 36):  # garagem: tijolos
        for y in range(0, 286, 14):
            ret(img, x + (y // 14 % 2) * 18, y, x + (y // 14 % 2) * 18 + 34, y + 12, (70, 74, 96))
    ret(img, 0, 286, 216, 384, CHAO)
    for x in range(0, 216, 30):
        ret(img, x, 300, x + 16, 302, (220, 200, 60))
    poeira(img, T, n=18)


def _roda(img, giro, quente):
    circulo(img, CX, CY, 52, PNEU)
    circulo(img, CX, CY, 40, ARO)
    circulo(img, CX, CY, 40, CONTORNO, cheio=False)
    for k in range(5):  # raios girando
        a = giro + k * 2 * math.pi / 5
        linha(img, (CX, CY), (CX + math.cos(a) * 38, CY + math.sin(a) * 38), (120, 124, 136), esp=4)
    circulo(img, CX, CY, 6, (90, 90, 100))
    for k in range(10):  # sulcos do pneu
        a = giro + k * 0.63
        linha(img, (CX + math.cos(a) * 44, CY + math.sin(a) * 44), (CX + math.cos(a) * 51, CY + math.sin(a) * 51),
              (60, 60, 70), esp=2)


def _disco(img, ctx, giro, calor):
    p = ctx.peca("disco")
    if p <= 0:
        return
    r = 30 * p
    cor = tuple(int(METAL[k] + ((255, 110, 40)[k] - METAL[k]) * calor) for k in range(3))
    circulo(img, CX, CY, r, cor)
    circulo(img, CX, CY, r, CONTORNO, cheio=False)
    for k in range(6):  # furos do disco girando
        a = giro + k * math.pi / 3
        circulo(img, CX + math.cos(a) * r * 0.7, CY + math.sin(a) * r * 0.7, 2, (90, 90, 100))
    if p >= 1 and ctx.peca("pinca") <= 0:  # pastilhas soltas antes da pinça
        ret(img, CX - 8, CY - 34, CX + 8, CY - 28, (60, 50, 50))


def _pinca(img, ctx, aperto):
    p = ctx.peca("pinca")
    pist = ctx.peca("pistao_roda")
    if p > 0:
        ret(img, CX - 18, CY - 52 + (1 - p) * -40, CX + 18, CY - 26 + (1 - p) * -40, VERMELHO)
        moldura(img, CX - 18, CY - 52 + (1 - p) * -40, CX + 18, CY - 26 + (1 - p) * -40, CONTORNO)
    if pist > 0:  # pistão largo empurrando a pastilha
        ret(img, CX - 12, CY - 46, CX + 12, CY - 40 + aperto * 4, (180, 180, 190), pist)
    if p > 0 or pist > 0:
        ret(img, CX - 10, CY - 38 + aperto * 4, CX + 10, CY - 32 + aperto * 4, (60, 50, 50))


def _pedal(img, ctx, T, pisado, fundo=False):
    if ctx.cena < 5:
        return
    desce = (14 if fundo else 8) * pisado
    linha(img, (60, 196), (40, 262 + desce), (90, 90, 100), esp=4)  # haste do pedal
    ret(img, 26, 258 + desce, 54, 268 + desce, (60, 60, 70))
    moldura(img, 26, 258 + desce, 54, 268 + desce, CONTORNO)
    ret(img, 8, 242 + desce, 40, 258 + desce, (40, 40, 50))  # sapato
    ret(img, 8, 236 + desce, 20, 244 + desce, (40, 40, 50))


CANO = [(96, 207), (112, 207), (112, 170), (CX, 170), (CX, 178)]


def desenhar(ctx):
    img, T, c = ctx.img, ctx.T, ctx.cena
    _cenario(img, T)
    if c >= 2:  # para-lama do carro
        for x in range(60, 216):
            topo = 150 - 40 * math.exp(-((x - 170) / 60) ** 2)
            ret(img, x, topo, x + 1, 176 - max(0, 26 - abs(x - CX) * 0.5), (200, 40, 50))
        ret(img, 60, 120, 216, 124, (240, 240, 250), 0.6)
    freando = 0.0
    if c == 4 and ctx.acao("atrito") is not None:
        freando = suave(ctx.acao("atrito") / 2.0)
    elif c in (7, 8, 9, 10) and (ctx.acao("pressao") is not None or c > 7):
        freando = 0.6 + 0.4 * math.sin(T * 2) ** 2
    elif c == 11:
        freando = 0.2
    elif c == 12:
        freando = suave((ctx.acao("pronto") or 0) / 2.0)
    vel = 7 * (1 - freando)
    giro = T * vel
    _roda(img, giro, freando)
    calor = freando if c in (4, 12) else 0.4 * freando
    _disco(img, ctx, giro, calor)
    _pinca(img, ctx, freando)
    if freando > 0.3 and c in (4, 10, 12):
        for k in range(8):  # faíscas do atrito
            fase = (T * 2 + k / 8) % 1.0
            a = -1.2 + k * 0.3
            luz(img, CX + 14 + math.cos(a) * fase * 30, CY - 34 + math.sin(a) * fase * 30 + fase * fase * 20,
                (255, int(220 - 100 * fase), 60), 1 - fase)
        ondas_calor(img, CX, CY - 30, T, largura=40, altura=24, alfa=0.7)
    if c == 1 and ctx.acao("mao") is not None:  # luva tentando segurar
        x = 40 + 40 * suave(ctx.acao("mao") / 0.8)
        ret(img, x, 210, x + 24, 236, (240, 240, 245))
        moldura(img, x, 210, x + 24, 236, CONTORNO)
    if c == 2 and ctx.acao("carro") is not None:  # placa de peso
        ret(img, 20, 70, 100, 100, (240, 200, 60))
        moldura(img, 20, 70, 100, 100, CONTORNO, 2)
        ret(img, 40, 80, 80, 90, CONTORNO)
    pisado = 1.0 if c in (7, 8, 9, 10, 12) else (0.5 + 0.5 * math.sin(T * 3) if c == 5 else 0.0)
    _pedal(img, ctx, T, pisado, fundo=c == 11)
    fl = ctx.peca("fluido")
    if fl > 0:
        polilinha(img, CANO, CONTORNO, esp=6, progresso=fl)
        polilinha(img, CANO, FLUIDO, esp=4, progresso=fl)
        if c >= 7:
            fluxo(img, CANO, ctx.T, (255, 255, 200), velocidade=50 if pisado else 0, passo=8)
        if c == 11:  # bolhas de ar no cano
            for k in range(4):
                circulo(img, 112 + (k % 2) * 3, 200 - k * 8 + math.sin(T * 4 + k) * 2, 2, (255, 255, 255),
                        cheio=False)
    elif c == 5:  # caminho pontilhado do pé até a roda
        for k in range(10):
            luz(img, 60 + k * 9, 230 - k * 5, (255, 255, 255), 0.4 + 0.4 * math.sin(T * 5 - k))
    cil = ctx.peca("cilindro")
    if cil > 0:
        ret(img, 56, 198, 98, 216, (160, 166, 180))
        moldura(img, 56, 198, 98, 216, CONTORNO)
        ret(img, 62 + pisado * 10, 200, 68 + pisado * 10, 214, (90, 90, 100))  # pistão empurrado
        ret(img, 70, 186, 90, 198, FLUIDO)  # reservatório
        moldura(img, 70, 186, 90, 198, CONTORNO)
    if c == 9 and ctx.acao("forca") is not None:  # seta pequena no pé, seta grande na roda
        f = suave(ctx.acao("forca") / 0.6)
        ret(img, 30, 226, 40, 240, (100, 220, 120), f)
        ret(img, CX - 10, CY - 80, CX + 10, CY - 56, (100, 220, 120), f)
    if c == 12:
        brilhos(img, 60, 120, 216, 290, T, n=14, semente=12)
