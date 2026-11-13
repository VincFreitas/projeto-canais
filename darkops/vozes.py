# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
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

# ---------- temas: o seletor mostra primeiro as vozes que combinam com o assunto do canal ----------
ROTULOS_TEMA = {"misterio": "mistério", "terror": "terror", "curiosidades": "curiosidades", "animais": "animais",
                "historia": "história", "geopolitica": "geopolítica e notícias", "bizarro": "histórias bizarras",
                "educativo": "como funciona e ciência"}
# assunto do canal (preset de config/nichos.json ou texto livre) -> tema; a 1ª regra que bater vale
REGRAS_TEMA = [
    ("terror", ["terror", "medo", "assombr", "horror", "sobrenatural", "creepy", "fantasma", "macabr"]),
    ("misterio", ["mist", "myster", "enigma", "ocult", "conspira", "segredo", "inexplic", "ovni", "alien", "ufo"]),
    ("bizarro", ["bizarr", "estranh", "inusitad", "weird", "absurd"]),
    ("geopolitica", ["geopol", "guerra", "polit", "notic", "econom", "pais", "paises", "mundo atual"]),
    ("historia", ["hist", "antig", "imperi", "civiliza", "arqueolog", "medieval"]),
    ("animais", ["anima", "bicho", "pet", "natureza", "fauna", "cachorro", "gato"]),
    ("educativo", ["como funciona", "cienc", "tecnolog", "explic", "fisica", "quimica", "engenharia", "espaco",
                   "astronom", "inven", "saude", "corpo humano"]),
    ("curiosidades", ["curios", "fato", "voce sabia", "fun fact"]),
]
T = {"mi": "misterio", "te": "terror", "cu": "curiosidades", "an": "animais", "hi": "historia",
     "ge": "geopolitica", "bi": "bizarro", "ed": "educativo"}
# o jeito de cada voz (ouvido nas amostras), pelo nome curto; vale para Azure/Edge, Gemini e Chirp
_TEMAS_VOZ = """
Thalita=cu,ed,an,hi Francisca=ge,ed Brenda=cu,an Elza=hi,mi Giovanna=cu,an Leila=te,mi Leticia=cu,bi Manuela=an,cu
Yara=mi,te Antonio=mi,hi,ge Macerio=mi,hi,cu Donato=te,mi Fabio=ge,ed Humberto=hi,ge Julio=cu,bi Nicolau=te,mi
Valerio=cu,bi Raquel=cu,ed,an Fernanda=hi,ge Duarte=mi,hi,ge Ava=cu,ed,an Emma=cu,an Amanda=ed,ge Phoebe=cu,bi
Jenny=ed,ge Andrew=mi,hi,ed Brian=cu,bi Adam=mi,te Davis=te,mi Christopher=hi,ge Guy=ge,hi Tony=bi,cu Ada=hi,ed
Sonia=ge,ed Libby=cu,an Hollie=cu,bi Ollie=cu,ed Ryan=mi,hi Thomas=te,mi Elliot=ge,hi Dalia=cu,ed,an Renata=ge,hi
Larissa=cu,bi Jorge=mi,hi Gerardo=te,mi Liberto=ge,ed Paloma=cu,ed,an Alonso=mi,hi,ge Arabella=cu,an Ximena=ed,ge
Isidora=hi,mi Elvira=ge,ed Triana=cu,bi Tristan=mi,te Alvaro=hi,ge Dario=cu,bi Vivienne=cu,ed,an Denise=ge,ed
Brigitte=hi Remy=mi,te,hi Lucien=ed,cu Henri=mi,hi,ge Alain=te Claude=bi,cu Seraphina=cu,ed Katja=ge,ed Amala=an,cu
Louisa=cu,bi Florian=mi,hi Conrad=ge,hi Klaus=te,mi Ralf=bi Isabella=cu,ed,an Elsa=ge,ed Fiamma=cu,bi
Giuseppe=mi,hi Marcello=te,mi Alessio=cu,ed Diego=ge,hi Gianni=bi Gacrux=mi,hi Kore=ge,ed Aoede=cu,an
Sulafat=an,cu Charon=ed,ge,hi Orus=mi,ge Algenib=te,mi Rasalgethi=hi,mi,ed Dora=cu,ed,an Alex=mi,hi,ge Santa=bi,cu
"""
TEMAS_VOZ = {nome: [T[c] for c in codigos.split(",")]
             for nome, codigos in (par.split("=") for par in _TEMAS_VOZ.split())}


