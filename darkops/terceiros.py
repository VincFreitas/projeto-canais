# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Rotina de atualizações de tudo o que é de terceiros (toda semana; `python -m darkops atualizar-dependencias`).

Só confere e avisa. Atualizar é sempre com o clique do dono em Saúde do app (ou `--aplicar`), decisão de
2026-11-12: versão nova pode quebrar a produção, e o dono escolhe a hora. Falha de segurança conhecida aparece em
destaque.

Confere: pacotes Python do projeto e do ambiente de voz local, n8n (só dentro da mesma versão principal), HyperFrames
e GSAP, Node.js (dentro da LTS do projeto, com o aviso de versão de segurança do nodejs.org), o Python em si (fim do
suporte pelo endoflife.date), Claude Code, o Chromium do palco (vem com o pacote playwright), o ffmpeg do HyperFrames
(build do BtbN), o desenho no PC (stable-diffusion.cpp) e as ações do GitHub usadas pela nuvem."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import config, sistema
from .seguranca import ocultar


def _json(url: str, timeout: int = 30):
    pedido = urllib.request.Request(url, headers={"User-Agent": "projeto-canais", "Accept": "application/json"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return json.load(r)


def _rodar(args: list, timeout: int = 300, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, **sistema.sem_janela(), **kw)


def _versao_tupla(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def _item(id_, nome, tipo, atual, nova=None, seguranca=False, obs="", aplicavel=True) -> dict:
    return {"id": id_, "nome": nome, "tipo": tipo, "atual": atual or "?", "nova": nova or None,
            "seguranca": bool(seguranca), "obs": ocultar(obs), "aplicavel": bool(aplicavel and nova)}


def _nossos_python() -> list[str]:
    linhas = (config.RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
    nomes = []
    for linha in (l.strip() for l in linhas if l.strip() and not l.startswith("#")):
        if ";" in linha:  # marcador de sistema (ex.: keyring só fora do Windows)
            try:
                from packaging.markers import Marker
                if not Marker(linha.split(";", 1)[1]).evaluate():
                    continue
            except ImportError:
                if 'sys_platform != "win32"' in linha and sys.platform == "win32":
                    continue
        nomes.append(re.split(r"[<>=!~\[ ;]", linha)[0].lower())
    return nomes


def python_pacotes(falhas: dict[str, list[str]] | None = None) -> list[dict]:
    r = _rodar([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    try:
        velhos = {p["name"].lower().replace("_", "-"): p for p in json.loads(r.stdout or "[]")}
    except json.JSONDecodeError:
        velhos = {}
    falhas = {k.replace("_", "-"): v for k, v in (falhas or {}).items()}
    nomes = list(dict.fromkeys(_nossos_python() + (["playwright"] if _instalado("playwright") else [])
                               + sorted(falhas)))
    itens = []
    for nome in nomes:
        chave = nome.replace("_", "-")
        p = velhos.get(chave)
        obs = f"falha conhecida: {', '.join(falhas[chave][:3])}" if chave in falhas else ""
        if nome == "playwright":
            obs = (obs + "; " if obs else "") + "traz o Chromium novo do palco 3D"
        itens.append(_item(f"py:{nome}", nome, "Python", p["version"] if p else _instalado(nome) or "em dia",
                           p["latest_version"] if p else None, chave in falhas, obs))
    return itens


def _instalado(nome: str) -> str | None:
    from importlib import metadata
    try:
        return metadata.version(nome)
    except metadata.PackageNotFoundError:
        return None


def voz_local() -> list[dict]:
    python = sistema.venv_python(config.VOZ_LOCAL) if (config.VOZ_LOCAL / "pyvenv.cfg").exists() else None
    if not python or not python.exists():
        return []
    r = _rodar([python, "-m", "pip", "list", "--outdated", "--format=json"], timeout=300)
    try:
        velhos = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []
    principais = {"kokoro", "faster-whisper", "misaki", "ctranslate2", "onnxruntime", "torch"}
    return [_item(f"voz:{p['name'].lower()}", p["name"], "voz no PC", p["version"], p["latest_version"])
            for p in velhos if p["name"].lower() in principais]


def n8n() -> list[dict]:
    from . import apps
    from .instalacao import _n8n_cmd
    npm, cmd = sistema.npm(), _n8n_cmd() or ""
    if not npm or not cmd or not Path(cmd).exists():
        return []
    env = apps.env_node()
    atual = (_rodar([cmd, "--version"], timeout=60, env=env).stdout.strip().splitlines() or ["?"])[-1]
    faixa = f"n8n@^{atual.split('.')[0]}" if atual[:1].isdigit() else "n8n@latest"
    linhas = _rodar([npm, "view", faixa, "version"], timeout=60, env=env).stdout.strip().splitlines()
    nova = linhas[-1].split()[-1].strip("'") if linhas else ""
    return [_item("n8n", "n8n", "automação", atual, nova if nova and nova != atual else None,
                  obs="só dentro da mesma versão principal: a seguinte pode mudar os nós do workflow")]


def hyperframes() -> list[dict]:
    from .hyperframes import PASTA
    npm = sistema.npm()
    if not npm or not (PASTA / "package.json").exists():
        return []
    from . import apps
    r = _rodar([npm, "outdated", "--json"], cwd=PASTA, env=apps.env_node(), timeout=120)
    try:
        velhos = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        velhos = {}
    itens = []
    for nome in ("hyperframes", "gsap"):
        info = velhos.get(nome) or {}
        atual = info.get("current") or _versao_pacote_npm(PASTA, nome)
        itens.append(_item(f"npm:{nome}", nome, "animação", atual, info.get("latest") if info.get("latest") != atual
                           else None))
    return itens


def _versao_pacote_npm(pasta: Path, nome: str) -> str:
    try:
        return json.loads((pasta / "node_modules" / nome / "package.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "?"


def node() -> list[dict]:
    from . import apps
    exe = apps.node_exe()
    if not exe:
        return []
    atual = _rodar([exe, "--version"], timeout=30).stdout.strip()
    if not atual:
        return []
    maior = atual.lstrip("v").split(".")[0]
    try:
        versoes = _json(f"{apps.NODE_DIST}/index.json")
    except Exception as erro:  # noqa: BLE001
        return [_item("node", "Node.js", "programa", atual, obs=f"não consegui consultar o nodejs.org ({erro})")]
    mesmas = [v for v in versoes if v["version"].lstrip("v").split(".")[0] == maior]
    novas = [v for v in mesmas if _versao_tupla(v["version"]) > _versao_tupla(atual)]
    seg = any(v.get("security") for v in novas)
    obs = "a versão nova corrige falha de segurança" if seg else ""
    fim = _fim_do_suporte("nodejs", maior)
    if fim:
        obs = (obs + "; " if obs else "") + fim
    return [_item("node", "Node.js", "programa", atual, novas[0]["version"] if novas else None, seg, obs,
                  aplicavel=Path(exe).is_relative_to(apps.NODE))]


def _fim_do_suporte(produto: str, ciclo: str) -> str:
    try:
        for c in _json(f"https://endoflife.date/api/{produto}.json"):
            if str(c.get("cycle")) == ciclo and isinstance(c.get("eol"), str):
                fim = dt.date.fromisoformat(c["eol"])
                faltam = (fim - dt.date.today()).days
                if faltam < 0:
                    return f"o suporte da versão {ciclo} acabou em {fim:%d/%m/%Y}"
                if faltam < 180:
                    return f"o suporte da versão {ciclo} acaba em {fim:%d/%m/%Y}"
    except Exception:  # noqa: BLE001 — informação extra, sem rede fica de fora
        pass
    return ""


def python() -> list[dict]:
    atual = ".".join(map(str, sys.version_info[:3]))
    ciclo = ".".join(map(str, sys.version_info[:2]))
    nova = None
    try:
        for c in _json("https://endoflife.date/api/python.json"):
            if c.get("cycle") == ciclo and _versao_tupla(c.get("latest", "0")) > _versao_tupla(atual):
                nova = c["latest"]
    except Exception:  # noqa: BLE001
        pass
    return [_item("python", "Python", "programa", atual, nova, obs=_fim_do_suporte("python", ciclo)
                  or "atualize pelo instalador do python.org (ou do seu sistema)", aplicavel=False)]


def claude_code() -> list[dict]:
    from .leva import _claude
    claude = _claude()
    if not claude:
        return []
    atual = (re.findall(r"\d+\.\d+\.\d+", _rodar([claude, "--version"], timeout=60).stdout) or ["?"])[0]
    try:
        nova = _json("https://registry.npmjs.org/@anthropic-ai/claude-code/latest")["version"]
    except Exception:  # noqa: BLE001
        nova = None
    return [_item("claude", "Claude Code", "IA", atual, nova if nova and _versao_tupla(nova) > _versao_tupla(atual)
                  else None, obs="o Claude Code também se atualiza sozinho")]


def _github_ultima(repo: str) -> dict | None:
    try:
        return _json(f"https://api.github.com/repos/{repo}/releases/latest")
    except Exception:  # noqa: BLE001 — limite de 60 consultas por hora sem login: tenta na próxima semana
        return None


def ffmpeg_hyperframes() -> list[dict]:
    from .hyperframes import PASTA
    exe = PASTA / "bin" / sistema.exe("ffmpeg")
    if not exe.exists():
        return []
    instalado = dt.datetime.fromtimestamp(exe.stat().st_mtime, dt.timezone.utc)
    ultima = _github_ultima("BtbN/FFmpeg-Builds")
    nova = None
    if ultima and ultima.get("published_at"):
        publicado = dt.datetime.fromisoformat(ultima["published_at"].replace("Z", "+00:00"))
        if (publicado - instalado).days > 90:
            nova = f"build de {publicado:%d/%m/%Y}"
    return [_item("ffmpeg-hf", "ffmpeg (HyperFrames)", "programa", f"build de {instalado:%d/%m/%Y}", nova,
                  obs="baixe o ffmpeg e o ffprobe novos em github.com/BtbN/FFmpeg-Builds/releases para "
                      "dados/apps/hyperframes-teste/bin", aplicavel=False)]


def sd_cpp() -> list[dict]:
    pasta = config.MODELOS / "sd"
    if not (pasta / sistema.exe("sd-cli")).exists():
        return []
    marcado = (pasta / "versao.txt").read_text(encoding="utf-8").strip() if (pasta / "versao.txt").exists() else "?"
    ultima = _github_ultima("leejet/stable-diffusion.cpp")
    nova = ultima["tag_name"] if ultima and ultima.get("tag_name") != marcado else None
    return [_item("sd", "stable-diffusion.cpp", "desenho no PC", marcado, nova, aplicavel=False,
                  obs="atualização manual: github.com/leejet/stable-diffusion.cpp/releases (anote a versão em "
                      "modelos/sd/versao.txt)")]


def acoes_github() -> list[dict]:
    """As ações (actions/checkout@v4...) do workflow que a nuvem grava no repositório de fila."""
    try:
        texto = (config.RAIZ / "n8n" / "nuvem.actions.yml").read_text(encoding="utf-8")
    except OSError:
        return []
    itens = []
    for repo, versao in sorted(set(re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@(v\d+)", texto))):
        ultima = _github_ultima(repo)
        if not ultima:
            continue
        maior = (re.findall(r"v\d+", ultima.get("tag_name", "")) or [versao])[0]
        itens.append(_item(f"gh:{repo}", repo, "ação do GitHub (nuvem)", versao,
                           maior if _versao_tupla(maior) > _versao_tupla(versao) else None, aplicavel=False,
                           obs=f"troque {repo}@{versao} em n8n/nuvem.actions.yml e rode nuvem-configurar"))
    return itens


def verificar(falhas_python: dict[str, list[str]] | None = None) -> list[dict]:
    itens = []
    for parte in (lambda: python_pacotes(falhas_python), voz_local, n8n, hyperframes, node, python, claude_code,
                  ffmpeg_hyperframes, sd_cpp, acoes_github):
        try:
            itens += parte()
        except Exception as erro:  # noqa: BLE001 — uma fonte fora do ar não derruba a lista toda
            itens.append(_item(f"erro:{getattr(parte, '__name__', 'parte')}", getattr(parte, "__name__", "?"),
                               "erro", "?", obs=f"não consegui conferir ({erro})", aplicavel=False))
    return itens


# ---------- aplicar (só com o clique do dono) ----------

def aplicar(itens: list[dict], ids: list[str] | None = None) -> list[dict]:
    """Atualiza os itens escolhidos (ou todos os aplicáveis) e devolve cada um com `resultado`."""
    from . import apps, integridade
    escolhidos = [i for i in itens if i["aplicavel"] and (not ids or i["id"] in ids)]
    py = [i["nome"] for i in escolhidos if i["id"].startswith("py:")]
    if py:
        r = _rodar([sys.executable, "-m", "pip", "install", "-q", "--upgrade", *py], timeout=1800)
        _marcar(escolhidos, "py:", r)
        if "playwright" in py and r.returncode == 0:
            env = apps.env_playwright()
            _rodar([sys.executable, "-m", "playwright", "install", "chromium"], timeout=1800, env=env)
    voz = [i["nome"] for i in escolhidos if i["id"].startswith("voz:")]
    if voz:
        r = _rodar([sistema.venv_python(config.VOZ_LOCAL), "-m", "pip", "install", "-q", "--upgrade", *voz],
                   timeout=3600)
        _marcar(escolhidos, "voz:", r)
    npm = sistema.npm()
    for i in escolhidos:
        if i["id"] == "n8n" and npm:
            from .instalacao import _n8n_cmd
            destino = ["--prefix", str(apps.N8N)] if Path(_n8n_cmd() or "").is_relative_to(apps.N8N) else ["-g"]
            r = _rodar([npm, "install", *destino, f"n8n@{i['nova']}", "--no-audit", "--no-fund"], timeout=1800,
                       env=apps.env_node())
            i["resultado"] = "atualizado (feche e abra o n8n)" if r.returncode == 0 else f"falhou: {r.stderr[-200:]}"
        elif i["id"].startswith("npm:") and npm:
            from .hyperframes import PASTA
            r = _rodar([npm, "install", f"{i['nome']}@{i['nova']}", "--no-audit", "--no-fund"], cwd=PASTA,
                       timeout=900, env=apps.env_node())
            i["resultado"] = "atualizado" if r.returncode == 0 else f"falhou: {r.stderr[-200:]}"
        elif i["id"] == "node":
            i["resultado"] = _trocar_node()
        elif i["id"] == "claude":
            from .leva import _claude
            r = _rodar([_claude(), "update"], timeout=600)
            i["resultado"] = ((r.stdout or r.stderr).strip().splitlines() or ["ok"])[-1][:160]
    integridade.registrar_programas()  # a base de SHA-256 passa a ser a dos programas novos
    return escolhidos


def _marcar(itens: list[dict], prefixo: str, r: subprocess.CompletedProcess) -> None:
    for i in itens:
        if i["id"].startswith(prefixo):
            i["resultado"] = "atualizado" if r.returncode == 0 else f"falhou: {ocultar(r.stderr[-200:])}"


def _trocar_node() -> str:
    """Node novo na mesma LTS: guarda o atual ao lado, instala e volta o antigo se der errado."""
    from . import apps
    reserva = apps.NODE.with_name("node-anterior")
    shutil.rmtree(reserva, ignore_errors=True)
    if apps.NODE.exists():
        apps.NODE.rename(reserva)
    try:
        apps.instalar_node()
    except (SystemExit, OSError) as erro:
        shutil.rmtree(apps.NODE, ignore_errors=True)
        if reserva.exists():
            reserva.rename(apps.NODE)
        return f"falhou, o Node anterior continua ({erro})"
    shutil.rmtree(reserva, ignore_errors=True)
    return "atualizado"
