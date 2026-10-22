"""Infográficos animados (motion graphics) num card de vidro sobre o clipe da cena.

Uma cena do roteiro ganha uma animação com o campo "animacao":

  {"tipo": "contador", "ate": 243, "sufixo": " dias", "rotulo": "1 dia em Vênus"}
  {"tipo": "comparacao", "itens": [{"rotulo": "Dia", "valor": 243}, {"rotulo": "Ano", "valor": 225}],
   "unidade": "dias", "titulo": "Vênus"}
  {"tipo": "linha_do_tempo", "marcos": [{"valor": -2560, "texto": "2560 a.C.", "rotulo": "Pirâmide"}, ...]}
  {"tipo": "icones", "simbolo": "coracao", "quantidade": 3, "rotulo": "3 corações"}

O resultado é um vídeo com transparência (.mov, qtrle/argb) do tamanho do card. O render põe esse
vídeo por cima do clipe real da cena (desfocado e escurecido), então o ritmo do vídeo não quebra.
Tudo fica vivo: o card entra com mola, o conteúdo pulsa e flutua, brilhos sobem, e o card sai no fim.

Sincronia com a fala: cada elemento entra no segundo em que a palavra correspondente é falada.
Use "em": ["dois", "dois", "terceiro"] (uma palavra por elemento, na ordem). Sem "em", o código tenta
achar sozinho (o número de cada barra, o ano de cada marco, a última palavra do rótulo dos ícones).
"""
import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .render import FFMPEG, FPS

AMARELO = (255, 212, 0)
BRANCO = (248, 248, 252)
CORES = [(255, 206, 40), (40, 200, 255), (255, 90, 125), (110, 230, 140)]
FONTE_FORTE = "C:/Windows/Fonts/ariblk.ttf"
FONTE = "C:/Windows/Fonts/arialbd.ttf"
VERSAO = 5  # mude para refazer as animações em cache
SAIDA_S = 0.3  # o card some nos últimos 0,3 s

# card em proporção da tela (a legenda da cena fica embaixo, fora dele)
CARD_X, CARD_Y, CARD_L, CARD_A = 0.07, 0.13, 0.86, 0.47
MARGEM = 60  # espaço em volta do card para sombra e brilhos


# ---------- utilidades ----------

def _fonte(caminho: str, tamanho: int):
    try:
        return ImageFont.truetype(caminho, max(tamanho, 8))
    except OSError:
        return ImageFont.load_default()


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _mola(x: float) -> float:
    """0 a 1 passando de 1 e voltando (efeito de pulo)."""
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


def _batimento(t: float) -> float:
    """Pulso duplo de coração (tum-tum) a cada 0,9 s, entre 0 e 1."""
    f = (t % 0.9) / 0.9
    return max(math.exp(-((f - 0.08) / 0.05) ** 2), 0.7 * math.exp(-((f - 0.28) / 0.05) ** 2))


