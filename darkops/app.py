# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
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
          "atualizar_sozinho": True, "verificar_a_cada_h": 6, "ultima_verificacao": 0,
          "atualizar_dependencias_sozinho": True}


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
    if os.name != "nt":  # Linux: menu de aplicativos do padrão XDG; macOS: pasta Aplicativos do usuário
        menu = Path.home() / "Applications" if sys.platform == "darwin" else \
            Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "applications"
        return {"area_de_trabalho": Path.home() / "Desktop", "menu_iniciar": menu}
    area = _pasta_windows("Desktop") or Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    menu = _pasta_windows("Programs") or Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return {"area_de_trabalho": area, "menu_iniciar": menu}


def _nome_atalho() -> str:
    """Windows: .lnk; macOS: .command (abre com dois cliques no Finder); Linux: .desktop."""
    return NOME + (".lnk" if os.name == "nt" else ".command" if sys.platform == "darwin" else ".desktop")


def _criar_atalho_posix(destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        texto = f'#!/bin/sh\ncd "{config.RAIZ}" && exec "{sys.executable}" -m darkops abrir\n'
    else:
        icone = config.RAIZ / "darkops" / "estudio" / "static" / "icone-192.png"
        texto = (f"[Desktop Entry]\nType=Application\nName={NOME}\nComment=Abre o Projeto Canais\n"
                 f"Exec=sh -c 'cd \"{config.RAIZ}\" && \"{sys.executable}\" -m darkops abrir'\n"
                 f"Icon={icone}\nTerminal=false\nCategories=AudioVideo;Video;\n")
    destino.write_text(texto, encoding="utf-8")
    destino.chmod(0o755)


# Logo da aplicação (decisão do dono em 2026-11-09): a estrela de 4 pontas desenhada com curvas, escura, no
# quadrado amarelo de cantos arredondados. Fonte única: assets/logo.svg, o Estúdio, o site, o README e os ícones
# saem destes números (num quadro de 100 x 100). Nunca use o caractere ✦ da fonte como logo.
LOGO_AMARELO = "#ffc400"
LOGO_ESCURO = "#1d1b18"
LOGO_RAIO = 26
LOGO_ESTRELA = ((50, 14), ((52.5, 36), (64, 47.5), (86, 50)), ((64, 52.5), (52.5, 64), (50, 86)),
                ((47.5, 64), (36, 52.5), (14, 50)), ((36, 47.5), (47.5, 36), (50, 14)))


def logo_caminho() -> str:
    """O "d" do SVG da estrela."""
    inicio, *curvas = LOGO_ESTRELA
    return f"M{inicio[0]} {inicio[1]} " + " ".join(
        "C" + " ".join(f"{x} {y}" for x, y in c) for c in curvas) + " Z"


def logo_svg() -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            f'<rect x="2" y="2" width="96" height="96" rx="{LOGO_RAIO}" fill="{LOGO_AMARELO}"/>'
            f'<path d="{logo_caminho()}" fill="{LOGO_ESCURO}"/></svg>\n')


def logo_imagem(lado: int):
    """A logo em PNG (Pillow), desenhada em 4x e reduzida para as bordas saírem lisas."""
    from PIL import Image, ImageDraw
    grande = lado * 4
    k = grande / 100
    img = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2 * k, 2 * k, 98 * k, 98 * k], radius=int(LOGO_RAIO * k), fill=LOGO_AMARELO)
    pontos, atual = [], LOGO_ESTRELA[0]
    for (c1, c2, fim) in LOGO_ESTRELA[1:]:
        for i in range(1, 41):  # cada curva de Bézier vira 40 pontos
            t = i / 40
            u = 1 - t
            pontos.append(tuple((u ** 3 * atual[j] + 3 * u * u * t * c1[j] + 3 * u * t * t * c2[j] + t ** 3 * fim[j]) * k
                                for j in (0, 1)))
        atual = fim
    d.polygon(pontos, fill=LOGO_ESCURO)
    return img.resize((lado, lado), Image.LANCZOS)


