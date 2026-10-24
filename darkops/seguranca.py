"""Proteções comuns: esconder tokens e chaves antes de gravar ou mostrar uma mensagem.

As mensagens de erro de bibliotecas HTTP às vezes trazem o endereço completo da chamada, com o token na query
(access_token=...). Tudo que vai para log, tela ou arquivo passa por ocultar().
"""
import re

_PADROES = [
    (re.compile(r"(access_token|client_secret|refresh_token|api_key|key)=([^&\s\"']+)", re.I), r"\1=***"),
    (re.compile(r"(Bearer|OAuth)\s+[A-Za-z0-9._\-]+", re.I), r"\1 ***"),
    (re.compile(r"\b(IGAA|EAA)[A-Za-z0-9]{20,}"), "***token-meta***"),
    (re.compile(r"\bya29\.[A-Za-z0-9._\-]{20,}"), "***token-google***"),
    (re.compile(r"\b1//0[A-Za-z0-9._\-]{20,}"), "***refresh-google***"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), "***chave-google***"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "***chave***"),
]


def ocultar(texto) -> str:
    texto = str(texto)
    for padrao, troca in _PADROES:
        texto = padrao.sub(troca, texto)
    return texto
