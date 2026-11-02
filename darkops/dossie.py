"""Edição "dossiê" (tema_cards = "dossie"): painéis de dados por cima da imagem inteira, sem card de vidro.

Estilo de reconstituição com dados: a imagem da cena fica nítida em tela cheia e os números aparecem em painéis
escuros e retos, com rótulo em fonte de terminal (ALTITUDE, TEMPO, REGISTRO), contando até o valor no segundo em
que a palavra é falada. As cores vêm do canal (a cor de destaque da legenda), nunca de outro canal.

Tipos próprios (campo "animacao" da cena):

  {"tipo": "painel", "itens": [{"rotulo": "Profundidade", "de": 0, "ate": 3800, "unidade": "m"},
                               {"rotulo": "Ano", "texto": "1912", "detalhe": "naufrágio"}]}
      1 ou 2 caixinhas acima da legenda; "ate" conta, "texto" aparece digitado.
  {"tipo": "citacao", "origem": "Diário de bordo · 1872", "texto": "Nenhum sinal da tripulação.",
   "detalhe": "trecho traduzido"}
      cartão com a fala ou o documento, digitado letra a letra, com a barra de alerta na cor de destaque.
  {"tipo": "checklist", "titulo": "O que se sabe", "subtitulo": "segundo os registros",
   "itens": ["o navio estava inteiro", "a carga estava lá", "o bote sumiu"], "em": ["inteiro", "carga", "bote"]}
      itens que ganham o "✓" um por um, na palavra falada.
  {"tipo": "barra", "valor": 81, "titulo": "Velocidade do som", "rotulo": "81%", "limite": 100}
      medidor reto com a faixa de limite riscada.

"contador" vira um painel grande; "comparacao", "linha_do_tempo" e "icones" usam o desenho de animacoes.py
dentro de um painel reto.
"""
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_F = "C:/Windows/Fonts/"
MONO = _F + "consola.ttf"
MONO_FORTE = _F + "consolab.ttf"
FORTE = _F + "ariblk.ttf"
TEXTO = _F + "segoeuib.ttf"
PAINEL = (12, 16, 30, 196)
BORDA = (255, 255, 255, 46)
CINZA = (150, 160, 176)
BRANCO = (240, 244, 250)
ALERTA = (255, 84, 84)
SAIDA_S = 0.3

# áreas da tela (proporção): a legenda do modo grupo fica perto de 0,70 da altura
TOPO = 0.15  # abaixo do título e da etiqueta do topo
LINHA_PAINEL = 0.555  # caixinhas do "painel", logo acima da legenda


def _fonte(caminho: str, tamanho: float):
    try:
        return ImageFont.truetype(caminho, max(int(tamanho), 8))
    except OSError:
        return ImageFont.load_default()


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _numero(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _cor(valor, padrao):
    if isinstance(valor, str) and valor.startswith("#") and len(valor) == 7:
        return tuple(int(valor[i:i + 2], 16) for i in (1, 3, 5))
    if isinstance(valor, (list, tuple)) and len(valor) == 3:
        return tuple(int(x) for x in valor)
    return padrao


def _caixa(d: ImageDraw.ImageDraw, x0, y0, x1, y1, opacidade: float = 1.0) -> None:
    r, g, b, a = PAINEL
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=(r, g, b, int(a * opacidade)),
                        outline=BORDA[:3] + (int(BORDA[3] * opacidade),), width=2)


def _escrever(d: ImageDraw.ImageDraw, xy, texto: str, fonte, cor, opacidade: float = 1.0, ancora: str = "la") -> None:
    if opacidade > 0.01 and texto:
        d.text(xy, texto, font=fonte, fill=tuple(cor[:3]) + (int(255 * opacidade),), anchor=ancora)


def _quebrar(texto: str, fonte, largura: float, d: ImageDraw.ImageDraw) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if d.textlength(teste, font=fonte) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    return linhas + ([atual] if atual else [])


def _entradas(n: int, gatilhos, padrao: float, passo: float) -> list[float]:
    saida: list[float] = []
    for k in range(n):
        g = gatilhos[k] if gatilhos and k < len(gatilhos) else None
        t = g if g is not None else (saida[-1] + passo if saida else padrao)
        if saida and t < saida[-1] + 0.15:
            t = saida[-1] + 0.15
        saida.append(t)
    return saida


