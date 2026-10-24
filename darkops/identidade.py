"""Identidade visual das contas de um perfil: foto de perfil, capa do YouTube, marca d'água e textos.

Tudo fica em perfis/<id>/marca/. O fluxo é: gerar, a pessoa que testa revisa e aprova no Estúdio
(ou no chat), e só então a skill /identidade-visual aplica nas contas pelo navegador. Nenhuma API
oficial troca foto de perfil ou bio, por isso a aplicação é feita na própria página, logada pelo usuário.
"""
import base64
import hashlib
import json
import subprocess
import zlib
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import config
from .perfis import Perfil

AMARELO, LARANJA, ESCURO = (255, 205, 40), (235, 140, 20), (40, 24, 14)
CAPA = (2560, 1440)           # banner do YouTube
SEGURA = (1546, 423)          # área que aparece em todos os aparelhos
GRADE = 4                     # a capa é montada em 640x360 e ampliada 4x sem suavizar
BIO_MAX = 150                 # limite da bio do Instagram


def pasta(p: Perfil) -> Path:
    return p.pasta / "marca"


def estado(p: Perfil) -> dict:
    return p.dados.get("identidade") or {}


def _salvar_estado(p: Perfil, **mudancas) -> dict:
    novo = {**estado(p), **mudancas}
    p.salvar({"identidade": novo})
    return novo


def textos_padrao(p: Perfil) -> dict:
    d = p.dados
    nome, arroba = d.get("nome", ""), d.get("arroba", "").lstrip("@")
    horarios = " e ".join(h.replace(":00", "h") for h in d.get("horarios", [])) or "todo dia"
    gancho = (d.get("descricao") or f"Vídeos curtos sobre {d.get('nicho') or 'curiosidades'}").rstrip(".")
    bio = "\n".join(linha for linha in [
        "🧠 Uma pulga atrás da orelha por dia" if d.get("narrador") else f"🧠 {gancho}",
        "Curiosidades rápidas e checadas" if d.get("narrador") else "",
        f"⏰ Reels novos às {horarios}",
        f"▶️ YouTube: @{arroba}" if d.get("youtube", True) else "",
    ] if linha)
    descricao = (f"{gancho}.\n"
                 f"O {nome} traz vídeos curtos, em menos de 1 minuto, sobre {d.get('nicho', 'curiosidades')}. "
                 "Tudo com fonte checada: se é lenda, a gente avisa.\n"
                 f"⏰ Shorts novos todo dia, às {horarios}.\n" +
                 (f"📸 Instagram: @{arroba}" if d.get("instagram", True) else ""))
    return {"bio_instagram": bio[:BIO_MAX], "descricao_youtube": descricao.strip(),
            "titulo_capa": nome.upper(), "subtitulo_capa": f"{gancho.split('.')[0]} · {horarios}"}


def _mascote(p: Perfil, lado: int, pixel: int) -> Image.Image:
    """Foto do perfil, se houver; senão a pulga narradora em pixel art."""
    if p.avatar:
        foto = ImageOps.fit(Image.open(p.avatar).convert("RGBA"), (lado, lado))
        return foto.resize((lado // pixel, lado // pixel), Image.BOX).resize((lado, lado), Image.NEAREST)
    from .narrador import _desenhar, _pixelar
    return _pixelar(_desenhar(0.4, 0.15, lado), pixel)


def _texto_pixel(texto: str, altura_px: int, cor, contorno) -> Image.Image:
    """Escreve pequeno, sem meia transparência: ampliado com NEAREST fica com cara de videogame."""
    fonte = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", altura_px)
    caixa = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), texto, font=fonte)
    w, h = caixa[2] - caixa[0] + 6, caixa[3] - caixa[1] + 6
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            d.text((3 - caixa[0] + dx, 3 - caixa[1] + dy), texto, font=fonte, fill=contorno)
    d.text((3 - caixa[0], 3 - caixa[1]), texto, font=fonte, fill=cor)
    img.putalpha(img.getchannel("A").point(lambda v: 255 if v > 100 else 0))
    return img


