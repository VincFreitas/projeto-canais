"""Aparência própria de cada canal, criada a partir do tema que o dono escolheu.

Regra do projeto: nunca copiar a foto, a mascote, as cores ou qualquer marca visual de outro canal (nem de outro
perfil daqui). A pulga é a identidade do Pulga do Saber e só aparece nele. Todo canal novo ganha, na criação:
paleta, cor e fonte da legenda, tema dos cards, música e uma foto (emblema) desenhada aqui a partir do tema.
"""
import colorsys
import math
import re
import unicodedata
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PULGA = "pulga-do-saber"  # o único perfil dono da pulga (foto, mascote do canto e narradora)
COR_PULGA = "#FFE500"     # amarelo da Pulga: nenhum canal novo recebe

# palavras do tema -> estilo. fundo e cor em RGB; legenda em hex; simbolo desenhado em _simbolo
TEMAS = [
    (("misterio", "mistery", "mystery", "enigma", "oculto", "lenda", "legend", "inexplic", "conspir", "ovni", "ufo"),
     {"fundo": (26, 18, 52), "cor": (0, 205, 185), "legenda": "#5CF2E0", "simbolo": "olho",
      "tema_cards": "arquivo_frio", "musica": "ambiente", "fonte": "Bahnschrift"}),
    (("terror", "horror", "medo", "assombr", "sobrenatural", "creepy", "miedo", "fantasma", "crime"),
     {"fundo": (22, 8, 10), "cor": (205, 32, 44), "legenda": "#FF5A5A", "simbolo": "lua",
      "tema_cards": "arquivo_frio", "musica": "ambiente", "fonte": "Impact"}),
    (("espaco", "space", "astronom", "universo", "universe", "planeta", "planet", "nasa", "galax", "cosmo"),
     {"fundo": (8, 14, 42), "cor": (125, 145, 255), "legenda": "#A5B8FF", "simbolo": "planeta",
      "tema_cards": "moderno_limpo", "musica": "ambiente", "fonte": "Segoe UI Black"}),
    (("anima", "bicho", "natureza", "nature", "wild", "selvag", "fauna", "pet", "oceano", "ocean"),
     {"fundo": (14, 46, 24), "cor": (95, 205, 95), "legenda": "#8CF27A", "simbolo": "pata",
      "tema_cards": "padrao", "musica": "animada", "fonte": "Verdana"}),
    (("historia", "history", "antig", "ancient", "guerra", "war", "imperio", "empire", "medieval", "egito"),
     {"fundo": (52, 32, 16), "cor": (225, 170, 90), "legenda": "#F2C77A", "simbolo": "ampulheta",
      "tema_cards": "jornal_antigo", "musica": "ambiente", "fonte": "Bahnschrift"}),
    (("acontece se", "acontece-se", "aconteceria", "what happens if", "what if"),
     {"fundo": (14, 22, 48), "cor": (255, 140, 30), "legenda": "#FFD23F", "simbolo": "planeta",
      "tema_cards": "moderno_limpo", "musica": "animada", "fonte": "Segoe UI Black"}),
    (("notic", "news", "jornal", "plantao", "aconteceu", "urgente"),
     {"fundo": (18, 18, 24), "cor": (225, 40, 45), "legenda": "#FFFFFF", "simbolo": "globo",
      "tema_cards": "moderno_limpo", "musica": "ambiente", "fonte": "Segoe UI Black"}),
    (("geopolit", "mapa", "map", "pais", "country", "mundo", "world", "politic", "fronteira"),
     {"fundo": (12, 30, 52), "cor": (60, 155, 235), "legenda": "#6FC3FF", "simbolo": "globo",
      "tema_cards": "moderno_limpo", "musica": "ambiente", "fonte": "Segoe UI Black"}),
    (("ciencia", "science", "tecnolog", "tech", "como funciona", "how it works", "engenharia", "engineer",
      "fisica", "physics", "quimica", "invento"),
     {"fundo": (8, 30, 42), "cor": (0, 175, 255), "legenda": "#4FD1FF", "simbolo": "engrenagem",
      "tema_cards": "moderno_limpo", "musica": "animada", "fonte": "Segoe UI Black"}),
]


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in rgb[:3])