def _numero(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _texto(camada: Image.Image, texto: str, caminho: str, tamanho: int, cx: float, y: float, cor,
           max_largura: float, brilho: bool = False) -> None:
    """Texto centrado com sombra suave (e brilho opcional); encolhe até caber em max_largura."""
    fonte = _fonte(caminho, tamanho)
    medir = ImageDraw.Draw(camada)
    caixa = medir.textbbox((0, 0), texto, font=fonte)
    while caixa[2] - caixa[0] > max_largura and fonte.size > 12:
        fonte = _fonte(caminho, int(fonte.size * 0.92))
        caixa = medir.textbbox((0, 0), texto, font=fonte)
    lw, lh = caixa[2] - caixa[0], caixa[3] - caixa[1]
    pad = 30
    sprite = Image.new("RGBA", (lw + 2 * pad, lh + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(sprite).text((pad - caixa[0], pad - caixa[1]), texto, font=fonte, fill=cor + (255,))
    sombra = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    sombra.putalpha(sprite.getchannel("A").point(lambda a: int(a * 0.75)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    x, yy = int(cx - sprite.width / 2), int(y - pad)
    camada.alpha_composite(sombra, (x + 3, yy + 6))
    if brilho:
        halo = Image.new("RGBA", sprite.size, cor + (0,))
        halo.putalpha(sprite.getchannel("A").point(lambda a: int(a * 0.55)))
        camada.alpha_composite(halo.filter(ImageFilter.GaussianBlur(14)), (x, yy))
    camada.alpha_composite(sprite, (x, yy))


def _sprite_brilhante(desenhar, tamanho: int, cor, glow: int = 18) -> Image.Image:
    """Forma desenhada em 2x (bordas lisas), com gradiente de luz, reflexo e brilho em volta."""
    lado = tamanho * 2
    mascara = Image.new("L", (lado, lado), 0)
    desenhar(ImageDraw.Draw(mascara), lado)
    mascara = mascara.resize((tamanho, tamanho), Image.LANCZOS)
    grad = Image.new("RGBA", (tamanho, tamanho))
    gd = ImageDraw.Draw(grad)
    for y in range(tamanho):  # mais claro em cima, mais escuro embaixo
        k = y / tamanho
        claro = tuple(min(255, int(c + (255 - c) * 0.35 * (1 - k) - c * 0.25 * k)) for c in cor)
        gd.line([(0, y), (tamanho, y)], fill=claro + (255,))
    forma = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    forma.paste(grad, (0, 0), mascara)
    reflexo = Image.new("L", (tamanho, tamanho), 0)
    ImageDraw.Draw(reflexo).ellipse([tamanho * 0.22, tamanho * 0.12, tamanho * 0.55, tamanho * 0.38], fill=150)
    reflexo = ImageChops.multiply(reflexo.filter(ImageFilter.GaussianBlur(tamanho * 0.04)), mascara)
    branco = Image.new("L", forma.size, 255)
    forma.alpha_composite(Image.merge("RGBA", (branco, branco, branco, reflexo)))
    total = tamanho + 2 * glow
    saida = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    halo = Image.new("RGBA", (total, total), cor + (0,))
    a = Image.new("L", (total, total), 0)
    a.paste(mascara.point(lambda v: int(v * 0.8)), (glow, glow))
    halo.putalpha(a.filter(ImageFilter.GaussianBlur(glow * 0.6)))
    saida.alpha_composite(halo)
    saida.alpha_composite(forma, (glow, glow))
    return saida


def _coracao(d: ImageDraw.ImageDraw, lado: int) -> None:
    pts = []
    for i in range(200):
        a = 2 * math.pi * i / 200
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((lado / 2 + x * lado / 36, lado * 0.46 - y * lado / 36))
    d.polygon(pts, fill=255)


def _estrela(d: ImageDraw.ImageDraw, lado: int) -> None:
    c, r = lado / 2, lado * 0.48
    d.polygon([(c + (r if i % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5),
                c + (r if i % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5))
               for i in range(10)], fill=255)


def _cubo(d: ImageDraw.ImageDraw, lado: int) -> None:
    d.rounded_rectangle([lado * 0.1, lado * 0.1, lado * 0.9, lado * 0.9], radius=lado * 0.14, fill=255)


def _circulo(d: ImageDraw.ImageDraw, lado: int) -> None:
    d.ellipse([lado * 0.06, lado * 0.06, lado * 0.94, lado * 0.94], fill=255)


FORMAS = {"coracao": _coracao, "estrela": _estrela, "cubo": _cubo, "circulo": _circulo}


def _colar(camada: Image.Image, sprite: Image.Image, cx: float, cy: float, escala: float = 1.0,
           opacidade: float = 1.0) -> None:
    if escala <= 0.02 or opacidade <= 0.01:
        return
    if abs(escala - 1) > 0.01:
        sprite = sprite.resize((max(int(sprite.width * escala), 1), max(int(sprite.height * escala), 1)),
                               Image.BILINEAR)
    if opacidade < 0.99:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel("A").point(lambda a: int(a * opacidade)))
    camada.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))


# ---------- card e brilhos ----------

def _card(largura: int, altura: int) -> Image.Image:
    """Card de vidro escuro com borda clara, gradiente e sombra, já com a margem em volta."""
    total = (largura + 2 * MARGEM, altura + 2 * MARGEM)
    saida = Image.new("RGBA", total, (0, 0, 0, 0))
    sombra = Image.new("L", total, 0)
    ImageDraw.Draw(sombra).rounded_rectangle([MARGEM, MARGEM + 18, MARGEM + largura, MARGEM + altura + 18],
                                             radius=48, fill=170)
    saida.putalpha(sombra.filter(ImageFilter.GaussianBlur(26)))
    corpo = Image.new("RGBA", (largura, altura))
    cd = ImageDraw.Draw(corpo)
    for y in range(altura):
        k = y / altura
        cd.line([(0, y), (largura, y)], fill=(int(24 + 10 * k), int(22 + 6 * k), int(52 - 14 * k), 205))
    mascara = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, largura - 1, altura - 1], radius=48, fill=255)
    vidro = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    vidro.paste(corpo, (0, 0), mascara)
    luz = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    ld = ImageDraw.Draw(luz)
    ld.rounded_rectangle([0, 0, largura - 1, altura * 0.35], radius=48, fill=(255, 255, 255, 18))
    ld.rounded_rectangle([1, 1, largura - 2, altura - 2], radius=48, outline=(255, 255, 255, 70), width=3)
    vidro.alpha_composite(Image.composite(luz, Image.new("RGBA", luz.size, (0, 0, 0, 0)), mascara))
    saida.alpha_composite(vidro, (MARGEM, MARGEM))
    return saida