def _caber(texto: str, altura: int, largura_max: int, cor, contorno) -> Image.Image:
    while altura > 8:
        img = _texto_pixel(texto, altura, cor, contorno)
        if img.width <= largura_max:
            return img
        altura -= 1
    return _texto_pixel(texto, 8, cor, contorno)


def _fundo_capa(p: Perfil, destino: Path) -> Image.Image:
    """Fundo da capa desenhado no PC (sd.cpp + Z-Image-Turbo) a partir do nicho; sem o gerador, um céu pixel."""
    sd = config.MODELOS / "sd" / "sd-cli.exe"
    pesos = [config.MODELOS / n for n in ("z_image_turbo-Q4_K.gguf", "ae.safetensors",
                                          "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")]
    if sd.exists() and all(x.exists() for x in pesos):
        if not destino.exists():
            nicho = p.dados.get("nicho") or "curiosities"
            prompt = ("16-bit pixel art, retro SNES video game style, crisp square pixels, limited palette, wide "
                      f"panoramic banner. A whimsical colorful world about {nicho}: several small cute scenes side "
                      "by side, cheerful, calm empty sky band across the middle. No text, no letters, no watermark.")
            print("desenhando o fundo da capa no PC (cerca de 3 min)")
            from .visuais import _vez_na_placa
            with _vez_na_placa():
                subprocess.run([str(sd), "--diffusion-model", str(pesos[0]), "--vae", str(pesos[1]), "--llm", str(pesos[2]),
                                "-p", prompt, "--cfg-scale", "1.0", "--steps", "8", "--offload-to-cpu",
                                "--flash-attn", "off,diffusion=on", "--vae-tiling", "-W", "1280", "-H", "720",
                                "--seed", str(zlib.crc32(p.id.encode()) % 100000), "-o", str(destino)],
                               capture_output=True, text=True, errors="replace")
        if destino.exists():
            return ImageOps.fit(Image.open(destino).convert("RGB"), (320, 180), Image.BOX)
    # sem o gerador local: degradê em faixas com estrelas, já na grade de pixels
    img = Image.new("RGB", (320, 180))
    d = ImageDraw.Draw(img)
    for y in range(0, 180, 6):
        t = y / 180
        d.rectangle([0, y, 320, y + 6], fill=(int(30 + 60 * t), int(40 + 90 * t), int(120 + 100 * t)))
    semente = zlib.crc32(p.id.encode())
    for i in range(60):
        x, y = (semente * (i + 3) * 7919) % 320, (semente * (i + 5) * 104729) % 120
        d.point((x, y), fill=(255, 255, 220))
    return img