def _rgb(texto: str) -> tuple:
    texto = texto.lstrip("#")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def estilo(dados: dict) -> dict:
    """O estilo visual que o tema pede. Tema sem par na lista: cor tirada do próprio tema e do nome (estável, mas
    diferente para cada canal), nunca o amarelo da Pulga."""
    tema = _sem_acento(f"{dados.get('nicho', '')} {dados.get('descricao', '')}")
    for palavras, e in TEMAS:
        if any(p in tema for p in palavras):
            return dict(e)
    semente = zlib.crc32(_sem_acento(f"{dados.get('nicho', '')}|{dados.get('nome', '')}").encode())
    matiz = (semente % 360) / 360
    if 0.1 <= matiz <= 0.2:  # faixa do amarelo da Pulga
        matiz = (matiz + 0.45) % 1
    cor = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(matiz, 0.75, 0.95))
    fundo = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(matiz, 0.65, 0.2))
    legenda = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(matiz, 0.45, 1.0))
    fontes = ["Bahnschrift", "Segoe UI Black", "Verdana", "Impact"]
    return {"fundo": fundo, "cor": cor, "legenda": _hex(legenda), "simbolo": "iniciais",
            "tema_cards": ["moderno_limpo", "arquivo_frio", "padrao"][semente % 3],
            "musica": ["ambiente", "animada"][semente % 2], "fonte": fontes[semente % len(fontes)]}


def campos(dados: dict) -> dict:
    """Os campos do perfil que guardam a aparência do canal."""
    e = estilo(dados)
    return {"cor_marca": _hex(e["cor"]), "cor_fundo_marca": _hex(e["fundo"]), "simbolo_marca": e["simbolo"],
            "legenda_cor": e["legenda"], "legenda_fonte": e["fonte"], "tema_cards": e["tema_cards"],
            "musica": e["musica"]}


def cores(dados: dict) -> tuple[tuple, tuple]:
    """(cor principal, fundo) do canal; perfil sem aparência própria cai no estilo do tema."""
    e = estilo(dados)
    cor = _rgb(dados["cor_marca"]) if re.match(r"^#[0-9A-Fa-f]{6}$", str(dados.get("cor_marca", ""))) else e["cor"]
    fundo = _rgb(dados["cor_fundo_marca"]) if re.match(r"^#[0-9A-Fa-f]{6}$", str(dados.get("cor_fundo_marca", ""))) \
        else e["fundo"]
    return cor, fundo


# ---------- foto do canal (emblema) ----------

def _iniciais(nome: str) -> str:
    palavras = [p for p in re.findall(r"[^\W\d_]+", nome or "") if len(p) > 2] or re.findall(r"[^\W\d_]+", nome or "")
    return ("".join(p[0] for p in palavras[:2]) or "?").upper()


