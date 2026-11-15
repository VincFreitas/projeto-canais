# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Proteções comuns: esconder tokens e chaves antes de gravar ou mostrar uma mensagem.

As mensagens de erro de bibliotecas HTTP às vezes trazem o endereço completo da chamada, com o token na query
(access_token=...). Tudo que vai para log, tela ou arquivo passa por ocultar().
"""
import re

_PADROES = [
    # qualquer parâmetro de endereço com nome de segredo: access_token, fb_exchange_token, input_token,
    # client_secret, password, senha, api_key, key, sig, signature...
    (re.compile(r"([\w-]*(?:token|secret|password|senha|key|sig|signature))=([^&\s\"']+)", re.I), r"\1=***"),
    (re.compile(r"(Bearer|OAuth)\s+[A-Za-z0-9._\-]+", re.I), r"\1 ***"),
    # cabeçalhos de chave (ElevenLabs, Google, Azure) que aparecem em repr de pedido ou em log de biblioteca
    (re.compile(r"\b(xi-api-key|x-api-key|x-goog-api-key|ocp-apim-subscription-key)(['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+",
                re.I), r"\1\2***"),
    (re.compile(r"\b(IGAA|EAA)[A-Za-z0-9]{20,}"), "***token-meta***"),
    (re.compile(r"\bya29\.[A-Za-z0-9._\-]{20,}"), "***token-google***"),
    (re.compile(r"\b1//0[A-Za-z0-9._\-]{20,}"), "***refresh-google***"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "***chave-google***"),
    (re.compile(r"\bsk[-_][A-Za-z0-9_\-]{20,}"), "***chave***"),  # sk-ant-... (Anthropic), sk_... (ElevenLabs)
    (re.compile(r"\b(gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"), "***token-github***"),
    (re.compile(r"GOCSPX-[A-Za-z0-9_\-]{10,}"), "***segredo-google***"),
    (re.compile(r'("(?:access_token|refresh_token|client_secret|token|api_key|secret|password|senha)"\s*:\s*")[^"]+"',
                re.I), r'\1***"'),
    # o mesmo em repr de dicionário do Python ({'access_token': '...'}), que aparece em mensagem de exceção
    (re.compile(r"('(?:access_token|refresh_token|client_secret|token|api_key|secret|password|senha)'\s*:\s*')[^']+'",
                re.I), r"\1***'"),
    (re.compile(r"\b[0-9a-f]{32}\b"), "***chave-hex***"),  # chave secreta do app da Meta, chave do Azure
    (re.compile(r"\bcofre:[A-Za-z0-9_\-=]{20,}"), "***cofre***"),
]


def ocultar(texto) -> str:
    texto = str(texto)
    for padrao, troca in _PADROES:
        texto = padrao.sub(troca, texto)
    return texto


def link_publico(url: str) -> bool:
    """Link colado pelo usuário que o app vai abrir sozinho (referência, por exemplo): só http(s) para um endereço da
    internet. Recusa o próprio PC e a rede de casa (127.0.0.1, localhost, 192.168..., 10..., [::1]...): um link
    desses faria o app pedir coisas ao n8n, ao Estúdio ou ao roteador em nome de quem colou (SSRF)."""
    import ipaddress
    from urllib.parse import urlsplit
    try:
        partes = urlsplit((url or "").strip())
        host = (partes.hostname or "").rstrip(".").lower()
    except ValueError:
        return False
    if partes.scheme not in ("http", "https") or not host or "\\" in url:
        return False
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa")):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." in host  # nome de site; um nome sem ponto é da rede local
    return ip.is_global
