"""Narração com motores plugáveis e legendas ASS sincronizadas por palavra.

Motores:
- edge: vozes neurais da Microsoft via edge-tts. Grátis, mas é um serviço não oficial
  que às vezes recusa conexões; em 'auto' cai para o Piper.
- piper: offline, grátis, roda na máquina. Qualidade média.
- elevenlabs: pago (ELEVENLABS_API_KEY), melhor qualidade, tempos por caractere.
- azure: oficial da Microsoft (AZURE_SPEECH_KEY + AZURE_SPEECH_REGION), mesmas vozes do edge,
  camada grátis de 500 mil caracteres/mês.
"""
import asyncio
import base64
import io
import json
import re
import wave
from pathlib import Path
from xml.sax.saxutils import escape

import edge_tts
import requests

from . import config

TICKS = 10_000_000  # edge-tts mede offset em unidades de 100 ns
VOZES_PIPER = {"pt": "pt_BR-faber-medium", "en": "en_US-ryan-high", "es": "es_MX-ald-medium"}
PASTA_PIPER = config.RAIZ / "assets" / "vozes"


def _fator(velocidade: str) -> float:
    """'+10%' -> 1.10"""
    achado = re.fullmatch(r"([+-]\d+)%", velocidade.strip())
    return 1 + int(achado.group(1)) / 100 if achado else 1.0


def _frases(texto: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.!?])\s+", texto.strip()) if f]


def _estimar(frases_pcm: list[tuple[str, bytes]], taxa: int, destino: Path) -> list[dict]:
    """Junta o PCM das frases num WAV e divide o tempo de cada frase entre as palavras pelo tamanho delas."""
    palavras, t = [], 0.0
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        for frase, pcm in frases_pcm:
            w.writeframes(pcm)
            dur = len(pcm) / 2 / taxa
            tokens = frase.split()
            pesos = [len(p) + 1 for p in tokens]
            total, acumulado = sum(pesos), 0
            for p, peso in zip(tokens, pesos):
                inicio = t + dur * acumulado / total
                acumulado += peso
                palavras.append({"texto": p, "inicio": inicio, "fim": t + dur * acumulado / total})
            t += dur
    return palavras


# ---------- motores ----------

async def _edge_async(texto: str, voz: str, velocidade: str, mp3: Path) -> list[dict]:
    com = edge_tts.Communicate(texto, voz, rate=velocidade, boundary="WordBoundary")
    palavras = []
    with open(mp3, "wb") as f:
        async for pedaco in com.stream():
            if pedaco["type"] == "audio":
                f.write(pedaco["data"])
            elif pedaco["type"] == "WordBoundary":
                palavras.append({
                    "texto": pedaco["text"],
                    "inicio": pedaco["offset"] / TICKS,
                    "fim": (pedaco["offset"] + pedaco["duration"]) / TICKS,
                })
    return palavras


def _edge(texto: str, voz: str, velocidade: str, base: Path) -> tuple[Path, list[dict]]:
    mp3 = base.with_suffix(".mp3")
    ultimo = None
    for _ in range(3):
        try:
            return mp3, asyncio.run(_edge_async(texto, voz, velocidade, mp3))
        except Exception as erro:  # o serviço derruba conexões com frequência
            ultimo = erro
    raise ConnectionError(f"edge-tts indisponível: {ultimo}")


def _piper(texto: str, voz: str, velocidade: str, base: Path) -> tuple[Path, list[dict]]:
    from piper import PiperVoice, SynthesisConfig
    from piper.download_voices import download_voice

    modelo = PASTA_PIPER / f"{voz}.onnx"
    if not modelo.exists():
        print(f"  baixando voz Piper {voz}")
        PASTA_PIPER.mkdir(parents=True, exist_ok=True)
        download_voice(voz, PASTA_PIPER)
    voice = PiperVoice.load(str(modelo))
    ajuste = SynthesisConfig(length_scale=1 / _fator(velocidade))
    partes = []
    for frase in _frases(texto):
        pcm = b"".join(c.audio_int16_bytes for c in voice.synthesize(frase, syn_config=ajuste))
        partes.append((frase, pcm))
    wav = base.with_suffix(".wav")
    return wav, _estimar(partes, voice.config.sample_rate, wav)


