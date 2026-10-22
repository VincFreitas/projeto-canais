"""Caminhos, variáveis de ambiente e presets de nicho."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

PESQUISA = RAIZ / "pesquisa"
ROTEIROS = RAIZ / "roteiros"
OBRA = RAIZ / "obra"          # arquivos intermediários de produção (áudio, cenas)
SAIDA = RAIZ / "saida"        # vídeos, thumbnails e metadados prontos
CACHE = RAIZ / "dados" / "cache"
MUSICA = RAIZ / "assets" / "musica"
MODELOS = RAIZ / "modelos"     # gerador de imagem local (sd.cpp + Z-Image-Turbo), fora do Git

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
MOTOR_VOZ = os.getenv("MOTOR_VOZ", "auto").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOZ = os.getenv("ELEVENLABS_VOZ", "").strip()
ELEVENLABS_MODELO = os.getenv("ELEVENLABS_MODELO", "eleven_multilingual_v2").strip()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "").strip()
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "").strip()

FORMATOS = {
    "longo": (1920, 1080),     # YouTube tradicional
    "vertical": (1080, 1920),  # Shorts, TikTok, Reels, Kwai
}
# layout "post": o vídeo final é vertical, mas as cenas são renderizadas nesta janela, que fica
# no meio de uma moldura branca com avatar, nome, @ e manchete (estilo post de rede social)
JANELA_POST = (1080, 780)
TOPO_JANELA_POST = 700

VOZ_PADRAO = {
    "pt": "pt-BR-AntonioNeural",
    "en": "en-US-AndrewMultilingualNeural",
    "es": "es-MX-JorgeNeural",
}


def nichos() -> dict:
    return json.loads((RAIZ / "config" / "nichos.json").read_text(encoding="utf-8"))


def nicho(nome: str) -> dict:
    todos = nichos()
    if nome not in todos:
        raise SystemExit(f"Nicho '{nome}' não existe em config/nichos.json. Opções: {', '.join(todos)}")
    return todos[nome]
