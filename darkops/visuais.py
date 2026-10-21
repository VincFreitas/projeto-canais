"""Visuais das cenas (arquivo próprio, Pexels ou fundo gerado) e thumbnail."""
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import config

EXT_VIDEO = {".mp4", ".mov", ".webm", ".mkv"}
EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".webp"}
FONTES = [Path("C:/Windows/Fonts/ariblk.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")]


def fonte(tamanho: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for f in FONTES:
        if f.exists():
            return ImageFont.truetype(str(f), tamanho)
    return ImageFont.load_default()


# ---------- Pexels ----------

def _pexels(caminho: str, params: dict) -> dict:
    r = requests.get(f"https://api.pexels.com/{caminho}", params=params,
                     headers={"Authorization": config.PEXELS_API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()


def _baixar(url: str, destino: Path) -> Path:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for bloco in r.iter_content(1 << 16):
                f.write(bloco)
    return destino


def buscar_pexels(consulta: str, largura: int, altura: int, tipo: str, destino: Path, usados: set) -> Path | None:
    """Baixa o primeiro resultado ainda não usado neste vídeo. tipo: 'video' ou 'foto'."""
    orientacao = "portrait" if altura > largura else "landscape"
    if tipo == "video":
        dados = _pexels("videos/search", {"query": consulta, "orientation": orientacao, "per_page": 15})
        for v in dados.get("videos", []):
            if v["id"] in usados:
                continue
            arquivos = [f for f in v["video_files"] if f.get("width") and f["file_type"] == "video/mp4"]
            # menor arquivo que ainda cobre a resolução final, para não baixar 4K à toa
            bons = sorted([f for f in arquivos if min(f["width"], f["height"]) >= min(largura, altura)],
                          key=lambda f: f["width"])
            escolhido = bons[0] if bons else max(arquivos, key=lambda f: f["width"], default=None)
            if escolhido:
                usados.add(v["id"])
                return _baixar(escolhido["link"], destino.with_suffix(".mp4"))
    else:
        dados = _pexels("v1/search", {"query": consulta, "orientation": orientacao, "per_page": 15})
        for foto in dados.get("photos", []):
            if foto["id"] in usados:
                continue
            usados.add(foto["id"])
            return _baixar(foto["src"]["large2x"], destino.with_suffix(".jpg"))
    return None


# ---------- fundo gerado (sem chave) ----------

def fundo_gerado(largura: int, altura: int, semente: int, destino: Path) -> Path:
    """Gradiente escuro com vinheta e granulado. Só um quebra-galho para o pipeline rodar sem imagens."""
    rng = random.Random(semente)
    matiz = [rng.randint(10, 70) for _ in range(3)]
    base = Image.new("RGB", (largura, altura))
    desenho = ImageDraw.Draw(base)
    for y in range(altura):
        k = y / altura
        desenho.line([(0, y), (largura, y)], fill=tuple(int(c * (1.2 - k)) for c in matiz))
    ruido = Image.effect_noise((largura, altura), 18).convert("RGB")
    base = Image.blend(base, ruido, 0.06)
    vinheta = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(vinheta).ellipse([-largura * 0.2, -altura * 0.2, largura * 1.2, altura * 1.2], fill=255)
    vinheta = vinheta.filter(ImageFilter.GaussianBlur(min(largura, altura) // 6))
    base = Image.composite(base, Image.new("RGB", base.size), vinheta)
    destino = destino.with_suffix(".jpg")
    base.save(destino, quality=92)
    return destino


def visual_da_cena(cena: dict, indice: int, pasta_roteiro: Path, pasta_visuais: Path,
                   largura: int, altura: int, tipo: str, usados: set) -> Path:
    """Ordem: arquivo indicado em 'arquivo' > cache já baixado > Pexels > fundo gerado."""
    if cena.get("arquivo"):
        caminho = Path(cena["arquivo"])
        if not caminho.is_absolute():
            caminho = (pasta_roteiro / caminho).resolve()
        if not caminho.exists():
            raise SystemExit(f"Cena {indice}: arquivo não encontrado: {caminho}")
        return caminho

    base = pasta_visuais / f"{indice:02d}"
    for existente in pasta_visuais.glob(f"{indice:02d}.*"):
        if existente.suffix.lower() in EXT_VIDEO | EXT_IMAGEM:
            return existente

    consulta = cena.get("visual", "").strip()
    if consulta and config.PEXELS_API_KEY:
        try:
            achado = buscar_pexels(consulta, largura, altura, cena.get("tipo_visual", tipo), base, usados)
            if achado:
                return achado
            print(f"  cena {indice}: Pexels sem resultado para '{consulta}'")
        except requests.RequestException as erro:
            print(f"  cena {indice}: Pexels falhou ({erro})")
    return fundo_gerado(largura, altura, indice, base)


# ---------- thumbnail ----------

def _quebrar(texto: str, f, largura_max: int, desenho: ImageDraw.ImageDraw) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if desenho.textlength(teste, font=f) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def thumbnail(imagem: Path | None, texto: str, destino: Path, destaque: str = "#FFD400") -> Path:
    """1280x720: imagem escurecida à esquerda + texto grande. A primeira linha sai na cor de destaque."""
    lw, lh = 1280, 720
    if imagem and imagem.suffix.lower() in EXT_IMAGEM:
        base = ImageOps.fit(Image.open(imagem).convert("RGB"), (lw, lh))
    else:
        base = Image.open(fundo_gerado(lw, lh, 99, destino.with_name("_thumb_fundo"))).convert("RGB")
    sombra = Image.new("L", (lw, lh))
    for x in range(lw):
        ImageDraw.Draw(sombra).line([(x, 0), (x, lh)], fill=int(200 * max(0.0, 1 - x / (lw * 0.75))))
    base = Image.composite(Image.new("RGB", (lw, lh)), base, sombra)

    desenho = ImageDraw.Draw(base)
    texto = texto.upper()
    tamanho, f, linhas = 150, fonte(150), [texto]
    for tamanho in range(150, 50, -6):
        f = fonte(tamanho)
        linhas = _quebrar(texto, f, int(lw * 0.62), desenho)
        if len(linhas) <= 3:
            break
    altura_linha = int(tamanho * 1.08)
    y = (lh - altura_linha * len(linhas)) // 2
    for i, linha in enumerate(linhas):
        cor = destaque if i == 0 else "#FFFFFF"
        desenho.text((60, y), linha, font=f, fill=cor, stroke_width=max(tamanho // 14, 4), stroke_fill="#000000")
        y += altura_linha
    base.save(destino, quality=92)
    return destino