def desenhar_icone(destino: Path = ICONE) -> Path:
    """Ícone da APLICAÇÃO (nunca o de um canal), com a logo de logo_imagem."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    logo_imagem(256).save(destino, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
    return destino


def desenhar_logos() -> list[Path]:
    """Regrava todos os arquivos da logo a partir dos números acima (rode depois de mudar a logo)."""
    raiz = config.RAIZ
    feitos = [desenhar_icone()]
    for caminho in (raiz / "assets" / "logo.svg", raiz / "site" / "img" / "icone.svg",
                    raiz / "darkops" / "estudio" / "static" / "logo.svg"):
        caminho.write_text(logo_svg(), encoding="utf-8")
        feitos.append(caminho)
    for n in (192, 512):
        caminho = raiz / "darkops" / "estudio" / "static" / f"icone-{n}.png"
        logo_imagem(n).save(caminho)
        feitos.append(caminho)
    return feitos


def _icone() -> Path | None:
    """O atalho sempre usa o ícone da aplicação (assets/icone.ico, versionado no Git)."""
    try:
        return ICONE if ICONE.exists() else desenhar_icone()
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
    pastas = _pastas()
    feito = []
    querer = {"area_de_trabalho": area_de_trabalho, "menu_iniciar": menu_iniciar or barra_de_tarefas}
    for onde, ligar in querer.items():
        lnk = pastas[onde] / _nome_atalho()
        if ligar:
            (_criar_lnk if os.name == "nt" else _criar_atalho_posix)(lnk)
            feito.append(f"atalho criado: {lnk}")
        elif lnk.exists():
            lnk.unlink()
            feito.append(f"atalho removido: {lnk}")
    if barra_de_tarefas and os.name == "nt":
        feito.append("barra de tarefas: abra o Menu Iniciar, clique com o botão direito em Projeto Canais e "
                     "escolha Fixar na barra de tarefas (o Windows não deixa programas fazerem isso sozinhos)")
    elif barra_de_tarefas:
        feito.append("Dock ou barra: abra o Projeto Canais pelo menu de aplicativos e fixe por lá")
    salvar({"atalho_area_de_trabalho": area_de_trabalho, "atalho_menu_iniciar": menu_iniciar,
            "atalho_barra_de_tarefas": barra_de_tarefas})
    return feito


def estado_atalhos() -> dict:
    pastas = _pastas()
    return {onde: (p / _nome_atalho()).exists() for onde, p in pastas.items()}


# ---------- abrir ----------

def n8n_ligado() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:5678/healthz", timeout=0.8) as r:
            return r.status == 200
    except OSError:
        return False


LIGANDO_N8N = config.RAIZ / "dados" / "n8n-ligando"


def n8n_ligando() -> bool:
    """O n8n foi mandado ligar há menos de 4 min (ele leva de 1 a 3 min para responder)."""
    return LIGANDO_N8N.exists() and time.time() - LIGANDO_N8N.stat().st_mtime < 240


def atalho_logon_n8n() -> Path:
    """O atalho que n8n/iniciar-com-windows.ps1 põe na pasta Inicializar."""
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / \
        "n8n (Pulga do Saber).lnk"


def ligar_n8n() -> str:
    """Liga o n8n escondido (o mesmo lançador do logon: só em 127.0.0.1, sem abrir o editor).
    Ele continua rodando depois que o Estúdio fecha, para postar às 12h e às 19h."""
    from .instalacao import _n8n_cmd
    if n8n_ligado():
        return "ligado"
    lancador = config.RAIZ / "n8n" / "n8n.ps1"
    n8n = _n8n_cmd()
    if not n8n or (os.name == "nt" and not lancador.exists()):
        return "sem-n8n"
    if n8n_ligando():
        return "ligando"  # já foi mandado ligar: não abre um segundo n8n
    LIGANDO_N8N.parent.mkdir(parents=True, exist_ok=True)
    LIGANDO_N8N.write_text(str(time.time()), encoding="utf-8")
    if os.name != "nt":  # macOS e Linux: o mesmo ambiente do n8n.ps1, numa sessão própria
        from .n8n_lancador import ligar
        ligar(n8n)
        return "ligando"
    atalho = atalho_logon_n8n()
    if atalho.exists():
        # o explorer.exe abre o atalho do logon como o próprio Windows faria: o n8n não fica preso à árvore de
        # processos de quem pediu. Pedido pelo terminal de um agente (ex.: app Claude), ele morreria junto com o app.
        subprocess.Popen(["explorer.exe", str(atalho)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return "ligando"
    # console escondido, não "destacado": sem console nenhum (DETACHED_PROCESS) o PowerShell fecha sem rodar nada
    sinais = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
                      "-File", str(lancador), "-NoOpen"], cwd=lancador.parent, creationflags=sinais,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "ligando"


def reiniciar_n8n() -> str:
    """Fecha e liga o n8n de novo (ele só passa a escutar um workflow importado pela linha de comando depois de
    reiniciar). Não reinicia perto de um horário de postagem, para não cortar uma publicação no meio."""
    if not parar_n8n():
        return "perto-do-horario"
    return ligar_n8n()


def parar_n8n(forcar: bool = False) -> bool:
    """Fecha o n8n (troca de versão, do Node ou reinício). Recusa perto de um horário de postagem, salvo `forcar`
    (desfazer uma atualização que deixou o n8n fora do ar). True quando ele ficou fechado."""
    from .mercados import perto_de_postar
    from .perfis import listar
    # cada canal posta no fuso do seu mercado, não no do Windows
    if not forcar and perto_de_postar([p.dados for p in listar() if p.dados.get("ativo")]
                                      or [{"horarios": ["12:00", "19:00"]}]):
        return False
    if os.name == "nt" and n8n_ligado():
        pids = subprocess.run(["powershell", "-NoProfile", "-Command",
                               "(Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue)"
                               ".OwningProcess"], capture_output=True, text=True).stdout.split()
        for pid in {p for p in pids if p.isdigit()}:
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
    elif n8n_ligado():  # macOS e Linux: quem escuta na porta 5678
        import signal
        from .n8n_lancador import pids_na_porta
        for pid in pids_na_porta():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    for _ in range(20):
        if not n8n_ligado():
            break
        time.sleep(0.5)
    LIGANDO_N8N.unlink(missing_ok=True)
    return not n8n_ligado()


def estudio_aberto(porta: int = 8765) -> bool:
    import socket
    with socket.socket() as teste:
        return teste.connect_ex(("127.0.0.1", porta)) == 0


def abrir() -> None:
    """O que o atalho roda: sem terminal, a saída vai para um arquivo de registro."""
    if sys.stdout is None or sys.stderr is None:  # pythonw não tem console
        registro = config.RAIZ / "dados" / "estudio.log"
        registro.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(registro, "a", encoding="utf-8", buffering=1)
    porta = int(os.environ.get("PORT", 8765))
    if not os.environ.get("DARKOPS_REINICIO") and estudio_aberto(porta):
        # já aberto: vai direto ao painel, sem carregar o Flask nem repetir a abertura animada
        import webbrowser
        ligar_n8n()
        webbrowser.open(f"http://127.0.0.1:{porta}/")
        return
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
    mudou = _git("diff", "--name-only", antes, "HEAD").stdout.split()
    if mudou and all(m == "README.md" or m.startswith(("site/", "docs/")) for m in mudou):
        # só textos (os números diários do canal de teste, por exemplo): nada a instalar nem reiniciar
        return {**info, "atualizado": True, "so_textos": True}
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
    args = dict(cwd=config.RAIZ, env={**os.environ, "DARKOPS_REINICIO": "1"}, close_fds=True)
    if os.name != "nt":  # macOS e Linux: sessão própria, sobrevive ao fim deste processo
        subprocess.Popen([sys.executable, "-m", "darkops", "abrir"], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **args)
        SINAL_REINICIO.unlink(missing_ok=True)
        os._exit(0)
    sinais = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    try:
        # sai do "job" do processo pai (terminal, agendador...), senão o Windows mata o novo junto com o antigo
        subprocess.Popen([str(exe), "-m", "darkops", "abrir"], creationflags=sinais | 0x01000000, **args)
    except OSError:  # o job não permite sair: abre mesmo assim
        subprocess.Popen([str(exe), "-m", "darkops", "abrir"], creationflags=sinais, **args)
    SINAL_REINICIO.unlink(missing_ok=True)
    os._exit(0)


# ---------- dependências ----------

def _rodar(args: list[str], timeout: int = 600, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=env)


def dependencias(aplicar: bool = False) -> list[dict]:
    """Lista (e, com aplicar, atualiza) tudo de terceiros que o projeto usa (terceiros.py)."""
    from . import integridade, terceiros
    _, falhas = integridade.falhas_python()
    itens = terceiros.verificar(falhas)
    if aplicar:
        feitos = {i["id"]: i for i in terceiros.aplicar(itens)}
        itens = [feitos.get(i["id"], i) for i in itens]
    return itens