def gerar(p: Perfil, textos: dict | None = None) -> dict:
    """Gera as artes e os textos. Volta a pedir aprovação, porque algo mudou."""
    m = pasta(p)
    m.mkdir(parents=True, exist_ok=True)
    tx = {**textos_padrao(p), **(json.loads((m / "textos.json").read_text(encoding="utf-8"))
                                if (m / "textos.json").exists() else {}), **(textos or {})}
    tx["bio_instagram"] = tx["bio_instagram"][:BIO_MAX]
    (m / "textos.json").write_text(json.dumps(tx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # foto de perfil 800x800 (as redes recortam em círculo) e marca d'água 150x150
    foto = Image.new("RGBA", (160, 160), AMARELO + (255,))
    ImageDraw.Draw(foto).ellipse([0, 0, 159, 159], outline=LARANJA + (255,), width=6)
    foto = foto.resize((800, 800), Image.NEAREST)
    foto.alpha_composite(_mascote(p, 620, 10), (90, 110))
    foto = foto.convert("RGB")
    foto.save(m / "foto-perfil.png")
    foto.resize((150, 150), Image.NEAREST).save(m / "marca-dagua.png")

    # capa: montada em 640x360 (grade de 4 px) e ampliada para 2560x1440
    capa = _fundo_capa(p, m / "fundo-capa.png").quantize(32, method=Image.Quantize.MEDIANCUT) \
        .convert("RGBA").resize((640, 360), Image.NEAREST)
    sw, sh = SEGURA[0] // GRADE, SEGURA[1] // GRADE
    sx, sy = (640 - sw) // 2, (360 - sh) // 2
    capa.alpha_composite(Image.new("RGBA", (sw, sh), (20, 20, 50, 150)), (sx, sy))
    capa.alpha_composite(_mascote(p, 90, 2), (sx + 10, (360 - 90) // 2))
    tx_x = sx + 108
    titulo = _caber(tx["titulo_capa"], 28, sx + sw - tx_x - 8, AMARELO + (255,), ESCURO + (255,))
    sub = _caber(tx["subtitulo_capa"], 10, sx + sw - tx_x - 8, (255, 255, 255, 255), ESCURO + (255,))
    capa.alpha_composite(titulo, (tx_x, 180 - titulo.height + 2))
    capa.alpha_composite(sub, (tx_x, 190))
    capa.resize(CAPA, Image.NEAREST).convert("RGB").save(m / "capa-youtube.png")

    # versões leves (PNG com paleta) que a skill leva para a página das contas
    capa.convert("RGB").quantize(64, method=Image.Quantize.MEDIANCUT).save(m / "capa-pequena.png", optimize=True)
    for nome in ("foto-perfil", "marca-dagua"):
        Image.open(m / f"{nome}.png").quantize(64, method=Image.Quantize.MEDIANCUT) \
            .save(m / f"{nome}-pequena.png", optimize=True)
    novo = _salvar_estado(p, gerada=date.today().isoformat(), aprovada=False, aprovada_por="", aplicada={})
    return {"pasta": str(m), "textos": tx, "estado": novo}


def aprovar(p: Perfil, quem: str = "") -> dict:
    if not (pasta(p) / "textos.json").exists():
        raise SystemExit("Gere a identidade antes de aprovar: python -m darkops identidade gerar")
    return _salvar_estado(p, aprovada=True, aprovada_por=quem, aprovada_em=date.today().isoformat())


def marcar_aplicada(p: Perfil, plataforma: str) -> dict:
    aplicada = {**estado(p).get("aplicada", {}), plataforma: date.today().isoformat()}
    return _salvar_estado(p, aplicada=aplicada)


def pacote(p: Perfil, bloco: int = 6000) -> dict:
    """Base64 das versões leves, em blocos com hash, para a skill montar os arquivos dentro da página
    (o navegador interno não envia arquivo do disco e a página logada não lê o localhost)."""
    if not estado(p).get("aprovada"):
        raise SystemExit("A identidade ainda não foi aprovada. Revise em Estúdio > Identidade e aprove.")
    m = pasta(p)
    arquivos = {}
    for chave, nome in (("foto", "foto-perfil-pequena.png"), ("marca", "marca-dagua-pequena.png"),
                        ("capa", "capa-pequena.png")):
        b64 = base64.b64encode((m / nome).read_bytes()).decode()
        arquivos[chave] = {"arquivo": nome, "tamanho": len(b64), "sha12": _sha(b64)[:12],
                           "blocos": [{"i": i, "sha8": _sha(b64[i:i + bloco])[:8], "dados": b64[i:i + bloco]}
                                      for i in range(0, len(b64), bloco)]}
    destino = m / "pacote.json"
    destino.write_text(json.dumps({"textos": json.loads((m / "textos.json").read_text(encoding="utf-8")),
                                   "arquivos": arquivos, "capa_ampliar": GRADE}, ensure_ascii=False),
                       encoding="utf-8")
    return {"pacote": str(destino), **{k: {"tamanho": v["tamanho"], "sha12": v["sha12"], "blocos": len(v["blocos"])}
                                       for k, v in arquivos.items()}}


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()
