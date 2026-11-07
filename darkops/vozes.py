"""Catálogo de vozes de cada público (mercado) e amostras para ouvir antes de escolher a voz do canal.

  python -m darkops vozes-amostras                       grava as amostras das vozes grátis que faltam
  python -m darkops vozes-amostras --motor gemini --mercado pt-BR    amostras de uma opção paga (precisa da chave)

Vozes grátis (Azure, que sem chave cai no Edge com os mesmos nomes, e Piper offline): as amostras vêm prontas no
repositório, em assets/vozes/amostras/<mercado>/, para quem está criando o canal ouvir sem chave nenhuma.
Vozes pagas (ElevenLabs, Chirp 3 HD, Gemini): só com a chave da pessoa. As amostras dela ficam em
dados/amostras-voz/<mercado>/ (fora do Git) e o estado da geração em dados/amostras-voz/estado.json.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
import requests

from . import config, mercados, narracao
from .seguranca import ocultar

GRATIS = config.RAIZ / "assets" / "vozes" / "amostras"
PAGAS = config.RAIZ / "dados" / "amostras-voz"
ESTADO = PAGAS / "estado.json"

TEXTOS = {
    "pt": "Em 1901, mergulhadores acharam no fundo do mar um bloco de bronze. Dentro dele, havia engrenagens "
          "capazes de prever eclipses.",
    "en": "In 1901, divers found a lump of bronze at the bottom of the sea. Inside it were gears that could "
          "predict eclipses.",
    "es": "En 1901, unos buzos encontraron en el fondo del mar un bloque de bronce. Dentro había engranajes "
          "capaces de predecir eclipses.",
    "fr": "En 1901, des plongeurs ont trouvé au fond de la mer un bloc de bronze. À l'intérieur, des engrenages "
          "capables de prédire les éclipses.",
    "de": "Im Jahr 1901 fanden Taucher auf dem Meeresgrund einen Bronzeklumpen. Darin steckten Zahnräder, die "
          "Finsternisse vorhersagen konnten.",
    "it": "Nel 1901, alcuni sommozzatori trovarono sul fondo del mare un blocco di bronzo. Dentro c'erano "
          "ingranaggi capaci di prevedere le eclissi.",
}

# vozes do Azure de cada mercado ("Nome:gênero"); o nome completo é <mercado>-<Nome>Neural
LOCAIS = {
    "pt-BR": "ThalitaMultilingual:F Francisca:F Brenda:F Elza:F Giovanna:F Leila:F Leticia:F Manuela:F Yara:F "
             "Antonio:M MacerioMultilingual:M Donato:M Fabio:M Humberto:M Julio:M Nicolau:M Valerio:M",
    "pt-PT": "Raquel:F Fernanda:F Duarte:M",
    "en-US": "AvaMultilingual:F EmmaMultilingual:F AmandaMultilingual:F PhoebeMultilingual:F Jenny:F "
             "AndrewMultilingual:M BrianMultilingual:M AdamMultilingual:M DavisMultilingual:M "
             "ChristopherMultilingual:M Guy:M Tony:M",
    "en-GB": "AdaMultilingual:F Sonia:F Libby:F Hollie:F OllieMultilingual:M Ryan:M Thomas:M Elliot:M",
    "es-MX": "DaliaMultilingual:F Dalia:F Renata:F Larissa:F JorgeMultilingual:M Jorge:M Gerardo:M Liberto:M",
    "es-US": "Paloma:F Alonso:M",
    "es-ES": "ArabellaMultilingual:F XimenaMultilingual:F IsidoraMultilingual:F Elvira:F Triana:F "
             "TristanMultilingual:M Alvaro:M Dario:M",
    "fr-FR": "VivienneMultilingual:F Denise:F Brigitte:F RemyMultilingual:M LucienMultilingual:M Henri:M Alain:M "
             "Claude:M",
    "de-DE": "SeraphinaMultilingual:F Katja:F Amala:F Louisa:F FlorianMultilingual:M Conrad:M Klaus:M Ralf:M",
    "it-IT": "IsabellaMultilingual:F Elsa:F Fiamma:F GiuseppeMultilingual:M MarcelloMultilingual:M "
             "AlessioMultilingual:M Diego:M Gianni:M",
}
# vozes multilíngues de outros países: falam a língua do público com um sotaque leve (a Remy no Enigma Oculto)
DE_FORA = ["en-US-AndrewMultilingualNeural:M", "en-US-BrianMultilingualNeural:M", "en-US-AvaMultilingualNeural:F",
           "en-US-EmmaMultilingualNeural:F", "fr-FR-RemyMultilingualNeural:M", "fr-FR-VivienneMultilingualNeural:F",
           "de-DE-FlorianMultilingualNeural:M", "de-DE-SeraphinaMultilingualNeural:F"]

PAIS = {"en-US": "americana", "fr-FR": "francesa", "de-DE": "alemã"}

# vozes prontas do Google (as mesmas no Gemini TTS e no Chirp 3 HD), com o jeito de cada uma
GOOGLE = [("Gacrux", "F", "madura"), ("Kore", "F", "firme"), ("Aoede", "F", "leve"), ("Sulafat", "F", "calorosa"),
          ("Charon", "M", "informativa"), ("Orus", "M", "firme"), ("Algenib", "M", "rouca"),
          ("Rasalgethi", "M", "de documentário")]

PAGOS = {
    "gemini": {"rotulo": "Gemini TTS", "chave": "GEMINI_API_KEY",
               "preco": "cota grátis de poucos vídeos por dia; no pago, cerca de US$ 3 por mês para 120 vídeos",
               "onde": "aistudio.google.com/apikey"},
    "chirp": {"rotulo": "Google Chirp 3 HD", "chave": "GOOGLE_TTS_API_KEY",
              "preco": "1 milhão de caracteres grátis por mês; exige o faturamento ativado no Google Cloud",
              "onde": "console.cloud.google.com (Credenciais)"},
    "elevenlabs": {"rotulo": "ElevenLabs", "chave": "ELEVENLABS_API_KEY",
                   "preco": "a voz mais natural; plano Pro (US$ 99) para 120 vídeos por mês, com licença comercial",
                   "onde": "elevenlabs.io (Developers > API Keys)"},
}
NOME_SEGURO = re.compile(r"^[\w.-]+$")


def _rotulo_azure(voz: str) -> str:
    return voz.split("-", 2)[2].replace("Neural", "").replace("Multilingual", "")


def azure(cod: str) -> list[dict]:
    """Vozes grátis do Azure/Edge para o mercado: as de lá primeiro, depois as multilíngues de fora."""
    itens = []
    for parte in LOCAIS.get(cod, "").split():
        nome, g = parte.split(":")
        itens.append({"voz": f"{cod}-{nome}Neural", "genero": g})
    for parte in DE_FORA:
        voz, g = parte.split(":")
        if not voz.startswith(cod + "-"):
            itens.append({"voz": voz, "genero": g, "fora": True})
    return [{**i, "motor": "auto", "nome": _rotulo_azure(i["voz"]),
             "nota": f"voz {PAIS.get(i['voz'][:5], i['voz'][:5])}, sotaque leve" if i.get("fora") else ""}
            for i in itens]


def _arquivo_gratis(cod: str, motor: str, voz: str) -> Path:
    return GRATIS / cod / (f"{voz}.mp3" if motor == "auto" else f"{motor}-{voz}.mp3")


def _arquivo_pago(cod: str, motor: str, voz: str) -> Path:
    seguro = re.sub(r"[^\w.-]", "_", voz)
    return PAGAS / cod / f"{motor}-{seguro}.mp3"


def url(arquivo: Path) -> str | None:
    if not arquivo.is_file():
        return None
    origem = "gratis" if GRATIS in arquivo.parents else "pagas"
    return f"/vozes/amostra/{origem}/{arquivo.parent.name}/{arquivo.name}"


def gratis(cod: str) -> list[dict]:
    itens = azure(cod)
    piper = narracao.VOZES_PIPER.get(mercados.MERCADOS[cod]["idioma"])
    # Piper só no país do modelo (pt_BR-faber não serve para Portugal)
    if piper and piper.startswith(cod.replace("-", "_")) and (narracao.PASTA_PIPER / f"{piper}.onnx").exists():
        itens.append({"motor": "piper", "voz": piper, "genero": "", "nome": "Piper (offline)",
                      "nota": "roda no seu PC sem internet; mais robótica"})
    return [{**i, "url": url(_arquivo_gratis(cod, i["motor"], i["voz"]))} for i in itens]


def _estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_estado(motor: str, cod: str, valor: dict) -> None:
    estado = _estado()
    estado.setdefault(motor, {})[cod] = valor
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def _tem_chave(motor: str) -> bool:
    from dotenv import dotenv_values
    return bool((dotenv_values(config.RAIZ / ".env").get(PAGOS[motor]["chave"]) or "").strip())


def pagas(cod: str) -> list[dict]:
    """Cada opção paga com a situação dela: sem chave, com chave e sem amostra, gerando, pronta ou com erro."""
    estado = _estado()
    saida = []
    for motor, info in PAGOS.items():
        e = estado.get(motor, {}).get(cod, {})
        vozes = [{**v, "motor": motor, "url": url(_arquivo_pago(cod, motor, v["voz"]))} for v in e.get("vozes", [])]
        if e.get("situacao") == "gerando" and time.time() - e.get("inicio", 0) > 1800:
            e = {**e, "situacao": "erro", "erro": "a geração parou no meio; tente de novo"}
        saida.append({"motor": motor, **info, "tem_chave": _tem_chave(motor), "situacao": e.get("situacao", ""),
                      "erro": e.get("erro", ""), "vozes": [v for v in vozes if v["url"]]})
    return saida


def catalogo(cod: str) -> dict:
    return {"gratis": gratis(cod), "pagas": pagas(cod)}


def escolha(valor: str) -> dict:
    """'motor|voz' do seletor -> campos do perfil. A voz é conferida com o mercado em mercados.coerente."""
    motor, _, voz = str(valor or "").partition("|")
    voz = voz.strip()[:120]
    if motor not in ("auto", "piper", *PAGOS) or not voz or not re.match(r"^[\w.:-]+$", voz):
        return {}
    return {"motor_voz": motor, "voz": voz}


def combina(cod: str, motor: str, voz: str | None) -> bool:
    """A voz serve para esse mercado e esse motor?"""
    v = str(voz or "")
    if not v:
        return False
    if motor in ("auto", "azure", "edge"):
        return mercados.voz_combina(cod, v) or any(i["voz"] == v for i in azure(cod))
    if motor == "chirp":
        return mercados.voz_combina(cod, v)
    if motor == "gemini":
        return v.isalpha()
    if motor == "piper":
        return v in narracao.VOZES_PIPER.values()
    return True  # ElevenLabs (voice_id da conta) e Chatterbox (código da língua)


# ---------- geração ----------

def _mp3(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(origem),
                    "-ac", "1", "-b:a", "48k", str(destino)], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _sintetizar(motor: str, voz: str, cod: str, destino: Path) -> None:
    """Mesmo caminho da produção (narracao), para a amostra soar como o vídeo vai soar."""
    texto = TEXTOS[mercados.MERCADOS[cod]["idioma"]]
    with tempfile.TemporaryDirectory() as pasta:
        base = Path(pasta) / "amostra"
        if motor == "auto":
            if config.AZURE_SPEECH_KEY and config.AZURE_SPEECH_REGION:
                audio, _ = narracao._azure(texto, voz, "+0%", base, cod)
            else:
                audio, _ = narracao._edge(texto, voz, "+0%", base)
        else:
            audio, _ = narracao.MOTORES[motor](texto, voz, "+0%", base)
        _mp3(audio, destino)


def gerar_gratis(cods: list[str] | None = None, refazer: bool = False) -> dict:
    feitos, falhas = 0, []
    for cod in cods or list(mercados.MERCADOS):
        for item in gratis(cod):
            destino = _arquivo_gratis(cod, item["motor"], item["voz"])
            if destino.is_file() and not refazer:
                continue
            try:
                _sintetizar(item["motor"], item["voz"], cod, destino)
                feitos += 1
                print(f"  {cod} {item['voz']}")
            except (SystemExit, ConnectionError, requests.RequestException, OSError,
                    subprocess.CalledProcessError) as erro:
                falhas.append(f"{cod} {item['voz']}: {ocultar(str(erro))[:160]}")
    return {"geradas": feitos, "falhas": falhas}


def _vozes_elevenlabs() -> list[dict]:
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                     timeout=60)
    r.raise_for_status()
    vozes = []
    for v in r.json().get("voices", [])[:8]:
        rotulos = v.get("labels") or {}
        g = {"female": "F", "male": "M"}.get(str(rotulos.get("gender", "")).lower(), "")
        vozes.append({"voz": v["voice_id"], "nome": v.get("name", v["voice_id"])[:40], "genero": g,
                      "nota": str(rotulos.get("description") or rotulos.get("accent") or "")[:40]})
    return vozes


def lista_paga(motor: str, cod: str) -> list[dict]:
    if motor == "elevenlabs":
        return _vozes_elevenlabs()
    if motor == "chirp":
        return [{"voz": f"{cod}-Chirp3-HD-{n}", "nome": n, "genero": g, "nota": j} for n, g, j in GOOGLE]
    return [{"voz": n, "nome": n, "genero": g, "nota": j} for n, g, j in GOOGLE]


def gerar_paga(motor: str, cod: str) -> dict:
    if motor not in PAGOS or cod not in mercados.MERCADOS:
        raise SystemExit("motor ou mercado inválido")
    if not getattr(config, PAGOS[motor]["chave"], ""):
        raise SystemExit(f"falta a chave {PAGOS[motor]['chave']} (Estúdio > Chaves)")
    _gravar_estado(motor, cod, {"situacao": "gerando", "inicio": time.time(), "vozes": []})
    prontas, falhas = [], []
    try:
        for v in lista_paga(motor, cod):
            try:
                _sintetizar(motor, v["voz"], cod, _arquivo_pago(cod, motor, v["voz"]))
                prontas.append(v)
                _gravar_estado(motor, cod, {"situacao": "gerando", "inicio": time.time(), "vozes": prontas})
            except (SystemExit, ConnectionError, requests.RequestException, OSError, KeyError,
                    subprocess.CalledProcessError) as erro:
                falhas.append(ocultar(str(erro))[:200])
                if "cota" in str(erro) or "401" in str(erro) or "403" in str(erro):
                    break  # chave recusada ou cota do dia: não adianta tentar as outras
    except requests.RequestException as erro:  # lista de vozes da ElevenLabs
        falhas.append(ocultar(str(erro))[:200])
    situacao = "pronto" if prontas else "erro"
    _gravar_estado(motor, cod, {"situacao": situacao, "vozes": prontas, "erro": falhas[0] if falhas else ""})
    return {"situacao": situacao, "vozes": len(prontas), "falhas": falhas}


def gerar_paga_em_segundo_plano(motor: str, cod: str) -> None:
    """Processo separado: lê o .env de novo (a chave pode ter acabado de entrar) e não segura o Estúdio."""
    if motor not in PAGOS or cod not in mercados.MERCADOS:
        return
    _gravar_estado(motor, cod, {"situacao": "gerando", "inicio": time.time(), "vozes": []})
    subprocess.Popen([sys.executable, "-m", "darkops", "vozes-amostras", "--motor", motor, "--mercado", cod],
                     cwd=config.RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