def _sem_acento(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def tema_de(nicho: str) -> str:
    """Tema do assunto do canal; sem pista nenhuma, curiosidades (o mais comum nos canais dark)."""
    texto = _sem_acento(str(nicho or "").replace("-", " "))
    for tema, palavras in REGRAS_TEMA:
        if any(p in texto for p in palavras):
            return tema
    return "curiosidades"


def temas_da_voz(nome: str) -> list[str]:
    return TEMAS_VOZ.get(nome, [])


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
    return [{**i, "motor": "auto", "nome": _rotulo_azure(i["voz"]), "temas": temas_da_voz(_rotulo_azure(i["voz"])),
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
        itens.append({"motor": "piper", "voz": piper, "genero": "", "nome": "Piper (offline)", "temas": [],
                      "nota": "roda no seu PC sem internet; mais robótica"})
    from . import voz_local
    if cod == "pt-BR" and voz_local.tem_voz():  # Kokoro (Apache 2.0): grátis, no PC, sem chave
        for voz, nome in voz_local.VOZES_PT.items():
            curto = nome.split()[0]
            itens.append({"motor": "kokoro", "voz": voz, "genero": "F" if voz[1] == "f" else "M", "nome": curto,
                          "temas": temas_da_voz(curto), "nota": "Kokoro: roda no seu PC, sem chave"})
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
    from .cofre import ler_env
    return bool((ler_env().get(PAGOS[motor]["chave"]) or "").strip())


def pagas(cod: str) -> list[dict]:
    """Cada opção paga com a situação dela: sem chave, com chave e sem amostra, gerando, pronta ou com erro."""
    estado = _estado()
    saida = []
    for motor, info in PAGOS.items():
        e = estado.get(motor, {}).get(cod, {})
        vozes = [{**v, "motor": motor, "temas": v.get("temas") or temas_da_voz(v.get("nome", "")),
                  "url": url(_arquivo_pago(cod, motor, v["voz"]))} for v in e.get("vozes", [])]
        if e.get("situacao") == "gerando" and time.time() - e.get("inicio", 0) > 1800:
            e = {**e, "situacao": "erro", "erro": "a geração parou no meio; tente de novo"}
        saida.append({"motor": motor, **info, "tem_chave": _tem_chave(motor), "situacao": e.get("situacao", ""),
                      "erro": e.get("erro", ""), "vozes": [v for v in vozes if v["url"]]})
    return saida


def propria(cod: str) -> dict:
    """A voz do próprio dono, clonada no PC pelo Chatterbox (MIT) a partir de uma gravação dele."""
    idioma = mercados.MERCADOS[cod]["idioma"]
    e = _estado().get("chatterbox", {}).get(cod, {})
    if e.get("situacao") == "gerando" and time.time() - e.get("inicio", 0) > 1800:
        e = {**e, "situacao": "erro", "erro": "a geração parou no meio; tente de novo"}
    amostra = url(_arquivo_pago(cod, "chatterbox", "minha-voz"))
    return {"disponivel": narracao.tem_chatterbox(idioma), "gravada": config.MINHA_VOZ.is_file(),
            "situacao": e.get("situacao", ""), "erro": e.get("erro", ""), "texto": TEXTO_GRAVAR,
            "cartao": {"motor": "chatterbox", "voz": "minha-voz", "nome": "Sua voz", "genero": "",
                       "nota": "clonada da sua gravação, no seu PC", "temas": [], "url": amostra}}


def catalogo(cod: str) -> dict:
    return {"gratis": gratis(cod), "pagas": pagas(cod), "propria": propria(cod)}


# o dono lê em voz alta: frases variadas, com pergunta e número, cobrem bem o jeito de falar
TEXTO_GRAVAR = ("Você sabia que o coração de um polvo bate em três ritmos diferentes? Pois é. Em mil novecentos e "
                "oitenta e dois, uma equipe de mergulhadores registrou isso pela primeira vez, e a descoberta mudou "
                "o que a gente pensava sobre esses animais. Hoje eu vou te contar como tudo aconteceu.")


def salvar_minha_voz(origem: Path) -> float:
    """Converte a gravação (qualquer formato do navegador ou do PC) para WAV mono 24 kHz, sem os silêncios das
    pontas, com até 30 s. Devolve a duração. Fica em dados/minha-voz, fora do Git: é a voz de uma pessoa."""
    destino = config.MINHA_VOZ
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".novo.wav")
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i",
                           str(origem), "-vn", "-ac", "1", "-ar", "24000", "-t", "30", "-af",
                           "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                           "silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm",
                           str(temporario)], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if proc.returncode != 0 or not temporario.is_file():
        temporario.unlink(missing_ok=True)
        raise SystemExit("não consegui ler a gravação: envie um áudio (mp3, wav, m4a, webm ou ogg)")
    import wave
    with wave.open(str(temporario)) as w:
        duracao = w.getnframes() / w.getframerate()
    if duracao < 8:
        temporario.unlink(missing_ok=True)
        raise SystemExit(f"a gravação tem {duracao:.0f} s de fala; grave pelo menos 10 s (o ideal é de 15 a 25 s)")
    temporario.replace(destino)
    return duracao


def gerar_minha_amostra(cod: str) -> dict:
    if cod not in mercados.MERCADOS:
        raise SystemExit("mercado inválido")
    _gravar_estado("chatterbox", cod, {"situacao": "gerando", "inicio": time.time()})
    try:
        _sintetizar("chatterbox", "minha-voz", cod, _arquivo_pago(cod, "chatterbox", "minha-voz"))
    except (SystemExit, OSError, subprocess.CalledProcessError) as erro:
        _gravar_estado("chatterbox", cod, {"situacao": "erro", "erro": ocultar(str(erro))[:200]})
        return {"situacao": "erro"}
    _gravar_estado("chatterbox", cod, {"situacao": "pronto"})
    return {"situacao": "pronto"}


def gerar_minha_amostra_em_segundo_plano(cod: str) -> None:
    if cod not in mercados.MERCADOS:
        return
    _gravar_estado("chatterbox", cod, {"situacao": "gerando", "inicio": time.time()})
    subprocess.Popen([sys.executable, "-m", "darkops", "vozes-amostras", "--minha-voz", "--mercado", cod],
                     cwd=config.RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def escolha(valor: str) -> dict:
    """'motor|voz' do seletor -> campos do perfil. A voz é conferida com o mercado em mercados.coerente."""
    motor, _, voz = str(valor or "").partition("|")
    voz = voz.strip()[:120]
    if motor == "chatterbox" and voz == "minha-voz":
        return {"motor_voz": motor, "voz": voz}
    if motor not in ("auto", "piper", "kokoro", *PAGOS) or not voz or not re.match(r"^[\w.:-]+$", voz):
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
    if motor == "kokoro":
        from .voz_local import LINGUA
        return narracao._serve("kokoro", v) and LINGUA.get(v[:1], "").lower() == cod.lower()
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
            if motor == "chatterbox" and voz == "minha-voz":
                voz = f"{mercados.MERCADOS[cod]['idioma']}|minha-voz"
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
