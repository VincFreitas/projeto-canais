"""Artes das contas: foto de perfil, capa do YouTube e marca d'água, no estilo pixel do canal."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, r"C:\Users\Vinic\canais-dark")
from darkops.narrador import _desenhar, _pixelar  # noqa: E402

S = Path(sys.argv[1])
AMARELO, LARANJA, ESCURO = (255, 205, 40), (235, 140, 20), (40, 24, 14)


def pulga(lado: int, pixel: int) -> Image.Image:
    return _pixelar(_desenhar(0.4, 0.15, lado), pixel)


def texto_pixel(texto: str, altura_px: int, escala: int, cor, contorno) -> Image.Image:
    """Escreve pequeno e amplia sem suavizar: letras com cara de videogame."""
    fonte = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", altura_px)
    caixa = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), texto, font=fonte)
    w, h = caixa[2] - caixa[0] + 6, caixa[3] - caixa[1] + 6
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            d.text((3 - caixa[0] + dx, 3 - caixa[1] + dy), texto, font=fonte, fill=contorno)
    d.text((3 - caixa[0], 3 - caixa[1]), texto, font=fonte, fill=cor)
    a = img.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    img.putalpha(a)
    return img.resize((w * escala, h * escala), Image.NEAREST)


# foto de perfil 800x800: pulga pixel num círculo amarelo (as redes recortam em círculo)
foto = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
d = ImageDraw.Draw(foto)
d.ellipse([0, 0, 159, 159], fill=AMARELO + (255,))
d.ellipse([0, 0, 159, 159], outline=LARANJA + (255,), width=6)
foto = foto.resize((800, 800), Image.NEAREST)
fundo = Image.new("RGBA", (800, 800), AMARELO + (255,))
fundo.alpha_composite(foto)
p = pulga(620, 10)
fundo.alpha_composite(p, ((800 - 620) // 2, (800 - 620) // 2 + 20))
fundo.convert("RGB").save(S / "foto-perfil.png")

# marca d'água do YouTube 150x150 (aparece no canto dos vídeos)
fundo.resize((150, 150), Image.NEAREST).convert("RGB").save(S / "marca-dagua.png")

# capa do YouTube 2560x1440; área segura no centro: 1546x423
bruto = Image.open(S / "banner-bruto.png").convert("RGB")
grade = ImageOps.fit(bruto, (320, 180), Image.BOX).quantize(32, method=Image.Quantize.MEDIANCUT).convert("RGBA")
capa = grade.resize((2560, 1440), Image.NEAREST)
faixa = Image.new("RGBA", (1546 // 8, 423 // 8), (20, 20, 50, 150))
capa.alpha_composite(faixa.resize((1546, 423), Image.NEAREST), ((2560 - 1546) // 2, (1440 - 423) // 2))
pg = pulga(360, 9)
x0 = (2560 - 1546) // 2 + 40
capa.alpha_composite(pg, (x0, (1440 - 360) // 2))
titulo = texto_pixel("PULGA DO SABER", 28, 4, AMARELO + (255,), ESCURO + (255,))
sub = texto_pixel("Curiosidades rápidas todo dia · 12h e 19h", 13, 3, (255, 255, 255, 255), ESCURO + (255,))
tx = x0 + 390
capa.alpha_composite(titulo, (tx, 1440 // 2 - titulo.height + 10))
capa.alpha_composite(sub, (tx, 1440 // 2 + 40))
capa.convert("RGB").save(S / "capa-youtube.png")
# prévia de como fica no celular (só a área segura)
capa.crop(((2560 - 1546) // 2, (1440 - 423) // 2, (2560 + 1546) // 2, (1440 + 423) // 2)).convert("RGB") \
    .save(S / "capa-area-segura.png")
print(titulo.width + tx, (2560 + 1546) // 2)
