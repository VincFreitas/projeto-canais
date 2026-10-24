"""A aplicação no PC do usuário: atalhos, abrir com um clique, atualizar sozinha e atualizar as dependências.

  python -m darkops abrir                       abre o Estúdio (ou só o navegador, se já estiver aberto)
  python -m darkops atalhos [--area-de-trabalho] [--menu-iniciar] [--remover]
  python -m darkops atualizar [--verificar]      busca a versão nova no GitHub e atualiza a pasta
  python -m darkops atualizar-dependencias [--aplicar]   pacotes Python, yt-dlp, n8n e Claude Code

Configurações em dados/app.json (fora do Git). O Windows não deixa um programa se fixar sozinho na barra de
tarefas: para ela, o atalho do Menu Iniciar é criado e o usuário fixa com o botão direito.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__, config

ARQUIVO = config.RAIZ / "dados" / "app.json"
NOVIDADE = config.RAIZ / "dados" / "ultima_atualizacao.json"
SINAL_REINICIO = config.RAIZ / "dados" / "reiniciar"
ICONE = config.RAIZ / "assets" / "icone.ico"
NOME = "Projeto Canais"
PADRAO = {"atalho_area_de_trabalho": False, "atalho_menu_iniciar": False, "atalho_barra_de_tarefas": False,
          "atualizar_sozinho": True, "verificar_a_cada_h": 6, "ultima_verificacao": 0}


# ---------- configurações ----------

def ler() -> dict:
    try:
        return {**PADRAO, **json.loads(ARQUIVO.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        return dict(PADRAO)


def salvar(novos: dict) -> dict:
    dados = {**ler(), **novos}
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return dados


# ---------- atalhos ----------

def _pasta_windows(nome: str) -> Path | None:
    """Pergunta ao Windows onde fica a pasta (a Área de Trabalho pode estar no OneDrive e ter nome traduzido)."""
    if os.name != "nt":
        return None
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        # sem isso o PowerShell responde na página de código do console e o "Á" chega quebrado
                        f"[Console]::OutputEncoding = [Text.Encoding]::UTF8; [Environment]::GetFolderPath('{nome}')"],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    caminho = r.stdout.strip()
    return Path(caminho) if caminho else None


def _pastas() -> dict:
    area = _pasta_windows("Desktop") or Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    menu = _pasta_windows("Programs") or Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return {"area_de_trabalho": area, "menu_iniciar": menu}


def _icone() -> Path | None:
    """Ícone da pulga (do avatar do perfil padrão ou da pulga desenhada), gerado uma vez."""
    if ICONE.exists():
        return ICONE
    try:
        from PIL import Image
        from .perfis import carregar
        origem = carregar().avatar or (carregar().controle / "pulga-avatar-pixel.png")
        if not Path(origem).exists():
            return None
        img = Image.open(origem).convert("RGBA")
        ICONE.parent.mkdir(parents=True, exist_ok=True)
        img.save(ICONE, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
        return ICONE
    except Exception:
        return None


def _criar_lnk(destino: Path) -> None:
    """Atalho do Windows que abre o Estúdio sem janela de terminal (pythonw)."""
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    alvo = pythonw if pythonw.exists() else Path(sys.executable)
    icone = _icone()
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:DESTINO_LNK); "
        "$s.TargetPath = $env:ALVO_LNK; $s.Arguments = '-m darkops abrir'; "
        "$s.WorkingDirectory = $env:PASTA_LNK; $s.Description = 'Abre o Projeto Canais'; "
        "if ($env:ICONE_LNK) { $s.IconLocation = $env:ICONE_LNK }; $s.Save()"
    )
    # os caminhos vão por variáveis de ambiente: nada do texto vira código do PowerShell
    env = {**os.environ, "DESTINO_LNK": str(destino), "ALVO_LNK": str(alvo), "PASTA_LNK": str(config.RAIZ),
           "ICONE_LNK": str(icone) if icone else ""}
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env=env, check=True,
                   capture_output=True)


def atalhos(area_de_trabalho: bool, menu_iniciar: bool, barra_de_tarefas: bool = False) -> list[str]:
    """Cria ou remove os atalhos conforme a escolha. A barra de tarefas usa o atalho do Menu Iniciar."""
    if os.name != "nt":
        return ["atalhos só no Windows"]
    pastas = _pastas()
    feito = []
    querer = {"area_de_trabalho": area_de_trabalho, "menu_iniciar": menu_iniciar or barra_de_tarefas}
    for onde, ligar in querer.items():
        lnk = pastas[onde] / f"{NOME}.lnk"
        if ligar:
            _criar_lnk(lnk)
            feito.append(f"atalho criado: {lnk}")
        elif lnk.exists():
            lnk.unlink()
            feito.append(f"atalho removido: {lnk}")
    if barra_de_tarefas:
        feito.append("barra de tarefas: abra o Menu Iniciar, clique com o botão direito em Projeto Canais e "
                     "escolha Fixar na barra de tarefas (o Windows não deixa programas fazerem isso sozinhos)")
    salvar({"atalho_area_de_trabalho": area_de_trabalho, "atalho_menu_iniciar": menu_iniciar,
            "atalho_barra_de_tarefas": barra_de_tarefas})
    return feito


def estado_atalhos() -> dict:
    pastas = _pastas()
    return {onde: (p / f"{NOME}.lnk").exists() for onde, p in pastas.items()}


# ---------- abrir ----------

def abrir() -> None:
    """O que o atalho roda: sem terminal, a saída vai para um arquivo de registro."""
    if sys.stdout is None or sys.stderr is None:  # pythonw não tem console
        registro = config.RAIZ / "dados" / "estudio.log"
        registro.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(registro, "a", encoding="utf-8", buffering=1)
    from .estudio import rodar
    rodar(abrir=True)


# ---------- atualização da aplicação (git) ----------

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def verificar() -> dict:
    """Há versão nova no GitHub? Não muda nada na pasta."""
    if not shutil.which("git") or not (config.RAIZ / ".git").exists():
        return {"ok": False, "motivo": "esta pasta não veio do git clone (baixe a versão nova no GitHub)"}
    ramo = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    busca = _git("fetch", "--quiet", "origin", ramo)
    salvar({"ultima_verificacao": time.time()})
    if busca.returncode != 0:
        return {"ok": False, "motivo": f"não consegui falar com o GitHub: {busca.stderr.strip()[-200:]}"}
    novos = _git("log", "--pretty=%s", f"HEAD..origin/{ramo}").stdout.strip().splitlines()
    return {"ok": True, "ramo": ramo, "novos": novos, "ha_novidade": bool(novos)}


def atualizar() -> dict:
    """Traz a versão nova sem perder nada local: só avança (fast-forward) e para se algo seu seria sobrescrito."""
    info = verificar()
    if not info.get("ok") or not info.get("ha_novidade"):
        return {**info, "atualizado": False}
    antes = _git("rev-parse", "HEAD").stdout.strip()
    req_antes = (config.RAIZ / "requirements.txt").read_text(encoding="utf-8")
    junta = _git("merge", "--ff-only", f"origin/{info['ramo']}")
    if junta.returncode != 0:
        return {**info, "atualizado": False,
                "motivo": "a atualização mexeria em arquivos que você mudou nesta pasta; nada foi alterado. "
                          f"Detalhe: {junta.stderr.strip()[-300:]}"}
    if (config.RAIZ / "requirements.txt").read_text(encoding="utf-8") != req_antes:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=config.RAIZ)
    versao = re.search(r'__version__ = "([\d.]+)"', (config.RAIZ / "darkops" / "__init__.py").read_text(encoding="utf-8"))
    novidade = {"de": __version__, "para": versao.group(1) if versao else "?", "quando": time.strftime("%Y-%m-%d %H:%M"),
                "mudancas": info["novos"][:30], "commit_anterior": antes, "vista": False}
    NOVIDADE.parent.mkdir(parents=True, exist_ok=True)
    NOVIDADE.write_text(json.dumps(novidade, ensure_ascii=False, indent=2), encoding="utf-8")
    SINAL_REINICIO.write_text(str(time.time()), encoding="utf-8")  # o Estúdio aberto reinicia sozinho
    return {**info, "atualizado": True, "novidade": novidade}


def novidade_pendente() -> dict | None:
    try:
        dados = json.loads(NOVIDADE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return None if dados.get("vista") else dados


def marcar_novidade_vista() -> None:
    dados = novidade_pendente()
    if dados:
        NOVIDADE.write_text(json.dumps({**dados, "vista": True}, ensure_ascii=False, indent=2), encoding="utf-8")


def reiniciar_processo() -> None:
    """Abre um Estúdio novo (com o código novo) e encerra este. O novo espera a porta ficar livre."""
    sinais = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS) if os.name == "nt" else 0
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if os.name == "nt" and pythonw.exists() else Path(sys.executable)
    args = dict(cwd=config.RAIZ, env={**os.environ, "DARKOPS_REINICIO": "1"}, close_fds=True)
    try:
        # sai do "job" do processo pai (terminal, agendador...), senão o Windows mata o novo junto com o antigo
        subprocess.Popen([str(exe), "-m", "darkops", "abrir"], creationflags=sinais | 0x01000000, **args)
    except OSError:  # o job não permite sair: abre mesmo assim
        subprocess.Popen([str(exe), "-m", "darkops", "abrir"], creationflags=sinais, **args)
    SINAL_REINICIO.unlink(missing_ok=True)
    os._exit(0)


# ---------- dependências ----------

def _rodar(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


def dependencias(aplicar: bool = False) -> list[dict]:
    """Lista (e, com aplicar, atualiza) o que o projeto usa. O yt-dlp é o que mais precisa: o YouTube e o
    Instagram mudam e versões antigas param de baixar."""
    itens = []
    pip = [sys.executable, "-m", "pip"]
    r = _rodar(pip + ["list", "--outdated", "--format=json"], timeout=300)
    try:
        velhos = {p["name"].lower(): p for p in json.loads(r.stdout or "[]")}
    except json.JSONDecodeError:
        velhos = {}
    nossos = [re.split(r"[<>=!~\[ ]", l.strip())[0].lower() for l in
              (config.RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    for nome in nossos:
        p = velhos.get(nome) or velhos.get(nome.replace("-", "_"))
        itens.append({"nome": nome, "tipo": "Python", "atual": p["version"] if p else "em dia",
                      "nova": p["latest_version"] if p else None})
    if aplicar and any(i["nova"] for i in itens):
        _rodar(pip + ["install", "-q", "--upgrade", "-r", "requirements.txt"])
        for i in itens:
            if i["nova"]:
                i["resultado"] = "atualizado"
    npm = shutil.which("npm")
    n8n = shutil.which("n8n") or (Path(os.environ.get("APPDATA", "")) / "npm" / "n8n.cmd")
    if npm and Path(n8n).exists():
        atual = _rodar([str(n8n), "--version"], timeout=60).stdout.strip().splitlines()[-1:] or ["?"]
        nova = _rodar([npm, "view", "n8n", "version"], timeout=60).stdout.strip()
        item = {"nome": "n8n", "tipo": "automação", "atual": atual[0], "nova": nova if nova and nova != atual[0] else None}
        if aplicar and item["nova"]:
            r = _rodar([npm, "install", "-g", "n8n@latest"], timeout=1800)
            item["resultado"] = "atualizado (feche e abra o n8n)" if r.returncode == 0 else f"falhou: {r.stderr[-200:]}"
        itens.append(item)
    from .leva import _claude
    claude = _claude()
    if claude:
        atual = _rodar([claude, "--version"], timeout=60).stdout.strip()
        item = {"nome": "Claude Code", "tipo": "IA", "atual": atual or "?", "nova": "o Claude Code se atualiza sozinho"}
        if aplicar:
            r = _rodar([claude, "update"], timeout=600)
            item["resultado"] = (r.stdout or r.stderr).strip().splitlines()[-1:] or ["ok"]
            item["resultado"] = item["resultado"][0]
        itens.append(item)
    sd = config.MODELOS / "sd" / "sd-cli.exe"
    itens.append({"nome": "stable-diffusion.cpp", "tipo": "desenho no PC", "atual": "instalado" if sd.exists() else "não instalado",
                  "nova": None, "obs": "atualização manual: github.com/leejet/stable-diffusion.cpp/releases"})
    return itens
