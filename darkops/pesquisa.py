"""Pesquisa de demanda: sugestões de busca, outliers e transcrições.

Tudo via yt-dlp e endpoints públicos, sem chave de API.
"""
import csv
import json
import statistics
import string
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import requests
import yt_dlp
from yt_dlp.utils import DownloadError

from . import config

CACHE_CANAIS = config.CACHE / "canais.json"
VALIDADE_CACHE_DIAS = 7


def _ydl(idioma: str, **extra) -> yt_dlp.YoutubeDL:
    # lang força títulos no idioma original em vez da tradução automática do YouTube
    opcoes = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "extractor_args": {"youtube": {"lang": [idioma]}},
    }
    opcoes.update(extra)
    return yt_dlp.YoutubeDL(opcoes)


def pasta_do_dia(nome: str) -> Path:
    pasta = config.PESQUISA / nome / date.today().isoformat()
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


# ---------- demanda ----------

def sugestoes(termo: str, idioma: str) -> list[str]:
    r = requests.get(
        "https://suggestqueries.google.com/complete/search",
        params={"client": "firefox", "ds": "yt", "hl": idioma, "q": termo},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()[1]


def demanda(termo: str, idioma: str, expandir: bool = True) -> list[tuple[str, int]]:
    """Mapa de demanda: autocomplete do YouTube para o termo e variações.

    Uma sugestão que aparece em várias expansões indica busca recorrente.
    """
    consultas = [termo]
    if expandir:
        consultas += [f"{termo} {letra}" for letra in string.ascii_lowercase]
        consultas += [f"{p} {termo}" for p in ("por que", "como", "o que") if idioma == "pt"]
        consultas += [f"{p} {termo}" for p in ("why", "how", "what") if idioma == "en"]
    contagem: Counter[str] = Counter()
    for c in consultas:
        try:
            contagem.update(sugestoes(c, idioma))
        except requests.RequestException as erro:
            print(f"  aviso: falhou '{c}': {erro}")
        time.sleep(0.2)
    return contagem.most_common()


# ---------- outliers ----------

def _ler_cache() -> dict:
    if CACHE_CANAIS.exists():
        return json.loads(CACHE_CANAIS.read_text(encoding="utf-8"))
    return {}


def _gravar_cache(cache: dict) -> None:
    CACHE_CANAIS.parent.mkdir(parents=True, exist_ok=True)
    CACHE_CANAIS.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def perfil_canal(ydl: yt_dlp.YoutubeDL, canal_id: str, aba: str, cache: dict) -> dict | None:
    """Mediana de views dos vídeos recentes do canal (aba 'videos' ou 'shorts')."""
    chave = f"{canal_id}/{aba}"
    item = cache.get(chave)
    if item and (time.time() - item["quando"]) < VALIDADE_CACHE_DIAS * 86400:
        return item
    try:
        info = ydl.extract_info(f"https://www.youtube.com/channel/{canal_id}/{aba}", download=False)
    except DownloadError:
        return None
    views = [e["view_count"] for e in (info.get("entries") or []) if e and e.get("view_count")]
    if not views:
        return None
    item = {
        "quando": time.time(),
        "mediana": statistics.median(views),
        "amostra": len(views),
        "inscritos": info.get("channel_follower_count"),
    }
    cache[chave] = item
    return item


def outliers(nome: str, buscas: list[str], idioma: str, por_busca: int = 30,
             min_views: int = 10_000, top: int = 30, detalhar: int = 15) -> Path:
    """Busca vídeos, compara com a mediana do canal e ranqueia os que furaram a bolha."""
    pasta = pasta_do_dia(nome)
    cache = _ler_cache()
    videos: dict[str, dict] = {}

    with _ydl(idioma) as ydl:
        for busca in buscas:
            print(f"buscando: {busca}")
            res = ydl.extract_info(f"ytsearch{por_busca}:{busca}", download=False)
            for e in res.get("entries") or []:
                if not e or not e.get("view_count") or not e.get("channel_id"):
                    continue
                if e["view_count"] < min_views:
                    continue
                v = videos.setdefault(e["id"], {
                    "id": e["id"],
                    "titulo": e.get("title"),
                    "canal": e.get("channel"),
                    "canal_id": e["channel_id"],
                    "views": e["view_count"],
                    "duracao_s": e.get("duration") or 0,
                    "url": f"https://www.youtube.com/watch?v={e['id']}",
                    "buscas": [],
                })
                v["buscas"].append(busca)

    canais = {(v["canal_id"], "shorts" if 0 < v["duracao_s"] <= 180 else "videos") for v in videos.values()}
    print(f"{len(videos)} vídeos, {len(canais)} perfis de canal para medir")
    perfis = {}
    # aba do canal em inglês: com outro idioma o yt-dlp lê "1,3 mi" como 1 e a mediana sai errada
    with _ydl("en", playlistend=30) as ydl:
        for i, (cid, aba) in enumerate(sorted(canais), 1):
            perfis[(cid, aba)] = perfil_canal(ydl, cid, aba, cache)
            if i % 10 == 0:
                print(f"  canais medidos: {i}/{len(canais)}")
                _gravar_cache(cache)
    _gravar_cache(cache)

    linhas = []
    for v in videos.values():
        aba = "shorts" if 0 < v["duracao_s"] <= 180 else "videos"
        p = perfis.get((v["canal_id"], aba))
        if not p:
            continue
        v["formato"] = "short" if aba == "shorts" else "longo"
        v["mediana_canal"] = int(p["mediana"])
        v["inscritos"] = p["inscritos"]
        v["score"] = round(v["views"] / max(p["mediana"], 1), 2)
        # views acima do tamanho do canal também é sinal forte de viralização fora da base
        v["views_por_inscrito"] = round(v["views"] / p["inscritos"], 2) if p["inscritos"] else None
        linhas.append(v)

    linhas.sort(key=lambda v: v["score"], reverse=True)
    linhas = linhas[:top]
    _detalhar(linhas[:detalhar], idioma)

    _salvar(pasta, linhas)
    return pasta


def _detalhar(linhas: list[dict], idioma: str) -> None:
    """Data de publicação e velocidade (views/dia) só para os melhores, porque é lento."""
    with _ydl(idioma, extract_flat=False) as ydl:
        for v in linhas:
            try:
                info = ydl.extract_info(v["url"], download=False)
            except DownloadError:
                continue
            if info.get("upload_date"):
                publicado = datetime.strptime(info["upload_date"], "%Y%m%d").date()
                dias = max((date.today() - publicado).days, 1)
                v["publicado"] = publicado.isoformat()
                v["views_por_dia"] = int(v["views"] / dias)
            v["tags"] = (info.get("tags") or [])[:15]


def _salvar(pasta: Path, linhas: list[dict]) -> None:
    (pasta / "outliers.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=2), encoding="utf-8")
    campos = ["score", "views", "mediana_canal", "inscritos", "views_por_inscrito", "views_por_dia",
              "publicado", "formato", "duracao_s", "titulo", "canal", "url"]
    with open(pasta / "outliers.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", delimiter=";")
        w.writeheader()
        w.writerows(linhas)

    md = ["| # | score | views | mediana canal | inscritos | views/dia | formato | título | canal |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, v in enumerate(linhas, 1):
        titulo = (v["titulo"] or "").replace("|", "/")
        md.append(f"| {i} | {v['score']}x | {v['views']:,} | {v['mediana_canal']:,} | "
                  f"{v['inscritos'] or '?'} | {v.get('views_por_dia', '')} | {v['formato']} | "
                  f"[{titulo}]({v['url']}) | {v['canal']} |")
    (pasta / "outliers.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ---------- transcrição ----------

def _melhor_legenda(info: dict, idioma: str) -> str | None:
    """Prefere a legenda automática no idioma original (sufixo -orig), senão a do idioma pedido."""
    auto = info.get("automatic_captions") or {}
    manuais = info.get("subtitles") or {}
    for chave in auto:
        if chave.endswith("-orig"):
            return next((f["url"] for f in auto[chave] if f.get("ext") == "json3"), None)
    for fonte in (manuais, auto):
        for chave in fonte:
            if chave.split("-")[0] == idioma:
                return next((f["url"] for f in fonte[chave] if f.get("ext") == "json3"), None)
    return None


def transcrever(url: str, destino: Path, idioma: str) -> Path | None:
    destino.mkdir(parents=True, exist_ok=True)
    with _ydl(idioma, extract_flat=False) as ydl:
        info = ydl.extract_info(url, download=False)
        link = _melhor_legenda(info, idioma)
        if not link:
            print(f"  sem legenda: {url}")
            return None
        dados = json.loads(ydl.urlopen(link).read().decode("utf-8"))
    texto = "".join(s.get("utf8", "") for e in dados.get("events", []) if "segs" in e for s in e["segs"])
    arquivo = destino / f"{info['id']}.txt"
    cabecalho = f"# {info.get('title')}\n# {url}\n# canal: {info.get('channel')} | views: {info.get('view_count')}\n\n"
    arquivo.write_text(cabecalho + texto.replace("\n", " "), encoding="utf-8")
    return arquivo
