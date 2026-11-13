# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Instala sozinho os programas de que a automação precisa, dentro da pasta do projeto (dados/apps):

  python -m darkops instalar-apps        Node.js portátil, n8n, Claude Code, workflow do n8n e início com o Windows

Por que na pasta do projeto: sem administrador, sem mexer no PATH do Windows e longe do AppData. O terminal do app
Claude (pacote MSIX) desvia o AppData para uma pasta virtual que o resto do Windows não vê; um `npm install -g`
feito ali some fora do Claude. A pasta do projeto é a mesma para todos os processos.
Cada download é conferido (SHA-256 publicado pelo Node.js e assinatura digital do Windows) antes de ser usado.
Fica com o usuário só o que é conta: login no Claude Code, conta local do n8n, chaves e contas das plataformas.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from . import config

WINDOWS = os.name == "nt"
PASTA = config.RAIZ / "dados" / "apps"
NODE = PASTA / "node"
NODE_BIN = NODE if WINDOWS else NODE / "bin"          # onde ficam node, npm e npx em cada sistema
N8N = PASTA / "n8n"
N8N_CMD = N8N / "node_modules" / ".bin" / ("n8n.cmd" if WINDOWS else "n8n")
NODE_MAJOR = 24          # LTS testada com o n8n 2.x deste projeto
N8N_VERSAO = "2"         # a última 2.x; a atualização de dependências sobe depois
NODE_DIST = "https://nodejs.org/dist"
# instaladores oficiais da Anthropic: install.ps1 no Windows, install.sh no macOS e no Linux
CLAUDE_INSTALADOR = "https://claude.ai/install.ps1" if WINDOWS else "https://claude.ai/install.sh"


def env_node() -> dict:
    """Ambiente com o Node do projeto na frente do PATH (o n8n chama "node")."""
    env = dict(os.environ)
    if (NODE_BIN / ("node.exe" if WINDOWS else "node")).exists():
        env["PATH"] = f"{NODE_BIN}{os.pathsep}{env.get('PATH', '')}"
    return env


def node_exe() -> str | None:
    local = NODE_BIN / ("node.exe" if WINDOWS else "node")
    return str(local) if local.exists() else shutil.which("node")