def _elevenlabs(texto: str, voz: str, velocidade: str, base: Path) -> tuple[Path, list[dict]]:
    if not config.ELEVENLABS_API_KEY:
        raise SystemExit("motor elevenlabs exige ELEVENLABS_API_KEY no .env")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": config.ELEVENLABS_API_KEY},
        json={"text": texto, "model_id": config.ELEVENLABS_MODELO,
              "voice_settings": {"speed": max(0.7, min(1.2, _fator(velocidade)))}},
        timeout=300,
    )
    r.raise_for_status()
    dados = r.json()
    mp3 = base.with_suffix(".mp3")
    mp3.write_bytes(base64.b64decode(dados["audio_base64"]))
    al = dados["alignment"]
    palavras, atual = [], None
    for ch, ini, fim in zip(al["characters"], al["character_start_times_seconds"],
                            al["character_end_times_seconds"]):
        if ch.isspace():
            atual = None
            continue
        if atual is None:
            atual = {"texto": "", "inicio": ini, "fim": fim}
            palavras.append(atual)
        atual["texto"] += ch
        atual["fim"] = fim
    return mp3, palavras


def _azure(texto: str, voz: str, velocidade: str, base: Path) -> tuple[Path, list[dict]]:
    if not (config.AZURE_SPEECH_KEY and config.AZURE_SPEECH_REGION):
        raise SystemExit("motor azure exige AZURE_SPEECH_KEY e AZURE_SPEECH_REGION no .env")
    lingua = "-".join(voz.split("-")[:2])
    partes = []
    for frase in _frases(texto):
        ssml = (f"<speak version='1.0' xml:lang='{lingua}'><voice name='{voz}'>"
                f"<prosody rate='{velocidade}'>{escape(frase)}</prosody></voice></speak>")
        r = requests.post(
            f"https://{config.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={"Ocp-Apim-Subscription-Key": config.AZURE_SPEECH_KEY,
                     "Content-Type": "application/ssml+xml",
                     "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm", "User-Agent": "canais-dark"},
            data=ssml.encode("utf-8"), timeout=120,
        )
        r.raise_for_status()
        with wave.open(io.BytesIO(r.content)) as w:
            partes.append((frase, w.readframes(w.getnframes())))
    wav = base.with_suffix(".wav")
    return wav, _estimar(partes, 24000, wav)


MOTORES = {"edge": _edge, "piper": _piper, "elevenlabs": _elevenlabs, "azure": _azure}


def voz_padrao(motor: str, idioma: str) -> str:
    if motor == "piper":
        return VOZES_PIPER.get(idioma, VOZES_PIPER["pt"])
    if motor == "elevenlabs":
        if not config.ELEVENLABS_VOZ:
            raise SystemExit("defina 'voz' no roteiro ou ELEVENLABS_VOZ no .env com o voice_id")
        return config.ELEVENLABS_VOZ
    return config.VOZ_PADRAO.get(idioma, config.VOZ_PADRAO["pt"])  # edge e azure usam os mesmos nomes


def narrar(texto: str, motor: str, voz: str | None, velocidade: str, idioma: str,
           base: Path) -> tuple[Path, list[dict]]:
    """Gera o áudio da cena e os tempos de cada palavra. Reaproveita se nada mudou.

    motor 'auto' = Azure se houver chave no .env, senão edge; se o serviço falhar, Piper offline.
    """
    if motor == "auto":
        escolhido = "azure" if config.AZURE_SPEECH_KEY and config.AZURE_SPEECH_REGION else "edge"
    else:
        escolhido = motor
    marcas = base.with_suffix(".json")
    assinatura = {"texto": texto, "motor": motor, "voz": voz, "velocidade": velocidade}
    if marcas.exists():
        salvo = json.loads(marcas.read_text(encoding="utf-8"))
        audio = base.with_name(salvo.get("arquivo") or "_")
        # áudio do Piper feito como reserva é refeito quando o motor preferido voltar
        reserva = salvo.get("motor_usado") != escolhido
        if salvo.get("assinatura") == assinatura and audio.is_file() and not reserva:
            return audio, salvo["palavras"]

    if escolhido not in MOTORES:
        raise SystemExit(f"motor de voz '{motor}' inválido. Opções: auto, {', '.join(MOTORES)}")
    try:
        audio, palavras = MOTORES[escolhido](texto, voz or voz_padrao(escolhido, idioma), velocidade, base)
    except (ConnectionError, requests.RequestException) as erro:
        if motor != "auto":
            raise
        print(f"  {str(erro)[:120]}\n  usando Piper (offline)")
        voz_piper = voz if voz and voz in VOZES_PIPER.values() else voz_padrao("piper", idioma)
        audio, palavras = _piper(texto, voz_piper, velocidade, base)
        escolhido = "piper"
    marcas.write_text(json.dumps({"assinatura": assinatura, "arquivo": audio.name, "palavras": palavras,
                                  "motor_usado": escolhido},
                                 ensure_ascii=False), encoding="utf-8")
    return audio, palavras


