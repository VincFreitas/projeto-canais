# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Ambiente de execução do Estúdio: hoje só "local"; "servidor" fica preparado para o futuro aplicativo/site.

  DARKOPS_AMBIENTE=local      (padrão) Estúdio no próprio PC, só em 127.0.0.1, como sempre
  DARKOPS_AMBIENTE=servidor   preparado, mas BLOQUEADO: as regras de segurança do projeto (AGENTS.md) só
                              permitem o Estúdio em 127.0.0.1. Liberar exige decisão do dono e a revisão de
                              segurança descrita em docs/app-e-site.md (login, HTTPS, CSRF por token, tokens
                              criptografados por usuário).

Tudo que muda de um ambiente para o outro (chave da sessão, cookies, origens aceitas) sai daqui, para que o
modo servidor seja uma troca de configuração e não uma caça a valores espalhados pelo código.
"""
import os
import re

LOCAL, SERVIDOR = "local", "servidor"
ORIGEM_LOCAL = re.compile(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)")


def atual() -> str:
    valor = os.getenv("DARKOPS_AMBIENTE", LOCAL).strip().lower() or LOCAL
    if valor not in (LOCAL, SERVIDOR):
        raise SystemExit(f"DARKOPS_AMBIENTE inválido: {valor!r} (use local ou servidor)")
    return valor


def exigir_local() -> None:
    """Chamado ao abrir o Estúdio: o modo servidor ainda não está liberado."""
    if atual() == SERVIDOR:
        raise SystemExit("DARKOPS_AMBIENTE=servidor está preparado, mas bloqueado: pelas regras de segurança do projeto o "
                         "Estúdio só roda em 127.0.0.1. Veja docs/app-e-site.md para o que falta antes de liberar.")


def chave_secreta() -> bytes:
    """Local: nova a cada abertura (a sessão acaba quando o Estúdio fecha). Servidor: fixa, vinda do ambiente,
    para várias instâncias aceitarem a mesma sessão."""
    if atual() == LOCAL:
        return os.urandom(32)
    chave = os.getenv("DARKOPS_CHAVE_SECRETA", "")
    if len(chave) < 32:
        raise SystemExit("modo servidor: defina DARKOPS_CHAVE_SECRETA com 32 caracteres ou mais (fora do Git)")
    return chave.encode()


def config_flask() -> dict:
    """Cookie de sessão: o único cookie do Estúdio, necessário (avisos entre telas). Nunca vai em pedido de outro
    site (SameSite=Strict) nem é lido por script (HttpOnly). No servidor, só por HTTPS e com prefixo __Host-."""
    servidor = atual() == SERVIDOR
    return {
        "SESSION_COOKIE_NAME": "__Host-sessao" if servidor else "session",
        "SESSION_COOKIE_SAMESITE": "Strict",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SECURE": servidor,
        "SESSION_PERMANENT": False,
        "PREFERRED_URL_SCHEME": "https" if servidor else "http",
    }


def origem_permitida(origem: str) -> bool:
    """Origin/Referer aceitos num POST. Local: só o próprio PC. Servidor: a lista DARKOPS_ORIGENS (https)."""
    if atual() == LOCAL:
        achado = ORIGEM_LOCAL.match(origem)
        porta = os.getenv("PORT", "")  # o Estúdio grava a porta dele ao abrir; outro servidor local não posta aqui
        return bool(achado) and (not porta or (achado.group(2) or ":80")[1:] == porta)
    permitidas = [o.strip().rstrip("/") for o in os.getenv("DARKOPS_ORIGENS", "").split(",") if o.strip()]
    return any(origem == o or origem.startswith(o + "/") for o in permitidas if o.startswith("https://"))
