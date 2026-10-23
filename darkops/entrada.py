"""Outros jeitos de começar um vídeo: roteiro pronto (texto) ou narração pronta (áudio).

- roteiro pronto: o texto é dividido em cenas pelo ritmo do canal (ritmo_corte_s), sempre em fim de frase,
  e cada cena ganha uma busca de imagem com as palavras mais fortes dela (revise no editor de cenas).
- narração pronta: o áudio é transcrito pelo Azure Speech com o tempo de cada palavra, cortado em cenas
  nas pausas da fala e cada cena usa o próprio trecho do áudio (sem voz sintética).
"""
import json
import os
import re
import subprocess
import urllib.request
import wave
from pathlib import Path

import imageio_ffmpeg

from . import config

PALAVRAS_POR_S = 2.6  # ritmo médio de narração em português
TICKS = 10_000_000    # o Azure mede tempo em unidades de 100 ns
PARADAS = set("""a o as os um uma uns umas de da do das dos em na no nas nos por para pra com sem que e ou mas se
eu tu ele ela nós vós eles elas você vocês isso isto aquilo esse essa este esta aquele aquela seu sua seus suas meu
minha é são foi era ser ter tem tinha há mais menos muito muita muitos muitas já não sim também como quando onde
porque então assim ainda até só lá aqui ali bem tão the of and to in is it that""".split())


def _frases(texto: str) -> list[str]:
    texto = re.sub(r"\s+", " ", texto).strip()
    return [f.strip() for f in re.split(r"(?<=[.!?…])\s+", texto) if f.strip()]


def _conteudo(texto: str) -> list[str]:
    return [p for p in re.findall(r"[\wÀ-ÿ]+", texto.lower()) if p not in PARADAS and len(p) > 3]


def _tema(texto: str) -> str:
    """A palavra de conteúdo que mais se repete no roteiro inteiro (o assunto do vídeo)."""
    from collections import Counter
    contagem = Counter(_conteudo(texto))
    return contagem.most_common(1)[0][0] if contagem else ""


def _busca(texto: str, tema: str = "") -> str:
    """O assunto do vídeo + as palavras mais longas da cena: ponto de partida para a busca de imagem."""
    vistas = [p for p in dict.fromkeys(_conteudo(texto)) if p != tema]
    return " ".join(([tema] if tema else []) + sorted(vistas, key=len, reverse=True)[:3 - bool(tema)])


def cenas_de_texto(texto: str, ritmo_s: float = 4) -> list[dict]:
    """Agrupa as frases até chegar perto do tamanho de cena do ritmo do canal."""
    alvo = max(int(ritmo_s * PALAVRAS_POR_S), 6)
    cenas, atual = [], []
    for frase in _frases(texto):
        atual.append(frase)
        if sum(len(f.split()) for f in atual) >= alvo:
            cenas.append(" ".join(atual))
            atual = []
    if atual:
        if cenas and sum(len(f.split()) for f in atual) < alvo // 2:
            cenas[-1] += " " + " ".join(atual)  # sobra curta junta com a cena anterior
        else:
            cenas.append(" ".join(atual))
    tema = _tema(texto)
    return [{"texto": c, "visual": _busca(c, tema), "visual_idioma": "pt"} for c in cenas]


# ---------- narração pronta ----------

def _ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", *args], capture_output=True,
                          text=True, errors="replace")


