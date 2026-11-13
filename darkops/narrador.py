# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
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

VERSAO = 2
SS = 3  # desenha em 3x e reduz: bordas lisas
REACAO = 1.3  # segundos que uma reação (susto, dúvida, alegria, aflição) dura
PULO = 0.35  # segundos do pulinho no começo da reação

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


EXPRESSOES = ("normal", "feliz", "surpresa", "preocupada", "duvida")
AMARELO_SINAL = (255, 214, 0)


def _reacao_ativa(t: float, reacoes: list[tuple[float, str]]) -> tuple[str, float] | None:
    """A reação em curso no instante t: (tipo, segundos desde o começo), ou None."""
    ativa = None
    for inicio, tipo in reacoes:
        if inicio <= t < inicio + REACAO:
            ativa = (tipo, t - inicio)
    return ativa


def _sinal(d: ImageDraw.ImageDraw, tipo: str, x: float, y: float, u: float, escala: float) -> None:
    """'!' no susto, '?' na dúvida e duas estrelinhas na alegria, flutuando acima da cabeça."""
    s = u * escala
    larg = int(2.6 * s)
    if tipo == "surpresa":
        fino = int(1.4 * s)  # contorno fino: o traço do '!' é estreito
        d.rounded_rectangle([(x - 3.2 * escala) * u, (y - 13 * escala) * u, (x + 3.2 * escala) * u, (y + 1 * escala) * u],
                            radius=int(3 * s), fill=AMARELO_SINAL, outline=CONTORNO, width=fino)
        d.ellipse([(x - 3 * escala) * u, (y + 3 * escala) * u, (x + 3 * escala) * u, (y + 9 * escala) * u],
                  fill=AMARELO_SINAL, outline=CONTORNO, width=fino)
    elif tipo == "duvida":
        d.arc([(x - 6 * escala) * u, (y - 13 * escala) * u, (x + 6 * escala) * u, (y - 1 * escala) * u],
              150, 420, fill=CONTORNO, width=int(5.2 * s))
        d.arc([(x - 6 * escala) * u, (y - 13 * escala) * u, (x + 6 * escala) * u, (y - 1 * escala) * u],
              150, 420, fill=AMARELO_SINAL, width=int(2.6 * s))
        d.line([(x * u, (y - 1 * escala) * u), (x * u, (y + 2.5 * escala) * u)], fill=AMARELO_SINAL, width=int(2.6 * s))
        d.ellipse([(x - 2.2 * escala) * u, (y + 4 * escala) * u, (x + 2.2 * escala) * u, (y + 8.4 * escala) * u],
                  fill=AMARELO_SINAL, outline=CONTORNO, width=larg)
    elif tipo == "feliz":
        for dx, dy, r in ((0, -4, 5.5), (-9, 4, 3.5)):
            cx, cy, r = x + dx * escala, y + dy * escala, r * escala
            pontas = []
            for k in range(8):  # estrela de 4 pontas
                raio = r if k % 2 == 0 else r * 0.35
                ang = math.pi / 4 * k - math.pi / 2
                pontas.append(((cx + math.cos(ang) * raio) * u, (cy + math.sin(ang) * raio) * u))
            d.polygon(pontas, fill=AMARELO_SINAL, outline=CONTORNO)


