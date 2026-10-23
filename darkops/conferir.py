"""Conferência automática do vídeo pronto, antes de aprovar.

  python -m darkops conferir saida/<slug>-vertical.mp4

Procura o que costuma passar despercebido: tela preta, silêncio no meio, volume baixo ou estourado,
duração fora do padrão do canal ou acima do limite do Shorts, e resolução errada para o formato.
Não substitui assistir: é uma segunda olhada que aponta o segundo exato de cada problema.
"""
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from . import config

LIMITE_SHORTS_S = 180


def _ffmpeg(video: Path, *filtros: str) -> str:
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video), *filtros,
                           "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    return proc.stderr


def _minuto(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def conferir(video: Path, duracao_alvo: float | None = None) -> dict:
    if not video.exists():
        raise SystemExit(f"vídeo não encontrado: {video}")
    info = _ffmpeg(video)
    total = sum(float(x) * m for x, m in zip(re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups(), (3600, 60, 1)))
    largura, altura = map(int, re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", info).groups())
    achados = []

    def anotar(nivel: str, texto: str, t: float | None = None):
        achados.append({"nivel": nivel, "texto": texto, "t": round(t, 1) if t is not None else None})

    pretas = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", _ffmpeg(video, "-vf", "blackdetect=d=0.4:pic_th=0.97", "-an"))
    for ini, fim in pretas:
        ini, fim = float(ini), float(fim)
        if ini > 0.3 and fim < total - 0.3:  # o fade do começo e do fim não conta
            anotar("erro", f"tela preta de {fim - ini:.1f} s em {_minuto(ini)}", ini)

    audio = _ffmpeg(video, "-af", "silencedetect=noise=-45dB:d=1.2,volumedetect", "-vn")
    for ini, fim in zip(re.findall(r"silence_start: ([\d.]+)", audio), re.findall(r"silence_end: ([\d.]+)", audio)):
        ini, fim = float(ini), float(fim)
        if fim < total - 0.5:
            anotar("aviso", f"silêncio de {fim - ini:.1f} s em {_minuto(ini)} (narração cortada?)", ini)
    media = re.search(r"mean_volume: (-?[\d.]+) dB", audio)
    pico = re.search(r"max_volume: (-?[\d.]+) dB", audio)
    if media and float(media.group(1)) < -28:
        anotar("aviso", f"volume médio baixo ({media.group(1)} dB); o ideal fica entre -20 e -14 dB")
    if pico and float(pico.group(1)) >= -0.1:
        anotar("aviso", "o áudio bate no máximo (pode estourar no celular)")
    if not media:
        anotar("erro", "o vídeo não tem áudio")

    vertical = altura > largura
    if vertical and (largura, altura) != config.FORMATOS["vertical"]:
        anotar("aviso", f"resolução {largura}x{altura}; o vertical do projeto é 1080x1920")
    if vertical and total > LIMITE_SHORTS_S:
        anotar("erro", f"{total:.0f} s passa do limite do Shorts ({LIMITE_SHORTS_S} s)")
    if duracao_alvo and abs(total - duracao_alvo) > max(duracao_alvo * 0.4, 10):
        anotar("aviso", f"duração {total:.0f} s, longe do padrão do canal ({duracao_alvo:.0f} s)")
    if not achados:
        anotar("ok", "nenhum problema encontrado")
    return {"video": video.name, "duracao_s": round(total, 1), "resolucao": f"{largura}x{altura}", "achados": achados}


def salvar(resultado: dict, perfil) -> Path:
    destino = perfil.controle / "conferencias" / (Path(resultado["video"]).stem + ".json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def ler(perfil, video: str) -> dict:
    destino = perfil.controle / "conferencias" / (Path(video).stem + ".json")
    return json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
