# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Autoria, versão e conferência de créditos.

O projeto é público, sob a licença PolyForm Shield (arquivo LICENSE): uso comercial liberado, inclusive
monetizar canais, menos oferecer um produto concorrente.
A versão aparece no Estúdio, no README e na CLI; se alguém apagar os créditos de autoria (LICENSE e
README), o Estúdio mostra um aviso de cópia modificada com o link do projeto original.
"""
import hashlib

from . import __version__, config

AUTOR = "Vinicius Freitas"
PROJETO = "Projeto Canais"
VERSAO = __version__
REPOSITORIO = "https://github.com/VincFreitas/projeto-canais"
LINKEDIN = "https://www.linkedin.com/in/vinicius-freitas-5941b9446"
ROTULO = f"{PROJETO} v{VERSAO}"

# sha256 de AUTOR: trocar o nome no código sem trocar o hash também conta como crédito removido
_ASSINATURA = "289596c808058900f6f9dd0f9bf5b74a21bd1fc01332db4a73bd1047c85abce7"


LICENCA_SPDX = "LicenseRef-PolyForm-Shield-1.0.0"
MARCA = f"Feito com o {PROJETO} ({REPOSITORIO.removeprefix('https://')})"
# marca d'água invisível dos arquivos de código (decisão do dono em 2026-11-12): duas linhas no topo
CABECALHO = (f"SPDX-License-Identifier: {LICENCA_SPDX}", f"{PROJETO} · {AUTOR} · {REPOSITORIO.removeprefix('https://')}")
_COMENTARIO = {".py": ("# ", ""), ".sh": ("# ", ""), ".ps1": ("# ", ""), ".js": ("// ", ""), ".mjs": ("// ", ""),
               ".cjs": ("// ", ""), ".css": ("/* ", " */"), ".html": ("<!-- ", " -->"), ".md": ("<!-- ", " -->")}
# arquivos centrais que precisam manter o cabeçalho (conferidos junto com LICENSE e README)
_SENTINELAS = ("darkops/__init__.py", "darkops/autoria.py", "darkops/estudio/__init__.py", "darkops/__main__.py")


def versao_cli() -> str:
    return ROTULO


def metadados_video() -> list[str]:
    """Marca d'água invisível do vídeo: metadados do MP4 (não aparecem na tela nem mudam o alcance)."""
    return ["-metadata", f"comment={MARCA}", "-metadata", f"encoded_by={ROTULO}"]


def metadados_png():
    """Marca d'água invisível das imagens PNG geradas (thumbnail, carrossel, identidade)."""
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text("Software", ROTULO)
    info.add_text("Comment", MARCA)
    return info


def comentario_svg() -> str:
    return f"<!-- {MARCA} · {AUTOR} -->"


def _linhas_cabecalho(sufixo: str) -> list[str]:
    abre, fecha = _COMENTARIO[sufixo]
    return [f"{abre}{linha}{fecha}" for linha in CABECALHO]


def tem_cabecalho(arquivo) -> bool:
    """O cabeçalho está no começo (código) ou, em Markdown e HTML, no fim do arquivo."""
    try:
        texto = arquivo.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return CABECALHO[0] in texto[:600] or CABECALHO[0] in texto[-600:]


def marcar_arquivo(arquivo) -> bool:
    """Põe o cabeçalho de autoria no arquivo (depois do shebang, da linha de codificação ou do BOM). Markdown e
    HTML de modelo ganham o comentário no fim, para não atrapalhar o cabeçalho de skill nem o {% extends %}."""
    sufixo = arquivo.suffix.lower()
    if sufixo not in _COMENTARIO or tem_cabecalho(arquivo):
        return False
    with arquivo.open(encoding="utf-8", newline="") as f:  # newline="": mantém o fim de linha que o arquivo já tem
        texto = f.read()
    nl = "\r\n" if "\r\n" in texto else "\n"
    bom = "﻿" if texto.startswith("﻿") else ""
    texto = texto.removeprefix("﻿")
    linhas_cab = _linhas_cabecalho(sufixo)
    if sufixo in (".md", ".html"):
        novo = texto.rstrip("\r\n") + nl + nl + nl.join(linhas_cab) + nl
    else:
        linhas = texto.split(nl)
        pos = 0
        while pos < len(linhas) and pos < 2 and (linhas[pos].startswith("#!") or "coding" in linhas[pos][:30]):
            pos += 1
        novo = nl.join(linhas[:pos] + linhas_cab + linhas[pos:])
    with arquivo.open("w", encoding="utf-8", newline="") as f:
        f.write(bom + novo)
    return True


def marcar_arquivos() -> list[str]:
    """Cabeçalho em todos os arquivos de código e documentação versionados (rode antes de cada versão)."""
    import subprocess
    # versionados e os novos que ainda não entraram no Git (os ignorados ficam de fora)
    r = subprocess.run(["git", "-C", str(config.RAIZ), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                       capture_output=True, text=True)
    feitos = []
    for nome in filter(None, r.stdout.split("\0")):
        caminho = config.RAIZ / nome
        # só código e documentação do app: dados, pesquisas e saídas de vídeo não levam a marca
        if (nome.startswith(("web/node_modules", "perfis/", "roteiros/", "dados/", "pesquisa/", "saida/", "obra/"))
                or ".min." in nome
                or not caminho.is_file() or caminho.stat().st_size > 400_000):
            continue
        if marcar_arquivo(caminho):
            feitos.append(nome)
    return feitos


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
    sem = [s for s in _SENTINELAS if (config.RAIZ / s).exists() and not tem_cabecalho(config.RAIZ / s)]
    if sem:
        faltando.append("cabeçalho de autoria em " + ", ".join(sem))
    return faltando