async def _vozes(prefixo: str) -> list[str]:
    todas = await edge_tts.list_voices()
    return [f"{v['ShortName']} ({v['Gender']})" for v in todas if v["Locale"].startswith(prefixo)]


def listar_vozes(prefixo: str) -> list[str]:
    return asyncio.run(_vozes(prefixo))


# ---------- legendas ----------

def _tempo(s: float) -> str:
    cs = int(round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _escapar(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")")


def _grupos(palavras: list[dict], max_palavras: int) -> list[list[dict]]:
    """Quebra por tamanho, pontuação ou pausa na fala (o edge-tts não devolve a pontuação)."""
    grupos, atual, cheio = [], [], []  # cheio[i]: grupo i fechou só por tamanho, sem fim de frase
    for i, p in enumerate(palavras):
        atual.append(p)
        pontuacao = p["texto"][-1:] in ".!?,;:"
        pausa = i + 1 < len(palavras) and palavras[i + 1]["inicio"] - p["fim"] > 0.2
        if pontuacao or pausa or i + 1 == len(palavras):
            # palavra solta no fim da frase volta para o grupo anterior ("...caem do" + "céu")
            if len(atual) == 1 and grupos and cheio[-1] and max_palavras > 1:
                grupos[-1].append(p)
                cheio[-1] = False
            else:
                grupos.append(atual)
                cheio.append(False)
            atual = []
        elif len(atual) >= max_palavras:
            grupos.append(atual)
            cheio.append(True)
            atual = []
    return grupos


def _cor_ass(hexa: str) -> str:
    """#RRGGBB vira &H00BBGGRR (o ASS guarda as cores ao contrário)."""
    hexa = hexa.lstrip("#")
    return f"&H00{hexa[4:6]}{hexa[2:4]}{hexa[0:2]}".upper()


def legenda_ass(palavras: list[dict], largura: int, altura: int, duracao: float, destino: Path,
               baixo: bool = False, destaque: tuple[str, float] | None = None, grande: bool = False,
               fonte: str = "Arial Black", escala: float = 1.0, cor: str = "#FFE500",
               palavra: bool = False, termo: tuple[str, float] | None = None,
               rotulos: list[tuple[str, float, float, float]] | None = None) -> None:
    """Horizontal: frases curtas embaixo. Vertical: 1-3 palavras grandes no centro (ou embaixo, com
    baixo=True, para não cobrir uma animação), a palavra falada fica na cor de destaque (amarelo por padrão)
    e cada grupo entra com um pulo. fonte, escala e cor vêm do padrão do canal.

    Formato explicativo: palavra=True mostra uma palavra por vez, branca, abaixo do centro, e as palavras do
    termo saem na cor de destaque; termo=(texto, segundo) fixa o nome técnico no topo até o fim da cena;
    rotulos=[(texto, x, y, segundo)] são etiquetas presas ao objeto (x e y de 0 a 1 na tela)."""
    vertical = altura > largura or grande  # grande: estilo de Shorts mesmo numa janela horizontal
    if palavra and vertical:
        estilo = (f"Style: Base,{fonte},{int(largura * 0.085 * escala)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
                  f"-1,0,0,0,100,100,0,0,1,{int(largura * 0.009)},3,2,60,60,{int(altura * 0.3)},1")
        max_palavras = 1
    elif vertical:
        # \kf pinta da cor secundária (branco) para a primária (destaque) conforme a palavra é falada
        alinhamento, margem = (2, int(altura * (0.2 if altura > largura else 0.06))) if baixo else (5, 0)
        estilo = (f"Style: Base,{fonte},{int(largura * (0.08 if altura > largura else 0.07) * escala)},{_cor_ass(cor)},&H00FFFFFF,&H00000000,&H64000000,"
                  f"-1,0,0,0,100,100,0,0,1,{int(altura * 0.005)},2,{alinhamento},60,60,{margem},1")
        max_palavras = 3
    else:
        estilo = (f"Style: Base,{'Arial' if fonte == 'Arial Black' else fonte},{int(altura * 0.05 * escala)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,"
                  f"-1,0,0,0,100,100,0,0,1,{int(altura * 0.0035)},1,2,120,120,{int(altura * 0.07)},1")
        max_palavras = 7

    linhas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {largura}", f"PlayResY: {altura}",
        "WrapStyle: 0", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        estilo,
        # palavra-herói: grande, amarela, contorno grosso, um pouco acima do centro
        (f"Style: Heroi,Arial Black,{int(largura * (0.133 if altura > largura else 0.11))},&H0000D4FF,"
         f"&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,2,0,1,{int(largura * 0.014)},4,5,40,40,0,1"),
        # termo técnico fixo no topo ("Esse é o tungstênio")
        (f"Style: Termo,Arial Black,{int(largura * 0.075)},{_cor_ass(cor)},&H00FFFFFF,&H00101010,&H96000000,"
         f"-1,0,0,0,100,100,1,0,1,{int(largura * 0.008)},3,8,40,40,{int(altura * 0.12)},1"),
        # etiqueta presa ao objeto: caixa branca (BorderStyle 3) com texto escuro
        (f"Style: Rotulo,Arial Black,{int(largura * 0.036)},&H00202020,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,"
         f"-1,0,0,0,100,100,0,0,3,{int(largura * 0.012)},0,5,0,0,0,1"),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    grupos = _grupos(palavras, max_palavras)
    for i, g in enumerate(grupos):
        inicio = g[0]["inicio"]
        # segura a legenda até o próximo grupo para não piscar entre palavras
        fim = grupos[i + 1][0]["inicio"] if i + 1 < len(grupos) else min(g[-1]["fim"] + 0.5, duracao)
        if palavra and vertical:
            p = g[0]
            from .sincronia import _norm
            no_termo = termo and _norm(p["texto"]) in [_norm(t) for t in termo[0].split()]
            cor_palavra = f"{{\\c{_cor_ass(cor)}&}}" if no_termo else ""
            texto = ("{\\fad(30,0)\\fscx80\\fscy80\\t(0,90,\\fscx106\\fscy106)\\t(90,160,\\fscx100\\fscy100)}"
                     + cor_palavra + _escapar(p["texto"].strip(".,;:!?\"'")).capitalize())
        elif vertical:
            partes = []
            for j, p in enumerate(g):
                prox = g[j + 1]["inicio"] if j + 1 < len(g) else p["fim"]
                partes.append(f"{{\\kf{max(int((prox - p['inicio']) * 100), 1)}}}{_escapar(p['texto']).upper()}")
            # pulo: o grupo entra a 75%, passa de 100% e assenta
            texto = ("{\\fad(40,0)\\fscx75\\fscy75\\t(0,110,\\fscx108\\fscy108)\\t(110,190,\\fscx100\\fscy100)}"
                     + " ".join(partes))
        else:
            texto = _escapar(" ".join(p["texto"] for p in g))
        linhas.append(f"Dialogue: 0,{_tempo(inicio)},{_tempo(fim)},Base,,0,0,0,,{texto}")
    if destaque and vertical:
        texto, inicio = destaque
        fim = min(inicio + 1.3, duracao)
        y = int(altura * (0.27 if altura > largura else 0.24))
        efeito = (f"{{\\pos({largura // 2},{y})\\fad(60,220)\\frz-4\\fscx30\\fscy30"
                  f"\\t(0,150,\\fscx118\\fscy118)\\t(150,260,\\fscx100\\fscy100)}}")
        linhas.append(f"Dialogue: 1,{_tempo(inicio)},{_tempo(fim)},Heroi,,0,0,0,,{efeito}{_escapar(texto.upper())}")
    if termo:
        texto, inicio = termo
        efeito = "{\\fad(60,0)\\fscx40\\fscy40\\t(0,140,\\fscx112\\fscy112)\\t(140,240,\\fscx100\\fscy100)}"
        linhas.append(f"Dialogue: 2,{_tempo(inicio)},{_tempo(duracao)},Termo,,0,0,0,,{efeito}{_escapar(texto.upper())}")
    for k, (texto, x, y, inicio) in enumerate(rotulos or []):
        bolinha = _cor_ass(("#FF5A7D", "#28C8FF", "#6EE68C", "#FFCE28")[k % 4])
        efeito = (f"{{\\pos({int(largura * x)},{int(altura * y)})\\fad(50,0)\\fscx30\\fscy30"
                  f"\\t(0,120,\\fscx110\\fscy110)\\t(120,200,\\fscx100\\fscy100)}}")
        linhas.append(f"Dialogue: 3,{_tempo(inicio)},{_tempo(duracao)},Rotulo,,0,0,0,,"
                      f"{efeito}{{\\c{bolinha}&}}●{{\\c&H00202020&}} {_escapar(texto.upper())}")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
