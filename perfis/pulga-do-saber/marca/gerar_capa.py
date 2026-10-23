import sys
from pathlib import Path
from PIL import Image, ImageOps
sys.path.insert(0, r"C:\Users\Vinic\canais-dark"); sys.argv_backup = sys.argv
S = Path(sys.argv[1])
exec(open(S.parent / "contas_arte.py", encoding="utf-8").read().split("# foto de perfil")[0].replace("S = Path(sys.argv[1])", "S = Path(r'%s')" % S))
bruto = Image.open(S / "banner-bruto.png").convert("RGB")
capa = ImageOps.fit(bruto, (320, 180), Image.BOX).quantize(32, method=Image.Quantize.MEDIANCUT).convert("RGBA").resize((640, 360), Image.NEAREST)
sx, sy, sw, sh = (640 - 386) // 2, (360 - 106) // 2, 386, 106   # área segura 1546x423 / 4
capa.alpha_composite(Image.new("RGBA", (sw, sh), (20, 20, 50, 150)), (sx, sy))
pg = _pixelar(_desenhar(0.4, 0.15, 90), 2)
capa.alpha_composite(pg, (sx + 10, (360 - 90) // 2))
titulo = texto_pixel("PULGA DO SABER", 28, 1, AMARELO + (255,), ESCURO + (255,))
sub = texto_pixel("Curiosidades rápidas todo dia · 12h e 19h", 10, 1, (255, 255, 255, 255), ESCURO + (255,))
tx = sx + 108
capa.alpha_composite(titulo, (tx, 180 - titulo.height + 2))
capa.alpha_composite(sub, (tx, 190))
print(tx + max(titulo.width, sub.width), sx + sw)
capa.convert("RGB").quantize(64, method=Image.Quantize.MEDIANCUT).save(S / "capa640.png", optimize=True)
capa.resize((2560, 1440), Image.NEAREST).convert("RGB").save(S / "capa-youtube-final.png")