def _desenhar(t: float, boca: float, lado: int, expressao: str = "normal",
              reacoes: list[tuple[float, str]] | None = None) -> Image.Image:
    """Um quadro da pulga (RGBA, lado x lado). expressao: normal, feliz, surpresa, preocupada ou duvida.

    reacoes: [(segundo, tipo)]. Na reação a pulga troca de rosto por REACAO segundos, dá um pulinho
    e mostra um sinal acima da cabeça (! no susto, ? na dúvida, estrelinhas na alegria)."""
    L = lado * SS
    img = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = L / 100  # unidade: o desenho vive num quadro de 100 x 100

    def e(x0, y0, x1, y1, cor, borda=True):
        d.ellipse([x0 * u, y0 * u, x1 * u, y1 * u], fill=cor,
                  outline=CONTORNO if borda else None, width=int(1.6 * u) if borda else 0)

    ativa = _reacao_ativa(t, reacoes or [])
    pulo = 0.0
    if ativa:
        expressao = ativa[0]
        if ativa[1] < PULO:
            pulo = math.sin(math.pi * ativa[1] / PULO) * 4
    flutua = math.sin(t * 2.4) * 2.2
    cy = 54 + flutua - pulo
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
        dentro = 1 if x < 50 else -1  # lado da sobrancelha voltado para o meio do rosto
        if expressao == "surpresa":  # sobrancelhas lá em cima
            d.arc([(x - 8) * u, (cy - 36) * u, (x + 8) * u, (cy - 26) * u], 200, 340, fill=CONTORNO, width=int(2.4 * u))
        elif expressao == "preocupada":  # ponta de dentro levantada
            d.line([((x - 8 * dentro) * u, (cy - 27) * u), ((x + 7 * dentro) * u, (cy - 32) * u)],
                   fill=CONTORNO, width=int(2.4 * u))
        elif expressao == "duvida":  # uma sobrancelha lá em cima, a outra reta
            if x > 50:
                d.arc([(x - 8) * u, (cy - 37) * u, (x + 8) * u, (cy - 27) * u], 200, 340, fill=CONTORNO, width=int(2.4 * u))
            else:
                d.line([((x - 7) * u, (cy - 27) * u), ((x + 7) * u, (cy - 27) * u)], fill=CONTORNO, width=int(2.4 * u))
        if expressao == "feliz" and not piscar:  # olhos fechados de alegria (^ ^)
            d.arc([(x - 6) * u, (cy - 15) * u, (x + 6) * u, (cy - 5) * u], 200, 340, fill=PRETO, width=int(2.4 * u))
        elif piscar:
            d.line([((x - 7) * u, (cy - 12) * u), ((x + 7) * u, (cy - 12) * u)], fill=PRETO, width=int(2.4 * u))
        else:
            olhar = 3 if expressao == "duvida" else math.sin(t * 0.7) * 2  # na dúvida olha para cima e de lado
            alto = -3 if expressao == "duvida" else 0
            r = 2.5 if expressao == "surpresa" else 4  # pupila pequena de susto
            e(x - r + olhar, cy - 12 - r + alto, x + r + olhar, cy - 12 + r + alto, PRETO, borda=False)
            e(x - 1.5 + olhar, cy - 15 + alto, x + 1 + olhar, cy - 12.5 + alto, BRANCO, borda=False)
        d.ellipse([(x - 11) * u, (cy - 23) * u, (x + 11) * u, (cy - 1) * u], outline=OCULOS, width=int(2.4 * u))
    d.line([(49 * u, (cy - 13) * u), (51 * u, (cy - 13) * u)], fill=OCULOS, width=int(2.4 * u))
    # bochechas
    for x in (30, 70):
        d.ellipse([(x - 4) * u, (cy + 1) * u, (x + 4) * u, (cy + 5) * u], fill=BOCHECHA + (150,))
    if expressao == "preocupada":  # gota de suor na testa
        gx, gy = 74, cy - 26 + (t * 6 % 6)
        d.polygon([(gx * u, (gy - 5) * u), ((gx - 3) * u, gy * u), ((gx + 3) * u, gy * u)], fill=(120, 200, 255))
        e(gx - 3, gy - 2.5, gx + 3, gy + 3.5, (120, 200, 255), borda=False)
    # boca: abre com o volume
    abre = 1.5 + boca * 9 + (4 if expressao == "surpresa" else 0)
    if expressao == "feliz" and boca < 0.15:  # sorriso quando não está falando
        d.arc([42 * u, (cy - 2) * u, 58 * u, (cy + 10) * u], 20, 160, fill=PRETO, width=int(2.4 * u))
        abre = 0
    if abre:
        d.rounded_rectangle([42 * u, (cy + 3) * u, 58 * u, (cy + 3 + abre) * u],
                            radius=int(min(abre, 8) * u / 1.2), fill=PRETO if abre > 3 else MARROM_ESCURO)
    if abre > 5:
        d.ellipse([45 * u, (cy + abre - 1) * u, 55 * u, (cy + 3 + abre) * u], fill=LINGUA)
    if ativa and ativa[0] in ("surpresa", "duvida", "feliz"):  # sinal acima da cabeça: cresce, balança e some
        dt = ativa[1]
        escala = 1.35 * min(dt / 0.15, 1.0) * (1 + 0.25 * math.sin(math.pi * min(dt / 0.15, 1.0)))
        escala *= max(0.0, min(1.0, (REACAO - dt) / 0.25))
        if escala > 0.05:
            _sinal(d, ativa[0], 87 + math.sin(dt * 9) * 1.2, cy - 30, u, escala)
    # sombra suave embaixo
    saida = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    sombra = Image.new("L", (L, L), 0)
    ImageDraw.Draw(sombra).ellipse([28 * u, 92 * u, 72 * u, 98 * u], fill=90)
    saida.putalpha(sombra.filter(ImageFilter.GaussianBlur(3 * u)))
    saida.alpha_composite(img)
    return saida.resize((lado, lado), Image.Resampling.LANCZOS)


