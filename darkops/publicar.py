"""Upload automático para os canais oficiais do projeto (YouTube Data API v3)."""
import json
import os
from pathlib import Path

from . import config

ESCOPOS = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
CLIENT_SECRET = config.RAIZ / "credenciais" / "client_secret.json"  # app OAuth, igual para todos os perfis


def _token_youtube() -> Path:
    from .perfis import carregar
    return carregar().token_youtube
CATEGORIA_EDUCACAO = "27"


def autorizar_youtube() -> Path:
    """Abre o navegador uma vez para o dono do canal permitir o acesso e salva o token local."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        raise SystemExit(f"falta {CLIENT_SECRET} (baixe o JSON do cliente OAuth no Google Cloud)")
    fluxo = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), ESCOPOS)
    # prompt=consent garante o refresh_token mesmo se o app já foi autorizado antes
    # select_account: deixa escolher a conta do Google do canal deste perfil
    cred = fluxo.run_local_server(port=0, prompt="consent select_account", access_type="offline")
    destino = _token_youtube()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(cred.to_json(), encoding="utf-8")
    return destino


def _credenciais():
    """Token da variável YOUTUBE_TOKEN (GitHub Actions) ou do arquivo local."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    bruto = os.getenv("YOUTUBE_TOKEN", "").strip()
    if bruto:
        info = json.loads(bruto)
    elif _token_youtube().exists():
        info = json.loads(_token_youtube().read_text(encoding="utf-8"))
    else:
        raise SystemExit("sem token do YouTube: rode '.\\dark.ps1 autorizar-youtube' ou defina YOUTUBE_TOKEN")
    cred = Credentials.from_authorized_user_info(info, ESCOPOS)
    if not cred.valid:
        cred.refresh(Request())
    return cred


def _servico():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credenciais(), cache_discovery=False)


def canal() -> dict:
    """Nome e ID do canal autorizado (confere se o token é do canal certo)."""
    resposta = _servico().channels().list(part="snippet", mine=True).execute()
    itens = resposta.get("items", [])
    if not itens:
        raise SystemExit("a conta autorizada não tem canal do YouTube")
    return {"id": itens[0]["id"], "nome": itens[0]["snippet"]["title"]}


def metadados_youtube(roteiro: dict, video: Path | None = None) -> dict:
    """Título, descrição e tags a partir do bloco 'metadados' do roteiro."""
    vertical = roteiro.get("formato", "longo") == "vertical"
    meta = (roteiro.get("metadados") or {}).get("youtube_shorts" if vertical else "youtube") or {}
    titulo = meta.get("titulo") or roteiro.get("titulo", roteiro.get("slug", "vídeo"))
    if vertical and "#shorts" not in titulo.lower():
        titulo = f"{titulo} #shorts"
    hashtags = meta.get("hashtags") or []
    descricao = meta.get("descricao") or roteiro.get("titulo", "")
    if hashtags:
        descricao = f"{descricao}\n\n{' '.join(hashtags)}"
    fontes = roteiro.get("fontes") or []
    if fontes:
        descricao += "\n\nFontes:\n" + "\n".join(f"- {f}" for f in fontes)
    if video:
        from .musica import credito
        if credito(video):
            descricao += f"\n\n{credito(video)}"
    tags = meta.get("tags") or [h.lstrip("#") for h in hashtags]
    return {"titulo": titulo[:100], "descricao": descricao[:5000], "tags": tags}


def enviar_youtube(video: Path, titulo: str, descricao: str, tags: list[str],
                   privacidade: str = "private", sintetico: bool = False) -> str:
    """Envia o vídeo e devolve o ID. Projeto sem auditoria do Google: o YouTube trava como privado."""
    from googleapiclient.http import MediaFileUpload

    corpo = {
        "snippet": {"title": titulo, "description": descricao, "tags": tags,
                    "categoryId": CATEGORIA_EDUCACAO, "defaultLanguage": "pt-BR"},
        "status": {"privacyStatus": privacidade, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": sintetico},
    }
    midia = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    pedido = _servico().videos().insert(part="snippet,status", body=corpo, media_body=midia)
    resposta = None
    while resposta is None:
        progresso, resposta = pedido.next_chunk()
        if progresso:
            print(f"  enviando {int(progresso.progress() * 100)}%")
    return resposta["id"]