def _baixar(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = destino.with_name(destino.name + ".baixando")
    with urllib.request.urlopen(url, timeout=600) as r, temp.open("wb") as f:
        shutil.copyfileobj(r, f)
    temp.replace(destino)
    return destino


def assinatura(arquivo: Path) -> str:
    """'Valid|<assinante>' quando a assinatura digital do Windows confere."""
    return subprocess.run(["powershell", "-NoProfile", "-Command",
                           f"$s = Get-AuthenticodeSignature -LiteralPath '{arquivo}'; "
                           "\"$($s.Status)|$($s.SignerCertificate.Subject)\""],
                          capture_output=True, text=True).stdout.strip()


def _pacote_node() -> tuple[str, str]:
    """(chave em index.json, nome do arquivo sem a versão) do Node para este sistema e processador."""
    import platform
    arq = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    if WINDOWS:
        return f"win-{arq}-zip", f"win-{arq}.zip"
    if sys.platform == "darwin":
        return f"osx-{arq}-tar", f"darwin-{arq}.tar.gz"
    return f"linux-{arq}", f"linux-{arq}.tar.xz"


def instalar_node() -> str:
    """Node.js LTS portátil (pacote oficial) em dados/apps/node, conferido pelo SHA-256 publicado pelo nodejs.org e,
    no Windows, também pela assinatura digital."""
    if node_exe() and Path(node_exe()).is_relative_to(NODE):
        return node_exe()
    chave, sufixo = _pacote_node()
    with urllib.request.urlopen(f"{NODE_DIST}/index.json", timeout=60) as r:
        versoes = json.load(r)
    versao = next(v["version"] for v in versoes
                  if v["version"].startswith(f"v{NODE_MAJOR}.") and chave in v.get("files", []))
    nome = f"node-{versao}-{sufixo}"
    print(f"baixando o Node.js {versao} (cerca de 35 MB)...")
    with urllib.request.urlopen(f"{NODE_DIST}/{versao}/SHASUMS256.txt", timeout=60) as r:
        linhas = [linha.split() for linha in r.read().decode().splitlines() if linha.strip()]
    somas = {nome_arquivo: soma for soma, nome_arquivo in linhas}  # "<sha256>  <arquivo>"
    pacote = _baixar(f"{NODE_DIST}/{versao}/{nome}", PASTA / nome)
    if hashlib.sha256(pacote.read_bytes()).hexdigest() != somas.get(nome):
        pacote.unlink(missing_ok=True)
        raise SystemExit("o Node.js baixado não confere com o SHA-256 publicado pelo nodejs.org; descartado")
    if nome.endswith(".zip"):
        with zipfile.ZipFile(pacote) as z:
            z.extractall(PASTA)
        pasta = PASTA / nome.removesuffix(".zip")
    else:
        import tarfile
        with tarfile.open(pacote) as t:
            t.extractall(PASTA, filter="data")  # sem link nem caminho para fora da pasta
        pasta = PASTA / nome.removesuffix(".tar.gz").removesuffix(".tar.xz")
    pacote.unlink()
    shutil.rmtree(NODE, ignore_errors=True)
    pasta.rename(NODE)
    if WINDOWS and "OpenJS Foundation" not in assinatura(NODE / "node.exe"):
        shutil.rmtree(NODE, ignore_errors=True)
        raise SystemExit("o node.exe não tem a assinatura da OpenJS Foundation; descartado")
    return node_exe() or ""


def _npm() -> str | None:
    local = NODE_BIN / ("npm.cmd" if WINDOWS else "npm")
    return str(local) if local.exists() else shutil.which("npm.cmd" if WINDOWS else "npm") or shutil.which("npm")


def instalar_n8n() -> str:
    """n8n na pasta do projeto (npm --prefix), com o Node do projeto. Leva de 5 a 15 minutos."""
    if N8N_CMD.exists():
        return str(N8N_CMD)
    npm = _npm()
    if not npm:
        raise SystemExit("npm não encontrado: instale o Node.js antes (python -m darkops instalar-apps)")
    print("instalando o n8n (de 5 a 15 minutos, cerca de 600 MB)...")
    N8N.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([str(npm), "install", "--prefix", str(N8N), f"n8n@{N8N_VERSAO}", "--no-audit", "--no-fund",
                           "--loglevel=error"], env=env_node(), timeout=3600)
    if proc.returncode != 0 or not N8N_CMD.exists():
        raise SystemExit("o npm não conseguiu instalar o n8n (veja a mensagem acima) ")
    return str(N8N_CMD)


def claude_instalado() -> str | None:
    from .leva import _claude
    return _claude()


def instalar_claude() -> str:
    """Claude Code pelo instalador oficial da Anthropic (vai para ~/.local/bin, fora do AppData).
    O login na conta continua com o usuário: rodar `claude` uma vez."""
    achado = claude_instalado()
    if achado:
        return achado
    print("instalando o Claude Code (instalador oficial da Anthropic)...")
    if WINDOWS:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                        f"irm {CLAUDE_INSTALADOR} | iex"], timeout=900)
    else:
        subprocess.run(["bash", "-c", f"curl -fsSL {CLAUDE_INSTALADOR} | bash"], timeout=900)
    exe = Path.home() / ".local" / "bin" / ("claude.exe" if WINDOWS else "claude")
    if not exe.exists():
        raise SystemExit("o instalador do Claude Code não terminou; instale em claude.com/claude-code")
    if WINDOWS and "Anthropic" not in assinatura(exe):
        raise SystemExit(f"{exe} não tem a assinatura da Anthropic: apague o arquivo e instale em claude.com/claude-code")
    return str(exe)


