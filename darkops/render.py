"""Montagem com ffmpeg: uma cena por arquivo (cacheável), depois concatenação e mixagem final."""
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from .visuais import EXT_VIDEO

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
ZOOM = 0.12  # quanto a imagem aproxima/afasta ao longo da cena


def rodar(args: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou:\n{proc.stderr[-2000:]}")


def duracao(arquivo: Path) -> float:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(arquivo)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    achado = re.search(r"Duration: (\d+):(\d+):([\d.]+)", proc.stderr)
    if not achado:
        raise RuntimeError(f"não consegui ler a duração de {arquivo}")
    h, m, s = achado.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def _movimento(indice: int, quadros: int) -> str:
    """Alterna aproximar, afastar e panorâmica para as cenas não parecerem iguais."""
    tipo = indice % 4
    if tipo == 0:
        z, x = f"1+{ZOOM}*on/{quadros}", "(iw-iw/zoom)/2"
    elif tipo == 1:
        z, x = f"{1 + ZOOM}-{ZOOM}*on/{quadros}", "(iw-iw/zoom)/2"
    elif tipo == 2:
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*on/{quadros}"
    else:
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*(1-on/{quadros})"
    return f"zoompan=z='{z}':x='{x}':y='(ih-ih/zoom)/2':d={quadros}"


def cena(visual: Path, audio: Path, legenda: Path | None, saida: Path,
         largura: int, altura: int, indice: int, pausa: float) -> float:
    """Renderiza uma cena com a duração da narração + pausa. Devolve a duração."""
    dur = duracao(audio) + pausa
    quadros = max(int(dur * FPS), 1)
    legendas = f",ass={legenda.name}" if legenda else ""  # caminho relativo evita escapar 'C:' no filtro
    if visual.suffix.lower() in EXT_VIDEO:
        entrada = ["-stream_loop", "-1", "-i", str(visual)]
        video = (f"[0:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
                 f"crop={largura}:{altura},fps={FPS},setsar=1")
    else:
        entrada = ["-i", str(visual)]
        # ampliar antes do zoompan tira o tremido causado pelo arredondamento de pixels
        video = (f"[0:v]scale={largura * 2}:{altura * 2}:force_original_aspect_ratio=increase,"
                 f"crop={largura * 2}:{altura * 2},{_movimento(indice, quadros)}:s={largura}x{altura}:fps={FPS},"
                 f"setsar=1")
    filtro = f"{video}{legendas},format=yuv420p[v];[1:a]aresample=48000,apad[a]"
    rodar([*entrada, "-i", str(audio), "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
           "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", saida.name], cwd=saida.parent)
    return dur


def ambiente(duracao_s: float, destino: Path) -> Path:
    """Trilha de suspense sintetizada (ruído grave + drones): livre de direitos, sem download."""
    filtro = ("anoisesrc=color=brown:amplitude=0.5,lowpass=f=300,volume=0.6[n];"
              "sine=f=55,volume=0.35,tremolo=f=0.15:d=0.6[a];"
              "sine=f=82.41,volume=0.2,tremolo=f=0.11:d=0.7[b];"
              "sine=f=116.54,volume=0.08,tremolo=f=0.1:d=0.9[c];"
              "[n][a][b][c]amix=inputs=4:normalize=0,aecho=0.8:0.7:900:0.4,"
              "highpass=f=35,alimiter=limit=0.8[out]")
    rodar(["-filter_complex", filtro, "-map", "[out]", "-t", f"{duracao_s:.2f}", "-ar", "48000", "-ac", "2",
           str(destino)])
    return destino


def juntar(cenas: list[Path], musica: Path | str | None, saida: Path, volume_musica: float = 0.12) -> None:
    """Concatena sem reencodar o vídeo; normaliza o volume para -14 LUFS (padrão das plataformas)."""
    pasta = cenas[0].parent
    lista = pasta / "lista.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in cenas), encoding="utf-8")
    junta = pasta / "junta.mp4"
    rodar(["-f", "concat", "-safe", "0", "-i", lista.name, "-c", "copy", junta.name], cwd=pasta)

    total = duracao(junta)
    if musica == "ambiente":
        musica = ambiente(total, pasta / "ambiente.wav")
    normalizar = "loudnorm=I=-14:TP=-1.5:LRA=11"
    if musica:
        fim = max(total - 3, 0)
        filtro = (f"[1:a]volume={volume_musica},afade=t=in:d=2,afade=t=out:st={fim:.2f}:d=3[m];"
                  f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,{normalizar}[a]")
        entradas = ["-i", str(junta), "-stream_loop", "-1", "-i", str(musica)]
    else:
        filtro = f"[0:a]{normalizar}[a]"
        entradas = ["-i", str(junta)]
    saida.parent.mkdir(parents=True, exist_ok=True)
    rodar([*entradas, "-filter_complex", filtro, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(saida)])
