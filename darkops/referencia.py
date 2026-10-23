"""Aprender com referência: mede o estilo de um vídeo de outro canal sem copiar nada dele.

  python -m darkops referencia <url> [<url> ...]      mede e mostra a proposta de padrão para o perfil

De cada link (YouTube, Shorts, Instagram...) sai: duração, formato, cortes por minuto, segundos por corte,
palavras por minuto (pela legenda do YouTube, quando existe) e uma folha de prints para ver o tipo de imagem.
O texto da narração é usado só para contar palavras; não é guardado. Os prints e o vídeo baixado ficam em
obra/referencias/ (fora do Git), porque são de terceiros.
"""
import json
import re
import statistics
import subprocess
from pathlib import Path

import imageio_ffmpeg

from . import config

PASTA = config.OBRA / "referencias"
LIMIAR_CORTE = 0.3  # diferença entre quadros (0 a 1) que conta como troca de cena


def _baixar(url: str) -> tuple[dict, Path]:
    import yt_dlp
    opcoes = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True,
              # resolução baixa basta para medir cortes e ver o tipo de imagem
              "format": "bv*[height<=480]+ba/b[height<=480]/b", "merge_output_format": "mp4",
              "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),  # o ffmpeg do projeto junta vídeo e áudio
              "outtmpl": str(PASTA / "%(id)s" / "video.%(ext)s")}
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=True)
    pasta = PASTA / info["id"]
    video = next(pasta.glob("video.*"))
    return info, video


def _cortes(video: Path) -> list[float]:
    """Segundos em que a imagem troca (filtro de cena do ffmpeg)."""
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video),
                           "-vf", f"select='gt(scene,{LIMIAR_CORTE})',showinfo", "-an", "-f", "null", "-"],
                          capture_output=True, text=True, errors="replace")
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]


def _folha(video: Path, duracao: float, destino: Path) -> Path:
    """18 prints espalhados pelo vídeo numa folha só (6x3)."""
    intervalo = max(duracao / 18, 0.5)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                    "-vf", f"fps=1/{intervalo:.2f},scale=240:-2,tile=6x3", "-frames:v", "1", str(destino)],
                   check=True)
    return destino


def _palavras(info: dict) -> int | None:
    """Conta as palavras da legenda do YouTube (o texto não é guardado)."""
    from .pesquisa import _melhor_legenda
    import yt_dlp
    link = _melhor_legenda(info, (info.get("language") or "pt").split("-")[0])
    if not link:
        return None
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        dados = json.loads(ydl.urlopen(link).read().decode("utf-8"))
    texto = " ".join(s.get("utf8", "") for e in dados.get("events", []) if "segs" in e for s in e["segs"])
    return len(texto.split())


def analisar(url: str) -> dict:
    PASTA.mkdir(parents=True, exist_ok=True)
    info, video = _baixar(url)
    duracao = float(info.get("duration") or 0) or None
    from .render import duracao as medir
    duracao = duracao or medir(video)
    cortes = _cortes(video)
    trechos = [b - a for a, b in zip([0.0] + cortes, cortes + [duracao]) if b - a > 0.2]
    palavras = _palavras(info)
    largura, altura = info.get("width") or 0, info.get("height") or 0
    resultado = {
        "url": url, "id": info["id"], "titulo": info.get("title"), "canal": info.get("channel") or info.get("uploader"),
        "duracao_s": round(duracao, 1),
        "formato": "vertical" if altura > largura else "longo",
        "cortes_por_min": round(len(cortes) / duracao * 60, 1) if duracao else None,
        "segundos_por_corte": round(statistics.median(trechos), 1) if trechos else None,
        "palavras_por_min": round(palavras / duracao * 60) if palavras and duracao else None,
        "folha": str(_folha(video, duracao, PASTA / info["id"] / "folha.jpg")),
    }
    (PASTA / info["id"] / "analise.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                                                     encoding="utf-8")
    return resultado


def proposta(analises: list[dict]) -> dict:
    """Padrão sugerido para o perfil a partir das médias das referências."""
    from .perfis import DURACOES, RITMOS
    validas = [a for a in analises if a.get("duracao_s")]
    if not validas:
        return {}
    formato = statistics.mode(a["formato"] for a in validas)
    duracao = statistics.median(a["duracao_s"] for a in validas)
    sugestao = {"formato": formato,
                "duracao_s": min(DURACOES[formato], key=lambda s: abs(s - duracao))}
    cortes = [a["segundos_por_corte"] for a in validas if a.get("segundos_por_corte")]
    if cortes:
        sugestao["ritmo_corte_s"] = min(RITMOS, key=lambda s: abs(s - statistics.median(cortes)))
    ppm = [a["palavras_por_min"] for a in validas if a.get("palavras_por_min")]
    if ppm:
        media = statistics.median(ppm)
        # a voz neural fala ~150 palavras/min em +0%; cada +10% acelera mais ~15
        sugestao["velocidade"] = "+0%" if media < 158 else "+10%" if media < 175 else "+20%"
        sugestao["palavras_por_min"] = round(media)
    return sugestao


def salvar(perfil, analises: list[dict]) -> Path:
    """Guarda as medições no controle do perfil (sem os prints, que ficam em obra/)."""
    destino = perfil.controle / "referencias.json"
    perfil.controle.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"analises": analises, "proposta": proposta(analises)},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def ler(perfil) -> dict:
    destino = perfil.controle / "referencias.json"
    return json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
