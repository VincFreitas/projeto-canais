"""Sincronia com a fala e efeitos sonoros.

- momento(): em que segundo da cena uma palavra (ou número) é falada, a partir dos tempos por
  palavra que o motor de voz devolve.
- Efeitos sonoros sintetizados (whoosh, pop, ding, thud): livres de direitos, sem download.
  A produção junta os eventos de todas as cenas numa única trilha que a mixagem final soma.
"""
import re
import unicodedata
import wave
from pathlib import Path

import numpy as np

TAXA = 48000


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", texto.replace(".", "").replace(",", ""))


def momento(palavras: list[dict], alvo: str, depois: float = 0.0) -> float | None:
    """Início da primeira palavra (a partir de 'depois') que bate com o começo de 'alvo'.

    Aceita alvo com várias palavras ("três corações"): casa a sequência. Números casam com
    ou sem separador ("2.530" = "2530")."""
    partes = [_norm(p) for p in str(alvo).split() if _norm(p)]
    if not partes:
        return None
    nomes = [_norm(p["texto"]) for p in palavras]
    for i, p in enumerate(palavras):
        if p["inicio"] < depois - 1e-6:
            continue
        if all(i + k < len(nomes) and nomes[i + k].startswith(partes[k]) for k in range(len(partes))):
            return float(p["inicio"])
    return None


# ---------- efeitos sonoros ----------

def _env(n: int, ataque: float, queda: float) -> np.ndarray:
    t = np.arange(n) / TAXA
    return np.minimum(t / max(ataque, 1e-4), 1.0) * np.exp(-t * queda)


def _whoosh(rng) -> np.ndarray:
    n = int(0.42 * TAXA)
    ruido = rng.standard_normal(n)
    t = np.arange(n) / TAXA
    # varredura de filtro: média móvel com janela que encurta (grave -> agudo)
    saida = np.zeros(n)
    acumulado = np.cumsum(np.concatenate([[0], ruido]))
    for i in range(n):
        janela = int(40 - 34 * (t[i] / t[-1]))
        a = max(i - janela, 0)
        saida[i] = (acumulado[i + 1] - acumulado[a]) / max(i + 1 - a, 1)
    forma = np.sin(np.pi * np.clip(t / t[-1], 0, 1)) ** 2
    return saida * forma * 3.0


def _pop(rng) -> np.ndarray:
    n = int(0.09 * TAXA)
    t = np.arange(n) / TAXA
    freq = 950 * np.exp(-t * 18) + 380
    return np.sin(2 * np.pi * np.cumsum(freq) / TAXA) * _env(n, 0.002, 38) * 0.9


def _ding(rng) -> np.ndarray:
    n = int(0.9 * TAXA)
    t = np.arange(n) / TAXA
    som = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1318, 1.0), (2637, 0.35), (3951, 0.15)))
    return som * _env(n, 0.003, 5.5) * 0.45


def _thud(rng) -> np.ndarray:
    n = int(0.3 * TAXA)
    t = np.arange(n) / TAXA
    grave = np.sin(2 * np.pi * (55 * t + 60 * (1 - np.exp(-t * 25)) / 25)) * _env(n, 0.002, 14)
    estalo = rng.standard_normal(n) * _env(n, 0.001, 90) * 0.25
    return (grave + estalo) * 0.9


SONS = {"whoosh": _whoosh, "pop": _pop, "ding": _ding, "thud": _thud}
VOLUMES = {"whoosh": 0.22, "pop": 0.32, "ding": 0.26, "thud": 0.42}


def trilha_efeitos(eventos: list[tuple[float, str]], duracao: float, destino: Path) -> Path | None:
    """Monta um WAV estéreo com os efeitos nos tempos absolutos do vídeo. None se não houver eventos."""
    if not eventos:
        return None
    rng = np.random.default_rng(7)
    n = int((duracao + 1) * TAXA)
    mix = np.zeros(n)
    cache = {}
    for t, nome in sorted(eventos):
        if nome not in SONS or t < 0:
            continue
        if nome not in cache:
            som = SONS[nome](rng)
            cache[nome] = som / (np.abs(som).max() or 1) * VOLUMES[nome]
        som = cache[nome]
        i = int(t * TAXA)
        fim = min(i + len(som), n)
        if i < n:
            mix[i:fim] += som[: fim - i]
    mix = np.clip(mix[: int(duracao * TAXA)], -0.98, 0.98)
    estereo = np.repeat(mix[:, None], 2, axis=1)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((estereo * 32767).astype("<i2").tobytes())
    return destino