class _Brilhos:
    """Pontinhos de luz de 4 pontas que sobem e piscam dentro do card."""

    def __init__(self, largura: int, altura: int, semente: int, cor):
        rng = random.Random(semente)
        self.itens = [(rng.uniform(0.05, 0.95) * largura, rng.uniform(0, 1) * altura, rng.uniform(5, 11),
                       rng.uniform(25, 60), rng.uniform(0, math.tau)) for _ in range(16)]
        self.altura, self.cor = altura, cor

    def desenhar(self, camada: Image.Image, t: float) -> None:
        d = ImageDraw.Draw(camada)
        for x, y, r, vel, fase in self.itens:
            yy = (y - vel * t) % self.altura
            a = int(110 * (0.5 + 0.5 * math.sin(t * 3 + fase)))
            if a < 8:
                continue
            cor = self.cor + (a,)
            d.polygon([(x, yy - r), (x + r * 0.25, yy), (x, yy + r), (x - r * 0.25, yy)], fill=cor)
            d.polygon([(x - r, yy), (x, yy - r * 0.25), (x + r, yy), (x, yy + r * 0.25)], fill=cor)


def _entradas(n: int, gatilhos: list[float] | None, padrao: float, passo: float) -> list[float]:
    """Segundo de entrada de cada um dos n elementos: o gatilho falado ou o espaçamento padrão."""
    if not gatilhos:
        return [padrao + passo * k for k in range(n)]
    saida: list[float] = []
    for k in range(n):
        t = gatilhos[k] if k < len(gatilhos) else saida[-1] + passo
        if saida and t < saida[-1] + 0.15:  # mesma palavra para dois elementos: um logo depois do outro
            t = saida[-1] + 0.15
        saida.append(t)
    return saida


def alvos_automaticos(animacao: dict) -> list[str]:
    """Palavras que disparam cada elemento quando o roteiro não diz ('em')."""
    tipo = animacao.get("tipo")
    if tipo == "comparacao":
        return [_numero(float(i["valor"]), int(animacao.get("casas", 0))) for i in animacao.get("itens", [])]
    if tipo == "linha_do_tempo":
        return [str(m.get("texto", "")).split()[0] if m.get("texto") else "" for m in animacao.get("marcos", [])]
    if tipo == "contador":
        return [_numero(float(animacao.get("ate", 0)), int(animacao.get("casas", 0)))]
    if tipo == "icones" and animacao.get("rotulo"):
        return [animacao["rotulo"].split()[-1]]
    return []


# ---------- conteúdos (desenham dentro do card, em coordenadas do card) ----------

class _Contador:
    def __init__(self, w, h, a, dur, gatilhos=None):
        self.w, self.h, self.a = w, h, a
        # o número termina de contar quando é falado
        self.fim = gatilhos[0] + 0.15 if gatilhos else 0.25 + max(dur * 0.5, 0.7)
        self.inicio = max(self.fim - 1.1, 0.15)

    def eventos(self) -> list[tuple[float, str]]:
        return [(self.fim, "ding")]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        a, w, h = self.a, self.w, self.h
        ate, de, casas = float(a.get("ate", 100)), float(a.get("de", 0)), int(a.get("casas", 0))
        p = _suave((t - self.inicio) / (self.fim - self.inicio))
        valor = de + (ate - de) * p
        pulo = 1 + 0.08 * math.sin(min(max(t - self.fim, 0) / 0.3, 1) * math.pi)  # pulo ao chegar
        flutua = math.sin(t * 2.2) * 6
        _texto(c, a.get("prefixo", "") + _numero(valor, casas) + a.get("sufixo", ""), FONTE_FORTE,
               int(w * 0.2 * pulo), w / 2, h * 0.28 + flutua, AMARELO, w * 0.88, brilho=True)
        if a.get("rotulo"):
            entrada = _suave((t - self.inicio - 0.2) / 0.4)
            if entrada > 0.02:
                _texto(c, a["rotulo"], FONTE, int(w * 0.068), w / 2, h * 0.68 + (1 - entrada) * 30,
                       BRANCO, w * 0.88)