class _Painel:
    """Caixinhas de dado (rótulo em fonte de terminal + número que conta ou texto digitado)."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        self.w, self.h, self.a, self.destaque = w, h, a, destaque
        self.itens = (a.get("itens") or [])[:2]
        self.fins = _entradas(len(self.itens), gatilhos, 0.25 + max(dur * 0.45, 0.7), 0.35)

    def eventos(self):
        return [(t, "ding") for t in self.fins]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h = self.w, self.h
        n = max(len(self.itens), 1)
        grande = 1.0 if n > 1 else 1.4  # um dado só ganha mais destaque
        larg = w * (0.38 if n > 1 else 0.62)
        alt = h * 0.085 * grande
        d = ImageDraw.Draw(c)
        for k, item in enumerate(self.itens):
            x0 = w * 0.06 if (n > 1 and k == 0) else (w * 0.94 - larg if n > 1 else (w - larg) / 2)
            y0 = h * LINHA_PAINEL
            inicio = max(min(0.2 + 0.15 * k, self.fins[k] - 0.6), 0.0)
            entra = _suave((t - inicio) / 0.35)
            if entra <= 0.01:
                continue
            dy = (1 - entra) * 24
            _caixa(d, x0, y0 + dy, x0 + larg, y0 + alt + dy, entra)
            _escrever(d, (x0 + w * 0.025, y0 + dy + alt * 0.12), str(item.get("rotulo", "")).upper(),
                      _fonte(MONO, h * 0.0125 * grande), CINZA, entra)
            p = _suave((t - inicio) / max(self.fins[k] - inicio, 0.3))
            if "ate" in item:
                de, ate, casas = float(item.get("de", 0)), float(item["ate"]), int(item.get("casas", 0))
                valor = item.get("prefixo", "") + _numero(de + (ate - de) * p, casas)
            else:
                texto = str(item.get("texto", ""))
                valor = texto[:max(int(round(len(texto) * p)), 0)]
            cor = self.destaque if t >= self.fins[k] - 0.05 else BRANCO
            tam = h * 0.032 * grande
            fonte = _fonte(MONO_FORTE, tam)
            while d.textlength(valor + " " + item.get("unidade", ""), font=fonte) > larg - w * 0.05 and tam > 14:
                tam *= 0.9
                fonte = _fonte(MONO_FORTE, tam)
            y_valor = y0 + dy + alt * 0.42
            _escrever(d, (x0 + w * 0.025, y_valor), valor, fonte, cor, entra)
            if item.get("unidade"):
                fim = x0 + w * 0.025 + d.textlength(valor + " ", font=fonte)
                _escrever(d, (fim, y_valor + tam * 0.35), item["unidade"], _fonte(MONO, h * 0.0135 * grande), CINZA, entra)
            if item.get("detalhe"):
                _escrever(d, (x0 + w * 0.025, y0 + dy + alt * 1.06), item["detalhe"], _fonte(MONO, h * 0.011 * grande),
                          CINZA, entra * 0.9)


class _Contador(_Painel):
    """"contador" no dossiê: um painel só, maior, com o rótulo embaixo."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        item = {"rotulo": a.get("titulo") or a.get("rotulo", ""), "de": a.get("de", 0), "ate": a.get("ate", 0),
                "casas": a.get("casas", 0), "prefixo": a.get("prefixo", ""),
                "unidade": str(a.get("sufixo", "")).strip(), "detalhe": a.get("rotulo") if a.get("titulo") else ""}
        super().__init__(w, h, {"itens": [item]}, dur, gatilhos, destaque)


class _Citacao:
    """Cartão de documento ou fala: origem em fonte de terminal, texto digitado, barra de alerta."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        self.w, self.h, self.a, self.destaque = w, h, a, destaque
        self.inicio = 0.15
        self.fim = gatilhos[-1] + 0.2 if gatilhos and gatilhos[-1] is not None else min(0.4 + dur * 0.55, dur - 0.4)

    def eventos(self):
        return [(self.inicio, "pop")]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h, a = self.w, self.h, self.a
        d = ImageDraw.Draw(c)
        entra = _suave((t - self.inicio) / 0.35)
        if entra <= 0.01:
            return
        fonte = _fonte(TEXTO, h * 0.024)
        x0, x1 = w * 0.06, w * 0.94
        linhas = _quebrar(f"“{a.get('texto', '')}”", fonte, x1 - x0 - w * 0.08, d)[:5]
        alt = h * (0.05 + 0.03 * len(linhas) + (0.018 if a.get("detalhe") else 0))
        y0 = h * TOPO + (1 - entra) * 24
        _caixa(d, x0, y0, x1, y0 + alt, entra)
        d.rectangle([x0, y0 + 10, x0 + 7, y0 + alt - 10], fill=self.destaque + (int(255 * entra),))
        pisca = 0.5 + 0.5 * math.sin(t * 6)
        d.ellipse([x0 + w * 0.035, y0 + h * 0.016, x0 + w * 0.035 + h * 0.008, y0 + h * 0.024],
                  fill=ALERTA + (int(255 * entra * (0.4 + 0.6 * pisca)),))
        _escrever(d, (x0 + w * 0.055, y0 + h * 0.013), str(a.get("origem", "registro")).upper(),
                  _fonte(MONO_FORTE, h * 0.012), ALERTA, entra)
        total = sum(len(l) for l in linhas)
        mostrar = int(total * _suave((t - self.inicio - 0.2) / max(self.fim - self.inicio - 0.2, 0.4)) ** 0.8)
        y = y0 + h * 0.04
        for linha in linhas:
            parte = linha[:max(mostrar, 0)]
            mostrar -= len(linha)
            _escrever(d, (x0 + w * 0.045, y), parte, fonte, BRANCO, entra)
            y += h * 0.03
        if a.get("detalhe"):
            _escrever(d, (x0 + w * 0.045, y + h * 0.004), a["detalhe"], _fonte(MONO, h * 0.011), CINZA, entra)


class _Checklist:
    """Lista que ganha o ✓ item por item na palavra falada."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        self.w, self.h, self.a, self.destaque = w, h, a, destaque
        self.itens = (a.get("itens") or [])[:5]
        self.marcas = _entradas(len(self.itens), gatilhos, 0.6, max((dur - 1.0) / max(len(self.itens), 1), 0.4))

    def eventos(self):
        return [(t, "pop") for t in self.marcas]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h, a = self.w, self.h, self.a
        d = ImageDraw.Draw(c)
        entra = _suave((t - 0.1) / 0.35)
        if entra <= 0.01:
            return
        x0, x1, y = w * 0.06, w * 0.94, h * TOPO
        _escrever(d, (x0, y), str(a.get("titulo", "")).upper(), _fonte(FORTE, h * 0.022), self.destaque, entra)
        if a.get("subtitulo"):
            _escrever(d, (x0, y + h * 0.032), a["subtitulo"], _fonte(MONO, h * 0.012), CINZA, entra)
        y += h * 0.058
        fonte = _fonte(TEXTO, h * 0.02)
        for k, item in enumerate(self.itens):
            aparece = _suave((t - (0.25 + 0.12 * k)) / 0.3)
            if aparece <= 0.01:
                continue
            _caixa(d, x0, y, x1, y + h * 0.045, aparece)
            _escrever(d, (x0 + w * 0.04, y + h * 0.0225), str(item), fonte, BRANCO, aparece, "lm")
            feito = _suave((t - self.marcas[k]) / 0.2)
            if feito > 0.01:
                cx, cy, r = x1 - w * 0.06, y + h * 0.0225, h * 0.009 * (0.6 + 0.4 * feito)
                d.line([(cx - r, cy), (cx - r * 0.3, cy + r * 0.7), (cx + r, cy - r * 0.8)],
                       fill=self.destaque + (int(255 * feito),), width=max(int(h * 0.0035), 3), joint="curve")
            y += h * 0.054


class _Medidor:
    """Barra reta de 0 a 100 com a faixa de limite riscada em vermelho."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        self.w, self.h, self.a, self.destaque = w, h, a, destaque
        self.fim = gatilhos[0] + 0.15 if gatilhos and gatilhos[0] is not None else 0.25 + max(dur * 0.5, 0.7)

    def eventos(self):
        return [(self.fim, "ding")]

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        w, h, a = self.w, self.h, self.a
        d = ImageDraw.Draw(c)
        entra = _suave((t - 0.1) / 0.35)
        if entra <= 0.01:
            return
        x0, x1, y = w * 0.08, w * 0.92, h * (TOPO + 0.12)
        if a.get("titulo"):
            _escrever(d, (w / 2, y - h * 0.05), str(a["titulo"]).upper(), _fonte(FORTE, h * 0.026),
                      ALERTA if a.get("limite") else self.destaque, entra, "mm")
        limite = float(a.get("limite", 0) or 0)
        d.rectangle([x0, y, x1, y + h * 0.018], fill=(255, 255, 255, int(60 * entra)))
        if limite and limite < 100:
            xl = x0 + (x1 - x0) * limite / 100
            for k in range(int((x1 - xl) / 14) + 2):
                xx = xl + k * 14
                d.line([(xx, y + h * 0.018), (min(xx + 10, x1), y)], fill=ALERTA + (int(220 * entra),), width=4)
        valor = max(0.0, min(float(a.get("valor", 50)), 100.0)) * _suave((t - 0.2) / max(self.fim - 0.2, 0.3))
        d.rectangle([x0, y, x0 + (x1 - x0) * valor / 100, y + h * 0.018], fill=BRANCO + (int(240 * entra),))
        mx = x0 + (x1 - x0) * valor / 100
        d.polygon([(mx - 10, y - 16), (mx + 10, y - 16), (mx, y - 2)], fill=self.destaque + (int(255 * entra),))
        _escrever(d, (x0, y + h * 0.026), "0", _fonte(MONO, h * 0.011), CINZA, entra)
        _escrever(d, (x1, y + h * 0.026), str(a.get("fim_escala", "100")), _fonte(MONO, h * 0.011), CINZA, entra, "ra")
        if a.get("rotulo"):
            _escrever(d, (w / 2, y + h * 0.065), a["rotulo"], _fonte(FORTE, h * 0.022), self.destaque, entra, "mm")


class _Legado:
    """comparacao, linha_do_tempo e icones: o desenho de animacoes.py dentro de um painel reto."""

    def __init__(self, w, h, a, dur, gatilhos, destaque):
        from . import animacoes
        animacoes.usar_tema("dossie")
        self.w, self.h = w, h
        self.cw, self.ch = int(w * 0.88), int(h * 0.3)
        self.conteudo = animacoes.TIPOS[a["tipo"]](self.cw, self.ch, a, dur, gatilhos)

    def eventos(self):
        return self.conteudo.eventos()

    def quadro(self, c: Image.Image, t: float, dur: float) -> None:
        entra = _suave((t - 0.1) / 0.35)
        if entra <= 0.01:
            return
        x0, y0 = int(self.w * 0.06), int(self.h * TOPO)
        d = ImageDraw.Draw(c)
        _caixa(d, x0, y0, x0 + self.cw, y0 + self.ch, entra)
        miolo = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        self.conteudo.quadro(miolo, t, dur)
        if entra < 0.99:
            miolo.putalpha(miolo.getchannel("A").point(lambda v: int(v * entra)))
        c.alpha_composite(miolo, (x0, y0))


TIPOS = {"painel": _Painel, "contador": _Contador, "citacao": _Citacao, "checklist": _Checklist,
         "barra": _Medidor, "comparacao": _Legado, "linha_do_tempo": _Legado, "icones": _Legado}


def alvos(animacao: dict) -> list[str]:
    """Palavras que disparam cada elemento quando o roteiro não diz ('em')."""
    tipo = animacao.get("tipo")
    if tipo == "painel":
        return [_numero(float(i["ate"]), int(i.get("casas", 0))) if "ate" in i else str(i.get("texto", "")).split()[0]
                if i.get("texto") else "" for i in animacao.get("itens", [])]
    if tipo in ("citacao", "checklist"):
        return []
    from .animacoes import alvos_automaticos
    return alvos_automaticos(animacao)


class Hud:
    """Camada transparente do tamanho da tela com o painel da cena; some nos últimos 0,3 s."""

    def __init__(self, animacao: dict, largura: int, altura: int, duracao: float, gatilhos=None):
        tipo = animacao.get("tipo")
        if tipo not in TIPOS:
            raise SystemExit(f"animação '{tipo}' não existe no dossiê. Opções: {', '.join(TIPOS)}")
        destaque = _cor(animacao.get("destaque"), (92, 242, 224))
        self.w, self.h, self.duracao = largura, altura, duracao
        self.conteudo = TIPOS[tipo](largura, altura, animacao, duracao, gatilhos, destaque)

    def eventos(self) -> list[tuple[float, str]]:
        return [(0.05, "whoosh")] + self.conteudo.eventos()

    def quadro(self, t: float) -> Image.Image:
        tela = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.conteudo.quadro(tela, t, self.duracao)
        saida = _suave((self.duracao - t) / SAIDA_S)
        if saida < 0.99:
            tela.putalpha(tela.getchannel("A").point(lambda v: int(v * saida)))
        # sombra desfocada em 1/4 do tamanho: o mesmo efeito, bem mais rápido na tela cheia
        pequena = tela.getchannel("A").resize((self.w // 4, self.h // 4), Image.Resampling.BILINEAR)
        alfa = pequena.point(lambda v: int(v * 0.35)).filter(ImageFilter.GaussianBlur(2.5))
        sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
        sombra.putalpha(alfa.resize(tela.size, Image.Resampling.BILINEAR))
        base = Image.new("RGBA", tela.size, (0, 0, 0, 0))
        base.alpha_composite(sombra, (0, 6))
        base.alpha_composite(tela)
        return base