def iniciar_com_windows() -> None:
    """Liga o n8n quando a pessoa entra no computador, para postar às 12h e às 19h mesmo sem abrir o Estúdio.
    Windows: atalho na pasta Inicializar. Linux: ~/.config/autostart (padrão XDG). macOS: LaunchAgent do usuário."""
    if WINDOWS:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(config.RAIZ / "n8n" / "iniciar-com-windows.ps1")], check=True)
        return
    import sys as _sys
    comando = [_sys.executable, "-c", "from darkops import app; app.ligar_n8n()"]
    if _sys.platform == "darwin":
        destino = Path.home() / "Library" / "LaunchAgents" / "com.projeto-canais.n8n.plist"
        argumentos = "".join(f"<string>{c}</string>" for c in comando)
        texto = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                 '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
                 '<key>Label</key><string>com.projeto-canais.n8n</string>'
                 f'<key>ProgramArguments</key><array>{argumentos}</array>'
                 f'<key>WorkingDirectory</key><string>{config.RAIZ}</string>'
                 '<key>RunAtLoad</key><true/></dict></plist>\n')
    else:
        destino = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart" / \
            "projeto-canais-n8n.desktop"
        texto = ("[Desktop Entry]\nType=Application\nName=n8n (Projeto Canais)\n"
                 f"Exec=sh -c 'cd \"{config.RAIZ}\" && \"{_sys.executable}\" -c \"from darkops import app; "
                 "app.ligar_n8n()\"'\nX-GNOME-Autostart-enabled=true\nNoDisplay=true\n")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")


PLAYWRIGHT = PASTA / "ms-playwright"  # navegador do palco 3D (palco_web.py)


def env_playwright() -> dict:
    """Aponta o Playwright para o Chromium da pasta do projeto: instalado pelo terminal do app Claude, o padrão
    (%LOCALAPPDATA%\\ms-playwright) cai na pasta virtual do pacote e o n8n não acha (a postagem falha)."""
    return {"PLAYWRIGHT_BROWSERS_PATH": str(PLAYWRIGHT)}


def instalar_playwright() -> str:
    """Chromium do Playwright em dados/apps/ms-playwright (só se faltar)."""
    import sys
    if PLAYWRIGHT.exists() and any(PLAYWRIGHT.glob("chromium*")):
        return "já instalado"
    proc = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], capture_output=True, text=True,
                          env={**os.environ, **env_playwright()}, timeout=1800)
    if proc.returncode != 0:
        dica = (" No Linux, as bibliotecas do sistema vêm com: sudo python -m playwright install-deps chromium"
                if sys.platform.startswith("linux") else "")
        raise SystemExit(f"o Chromium do palco 3D não instalou: {(proc.stdout + proc.stderr).strip()[-300:]}{dica}")
    return str(PLAYWRIGHT)


def instalar_tudo(claude: bool = True, n8n: bool = True, logon: bool = True) -> list[str]:
    """Cada etapa é independente: uma falha não impede as outras. Devolve a lista de falhas."""
    falhas = []

    def etapa(nome, fn):
        try:
            print(f"ok: {nome}: {fn() or 'pronto'}")
        except (SystemExit, OSError, subprocess.SubprocessError, ValueError, StopIteration) as erro:
            from .seguranca import ocultar
            falhas.append(nome)
            print(f"FALHOU: {nome}: {ocultar(str(erro))}")

    if n8n:
        etapa("Node.js", instalar_node)
        etapa("n8n", instalar_n8n)
        if N8N_CMD.exists():
            if logon:  # antes do workflow: o reinício do n8n usa este atalho para abrir fora do terminal do agente
                etapa("n8n iniciando com o Windows", iniciar_com_windows)
            from .instalacao import gerar_workflow
            etapa("workflow de postagem no n8n", lambda: gerar_workflow(importar=True) and "importado e ligado")
    if claude:
        etapa("Claude Code", instalar_claude)
    etapa("Chromium do palco 3D", instalar_playwright)
    return falhas