def _simbolo(img: Image.Image, simbolo: str, c: float, r: float, claro, cor, fundo, nome: str) -> None:
    """Desenha o símbolo do tema centrado em (c, c), cabendo no raio r."""
    d = ImageDraw.Draw(img)
    if simbolo == "olho":
        d.ellipse([c - r, c - r * 0.55, c + r, c + r * 0.55], fill=claro)
        d.ellipse([c - r * 0.45, c - r * 0.45, c + r * 0.45, c + r * 0.45], fill=cor)
        d.ellipse([c - r * 0.2, c - r * 0.2, c + r * 0.2, c + r * 0.2], fill=fundo)
        d.ellipse([c + r * 0.05, c - r * 0.3, c + r * 0.2, c - r * 0.15], fill=claro)
    elif simbolo == "lua":
        d.ellipse([c - r * 0.8, c - r * 0.8, c + r * 0.8, c + r * 0.8], fill=claro)
        d.ellipse([c - r * 0.45, c - r * 1.0, c + r * 1.0, c + r * 0.55], fill=fundo)
        for x, y, s in ((0.55, -0.55, 0.09), (0.75, 0.15, 0.06), (0.35, 0.6, 0.07)):
            d.ellipse([c + r * (x - s), c + r * (y - s), c + r * (x + s), c + r * (y + s)], fill=cor)
    elif simbolo == "planeta":
        anel = Image.new("RGBA", (int(r * 4), int(r * 4)), (0, 0, 0, 0))
        da = ImageDraw.Draw(anel)
        m = r * 2
        da.ellipse([m - r * 1.25, m - r * 0.38, m + r * 1.25, m + r * 0.38], outline=cor, width=max(int(r * 0.1), 2))
        anel = anel.rotate(-20, resample=Image.Resampling.BICUBIC)
        d.ellipse([c - r * 0.7, c - r * 0.7, c + r * 0.7, c + r * 0.7], fill=claro)
        img.alpha_composite(anel, (int(c - m), int(c - m)))  # anel por cima: lê como planeta com anel
    elif simbolo == "pata":
        d.ellipse([c - r * 0.5, c - r * 0.05, c + r * 0.5, c + r * 0.75], fill=claro)
        for x, y in ((-0.62, -0.25), (-0.22, -0.62), (0.22, -0.62), (0.62, -0.25)):
            d.ellipse([c + r * (x - 0.2), c + r * (y - 0.24), c + r * (x + 0.2), c + r * (y + 0.24)], fill=claro)
    elif simbolo == "ampulheta":
        w = r * 0.62
        d.rectangle([c - w - r * 0.12, c - r * 0.9, c + w + r * 0.12, c - r * 0.74], fill=cor)
        d.rectangle([c - w - r * 0.12, c + r * 0.74, c + w + r * 0.12, c + r * 0.9], fill=cor)
        d.polygon([(c - w, c - r * 0.74), (c + w, c - r * 0.74), (c, c)], fill=claro)
        d.polygon([(c - w, c + r * 0.74), (c + w, c + r * 0.74), (c, c)], fill=claro)
        d.polygon([(c - w * 0.55, c + r * 0.74), (c + w * 0.55, c + r * 0.74), (c, c + r * 0.3)], fill=cor)
    elif simbolo == "globo":
        largura = max(int(r * 0.08), 2)
        d.ellipse([c - r * 0.8, c - r * 0.8, c + r * 0.8, c + r * 0.8], outline=claro, width=largura * 2)
        d.ellipse([c - r * 0.35, c - r * 0.8, c + r * 0.35, c + r * 0.8], outline=claro, width=largura)
        d.line([c, c - r * 0.8, c, c + r * 0.8], fill=claro, width=largura)
        for y in (-0.4, 0, 0.4):
            meia = r * 0.8 * math.sqrt(1 - y * y)
            d.line([c - meia, c + r * y, c + meia, c + r * y], fill=claro, width=largura)
    elif simbolo == "engrenagem":
        pontos = []
        for i in range(48):
            ang = i / 48 * 2 * math.pi
            raio = r * (0.85 if (i // 3) % 2 == 0 else 0.66)
            pontos.append((c + raio * math.cos(ang), c + raio * math.sin(ang)))
        d.polygon(pontos, fill=claro)
        d.ellipse([c - r * 0.28, c - r * 0.28, c + r * 0.28, c + r * 0.28], fill=fundo)
    else:  # iniciais do nome
        texto = _iniciais(nome)
        for arquivo in ("bahnschrift.ttf", "segoeuib.ttf", "arialbd.ttf"):
            try:
                fonte = ImageFont.truetype(f"C:/Windows/Fonts/{arquivo}", int(r * (1.2 if len(texto) == 1 else 0.95)))
                break
            except OSError:
                fonte = ImageFont.load_default()
        d.text((c, c), texto, font=fonte, fill=claro, anchor="mm")


def desenhar_avatar(dados: dict, destino: Path, lado: int = 800) -> Path:
    """Foto do canal: fundo em degradê na cor do tema, aro na cor principal e o símbolo do tema no meio."""
    cor, fundo = cores(dados)
    simbolo = dados.get("simbolo_marca") or estilo(dados)["simbolo"]
    escala = 2  # desenha grande e reduz: bordas lisas
    t = lado * escala
    img = Image.new("RGBA", (t, t), fundo + (255,))
    d = ImageDraw.Draw(img)
    c = t / 2
    for i in range(60, 0, -1):  # brilho no centro
        f = i / 60
        tom = tuple(int(fundo[k] + (cor[k] - fundo[k]) * 0.35 * (1 - f)) for k in range(3))
        d.ellipse([c - c * f, c - c * f, c + c * f, c + c * f], fill=tom + (255,))
    d.ellipse([t * 0.04, t * 0.04, t * 0.96, t * 0.96], outline=cor + (255,), width=int(t * 0.035))
    claro = tuple(min(255, int(v * 0.25 + 255 * 0.75)) for v in cor) + (255,)
    _simbolo(img, simbolo, c, t * 0.3, claro, cor + (255,), fundo + (255,), dados.get("nome", ""))
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.resize((lado, lado), Image.Resampling.LANCZOS).convert("RGB").save(destino)
    return destino


def garantir(perfil) -> Path | None:
    """Foto do canal: a enviada pelo dono, ou um emblema novo do tema. O Pulga do Saber fica com a pulga."""
    if perfil.avatar or perfil.id == PULGA:
        return perfil.avatar
    return desenhar_avatar(perfil.dados, perfil.pasta / "avatar.png")


def aplicar(perfil) -> dict:
    """Canal novo: grava a aparência do tema no perfil e desenha a foto. Devolve os campos gravados."""
    novos = campos(perfil.dados)
    perfil.salvar(novos)
    if not perfil.avatar:
        desenhar_avatar(perfil.dados, perfil.pasta / "avatar.png")
    return novos