class _Comparacao:
    def __init__(self, w, h, a, dur, gatilhos=None):
        self.w, self.h, self.a = w, h, a
        self.itens = a.get("itens", [])[:3]
        self.entradas = _entradas(len(self.itens), gatilhos, 0.3, 0.3)
        n = max(len(self.itens), 1)
        self.larg_barra = int(w * 0.6 / n)
        self.espaco = (w - self.larg_barra * n) / (n + 1)

    def eventos(self) -> list[tuple[float, str]]:
        return [(t, "pop") for t in self.entradas]

    def _barra(self, altura: int, cor) -> Image.Image:
        lb, altura = self.larg_barra, max(altura, 2)
        img = Image.new("RGBA", (lb, altura), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for x in range(lb):  # luz vindo da esquerda, como um cilindro
            luz = 1 - abs(x / lb - 0.35) * 1.4
            d.line([(x, 0), (x, altura)], fill=tuple(min(255, int(c * (0.75 + 0.35 * luz))) for c in cor) + (255,))
        mascara = Image.new("L", img.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle([0, 0, lb - 1, altura - 1], radius=22, fill=255)
        img.putalpha(mascara)
        return img

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        a, w, h = self.a, self.w, self.h
        if not self.itens:
            return
        if a.get("titulo"):
            _texto(c, a["titulo"], FONTE_FORTE, int(w * 0.075), w / 2, h * 0.07, BRANCO, w * 0.88)
        maior = max(float(i["valor"]) for i in self.itens) or 1
        base, topo = h * 0.80, h * 0.33
        for k, item in enumerate(self.itens):
            p = _mola((t - self.entradas[k]) / 0.7)
            alto = int((base - topo) * float(item["valor"]) / maior * p * (1 + 0.012 * math.sin(t * 3 + k)))
            x0 = int(self.espaco + k * (self.larg_barra + self.espaco))
            cor = CORES[k % len(CORES)]
            if alto > 4:
                barra = self._barra(alto, cor)
                topo_barra = int(base - alto)
                halo = Image.new("RGBA", (barra.width + 40, barra.height + 40), cor + (0,))
                ah = Image.new("L", halo.size, 0)
                ah.paste(barra.getchannel("A").point(lambda v: int(v * 0.5)), (20, 20))
                halo.putalpha(ah.filter(ImageFilter.GaussianBlur(14)))
                c.alpha_composite(halo, (x0 - 20, topo_barra - 20))
                c.alpha_composite(barra, (x0, topo_barra))
                fx = ((t * 0.6 + k * 0.3) % 1.6) - 0.3  # faixa de brilho que atravessa a barra
                if 0 <= fx <= 1:
                    faixa = Image.new("RGBA", barra.size, (0, 0, 0, 0))
                    px = int(fx * barra.width)
                    ImageDraw.Draw(faixa).polygon([(px - 18, barra.height), (px + 6, barra.height),
                                                   (px + 36, 0), (px + 12, 0)], fill=(255, 255, 255, 70))
                    vazio = Image.new("RGBA", faixa.size, (0, 0, 0, 0))
                    c.alpha_composite(Image.composite(faixa, vazio, barra.getchannel("A")), (x0, topo_barra))
            cx = x0 + self.larg_barra / 2
            coluna = self.larg_barra + self.espaco * 0.8
            valor = (_numero(float(item["valor"]) * min(p, 1), int(a.get("casas", 0)))
                     + (f" {a['unidade']}" if a.get("unidade") else ""))
            if p > 0.02:
                _texto(c, valor, FONTE_FORTE, int(w * 0.058), cx, base - alto - w * 0.085, BRANCO, coluna)
            _texto(c, item["rotulo"], FONTE_FORTE, int(w * 0.058), cx, base + h * 0.035, cor, coluna)


class _LinhaDoTempo:
    def __init__(self, w, h, a, dur, gatilhos=None):
        self.w, self.h, self.a = w, h, a
        self.marcos = a.get("marcos", [])[:5]
        self.pontos: dict[int, Image.Image] = {}
        valores = [float(m["valor"]) for m in self.marcos] or [0.0]
        vmin, vmax = min(valores), max(valores)
        self.posicoes = [(v - vmin) / ((vmax - vmin) or 1) for v in valores]
        revelar = max(dur * 0.65, 0.9)
        self.chegadas = [gatilhos[k] if gatilhos and k < len(gatilhos) else 0.2 + self.posicoes[k] * revelar
                         for k in range(len(self.marcos))]

    def eventos(self) -> list[tuple[float, str]]:
        return [(t, "pop") for t in self.chegadas]

    def _progresso(self, t: float) -> float:
        """Ponta da linha: chega em cada marco no segundo em que ele é falado."""
        pares = sorted(zip(self.chegadas, self.posicoes))
        if t <= pares[0][0]:
            return pares[0][1] * _suave(t / max(pares[0][0], 0.01))
        for (t0, p0), (t1, p1) in zip(pares, pares[1:]):
            if t <= t1:
                return p0 + (p1 - p0) * _suave((t - t0) / max(t1 - t0, 0.01))
        return 1.0

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h = self.w, self.h
        if len(self.marcos) < 2:
            return
        x0, x1, y = w * 0.12, w * 0.88, h * 0.52
        p = self._progresso(t)
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([x0, y - 5, x1, y + 5], radius=5, fill=(255, 255, 255, 45))
        fim = x0 + (x1 - x0) * p
        if fim > x0 + 2:  # parte acesa com brilho
            linha = Image.new("RGBA", c.size, (0, 0, 0, 0))
            ImageDraw.Draw(linha).rounded_rectangle([x0, y - 6, fim, y + 6], radius=6, fill=AMARELO + (255,))
            c.alpha_composite(linha.filter(ImageFilter.GaussianBlur(10)))
            c.alpha_composite(linha)
        for k, m in enumerate(self.marcos):
            pos = self.posicoes[k]
            chegou = t - self.chegadas[k]
            if chegou < 0:
                continue
            cor = CORES[k % len(CORES)]
            if k not in self.pontos:
                self.pontos[k] = _sprite_brilhante(_circulo, int(w * 0.07), cor, glow=16)
            cx = x0 + (x1 - x0) * pos
            _colar(c, self.pontos[k], cx, y, _mola(chegou / 0.35) * (1 + 0.06 * math.sin(t * 4 + k)))
            onda = (chegou % 1.4) / 1.4  # anel que se expande do ponto
            r = w * 0.035 + onda * w * 0.06
            d.ellipse([cx - r, y - r, cx + r, y + r], outline=cor + (int(160 * (1 - onda)),), width=4)
            acima = k % 2 == 0
            ty = y - h * 0.36 if acima else y + h * 0.10
            cx_texto = min(max(cx, w * 0.2), w * 0.8)
            entrada = _suave(chegou / 0.35)
            desloc = (1 - entrada) * (20 if acima else -20)
            if entrada > 0.05:
                _texto(c, m.get("texto", ""), FONTE_FORTE, int(w * 0.062), cx_texto, ty + desloc, cor, w * 0.34)
                _texto(c, m.get("rotulo", ""), FONTE, int(w * 0.05), cx_texto, ty + w * 0.08 + desloc,
                       BRANCO, w * 0.34)


class _Icones:
    def __init__(self, w, h, a, dur, gatilhos=None):
        self.w, self.h, self.a = w, h, a
        self.n = max(1, min(int(a.get("quantidade", 3)), 12))
        self.entradas = _entradas(self.n, gatilhos, 0.3, 0.2)
        simbolo = a.get("simbolo", "circulo")
        cor = tuple(a["cor"]) if a.get("cor") else (240, 55, 85) if simbolo == "coracao" else AMARELO
        self.colunas = min(self.n, 4)
        self.linhas = math.ceil(self.n / self.colunas)
        self.tam = int(w * (0.22 if self.n <= 4 else 0.15))
        self.sprite = _sprite_brilhante(FORMAS.get(simbolo, _circulo), self.tam, cor, glow=22)
        self.coracao = simbolo == "coracao"

    def eventos(self) -> list[tuple[float, str]]:
        return [(t, "pop") for t in self.entradas]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h = self.w, self.h
        passo = self.tam * 1.25
        for k in range(self.n):
            lin, col = divmod(k, self.colunas)
            nesta = min(self.colunas, self.n - lin * self.colunas)
            cx = w / 2 + (col - (nesta - 1) / 2) * passo
            cy = h * 0.40 + (lin - (self.linhas - 1) / 2) * passo * 0.95 + math.sin(t * 2 + k * 1.3) * 7
            entrada = _mola((t - self.entradas[k]) / 0.4)
            if entrada <= 0:
                continue
            vivo = 1 + (0.12 * _batimento(t + k * 0.15) if self.coracao else 0.04 * math.sin(t * 3 + k))
            _colar(c, self.sprite, cx, cy, entrada * vivo)
        if self.a.get("rotulo"):
            entrada = _suave((t - max(self.entradas) - 0.25) / 0.4)
            if entrada > 0.02:
                _texto(c, self.a["rotulo"], FONTE_FORTE, int(w * 0.085), w / 2, h * 0.74 + (1 - entrada) * 30,
                       BRANCO, w * 0.88)


TIPOS = {"contador": _Contador, "comparacao": _Comparacao, "linha_do_tempo": _LinhaDoTempo,
         "icones": _Icones}


class _Animador:
    def __init__(self, animacao: dict, largura: int, altura: int, duracao: float,
                 gatilhos: list[float] | None = None):
        tipo = animacao.get("tipo")
        if tipo not in TIPOS:
            raise SystemExit(f"animação '{tipo}' não existe. Opções: {', '.join(TIPOS)}")
        self.cw, self.ch = int(largura * CARD_L), int(altura * CARD_A)
        self.base = _card(self.cw, self.ch)
        self.conteudo = TIPOS[tipo](self.cw, self.ch, animacao, duracao, gatilhos)
        self.brilhos = _Brilhos(self.cw, self.ch, len(json.dumps(animacao)), (255, 235, 160))
        self.duracao = duracao

    def quadro(self, t: float) -> Image.Image:
        conteudo = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        self.brilhos.desenhar(conteudo, t)
        self.conteudo.quadro(conteudo, t, self.duracao)
        card = self.base.copy()
        card.alpha_composite(conteudo, (MARGEM, MARGEM))
        entrada = _mola(t / 0.45)
        saida = _suave((self.duracao - t) / SAIDA_S)
        escala = (0.82 + 0.18 * entrada) * (0.9 + 0.1 * saida)
        tela = Image.new("RGBA", card.size, (0, 0, 0, 0))
        _colar(tela, card, card.width / 2, card.height / 2 + (1 - entrada) * 40, escala,
               min(_suave(t / 0.25), saida))
        return tela


def posicao(largura: int, altura: int) -> tuple[int, int]:
    """Canto superior esquerdo do vídeo do card na tela (já descontando a margem)."""
    return int(largura * CARD_X) - MARGEM, int(altura * CARD_Y) - MARGEM


def quadro_teste(animacao: dict, largura: int, altura: int, t: float, duracao: float,
                 gatilhos: list[float] | None = None) -> Image.Image:
    """Um quadro avulso (RGBA, tamanho do card) para conferir o visual sem gerar o vídeo."""
    return _Animador(animacao, largura, altura, duracao, gatilhos).quadro(t)


def eventos(animacao: dict, largura: int, altura: int, duracao: float,
            gatilhos: list[float] | None = None) -> list[tuple[float, str]]:
    """Efeitos sonoros da animação, em segundos dentro da cena: whoosh do card e pop de cada elemento."""
    conteudo = TIPOS[animacao["tipo"]](int(largura * CARD_L), int(altura * CARD_A), animacao, duracao, gatilhos)
    return [(0.05, "whoosh")] + conteudo.eventos()


def gerar(animacao: dict, duracao: float, largura: int, altura: int, destino: Path,
          gatilhos: list[float] | None = None) -> Path:
    """Grava o card animado como .mov com transparência. Reaproveita se nada mudou."""
    destino = destino.with_suffix(".mov")
    assinatura = {"animacao": animacao, "duracao": round(duracao, 2), "tamanho": [largura, altura],
                  "gatilhos": [round(g, 2) for g in gatilhos or []], "versao": VERSAO}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino

    animador = _Animador(animacao, largura, altura, duracao, gatilhos)
    cw, ch = animador.base.size
    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                             "-pix_fmt", "rgba", "-s", f"{cw}x{ch}", "-r", str(FPS), "-i", "-",
                             "-c:v", "qtrle", "-pix_fmt", "argb", str(destino)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(max(int(duracao * FPS), 1)):
            proc.stdin.write(animador.quadro(q / FPS).tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar a animação {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino
