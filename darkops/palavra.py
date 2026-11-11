"""Chamada final que divulga o Projeto Canais e manda o link do repositório para quem comenta a palavra-chave.

Decisão do dono em 2026-11-11: o fim do vídeo deixa de pedir um comentário sobre o tema e passa a dizer que o vídeo
foi feito pelo app, com "Comenta DARK que eu te mando o projeto". Quem comenta a palavra recebe o link:
- Instagram: resposta privada (DM) ao comentário pela API oficial (POST /<IG_ID>/messages com recipient.comment_id,
  permissões instagram_business_basic e instagram_business_manage_comments, até 7 dias depois do comentário,
  uma por comentário) e uma resposta curta no comentário avisando que foi na DM.
- YouTube: não existe mensagem direta; a resposta vai no próprio comentário, com o link.
Uma resposta por pessoa e por vídeo, frases fixas (nada de IA), sem @ e sem pedir nada em troca.
Liga e desliga por canal em "chamada_app" no perfil; a palavra fica em "palavra_app" (padrão DARK)."""
from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timedelta, timezone

import requests

REPO = "https://github.com/VincFreitas/projeto-canais"
PALAVRA_PADRAO = "DARK"
LIMITE_DIA = 200  # respostas por canal por dia, somando as duas plataformas
DIAS_INSTAGRAM = 7  # a Meta só aceita a resposta privada até 7 dias depois do comentário

# frases por língua do mercado (mercados.de(...)["codigo"][:2]); a escolha é pelo id do comentário (sem acaso)
TEXTOS = {
    "pt": {
        "dm": ("Oi! Aqui está o Projeto Canais, o app aberto que fez esse vídeo: {repo}\n\n"
               "Ele roda no seu PC e o passo a passo está no README. Se curtir, deixa uma ⭐ lá no GitHub!"),
        "publica_instagram": ["Te mandei na DM! 📩", "Enviado na sua DM 😉", "Olha a DM! 📬"],
        "publica_youtube": ["Aqui está o projeto que fez esse vídeo: {repo}",
                            "Tá aqui o app que fez esse vídeo: {repo} (o passo a passo está no README)",
                            "Projeto aberto que fez esse vídeo: {repo}"],
        "chamada": ["Esse vídeo foi feito inteiro por um app. Comenta {palavra} que eu te mando o projeto.",
                    "Ninguém editou esse vídeo: um app fez tudo sozinho. Comenta {palavra} e eu te mando o link.",
                    "Quer fazer vídeos assim sem aparecer? Comenta {palavra} que eu te mando o app que fez esse."],
        "descricao": "Esse vídeo foi feito por um app aberto. Comenta {palavra} que eu te mando o projeto.",
    },
    "en": {
        "dm": ("Hi! Here's Projeto Canais, the open app that made this video: {repo}\n\n"
               "It runs on your PC and the README has the step by step. If you like it, leave a ⭐ on GitHub!"),
        "publica_instagram": ["Sent it to your DMs! 📩", "Check your DMs 😉", "It's in your DMs! 📬"],
        "publica_youtube": ["Here's the project that made this video: {repo}",
                            "Here's the app that made this video: {repo} (the README has the step by step)",
                            "Open project that made this video: {repo}"],
        "chamada": ["This whole video was made by an app. Comment {palavra} and I'll send you the project.",
                    "Nobody edited this video: an app did it all. Comment {palavra} and I'll send you the link.",
                    "Want to make videos like this without showing your face? Comment {palavra} for the app."],
        "descricao": "This video was made by an open app. Comment {palavra} and I'll send you the project.",
    },
    "es": {
        "dm": ("¡Hola! Aquí está Projeto Canais, la app abierta que hizo este video: {repo}\n\n"
               "Funciona en tu PC y el paso a paso está en el README. Si te gusta, ¡deja una ⭐ en GitHub!"),
        "publica_instagram": ["¡Te lo mandé por DM! 📩", "Revisa tu DM 😉", "¡Está en tu DM! 📬"],
        "publica_youtube": ["Aquí está el proyecto que hizo este video: {repo}",
                            "Esta es la app que hizo este video: {repo} (el paso a paso está en el README)",
                            "Proyecto abierto que hizo este video: {repo}"],
        "chamada": ["Este video lo hizo entero una app. Comenta {palavra} y te mando el proyecto.",
                    "Nadie editó este video: una app lo hizo todo. Comenta {palavra} y te mando el link.",
                    "¿Quieres hacer videos así sin mostrar la cara? Comenta {palavra} y te mando la app."],
        "descricao": "Este video lo hizo una app abierta. Comenta {palavra} y te mando el proyecto.",
    },
}


def ligado(perfil_ou_dados) -> bool:
    dados = getattr(perfil_ou_dados, "dados", perfil_ou_dados) or {}
    return bool(dados.get("chamada_app", True))


def palavra(perfil_ou_dados) -> str:
    dados = getattr(perfil_ou_dados, "dados", perfil_ou_dados) or {}
    valor = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", str(dados.get("palavra_app") or "")).upper()
    return valor[:20] or PALAVRA_PADRAO


def _textos(dados: dict) -> dict:
    from .mercados import de
    return TEXTOS.get(de(dados)["codigo"][:2].lower(), TEXTOS["en"])


def _escolher(opcoes: list[str], chave: str) -> str:
    return opcoes[int(hashlib.sha1(chave.encode()).hexdigest(), 16) % len(opcoes)]


def instrucao_roteiro(dados: dict) -> str:
    """O que o pedido de roteiro diz sobre a última frase (vazio com a chamada desligada)."""
    if not ligado(dados):
        return ""
    t, p = _textos(dados), palavra(dados)
    exemplos = " | ".join(f"«{x.format(palavra=p)}»" for x in t["chamada"])
    return (f"Chamada final (decisão do dono): a ÚLTIMA frase da narração não pede comentário sobre o tema; ela conta, "
            f"no tom do canal, que o vídeo foi feito por um app e pede para comentar {p} (sempre em MAIÚSCULAS, "
            f"exatamente essa palavra) para receber o projeto. Varie a frase de um vídeo para outro, na língua do "
            f"roteiro, até 20 palavras, sem \"link na bio\", sem \"se inscreva\" e sem prometer nada além do link do "
            f"projeto. Exemplos (não copie sempre o mesmo): {exemplos}. ")


def instrucao_descricao(dados: dict) -> str:
    """O que o pedido da descrição diz sobre a chamada (a mesma palavra do vídeo)."""
    if not ligado(dados):
        return ""
    return (f"A chamada da descrição é a mesma do fim do vídeo: comentar {palavra(dados)} (em MAIÚSCULAS) para "
            f"receber o projeto que fez o vídeo, por exemplo «{_textos(dados)['descricao'].format(palavra=palavra(dados))}». "
            "Não escreva o link nem \"link na bio\". ")


def chamada_descricao(dados: dict) -> str:
    return _textos(dados)["descricao"].format(palavra=palavra(dados)) if ligado(dados) else ""


def bate(texto: str, chave: str) -> bool:
    """O comentário traz a palavra sozinha (DARK, dark, Dark!, #dark), não dentro de outra palavra."""
    return bool(re.search(rf"(?<![A-Za-zÀ-ÿ0-9]){re.escape(chave)}(?![A-Za-zÀ-ÿ0-9])", texto or "", re.I))


def _recente(data: str, dias: int) -> bool:
    try:
        quando = datetime.strptime(data[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - quando <= timedelta(days=dias)


def _dm_instagram(perfil, comentario_id: str, texto: str) -> None:
    from .comentarios import _token_instagram
    from .instagram import GRAPH
    tk = _token_instagram(perfil)
    eu = requests.get(f"{GRAPH}/me", params={"fields": "user_id", "access_token": tk}, timeout=30).json()
    if "error" in eu or not eu.get("user_id"):
        raise RuntimeError((eu.get("error") or {}).get("message", "não achei a conta do Instagram"))
    r = requests.post(f"{GRAPH}/{eu['user_id']}/messages", timeout=30, headers={"Authorization": f"Bearer {tk}"},
                      json={"recipient": {"comment_id": comentario_id}, "message": {"text": texto}}).json()
    if "error" in r:
        raise RuntimeError(r["error"].get("message", "o Instagram recusou a mensagem"))


def responder(perfil, dados: dict | None = None, avisar=print) -> int:
    """Manda o link para quem comentou a palavra-chave. Devolve quantas pessoas receberam."""
    from . import comentarios
    from .seguranca import ocultar
    if not ligado(perfil):
        return 0
    dados = dados or comentarios.ler(perfil)
    chave, t = palavra(perfil), _textos(perfil.dados)
    hoje = time.strftime("%Y-%m-%d")
    contagem = dados.setdefault("palavra_hoje", {})
    feitos = contagem.get(hoje, 0)
    ja = {(c["plataforma"], c.get("video_id"), c.get("autor")) for c in dados["comentarios"].values()
          if c.get("por") == "palavra"}
    enviados = 0
    for c in sorted(dados["comentarios"].values(), key=lambda x: x.get("data") or ""):
        if feitos + enviados >= LIMITE_DIA:
            break
        if c.get("estado") == "respondido" or c.get("palavra_erro") or not bate(c.get("texto", ""), chave):
            continue
        quem = (c["plataforma"], c.get("video_id"), c.get("autor"))
        if quem in ja:
            c.update({"estado": "ignorado", "por": "palavra-repetida"})  # a mesma pessoa já recebeu neste vídeo
            continue
        try:
            if c["plataforma"] == "instagram":
                if not _recente(c.get("data", ""), DIAS_INSTAGRAM):
                    continue
                _dm_instagram(perfil, c["id"], t["dm"].format(repo=REPO))
                publica = _escolher(t["publica_instagram"], c["id"])
                from .instagram import GRAPH
                r = requests.post(f"{GRAPH}/{c['id']}/replies", timeout=30,
                                  data={"message": publica, "access_token": comentarios._token_instagram(perfil)}).json()
                resposta = publica + " (link na DM)" if "error" not in r else "(link na DM)"
            else:
                if not comentarios.pode_responder_youtube(perfil):
                    c["palavra_erro"] = "falta liberar os comentários do YouTube"
                    continue
                resposta = _escolher(t["publica_youtube"], c["id"]).format(repo=REPO)
                yt, _ = comentarios._youtube(perfil)
                yt.comments().insert(part="snippet", body={"snippet": {"parentId": c["id"],
                                                                       "textOriginal": resposta}}).execute()
        except Exception as erro:  # noqa: BLE001 — um comentário que falha não para os outros
            c["palavra_erro"] = ocultar(erro)[:200]
            avisar(f"  não mandou o link para {c.get('autor')}: {c['palavra_erro']}")
            continue
        c.update({"estado": "respondido", "resposta": resposta, "por": "palavra", "categoria": "conversa",
                  "respondido_em": time.strftime("%Y-%m-%d %H:%M")})
        ja.add(quem)
        enviados += 1
    contagem.clear()
    contagem[hoje] = feitos + enviados
    comentarios._gravar(perfil, dados)
    if enviados:
        avisar(f"  link do projeto enviado para {enviados} pessoa(s) que comentaram {chave}")
    return enviados

