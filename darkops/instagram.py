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


def token() -> str:
    """Token da variável INSTAGRAM_TOKEN ou do arquivo do perfil atual."""
    from .perfis import carregar
    arquivo = carregar().token_instagram
    valor = os.getenv("INSTAGRAM_TOKEN", "").strip()
    if not valor and arquivo.exists():
        valor = arquivo.read_text(encoding="utf-8-sig").strip()
    if not valor:
        raise SystemExit("sem token do Instagram neste perfil: cole no Estúdio (Conexões)")
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


def legenda_instagram(roteiro: dict, video: Path | None = None, publicacao: dict | None = None) -> str:
    """Legenda do Reel. 'publicacao' (descricao.para_publicar) traz a descrição e as hashtags do vídeo."""
    from .musica import credito
    publicacao = publicacao or {}
    meta = (roteiro.get("metadados") or {}).get("instagram") or {}
    texto = publicacao.get("descricao") or meta.get("legenda") or roteiro.get("titulo", "")
    if video and credito(video):
        texto = f"{texto}\n\n{credito(video)}"
    hashtags = (publicacao.get("hashtags") or meta.get("hashtags") or [])[:5]  # o Instagram aceita até 5
    return (f"{texto}\n\n{' '.join(hashtags)}" if hashtags else texto)[:2200]


def publicar_reel(video: Path, legenda: str, espera_max_s: int = 600, publicar: bool = True) -> str:
    """Cria o contêiner, espera o processamento e publica. Devolve o ID da mídia (ou do contêiner, sem publicar).

    Com o Instagram Login (graph.instagram.com) a Meta não aceita o envio do arquivo (upload resumível é só do
    Facebook Login for Business): o contêiner exige um video_url público. O vídeo passa pelo repositório
    público de passagem (nuvem.video_publico) só enquanto a Meta baixa, e é apagado em seguida."""
    from . import nuvem
    if not nuvem.passagem_configurada():
        raise SystemExit("o Instagram precisa de um link público do vídeo: configure o repositório de passagem "
                         "(Estúdio > Ajustes > Contas > Nuvem)")
    tk = token()
    ig_id = conta()["user_id"]
    url, apagar = nuvem.video_publico(video)
    try:
        conteiner = _checar(requests.post(f"{GRAPH}/{ig_id}/media", timeout=60, data={
            "media_type": "REELS", "video_url": url, "caption": legenda,
            "share_to_feed": "true", "access_token": tk}))["id"]
        _esperar(conteiner, tk, espera_max_s)
    finally:
        apagar()
    if not publicar:
        return conteiner
    return _checar(requests.post(f"{GRAPH}/{ig_id}/media_publish", timeout=60, data={
        "creation_id": conteiner, "access_token": tk}))["id"]


def _esperar(conteiner: str, tk: str, espera_max_s: int) -> None:
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
