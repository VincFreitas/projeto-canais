# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Sincronia com a fala e efeitos sonoros.

- momento(): em que segundo da cena uma palavra (ou número) é falada, a partir dos tempos por
  palavra que o motor de voz devolve.
- Efeitos sonoros (whoosh, pop, ding, thud, riser, impacto): o sintetizado daqui mais os sons CC0 do banco
  assets/efeitos (efeitos.py), sorteados por vídeo. O riser termina no tempo do evento (a revelação), o resto
  começa nele. A produção junta os eventos de todas as cenas numa única trilha que a mixagem final soma.
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


def _riser(rng) -> np.ndarray:
    """Subida de tensão: ruído que abre e um tom que sobe, crescendo até o fim (o fim cai no impacto)."""
    n = int(1.2 * TAXA)
    t = np.arange(n) / TAXA
    p = t / t[-1]
    tom = np.sin(2 * np.pi * np.cumsum(180 + 900 * p ** 2) / TAXA)
    ruido = np.convolve(rng.standard_normal(n), np.ones(6) / 6, mode="same")
    return (tom * 0.5 + ruido * (0.3 + 0.9 * p)) * p ** 2.2


def _impacto(rng) -> np.ndarray:
    """Batida grave de revelação: queda de 70 para 35 Hz, estalo no ataque e cauda curta."""
    n = int(1.1 * TAXA)
    t = np.arange(n) / TAXA
    grave = np.sin(2 * np.pi * np.cumsum(35 + 35 * np.exp(-t * 9)) / TAXA) * _env(n, 0.002, 4.5)
    estalo = rng.standard_normal(n) * _env(n, 0.0005, 60) * 0.5
    return grave + estalo


def _tique(rng) -> np.ndarray:
    """Matraca do painel de aeroporto: estalos curtos e secos em sequência, cada vez mais espaçados até parar."""
    n = int(0.8 * TAXA)
    saida = np.zeros(n)
    t, passo = 0.0, 0.028
    while t < 0.75:
        i = int(t * TAXA)
        m = min(int(0.012 * TAXA), n - i)
        estalo = np.diff(rng.standard_normal(m + 1)) * _env(m, 0.0003, 420)
        saida[i:i + m] += estalo * (1 - t / 0.9) * (0.7 + 0.3 * rng.random())
        t += passo * (0.8 + 0.4 * rng.random())
        passo *= 1.05
    return saida


SONS = {"whoosh": _whoosh, "pop": _pop, "ding": _ding, "thud": _thud, "riser": _riser, "impacto": _impacto, "tique": _tique}
VOLUMES = {"whoosh": 0.22, "pop": 0.32, "ding": 0.26, "thud": 0.42, "riser": 0.2, "impacto": 0.5, "tique": 0.28}
ANTES = {"riser"}  # som que termina no tempo do evento, em vez de começar nele


def _carregar(arquivo: Path) -> np.ndarray:
    with wave.open(str(arquivo)) as w:
        dados = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        if w.getnchannels() > 1:
            dados = dados.reshape(-1, w.getnchannels()).mean(axis=1)
    return dados


def _variacoes(nome: str, rng) -> list[np.ndarray]:
    """Sintetizado + os sons CC0 do banco (assets/efeitos), já no volume do tipo."""
    from .efeitos import do_tipo
    sons = [SONS[nome](rng)]
    for arquivo in do_tipo(nome):
        try:
            sons.append(_carregar(arquivo))
        except (OSError, wave.Error, EOFError):
            continue
    return [s / (np.abs(s).max() or 1) * VOLUMES[nome] for s in sons if len(s)]


def trilha_efeitos(eventos: list[tuple[float, str]], duracao: float, destino: Path, semente: str = "") -> Path | None:
    """Monta um WAV estéreo com os efeitos nos tempos absolutos do vídeo. None se não houver eventos.
    Cada vídeo (semente = slug) sorteia uma variação por tipo e alterna entre elas a cada uso."""
    if not eventos:
        return None
    rng = np.random.default_rng(sum(map(ord, semente)) or 7)
    n = int((duracao + 1) * TAXA)
    mix = np.zeros(n)
    cache, usos = {}, {}
    for t, nome in sorted(eventos):
        if nome not in SONS or t < 0:
            continue
        if nome not in cache:
            variacoes = _variacoes(nome, rng)
            cache[nome] = [variacoes[k] for k in rng.permutation(len(variacoes))]
        som = cache[nome][usos.get(nome, 0) % len(cache[nome])]
        usos[nome] = usos.get(nome, 0) + 1
        i = int(t * TAXA) - (len(som) if nome in ANTES else 0)
        if i < 0:
            som, i = som[-i:], 0
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
