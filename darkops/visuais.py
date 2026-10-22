"""Visuais das cenas (arquivo próprio, Pexels, Pixabay ou fundo gerado) e thumbnail."""
import json
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import config

EXT_VIDEO = {".mp4", ".mov", ".webm", ".mkv"}
EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".webp"}
VERSAO_BUSCA = 4  # mude para baixar de novo os visuais em cache (ex.: filtro de busca novo)
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


# ---------- Pixabay (licença livre, sem atribuição obrigatória) ----------

def _pixabay(caminho: str, params: dict) -> dict:
    r = requests.get(f"https://pixabay.com/api/{caminho}", timeout=30,
                     params={"key": config.PIXABAY_API_KEY, "safesearch": "true", "per_page": 50, **params})
    r.raise_for_status()
    return r.json()


BLOQUEADAS = {"cartoon", "3d", "animation", "animated", "illustration", "render", "christmas", "santa", "toy",
              "fair", "carousel", "fairground", "logo", "text", "drawing", "clipart", "anime", "digital",
              "fantasy", "painting", "artwork", "art", "character", "avatar", "generated"}


def _filtrar_pixabay(hits: list[dict], consulta: str, usados: set) -> list[dict]:
    """Só mídia real (sem IA, que exigiria marcar 'conteúdo sintético'), sem desenho nem 3D, com o
    assunto (1ª palavra da busca) entre as 3 primeiras tags. Ordena pela posição das palavras nas tags."""
    palavras = consulta.lower().split()
    bons = []
    for h in hits:
        tags = [t.strip().lower() for t in h.get("tags", "").split(",")]
        if (h.get("isAiGenerated") or "ai generated" in tags or f"pb{h['id']}" in usados
                or BLOQUEADAS & {p for t in tags for p in t.split()}):
            continue
        def posicao(palavra):
            return next((i for i, t in enumerate(tags) if palavra in t), 99)
        if posicao(palavras[0]) > 2:
            continue
        todas = all(posicao(p) < 99 for p in palavras)  # "great pyramid" não pode virar "great wall"
        bons.append((not todas, sum(posicao(p) for p in palavras), h))
    completos = [b for b in bons if not b[0]]
    return [h for *_, h in sorted(completos or bons, key=lambda x: (x[0], x[1]))]


def buscar_pixabay(consulta: str, largura: int, altura: int, tipo: str, destino: Path, usados: set) -> Path | None:
    """Mesmo contrato de buscar_pexels. Vídeo: prefere a orientação do formato e a menor resolução suficiente."""
    vertical = altura > largura
    consulta = consulta[:100]
    if tipo == "video":
        hits = _filtrar_pixabay(_pixabay("videos/", {"q": consulta}).get("hits", []), consulta, usados)
        hits.sort(key=lambda h: (h["videos"]["large"].get("height", 0) > h["videos"]["large"].get("width", 0)) != vertical)
        for h in hits:
            opcoes = [v for v in h["videos"].values() if v.get("url") and v.get("width")]
            bons = sorted([v for v in opcoes if min(v["width"], v["height"]) >= min(largura, altura)],
                          key=lambda v: v["width"])
            escolhido = bons[0] if bons else max(opcoes, key=lambda v: v["width"], default=None)
            if escolhido:
                usados.add(f"pb{h['id']}")
                return _baixar(escolhido["url"], destino.with_suffix(".mp4"))
    else:
        dados = _pixabay("", {"q": consulta, "image_type": "photo",
                              "orientation": "vertical" if vertical else "horizontal"})
        for h in _filtrar_pixabay(dados.get("hits", []), consulta, usados):
            usados.add(f"pb{h['id']}")
            return _baixar(h["largeImageURL"], destino.with_suffix(".jpg"))
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
    """Ordem: arquivo indicado em 'arquivo' > cache já baixado > Pexels > Pixabay > fundo gerado."""
    if cena.get("arquivo"):
        caminho = Path(cena["arquivo"])
        if not caminho.is_absolute():
            caminho = (pasta_roteiro / caminho).resolve()
        if not caminho.exists():
            raise SystemExit(f"Cena {indice}: arquivo não encontrado: {caminho}")
        return caminho

    base = pasta_visuais / f"{indice:02d}"
    consulta = cena.get("visual", "").strip()
    # o cache só vale para a mesma busca: trocar 'visual' no roteiro baixa outra imagem
    marca = pasta_visuais / f"{indice:02d}.visual.json"
    if marca.exists():
        anterior = json.loads(marca.read_text(encoding="utf-8"))
        if (anterior.get("consulta") == consulta and anterior.get("tipo", "foto") == cena.get("tipo_visual", tipo)
                and anterior.get("versao") == VERSAO_BUSCA
                and Path(anterior.get("arquivo", "")).exists()):
            return Path(anterior["arquivo"])
    achado = _buscar_em_bancos(consulta, indice, largura, altura, cena.get("tipo_visual", tipo), base, usados)
    marca.write_text(json.dumps({"consulta": consulta, "tipo": cena.get("tipo_visual", tipo), "versao": VERSAO_BUSCA,
                                 "arquivo": str(achado)}),
                     encoding="utf-8")
    return achado


def _buscar_em_bancos(consulta: str, indice: int, largura: int, altura: int, tipo: str,
                      base: Path, usados: set) -> Path:
    """Tipo 'video' tenta clipe em cada banco e, se não achar, foto (que ganha movimento no render)."""
    bancos = [("Pexels", config.PEXELS_API_KEY, buscar_pexels), ("Pixabay", config.PIXABAY_API_KEY, buscar_pixabay)]
    for tentativa in (["video", "foto"] if tipo == "video" else [tipo]):
        for nome, chave, buscar in bancos:
            if not (consulta and chave):
                continue
            try:
                achado = buscar(consulta, largura, altura, tentativa, base, usados)
                if achado:
                    return achado
                print(f"  cena {indice}: {nome} sem {tentativa} para '{consulta}'")
            except requests.RequestException as erro:
                print(f"  cena {indice}: {nome} falhou ({erro})")
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
