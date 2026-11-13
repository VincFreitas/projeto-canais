# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Voz e escuta no próprio PC, de graça e sem chave, num ambiente separado (dados/apps/voz-local).

- Kokoro (Apache 2.0, uso comercial liberado): motor de voz "kokoro". Vozes pt-BR: pf_dora, pm_alex, pm_santa.
- faster-whisper (MIT): transcrição de áudio no PC, no lugar do serviço pago, quando o vídeo não tem legenda.

O ambiente é instalado por `python -m darkops instalar-voz-local` (pacotes e modelos baixados uma vez). O .venv do
projeto não recebe nada disso: a ponte (voz_local_ponte.py) roda com o Python do ambiente separado."""
import json
import os
import subprocess
import sys
from pathlib import Path

from . import config

PYTHON = config.VOZ_LOCAL / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MODELOS = config.VOZ_LOCAL / "modelos"
# av<16: o PyAV 16 tirou o argumento metadata_errors que o faster-whisper usa ao abrir o áudio
PACOTES = ("kokoro-onnx", "soundfile", "faster-whisper", "av<16")
ARQUIVOS = {  # modelos do Kokoro (release oficial do kokoro-onnx; pesos Apache 2.0 do hexgrad/Kokoro-82M)
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
# 1ª letra da voz = língua (a, b = inglês; p = português do Brasil...), como no catálogo do Kokoro
LINGUA = {"a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr", "h": "hi", "i": "it", "j": "ja", "p": "pt-br",
          "z": "cmn"}
VOZ_PADRAO = {"pt": "pf_dora", "en": "af_heart", "es": "ef_dora", "fr": "ff_siwis", "it": "if_sara",
              "ja": "jf_alpha", "hi": "hf_alpha", "zh": "zf_xiaobei"}
VOZES_PT = {"pf_dora": "Dora (feminina)", "pm_alex": "Alex (masculina)", "pm_santa": "Santa (masculina)"}
WHISPER = "small"  # bom em português e leve no processador (int8)


def tem_voz() -> bool:
    return PYTHON.exists() and all((MODELOS / nome).is_file() for nome in ARQUIVOS)


def tem_escuta() -> bool:
    return PYTHON.exists()


def _ponte(pedido: dict, timeout: int) -> dict:
    proc = subprocess.run([str(PYTHON), str(Path(__file__).with_name("voz_local_ponte.py"))],
                          input=json.dumps(pedido, ensure_ascii=False), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if proc.returncode != 0:
        raise SystemExit(f"voz local falhou: {proc.stderr.strip()[-400:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def falar(frases: list[str], voz: str, velocidade: float, pasta: Path) -> int:
    """Grava frase-<i>.wav em `pasta` e devolve a taxa de amostragem."""
    if not tem_voz():
        raise SystemExit("motor kokoro exige a voz local: rode `python -m darkops instalar-voz-local`")
    return _ponte({"acao": "falar", "frases": frases, "voz": voz, "lingua": LINGUA.get(voz[:1], "pt-br"),
                   "velocidade": velocidade, "modelos": str(MODELOS), "pasta": str(pasta)}, 1800)["taxa"]


def transcrever(audio: Path, idioma: str = "pt") -> dict:
    """{"texto", "segmentos"} do áudio (ou vídeo), transcrito no PC. O modelo baixa uma vez na 1ª chamada."""
    if not tem_escuta():
        raise SystemExit("a transcrição local exige `python -m darkops instalar-voz-local`")
    return _ponte({"acao": "ouvir", "audio": str(audio), "idioma": (idioma or "")[:2], "modelo": WHISPER,
                   "modelos": str(MODELOS)}, 3600)


def instalar() -> None:
    """Cria o ambiente separado, instala os pacotes e baixa os modelos do Kokoro (cerca de 340 MB)."""
    import requests
    if not PYTHON.exists():
        base = Path(getattr(sys, "_base_executable", sys.executable))
        subprocess.run([str(base), "-m", "venv", str(config.VOZ_LOCAL)], check=True)
    subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", "--disable-pip-version-check", *PACOTES], check=True)
    MODELOS.mkdir(parents=True, exist_ok=True)
    for nome, url in ARQUIVOS.items():
        destino = MODELOS / nome
        if destino.is_file() and destino.stat().st_size > 1_000_000:
            continue
        print(f"baixando {nome}")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            parcial = destino.with_suffix(".parcial")
            with open(parcial, "wb") as f:
                for bloco in r.iter_content(1 << 20):
                    f.write(bloco)
            parcial.replace(destino)
    print("voz local pronta" if tem_voz() else "a voz local não ficou pronta: confira a internet e rode de novo")
