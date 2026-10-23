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


def buscar_pexels(consulta: str, largura: int, altura: int, tipo: str, destino: Path, usados: set,
                  idioma: str = "en") -> Path | None:
    """Baixa o primeiro resultado ainda não usado neste vídeo. tipo: 'video' ou 'foto'.
    idioma: língua da busca (as buscas montadas de roteiro pronto ou narração vêm em português)."""
    orientacao = "portrait" if altura > largura else "landscape"
    local = {"locale": {"pt": "pt-BR", "es": "es-ES"}[idioma]} if idioma in ("pt", "es") else {}
    if tipo == "video":
        dados = _pexels("videos/search", {"query": consulta, "orientation": orientacao, "per_page": 15, **local})
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
        dados = _pexels("v1/search", {"query": consulta, "orientation": orientacao, "per_page": 15, **local})
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


def buscar_pixabay(consulta: str, largura: int, altura: int, tipo: str, destino: Path, usados: set,
                   idioma: str = "en") -> Path | None:
    """Mesmo contrato de buscar_pexels. Vídeo: prefere a orientação do formato e a menor resolução suficiente."""
    vertical = altura > largura
    consulta = consulta[:100]
    if tipo == "video":
        hits = _filtrar_pixabay(_pixabay("videos/", {"q": consulta, "lang": idioma}).get("hits", []), consulta, usados)
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
        dados = _pixabay("", {"q": consulta, "image_type": "photo", "lang": idioma,
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


ESTILO_PIXEL = ("16-bit pixel art, retro SNES video game style, crisp visible square pixels, limited color "
                "palette, no anti-aliasing, dithering, side view game scene, cute and friendly. "
                "No text, no letters, no numbers, no watermark. ")
_SEM_TEXTO = "No text, no letters, no numbers, no watermark. "
# estilos que o gerador local desenha a partir de 'ilustracao' e 'personagem' (o prompt vai em inglês)
ESTILOS_IA = {
    "pixel": ESTILO_PIXEL,
    "desenho2d": "Flat 2D cartoon illustration, clean bold outlines, soft cel shading, warm friendly colors, "
                 "storybook style, simple readable shapes. " + _SEM_TEXTO,
    "pintura": "Classical historical oil painting, visible brush strokes, dramatic chiaroscuro lighting, rich "
               "earthy palette, museum quality. " + _SEM_TEXTO,
    "foto_antiga": "Old black and white vintage photograph, early twentieth century, film grain, light scratches, "
                   "faded sepia tones, documentary look. " + _SEM_TEXTO,
    "anime": "Japanese anime style illustration, cel shading, vibrant colors, expressive characters, detailed "
             "painted background. " + _SEM_TEXTO,
    "3d": "Stylized 3D animated movie render, soft global illumination, cute rounded characters, vibrant colors. "
          + _SEM_TEXTO,
    "sombrio": "Dark moody cinematic illustration, mysterious atmosphere, fog, low key lighting, muted cold colors, "
               "suspense. " + _SEM_TEXTO,
    "realista": "Photorealistic cinematic still, 35mm film look, natural lighting, highly detailed, documentary. "
                + _SEM_TEXTO,
}
# imagem realista feita por IA exige marcar "conteúdo alterado ou sintético" no YouTube Studio
ESTILOS_SINTETICOS = {"realista", "foto_antiga"}


def ilustracao_pixel(prompt: str, personagem: str, indice: int, pasta_visuais: Path, largura: int, altura: int,
                     pixel: int, semente: str) -> Path | None:
    return ilustracao_local(prompt, personagem, indice, pasta_visuais, largura, altura, "pixel", semente, pixel)


def ilustracao_local(prompt: str, personagem: str, indice: int, pasta_visuais: Path, largura: int, altura: int,
                     estilo: str, semente: str, pixel: int = 0) -> Path | None:
    """Desenha a cena no próprio PC (stable-diffusion.cpp + Z-Image-Turbo, grátis) no estilo pedido. No pixel art
    reduz à grade de pixels da tela. A mesma semente e o mesmo 'personagem' em todas as cenas mantêm o visual.
    Devolve None se o gerador local não estiver instalado (a cena cai na busca normal)."""
    import hashlib
    import subprocess
    import zlib

    sd = config.MODELOS / "sd" / "sd-cli.exe"
    pesos = [config.MODELOS / n for n in ("z_image_turbo-Q4_K.gguf", "ae.safetensors",
                                          "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")]
    if not sd.exists() or not all(p.exists() for p in pesos):
        print(f"  cena {indice}: gerador local ausente em {config.MODELOS}; usando a busca de mídia")
        return None
    texto = ESTILOS_IA[estilo] + (personagem.strip() + " " if personagem else "") + "Scene: " + prompt.strip()
    chave = hashlib.md5(texto.encode("utf-8")).hexdigest()[:10]
    final = pasta_visuais / f"{indice:02d}-{estilo}-{chave}.png"
    if final.exists():
        return final
    bruto = pasta_visuais / f"{indice:02d}-{estilo}-bruto.png"
    # tela cheia vertical pede desenho em pé; o resto (layout post e 16:9) sai deitado
    w, h = (768, 1344) if altura > largura else (1024, 768)
    print(f"  cena {indice}: desenhando no PC, estilo {estilo} (cerca de 2 a 5 min)")
    r = subprocess.run([str(sd), "--diffusion-model", str(pesos[0]), "--vae", str(pesos[1]), "--llm", str(pesos[2]),
                        "-p", texto, "--cfg-scale", "1.0", "--steps", "8", "--offload-to-cpu",
                        "--flash-attn", "off,diffusion=on", "--vae-tiling", "-W", str(w), "-H", str(h),
                        "--seed", str(zlib.crc32(semente.encode("utf-8")) % 100000), "-o", str(bruto)],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not bruto.exists():
        print(f"  cena {indice}: gerador local falhou; usando a busca de mídia\n{r.stderr[-400:]}")
        return None
    if not pixel:
        ImageOps.fit(Image.open(bruto).convert("RGB"), (largura, altura), Image.LANCZOS).save(final)
        bruto.unlink(missing_ok=True)
        return final
    # grade de pixels da tela (com a folga da panorâmica): cada pixel do desenho vira um bloco
    folga = pixel * 16
    grade = (-(-(largura + folga) // pixel), -(-(altura + folga) // pixel))
    ImageOps.fit(Image.open(bruto).convert("RGB"), grade, Image.BOX) \
        .quantize(32, method=Image.Quantize.MEDIANCUT).convert("RGB").save(final)
    bruto.unlink(missing_ok=True)
    return final


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
                and anterior.get("versao") == VERSAO_BUSCA and anterior.get("variante", 0) == cena.get("variante", 0)
                and anterior.get("idioma", "en") == cena.get("visual_idioma", "en")
                and Path(anterior.get("arquivo", "")).exists()):
            return Path(anterior["arquivo"])
    achado = _buscar_em_bancos(consulta, indice, largura, altura, cena.get("tipo_visual", tipo), base, usados,
                               int(cena.get("variante", 0)), cena.get("visual_idioma", "en"))
    marca.write_text(json.dumps({"consulta": consulta, "tipo": cena.get("tipo_visual", tipo), "versao": VERSAO_BUSCA,
                                 "variante": cena.get("variante", 0), "idioma": cena.get("visual_idioma", "en"),
                                 "arquivo": str(achado)}),
                     encoding="utf-8")
    return achado


def _buscar_em_bancos(consulta: str, indice: int, largura: int, altura: int, tipo: str,
                      base: Path, usados: set, variante: int = 0, idioma: str = "en") -> Path:
    """Tipo 'video' tenta clipe em cada banco e, se não achar, foto (que ganha movimento no render).
    variante > 0 pula as primeiras opções (marcadas como usadas) para trazer outra imagem."""
    bancos = [("Pexels", config.PEXELS_API_KEY, buscar_pexels), ("Pixabay", config.PIXABAY_API_KEY, buscar_pixabay)]
    for tentativa in (["video", "foto"] if tipo == "video" else [tipo]):
        for nome, chave, buscar in bancos:
            if not (consulta and chave):
                continue
            try:
                pulados = set(usados)
                for _ in range(variante):  # baixa e descarta as opções anteriores só para marcá-las
                    anterior = buscar(consulta, largura, altura, tentativa, base.with_name(base.name + "-pulado"), pulados,
                                      idioma)
                    if anterior:
                        anterior.unlink(missing_ok=True)
                achado = buscar(consulta, largura, altura, tentativa, base, pulados, idioma)
                usados |= pulados
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