def _duracao(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def _cortes(wav: Path, total: float, maximo: float = 50) -> list[float]:
    """Pontos de corte nas pausas da fala, com trechos de no máximo ~50 s (o limite do Azure é 60 s)."""
    saida = _ffmpeg("-i", str(wav), "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-").stderr
    pausas = [(float(a) + float(b)) / 2 for a, b in zip(re.findall(r"silence_start: ([\d.]+)", saida),
                                                        re.findall(r"silence_end: ([\d.]+)", saida))]
    cortes, inicio = [], 0.0
    while total - inicio > maximo:
        candidatas = [p for p in pausas if inicio + 10 < p <= inicio + maximo]
        corte = candidatas[-1] if candidatas else inicio + maximo
        cortes.append(corte)
        inicio = corte
    return cortes


def _transcrever_trecho(wav: Path, idioma: str) -> list[dict]:
    chave, regiao = os.getenv("AZURE_SPEECH_KEY", ""), os.getenv("AZURE_SPEECH_REGION", "brazilsouth")
    if not chave:
        raise SystemExit("a narração pronta precisa da chave do Azure Speech (Estúdio > Conexões)")
    lingua = {"pt": "pt-BR", "en": "en-US", "es": "es-MX"}.get(idioma, idioma)
    url = (f"https://{regiao}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
           f"?language={lingua}&format=detailed&wordLevelTimestamps=true")
    req = urllib.request.Request(url, data=wav.read_bytes(), headers={
        "Ocp-Apim-Subscription-Key": chave, "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000"})
    resposta = json.loads(urllib.request.urlopen(req, timeout=180).read())
    if resposta.get("RecognitionStatus") != "Success" or not resposta.get("NBest"):
        return []
    melhor = resposta["NBest"][0]
    exibidas = melhor.get("Display", "").split()
    palavras = melhor.get("Words", [])
    # o texto exibido tem pontuação e maiúsculas; usa ele quando bate palavra por palavra com os tempos
    usar_exibidas = len(exibidas) == len(palavras)
    return [{"texto": exibidas[i] if usar_exibidas else w["Word"],
             "inicio": w["Offset"] / TICKS, "fim": (w["Offset"] + w["Duration"]) / TICKS}
            for i, w in enumerate(palavras)]


def transcrever(audio: Path, idioma: str, pasta: Path) -> tuple[Path, list[dict]]:
    """WAV 16 kHz mono do áudio inteiro + palavras com tempo absoluto."""
    pasta.mkdir(parents=True, exist_ok=True)
    wav = pasta / "narracao-16k.wav"
    r = _ffmpeg("-loglevel", "error", "-y", "-i", str(audio), "-ac", "1", "-ar", "16000", str(wav))
    if r.returncode != 0:
        raise SystemExit(f"não consegui ler o áudio: {r.stderr[-300:]}")
    total = _duracao(wav)
    limites = [0.0, *_cortes(wav, total), total]
    palavras = []
    for i, (ini, fim) in enumerate(zip(limites, limites[1:])):
        trecho = pasta / f"trecho{i:02d}.wav"
        _ffmpeg("-loglevel", "error", "-y", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}", "-i", str(wav), str(trecho))
        palavras += [{**p, "inicio": p["inicio"] + ini, "fim": p["fim"] + ini}
                     for p in _transcrever_trecho(trecho, idioma)]
        trecho.unlink(missing_ok=True)
    return wav, palavras


def cenas_de_narracao(audio: Path, idioma: str, ritmo_s: float, pasta_midia: Path, nome: str) -> list[dict]:
    """Corta o áudio original em cenas (fim de frase perto do ritmo do canal) e guarda o tempo das palavras
    de cada cena, relativo ao começo dela, para a legenda sair sincronizada."""
    trabalho = config.OBRA / "narracoes" / nome
    _, palavras = transcrever(audio, idioma, trabalho)
    if not palavras:
        raise SystemExit("não reconheci fala nesse áudio")
    grupos, atual = [], []
    for i, p in enumerate(palavras):
        atual.append(p)
        duracao = p["fim"] - atual[0]["inicio"]
        fim_de_frase = p["texto"][-1:] in ".!?…"
        pausa = i + 1 < len(palavras) and palavras[i + 1]["inicio"] - p["fim"] > 0.35
        if duracao >= ritmo_s and (fim_de_frase or pausa) or duracao >= ritmo_s * 2.5:
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    pasta_midia.mkdir(parents=True, exist_ok=True)
    tema = _tema(" ".join(p["texto"] for p in palavras))
    cenas = []
    for n, g in enumerate(grupos, 1):
        # cada cena começa logo depois do fim da anterior, para não perder respiração nem cortar sílaba
        inicio = 0.0 if n == 1 else (grupos[n - 2][-1]["fim"] + g[0]["inicio"]) / 2
        fim = (g[-1]["fim"] + grupos[n][0]["inicio"]) / 2 if n < len(grupos) else g[-1]["fim"] + 0.4
        arquivo = pasta_midia / f"{nome}-narracao-{n:02d}.wav"
        _ffmpeg("-loglevel", "error", "-y", "-ss", f"{inicio:.3f}", "-to", f"{fim:.3f}", "-i", str(audio),
                "-ac", "2", "-ar", "48000", str(arquivo))
        texto = " ".join(p["texto"] for p in g)
        cenas.append({"texto": texto, "visual": _busca(texto, tema), "visual_idioma": "pt", "audio": f"midia/{arquivo.name}", "pausa": 0,
                      "palavras": [{"texto": p["texto"], "inicio": round(p["inicio"] - inicio, 3),
                                    "fim": round(p["fim"] - inicio, 3)} for p in g]})
    return cenas
