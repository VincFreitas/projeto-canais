# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""O que muda entre Windows, macOS e Linux, num lugar só.

Todo o resto do código pergunta aqui: nome de executável (.exe ou não), o Python do .venv, como rodar um programa
sem abrir janela de terminal, como abrir um arquivo ou endereço, onde fica a pasta Downloads e onde o sistema guarda
os dados do usuário. Assim o app roda igual nos três sistemas sem `if os.name` espalhado."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
NOME = "Windows" if WINDOWS else "macOS" if MACOS else "Linux" if LINUX else platform.system() or "outro"


def exe(nome: str) -> str:
    """Nome do executável neste sistema: ffmpeg.exe no Windows, ffmpeg no resto."""
    return f"{nome}.exe" if WINDOWS and not nome.lower().endswith((".exe", ".cmd", ".bat")) else nome


def cmd(nome: str) -> str:
    """Programa de linha de comando do Node (npm, npx, n8n): npm.cmd no Windows, npm no resto."""
    return f"{nome}.cmd" if WINDOWS else nome


def venv_python(raiz: Path) -> Path:
    """O Python do ambiente do projeto (.venv)."""
    return raiz / ".venv" / ("Scripts/python.exe" if WINDOWS else "bin/python")


def venv_bin(raiz: Path) -> Path:
    return raiz / ".venv" / ("Scripts" if WINDOWS else "bin")


def sem_janela() -> dict:
    """Argumentos do subprocess para não abrir janela de terminal (só o Windows abre)."""
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if WINDOWS else {}


def em_segundo_plano() -> dict:
    """Argumentos para um processo que continua depois que este fecha, sem janela."""
    if WINDOWS:
        return {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def npm() -> str | None:
    """O npm do Node portátil do projeto, ou o do sistema."""
    from . import apps
    local = apps.NODE / ("npm.cmd" if WINDOWS else "bin/npm")
    return str(local) if local.exists() else shutil.which(cmd("npm")) or shutil.which("npm")


def abrir(alvo: str | Path) -> None:
    """Abre um arquivo, pasta ou endereço com o programa padrão do sistema."""
    alvo = str(alvo)
    if alvo.startswith(("http://", "https://")):
        webbrowser.open(alvo)
    elif WINDOWS:
        os.startfile(alvo)  # noqa: S606 — caminho do próprio app
    else:
        subprocess.Popen(["open" if MACOS else "xdg-open", alvo], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)


def pastas_downloads() -> list[Path]:
    """A pasta Downloads de verdade (no Windows pode ter sido movida) e a padrão em ~/Downloads."""
    pastas = []
    if WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as chave:
                valor, _ = winreg.QueryValueEx(chave, "{374DE290-123F-4565-9164-39C4925E467B}")
                pastas.append(Path(os.path.expandvars(valor)))
        except OSError:
            pass
    elif LINUX:  # xdg-user-dirs: a pasta pode ter outro nome (Transferências, Downloads...)
        try:
            r = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                pastas.append(Path(r.stdout.strip()))
        except (OSError, subprocess.SubprocessError):
            pass
    pastas.append(Path.home() / "Downloads")
    vistas, saida = set(), []
    for p in pastas:
        chave = str(p).lower() if WINDOWS else str(p)
        if chave not in vistas and p.is_dir():
            vistas.add(chave)
            saida.append(p)
    return saida


def pasta_usuario() -> Path:
    """Onde o app guarda o que não pode ir junto com a pasta do projeto (a chave do cofre no Linux sem chaveiro)."""
    if WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "projeto-canais"


def arquitetura() -> str:
    """x64 ou arm64, no formato dos downloads do Node e do ffmpeg."""
    m = platform.machine().lower()
    return "arm64" if m in ("arm64", "aarch64") else "x64"


def env_sem_segredos() -> dict:
    """O ambiente deste processo sem as chaves e tokens do .env, para programas que não precisam deles (o Claude
    Code das tarefas automáticas lê páginas e comentários de fora; se for enganado, não tem segredo para vazar)."""
    from .cofre import segredo_env
    return {k: v for k, v in os.environ.items()
            if not segredo_env(k) or k.startswith(("ANTHROPIC_", "CLAUDE_"))}


def nuvem_ci() -> bool:
    """Rodando no GitHub Actions (a nuvem do app ou os testes do repositório)."""
    return os.environ.get("GITHUB_ACTIONS") == "true"
