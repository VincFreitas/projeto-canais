"""Autoria, versão e conferência de créditos.

O projeto é público para teste e estudo, sob a licença PolyForm Noncommercial (arquivo LICENSE).
O carimbo do autor aparece no Estúdio, no README e na CLI; se alguém apagar os créditos, o Estúdio
mostra um aviso de cópia modificada com o link do projeto original.
"""
import hashlib

from . import __version__, config

AUTOR = "Vinicius Freitas"
PROJETO = "Fábrica de Canais"
VERSAO = __version__
REPOSITORIO = "https://github.com/VincFreitas/pulga-do-saber"
LINKEDIN = "https://www.linkedin.com/in/vinicius-freitas-5941b9446"
YOUTUBE = "https://www.youtube.com/@pulgadosaber"
INSTAGRAM = "https://www.instagram.com/pulgadosaber"
CARIMBO = f"{PROJETO} v{VERSAO} · criado por {AUTOR}"

# sha256 de AUTOR: trocar o nome no código sem trocar o hash também conta como crédito removido
_ASSINATURA = "289596c808058900f6f9dd0f9bf5b74a21bd1fc01332db4a73bd1047c85abce7"


def carimbo_cli() -> str:
    return f"{CARIMBO} · {REPOSITORIO}"


def creditos_removidos() -> list[str]:
    """Lista o que sumiu dos créditos (vazia quando está tudo no lugar)."""
    faltando = []
    if hashlib.sha256(AUTOR.encode("utf-8")).hexdigest() != _ASSINATURA:
        faltando.append("nome do autor alterado no código")
    licenca = config.RAIZ / "LICENSE"
    if not licenca.exists() or AUTOR not in licenca.read_text(encoding="utf-8", errors="ignore"):
        faltando.append("arquivo LICENSE")
    readme = config.RAIZ / "README.md"
    if not readme.exists() or AUTOR not in readme.read_text(encoding="utf-8", errors="ignore"):
        faltando.append("crédito no README")
    base = config.RAIZ / "darkops" / "estudio" / "templates" / "base.html"
    if not base.exists() or 'class="carimbo"' not in base.read_text(encoding="utf-8", errors="ignore"):
        faltando.append("carimbo do Estúdio")
    return faltando
