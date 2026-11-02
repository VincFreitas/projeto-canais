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
import urllib.request
import zipfile
from pathlib import Path

from . import config

PASTA = config.RAIZ / "dados" / "apps"
NODE = PASTA / "node"
N8N = PASTA / "n8n"
N8N_CMD = N8N / "node_modules" / ".bin" / "n8n.cmd"
NODE_MAJOR = 24          # LTS testada com o n8n 2.x deste projeto
N8N_VERSAO = "2"         # a última 2.x; a atualização de dependências sobe depois
NODE_DIST = "https://nodejs.org/dist"
CLAUDE_INSTALADOR = "https://claude.ai/install.ps1"  # instalador oficial da Anthropic (Windows)


def env_node() -> dict:
    """Ambiente com o Node do projeto na frente do PATH (o n8n.cmd chama "node")."""
    env = dict(os.environ)
    if (NODE / "node.exe").exists():
        env["PATH"] = f"{NODE}{os.pathsep}{env.get('PATH', '')}"
    return env


def node_exe() -> str | None:
    local = NODE / "node.exe"
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


def instalar_node() -> str:
    """Node.js LTS portátil (zip oficial) em dados/apps/node, conferido pelo SHA-256 e pela assinatura."""
    if (NODE / "node.exe").exists():
        return str(NODE / "node.exe")
    with urllib.request.urlopen(f"{NODE_DIST}/index.json", timeout=60) as r:
        versoes = json.load(r)
    versao = next(v["version"] for v in versoes
                  if v["version"].startswith(f"v{NODE_MAJOR}.") and "win-x64-zip" in v.get("files", []))
    nome = f"node-{versao}-win-x64.zip"
    print(f"baixando o Node.js {versao} (cerca de 35 MB)...")
    with urllib.request.urlopen(f"{NODE_DIST}/{versao}/SHASUMS256.txt", timeout=60) as r:
        linhas = [linha.split() for linha in r.read().decode().splitlines() if linha.strip()]
    somas = {nome_arquivo: soma for soma, nome_arquivo in linhas}  # "<sha256>  <arquivo>"
    zip_ = _baixar(f"{NODE_DIST}/{versao}/{nome}", PASTA / nome)
    if hashlib.sha256(zip_.read_bytes()).hexdigest() != somas.get(nome):
        zip_.unlink(missing_ok=True)
        raise SystemExit("o Node.js baixado não confere com o SHA-256 publicado pelo nodejs.org; descartado")
    with zipfile.ZipFile(zip_) as z:
        z.extractall(PASTA)
    zip_.unlink()
    shutil.rmtree(NODE, ignore_errors=True)
    (PASTA / nome.removesuffix(".zip")).rename(NODE)
    if "OpenJS Foundation" not in assinatura(NODE / "node.exe"):
        shutil.rmtree(NODE, ignore_errors=True)
        raise SystemExit("o node.exe não tem a assinatura da OpenJS Foundation; descartado")
    return str(NODE / "node.exe")


def instalar_n8n() -> str:
    """n8n na pasta do projeto (npm --prefix), com o Node do projeto. Leva de 5 a 15 minutos."""
    if N8N_CMD.exists():
        return str(N8N_CMD)
    npm = NODE / "npm.cmd" if (NODE / "npm.cmd").exists() else shutil.which("npm.cmd") or shutil.which("npm")
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
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                    f"irm {CLAUDE_INSTALADOR} | iex"], timeout=900)
    exe = Path.home() / ".local" / "bin" / "claude.exe"
    if not exe.exists():
        raise SystemExit("o instalador do Claude Code não terminou; instale em claude.com/claude-code")
    if "Anthropic" not in assinatura(exe):
        raise SystemExit(f"{exe} não tem a assinatura da Anthropic: apague o arquivo e instale em claude.com/claude-code")
    return str(exe)


def iniciar_com_windows() -> None:
    """Liga o n8n no logon (atalho na pasta Inicializar), para postar às 12h e às 19h mesmo sem abrir o Estúdio."""
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(config.RAIZ / "n8n" / "iniciar-com-windows.ps1")], check=True)


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
        raise SystemExit(f"o Chromium do palco 3D não instalou: {(proc.stdout + proc.stderr).strip()[-300:]}")
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
