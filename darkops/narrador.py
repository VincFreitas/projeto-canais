"""Narrador cartoon: a pulga mascote do canal, desenhada em vetor com Pillow, que fala junto com a voz.

A boca abre conforme o volume da narração (sincronia labial simples), os olhos piscam, as antenas
balançam e o corpo flutua. O resultado é um vídeo com transparência (.mov) que o render põe num canto
da cena. Tudo gerado pelo código: grátis e sempre igual em todos os vídeos.
"""
import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .render import FFMPEG, FPS

VERSAO = 1
SS = 3  # desenha em 3x e reduz: bordas lisas

MARROM = (150, 86, 44)
MARROM_ESCURO = (98, 52, 24)
BARRIGA = (214, 150, 92)
CONTORNO = (52, 28, 14)
BRANCO = (255, 255, 255)
PRETO = (24, 20, 18)
LINGUA = (232, 96, 108)
BOCHECHA = (240, 120, 120)
OCULOS = (40, 34, 30)


def _volumes(audio: Path, quadros: int) -> np.ndarray:
    """Volume (0 a 1) da narração em cada quadro do vídeo."""
    tmp = audio.with_suffix(".mono.wav")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio), "-ac", "1",
                    "-ar", "16000", str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        amostras = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    tmp.unlink(missing_ok=True)
    por_quadro = 16000 // FPS
    vol = np.array([np.sqrt(np.mean(amostras[i * por_quadro:(i + 1) * por_quadro] ** 2) + 1e-9)
                    if i * por_quadro < len(amostras) else 0.0 for i in range(quadros)])
    vol = np.clip(vol / (np.percentile(vol[vol > 0], 90) if np.any(vol > 0) else 1), 0, 1)
    # suaviza para a boca não tremer
    return np.convolve(vol, np.ones(3) / 3, mode="same")


def _desenhar(t: float, boca: float, lado: int) -> Image.Image:
    """Um quadro da pulga (RGBA, lado x lado)."""
    L = lado * SS
    img = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = L / 100  # unidade: o desenho vive num quadro de 100 x 100

    def e(x0, y0, x1, y1, cor, borda=True):
        d.ellipse([x0 * u, y0 * u, x1 * u, y1 * u], fill=cor,
                  outline=CONTORNO if borda else None, width=int(1.6 * u) if borda else 0)

    flutua = math.sin(t * 2.4) * 2.2
    cy = 54 + flutua
    # patas (atrás do corpo), balançando
    for i, x in enumerate((30, 42, 58, 70)):
        ang = math.sin(t * 6 + i) * 4
        d.line([(x * u, (cy + 18) * u), ((x - 6 + ang) * u, (cy + 32) * u), ((x - 12 + ang) * u, (cy + 33) * u)],
               fill=CONTORNO, width=int(3 * u), joint="curve")
    # antenas
    for lado_ant, base in ((-1, 40), (1, 60)):
        balanco = math.sin(t * 3.1 + lado_ant) * 5
        topo = (base + lado_ant * 12 + balanco, cy - 44)
        d.line([(base * u, (cy - 22) * u), ((base + lado_ant * 6 + balanco / 2) * u, (cy - 36) * u),
                (topo[0] * u, topo[1] * u)], fill=CONTORNO, width=int(2.6 * u), joint="curve")
        e(topo[0] - 3.5, topo[1] - 3.5, topo[0] + 3.5, topo[1] + 3.5, MARROM_ESCURO)
    # corpo e barriga
    e(20, cy - 30, 80, cy + 24, MARROM)
    e(32, cy - 4, 68, cy + 20, BARRIGA, borda=False)
    # brilho no corpo
    d.ellipse([28 * u, (cy - 24) * u, 44 * u, (cy - 14) * u], fill=(255, 255, 255, 70))
    # olhos com óculos
    piscar = (t % 3.7) < 0.12
    for x in (38, 62):
        e(x - 10, cy - 22, x + 10, cy - 2, BRANCO)
        if piscar:
            d.line([((x - 7) * u, (cy - 12) * u), ((x + 7) * u, (cy - 12) * u)], fill=PRETO, width=int(2.4 * u))
        else:
            olhar = math.sin(t * 0.7) * 2
            e(x - 4 + olhar, cy - 16, x + 4 + olhar, cy - 8, PRETO, borda=False)
            e(x - 1.5 + olhar, cy - 15, x + 1 + olhar, cy - 12.5, BRANCO, borda=False)
        d.ellipse([(x - 11) * u, (cy - 23) * u, (x + 11) * u, (cy - 1) * u], outline=OCULOS, width=int(2.4 * u))
    d.line([(49 * u, (cy - 13) * u), (51 * u, (cy - 13) * u)], fill=OCULOS, width=int(2.4 * u))
    # bochechas
    for x in (30, 70):
        d.ellipse([(x - 4) * u, (cy + 1) * u, (x + 4) * u, (cy + 5) * u], fill=BOCHECHA + (150,))
    # boca: abre com o volume
    abre = 1.5 + boca * 9
    d.rounded_rectangle([42 * u, (cy + 3) * u, 58 * u, (cy + 3 + abre) * u], radius=int(min(abre, 8) * u / 1.2),
                        fill=PRETO if abre > 3 else MARROM_ESCURO)
    if abre > 5:
        d.ellipse([45 * u, (cy + abre - 1) * u, 55 * u, (cy + 3 + abre) * u], fill=LINGUA)
    # sombra suave embaixo
    saida = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    sombra = Image.new("L", (L, L), 0)
    ImageDraw.Draw(sombra).ellipse([28 * u, 92 * u, 72 * u, 98 * u], fill=90)
    saida.putalpha(sombra.filter(ImageFilter.GaussianBlur(3 * u)))
    saida.alpha_composite(img)
    return saida.resize((lado, lado), Image.LANCZOS)


def gerar(audio: Path, duracao: float, lado: int, destino: Path) -> Path:
    """Vídeo .mov com transparência da pulga falando junto com 'audio'. Reaproveita se nada mudou."""
    destino = destino.with_suffix(".mov")
    assinatura = {"audio": audio.name, "mtime": audio.stat().st_mtime, "duracao": round(duracao, 2),
                  "lado": lado, "versao": VERSAO}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino
    quadros = max(int(duracao * FPS), 1)
    vol = _volumes(audio, quadros)
    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                             "-pix_fmt", "rgba", "-s", f"{lado}x{lado}", "-r", str(FPS), "-i", "-",
                             "-c:v", "qtrle", "-pix_fmt", "argb", str(destino)], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(quadros):
            proc.stdin.write(_desenhar(q / FPS, float(vol[q]), lado).tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao gravar o narrador")
    marca.write_text(json.dumps(assinatura), encoding="utf-8")
    return destino