def _pixelar(img: Image.Image, pixel: int) -> Image.Image:
    """Versão pixel art do quadro: desenha pequeno, sem meia transparência, e amplia sem suavizar."""
    lado = img.width
    peq = img.resize((lado // pixel, lado // pixel), Image.Resampling.BOX)
    alfa = peq.getchannel("A").point(lambda a: 255 if a > 110 else 0)
    peq = peq.convert("RGB").quantize(24, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    peq.putalpha(alfa)
    return peq.resize((lado, lado), Image.Resampling.NEAREST)


def reacoes_da_cena(cena: dict, palavras: list[dict], destaque: tuple | None = None,
                    selo: tuple | None = None) -> list[tuple[float, str]]:
    """Quando a pulga reage, tirado do que já está marcado na cena:

    palavra-herói = susto (!), carimbo `ruim` = aflição, carimbo `bom` = alegria (estrelinhas),
    fim de pergunta = dúvida (?). `"reacoes": [{"em": "palavra", "tipo": "surpresa"}]` na cena acrescenta outras.
    Reações a menos de REACAO segundos da anterior saem, para a pulga não ficar trocando de cara."""
    from .sincronia import momento
    lista: list[tuple[float, str]] = []
    if destaque:
        lista.append((float(destaque[1]), "surpresa"))
    if selo:
        lista.append((float(selo[2]), "feliz" if selo[1] == "bom" else "preocupada"))
    for p in palavras:
        if str(p.get("texto", "")).rstrip().endswith("?"):
            lista.append((float(p["inicio"]), "duvida"))
    for r in cena.get("reacoes", []):
        t = momento(palavras, r.get("em", "")) if r.get("em") else r.get("t")
        if t is not None and r.get("tipo") in EXPRESSOES:
            lista.append((float(t), r["tipo"]))
    saida: list[tuple[float, str]] = []
    # na mesma palavra, o carimbo ganha da palavra-herói, que ganha da pergunta
    ordem = {"preocupada": 0, "feliz": 0, "surpresa": 1, "duvida": 2}
    for t, tipo in sorted(lista, key=lambda r: (round(r[0], 2), ordem.get(r[1], 3))):
        if not saida or t - saida[-1][0] >= REACAO - 1e-6:
            saida.append((t, tipo))
    return saida


def gerar(audio: Path, duracao: float, lado: int, destino: Path, pixel: int = 0,
          expressao: str = "normal", reacoes: list[tuple[float, str]] | None = None) -> Path:
    """Vídeo .mov com transparência da pulga falando junto com 'audio'. Reaproveita se nada mudou.

    pixel > 0 = pulga em pixel art (cada pixel do desenho vira um bloco de 'pixel' x 'pixel').
    reacoes = [(segundo, tipo)] em que a pulga reage ao que está sendo dito (veja _desenhar)."""
    destino = destino.with_suffix(".mov")
    reacoes = sorted((round(float(t), 2), tipo) for t, tipo in (reacoes or []) if tipo in EXPRESSOES)
    assinatura = {"audio": audio.name, "mtime": audio.stat().st_mtime, "duracao": round(duracao, 2),
                  "lado": lado, "versao": VERSAO, "pixel": pixel, "expressao": expressao,
                  "reacoes": [list(r) for r in reacoes]}
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
            quadro = _desenhar(q / FPS, float(vol[q]), lado, expressao, reacoes)
            if pixel:
                quadro = _pixelar(quadro, pixel)
            proc.stdin.write(quadro.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao gravar o narrador")
    marca.write_text(json.dumps(assinatura), encoding="utf-8")
    return destino
