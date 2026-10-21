"""Publicação de Reels pela Instagram API com login do Instagram (graph.instagram.com).

Envio por upload resumível (rupload.facebook.com): o vídeo sai do disco local,
sem precisar de URL pública.
"""
import os
import time
from pathlib import Path

import requests

from . import config

VERSAO = "v23.0"
GRAPH = f"https://graph.instagram.com/{VERSAO}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{VERSAO}"
TOKEN_ARQUIVO = config.RAIZ / "credenciais" / "token_instagram.txt"


def token() -> str:
    """Token da variável INSTAGRAM_TOKEN (GitHub Actions) ou do arquivo local."""
    valor = os.getenv("INSTAGRAM_TOKEN", "").strip()
    if not valor and TOKEN_ARQUIVO.exists():
        valor = TOKEN_ARQUIVO.read_text(encoding="utf-8").strip()
    if not valor:
        raise SystemExit(f"sem token do Instagram: salve em {TOKEN_ARQUIVO} ou defina INSTAGRAM_TOKEN")
    return valor


def _checar(resposta: requests.Response) -> dict:
    dados = resposta.json()
    if resposta.status_code >= 400 or "error" in dados:
        erro = dados.get("error", dados)
        raise SystemExit(f"Instagram API: {erro.get('message', erro)}")
    return dados


def conta() -> dict:
    """ID e @ da conta dona do token."""
    return _checar(requests.get(f"{GRAPH}/me", params={"fields": "user_id,username",
                                                        "access_token": token()}, timeout=30))


def renovar_token() -> str:
    """Renova o token de longa duração por mais 60 dias (precisa ter mais de 24 h)."""
    dados = _checar(requests.get("https://graph.instagram.com/refresh_access_token",
                                 params={"grant_type": "ig_refresh_token", "access_token": token()},
                                 timeout=30))
    return dados["access_token"]


def legenda_instagram(roteiro: dict) -> str:
    meta = (roteiro.get("metadados") or {}).get("instagram") or {}
    texto = meta.get("legenda") or roteiro.get("titulo", "")
    hashtags = (meta.get("hashtags") or [])[:30]
    return (f"{texto}\n\n{' '.join(hashtags)}" if hashtags else texto)[:2200]


def publicar_reel(video: Path, legenda: str, espera_max_s: int = 600) -> str:
    """Cria o contêiner, envia o vídeo, espera o processamento e publica. Devolve o ID da mídia."""
    tk = token()
    ig_id = conta()["user_id"]

    conteiner = _checar(requests.post(f"{GRAPH}/{ig_id}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": legenda,
        "share_to_feed": "true", "access_token": tk}))["id"]

    with open(video, "rb") as f:
        _checar(requests.post(f"{RUPLOAD}/{conteiner}", data=f, timeout=600, headers={
            "Authorization": f"OAuth {tk}", "offset": "0", "file_size": str(video.stat().st_size)}))

    inicio = time.time()
    while True:
        estado = _checar(requests.get(f"{GRAPH}/{conteiner}", timeout=30, params={
            "fields": "status_code,status", "access_token": tk}))
        codigo = estado.get("status_code")
        if codigo == "FINISHED":
            break
        if codigo in ("ERROR", "EXPIRED"):
            raise SystemExit(f"processamento falhou: {estado.get('status')}")
        if time.time() - inicio > espera_max_s:
            raise SystemExit("processamento do vídeo passou do tempo limite")
        print(f"  processando ({codigo})")
        time.sleep(10)

    return _checar(requests.post(f"{GRAPH}/{ig_id}/media_publish", timeout=60, data={
        "creation_id": conteiner, "access_token": tk}))["id"]
