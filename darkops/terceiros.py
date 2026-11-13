# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Rotina de atualizações de tudo o que é de terceiros (todo dia; `python -m darkops atualizar-dependencias`).

Confere e aplica sozinha (decisão do dono em 2026-11-12, no lugar do "avisa e o dono aplica" do mesmo dia): cada grupo
é atualizado, o app é conferido de verdade (testes, importação de todo o código, imagem, Chromium do palco, uma cena do
HyperFrames, o n8n de pé) e o que quebrar volta para a versão anterior e fica marcado como recusado até sair outra
versão. Nada roda com vídeo sendo feito nem perto de um horário de postagem. Falha de segurança conhecida aparece em
destaque até ser corrigida.

Confere: pacotes Python do projeto e do ambiente de voz local, n8n (só dentro da mesma versão principal), HyperFrames
e GSAP, Node.js (dentro da LTS do projeto, com o aviso de versão de segurança do nodejs.org), o Python em si (fim do
suporte pelo endoflife.date), Claude Code, o Chromium do palco (vem com o pacote playwright), o ffmpeg do HyperFrames
(build do BtbN), o desenho no PC (stable-diffusion.cpp) e as ações do GitHub usadas pela nuvem."""
from __future__ import annotations

import datetime as dt
import json
import os
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


PYTHON_FTP = "https://www.python.org/ftp/python"


def _python_do_site() -> bool:
    """O Python do .venv veio do instalador do python.org só para este usuário (o que dá para trocar sozinho)?"""
    local = os.environ.get("LOCALAPPDATA")
    if not sistema.WINDOWS or not local:
        return False
    return Path(sys.base_prefix).resolve().is_relative_to((Path(local) / "Programs" / "Python").resolve())


def _instalador_python(versao: str) -> str:
    return f"{PYTHON_FTP}/{versao}/python-{versao}-{'arm64' if sistema.arquitetura() == 'arm64' else 'amd64'}.exe"


def _tem_instalador(versao: str) -> bool:
    try:
        pedido = urllib.request.Request(_instalador_python(versao), method="HEAD",
                                        headers={"User-Agent": "projeto-canais"})
        with urllib.request.urlopen(pedido, timeout=20) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def python() -> list[dict]:
    """O Python em si, na mesma versão principal. Na fase só de segurança o python.org solta só o código-fonte: no
    Windows vale a última versão que ainda tem instalador."""
    atual = ".".join(map(str, sys.version_info[:3]))
    ciclo = ".".join(map(str, sys.version_info[:2]))
    nova = None
    try:
        for c in _json("https://endoflife.date/api/python.json"):
            if c.get("cycle") == ciclo and _versao_tupla(c.get("latest", "0")) > _versao_tupla(atual):
                nova = c["latest"]
    except Exception:  # noqa: BLE001
        pass
    obs = _fim_do_suporte("python", ciclo)
    do_site = _python_do_site()
    if nova and do_site:
        maior, menor, patch = _versao_tupla(nova)
        nova = next((f"{maior}.{menor}.{p}" for p in range(patch, sys.version_info[2], -1)
                     if _tem_instalador(f"{maior}.{menor}.{p}")), None)
        obs = (obs + "; " if obs else "") + "o Estúdio fecha por cerca de 1 minuto enquanto o Python é trocado"
    elif nova:
        obs = (obs + "; " if obs else "") + "atualize pelo gerenciador do sistema (Homebrew, apt, python.org)"
    return [_item("python", "Python", "programa", atual, nova, obs=obs, aplicavel=do_site)]


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


def _sd_commit(pasta: Path) -> str:
    """O commit do sd-cli instalado (`sd-cli --version` diz "commit fd21ecf")."""
    try:
        saida = _rodar([pasta / sistema.exe("sd-cli"), "--version"], timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return "?"
    return (re.findall(r"commit\s+([0-9a-f]{7,})", saida) or ["?"])[0][:7]


def _sd_pacote(release: dict, pasta: Path) -> dict | None:
    """O pacote da release com o mesmo motor do instalado (Vulkan, CUDA ou só processador) para este sistema."""
    arquivos = {p.name.lower() for p in pasta.iterdir()} if pasta.exists() else set()
    motor = ("vulkan" if any("ggml-vulkan" in a for a in arquivos) else
             "cuda12" if any("ggml-cuda" in a for a in arquivos) else "cpu")
    if sistema.WINDOWS:
        quer = [f"bin-win-{motor}-x64"]
    elif sistema.MACOS:
        quer = ["darwin", "arm64" if sistema.arquitetura() == "arm64" else "x86_64"]
    else:
        quer = ["linux", "vulkan"] if motor == "vulkan" else ["linux", "x86_64"]
    for a in release.get("assets", []):
        nome = a["name"].lower()
        if nome.endswith(".zip") and nome.startswith("sd-") and all(q in nome for q in quer) and (
                motor == "vulkan" or "vulkan" not in nome) and "rocm" not in nome:
            return a
    return None


def sd_cpp() -> list[dict]:
    pasta = config.MODELOS / "sd"
    if not (pasta / sistema.exe("sd-cli")).exists():
        return []
    atual = _sd_commit(pasta)
    ultima = _github_ultima("leejet/stable-diffusion.cpp")
    nova = ultima["tag_name"] if ultima and atual != "?" and atual not in ultima.get("tag_name", "") else None
    pacote = _sd_pacote(ultima or {}, pasta) if nova else None
    return [_item("sd", "stable-diffusion.cpp", "desenho no PC", f"commit {atual}", nova, aplicavel=bool(pacote),
                  obs="" if pacote or not nova else
                  "sem pacote pronto para este sistema: github.com/leejet/stable-diffusion.cpp/releases")]


def acoes_github() -> list[dict]:
    """As ações (actions/checkout@v4...) do workflow que a nuvem grava no repositório de fila. Quem as troca é a versão
    nova do app (o arquivo é do repositório); a rotina diária leva o workflow novo para a nuvem sozinha."""
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
                           obs="chega com a próxima versão do app, que a nuvem recebe sozinha"))
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


# ---------- aplicar: grupo por grupo, conferindo o app de verdade e desfazendo o que quebrar ----------

RECUSADAS = config.RAIZ / "dados" / "rotinas" / "recusadas.json"
PYTHON_PRONTO = config.RAIZ / "dados" / "apps" / "instaladores" / "python-pronto.json"
# comandos do app que podem rodar junto com a atualização (o resto é vídeo, publicação ou leva: espera)
LIVRES = {"estudio", "abrir", "mcp", "rotinas", "atualizar-dependencias", "integridade", "ferramentas-buscar",
          "diagnostico", "progresso", "vitrine"}

_CONFERIR_PYTHON = r'''
import importlib, io, pkgutil
falhas = []
import darkops
for m in pkgutil.iter_modules(darkops.__path__):
    if m.name == "__main__":
        continue
    try:
        importlib.import_module("darkops." + m.name)
    except Exception as e:
        falhas.append(f"importar darkops.{m.name}: {type(e).__name__}")
try:
    import numpy as np
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, PngImagePlugin
    img = Image.fromarray(np.zeros((64, 96, 3), dtype="uint8"))
    ImageDraw.Draw(img).text((4, 4), "ok", fill=(255, 255, 255), font=ImageFont.load_default(20))
    img = img.filter(ImageFilter.GaussianBlur(2)).filter(ImageFilter.UnsharpMask())
    img = ImageOps.fit(img, (48, 32), Image.LANCZOS).resize((40, 30), Image.Resampling.BICUBIC)
    img = ImageChops.multiply(img, Image.new("RGB", img.size, "white"))
    img.quantize(8, Image.Quantize.MEDIANCUT)
    info = PngImagePlugin.PngInfo()
    info.add_text("Software", "teste")
    img.save(io.BytesIO(), "PNG", pnginfo=info)
    img.save(io.BytesIO(), "JPEG", quality=90, comment=b"teste")
except Exception as e:
    falhas.append(f"imagens: {type(e).__name__}: {e}"[:160])
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        p.chromium.launch().close()
except Exception as e:
    falhas.append(f"Chromium do palco: {type(e).__name__}")
print("\n".join(falhas))
'''


def _ultima_linha(texto: str) -> str:
    linhas = (texto or "").strip().splitlines()
    return ocultar(linhas[-1] if linhas else "?")[:200]


def ocupado() -> str:
    """O comando do app que está fazendo vídeo, publicando ou rodando uma leva agora ("" = livre)."""
    if sistema.WINDOWS:
        r = _rodar(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | "
                    "ForEach-Object { $_.CommandLine }"], timeout=90)
    else:
        r = _rodar(["ps", "-eo", "args"], timeout=30)
    for linha in r.stdout.splitlines():
        achado = re.search(r"-m\s+darkops\s+([\w-]+)", linha)
        if achado and achado.group(1) not in LIVRES:
            return achado.group(1)
    return ""


def recusadas() -> dict:
    try:
        return json.loads(RECUSADAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ok(item: dict, texto: str = "atualizado") -> None:
    item.update(resultado=texto, atualizado=True)
    r = recusadas()
    if r.pop(item["id"], None) is not None:
        RECUSADAS.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


def _desfeito(item: dict, motivo: str) -> None:
    """A versão nova quebrou o app: voltou a anterior, e esta versão não é tentada de novo sozinha."""
    motivo = ocultar(motivo)[:300]
    item.update(resultado=f"voltou para a {item['atual']}: {motivo}", desfeito=True)
    r = recusadas()
    r[item["id"]] = {"versao": item["nova"], "motivo": motivo, "quando": dt.date.today().isoformat()}
    RECUSADAS.parent.mkdir(parents=True, exist_ok=True)
    RECUSADAS.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


def _em_grupo(itens: list[dict], subir, voltar, conferir) -> None:
    """Sobe o grupo inteiro e confere. Se o app quebrar, volta e tenta um por um: fica só o que passa. Só conta o que
    quebrou com a troca (o que já falhava antes não culpa a versão nova)."""
    if not itens:
        return
    antes = set(conferir())

    def tentar(lote):
        erro = subir(lote)
        return [erro] if erro else sorted(set(conferir()) - antes)

    falhas = tentar(itens)
    if not falhas:
        for i in itens:
            _ok(i)
        return
    voltar(itens)
    if len(itens) == 1:
        _desfeito(itens[0], "; ".join(falhas))
        return
    for i in itens:
        falhas = tentar([i])
        if falhas:
            voltar([i])
            _desfeito(i, "; ".join(falhas))
        else:
            _ok(i)


# --- Python (o .venv do app) ---

def _pip(python, *args) -> subprocess.CompletedProcess:
    return _rodar([python, "-m", "pip", "install", "-q", "--disable-pip-version-check", *args], timeout=1800)


def conferir_python() -> list[str]:
    """Num Python novo (com os pacotes recém-instalados): importa todo o código, desenha e grava imagem, abre o
    Chromium do palco, roda os testes e o `pip check`. Devolve o que falhou."""
    from . import apps
    env = {**os.environ, **apps.env_playwright()}
    r = _rodar([sys.executable, "-c", _CONFERIR_PYTHON], timeout=600, cwd=config.RAIZ, env=env)
    falhas = [linha.strip() for linha in r.stdout.splitlines() if linha.strip()]
    if r.returncode != 0:
        falhas.append(f"conferência parou: {_ultima_linha(r.stderr)}")
    if (config.RAIZ / "tests").exists():
        t = _rodar([sys.executable, "-m", "unittest", "discover", "-s", "tests"], timeout=900, cwd=config.RAIZ, env=env)
        if t.returncode != 0:
            falhas += [f"teste {m}" for m in re.findall(r"^(?:FAIL|ERROR): (\S+)", t.stderr, re.M)] or ["testes"]
    c = _rodar([sys.executable, "-m", "pip", "check"], timeout=120)
    if c.returncode != 0:
        falhas += [f"pip check: {linha.strip()[:120]}" for linha in c.stdout.splitlines() if linha.strip()]
    return falhas


def _depois_python(lote: list[dict]) -> None:
    from . import apps
    nomes = {i["nome"] for i in lote}
    if "playwright" in nomes:  # cada versão do playwright usa o seu Chromium
        _rodar([sys.executable, "-m", "playwright", "install", "chromium"], timeout=1800,
               env={**os.environ, **apps.env_playwright()})
    if "imageio-ffmpeg" in nomes:  # a cópia do ffmpeg do projeto ao lado do HyperFrames é refeita no próximo uso
        from .hyperframes import PASTA
        (PASTA / "bin-x264" / sistema.exe("ffmpeg")).unlink(missing_ok=True)


def _aplicar_python(itens: list[dict]) -> None:
    def subir(lote):
        r = _pip(sys.executable, "--upgrade", *[i["nome"] for i in lote])
        _depois_python(lote)
        return "" if r.returncode == 0 else f"pip: {_ultima_linha(r.stderr)}"

    def voltar(lote):
        _pip(sys.executable, *[f"{i['nome']}=={i['atual']}" for i in lote if _versao_tupla(i["atual"])])
        _depois_python(lote)

    _em_grupo(itens, subir, voltar, conferir_python)


def _aplicar_voz(itens: list[dict]) -> None:
    python = sistema.venv_python(config.VOZ_LOCAL)

    def conferir():
        r = _rodar([python, "-c", "import kokoro, faster_whisper"], timeout=600)
        return [] if r.returncode == 0 else [f"voz no PC: {_ultima_linha(r.stderr)}"]

    def subir(lote):
        r = _pip(python, "--upgrade", *[i["nome"] for i in lote])
        return "" if r.returncode == 0 else f"pip: {_ultima_linha(r.stderr)}"

    _em_grupo(itens, subir, lambda lote: _pip(python, *[f"{i['nome']}=={i['atual']}" for i in lote]), conferir)


# --- animação (Node, HyperFrames e GSAP) ---

def conferir_animacao() -> list[str]:
    """Uma cena de 1,5 s pela camada do HyperFrames de verdade (Node, GSAP, Chromium e ffmpeg), num Python novo: este
    processo pode estar com pacotes velhos na memória depois de um `pip install` (o imageio-ffmpeg, por exemplo)."""
    r = _rodar([sys.executable, "-c", "import json; from darkops import terceiros; "
                "print(json.dumps(terceiros._conferir_animacao_aqui()))"], timeout=900, cwd=config.RAIZ)
    try:
        return json.loads((r.stdout.strip().splitlines() or ["?"])[-1])
    except ValueError:
        return [f"conferência da animação parou: {_ultima_linha(r.stderr)}"]


def _conferir_animacao_aqui() -> list[str]:
    import tempfile

    import imageio_ffmpeg

    from . import hyperframes
    if not hyperframes.disponivel():
        return ["HyperFrames incompleto"]
    with tempfile.TemporaryDirectory(prefix="conferir-hf-") as tmp:
        base, saida = Path(tmp) / "base.mp4", Path(tmp) / "saida.mp4"
        _rodar([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "lavfi", "-i", "color=c=0x202020:s=540x960:d=1.5:r=30",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.5", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", base], timeout=120)
        palavras = [{"texto": "conferindo", "inicio": 0.1, "fim": 0.7}, {"texto": "animação.", "inicio": 0.8, "fim": 1.4}]
        try:
            hyperframes.cena(base, palavras, 1.5, 540, 960, 2, saida, semente="conferir")
        except Exception as erro:  # noqa: BLE001
            return [f"cena do HyperFrames: {_ultima_linha(str(erro))}"]
        return [] if saida.exists() and saida.stat().st_size > 1000 else ["cena do HyperFrames sem vídeo"]


def _aplicar_node(item: dict) -> None:
    """Node novo na mesma LTS: o atual fica guardado ao lado e volta se a animação ou o n8n quebrarem."""
    from . import app, apps
    ligado = app.n8n_ligado()
    antes = set(conferir_animacao())  # antes de fechar o n8n: um erro aqui não deixa a postagem sem ele
    if ligado and not app.parar_n8n():  # o n8n roda neste Node: sem fechar, a pasta não pode ser trocada
        item["resultado"] = "fica para depois: perto de um horário de postagem"
        return
    reserva = apps.NODE.with_name("node-anterior")
    shutil.rmtree(reserva, ignore_errors=True)
    try:
        if apps.NODE.exists():
            apps.NODE.rename(reserva)
    except OSError:  # algum programa ainda usa este Node: tenta de novo na próxima rodada, sem recusar a versão
        if ligado:
            app.ligar_n8n()
        item["resultado"] = "fica para depois: o Node está em uso por outro programa"
        return
    falhas = []
    try:
        apps.instalar_node()
        versao = _rodar([apps.node_exe(), "--version"], timeout=30).stdout.strip()
        falhas = [f"node --version deu {versao or 'nada'}"] if versao != item["nova"] else []
        falhas = falhas or sorted(set(conferir_animacao()) - antes)
        if not falhas and ligado:
            app.ligar_n8n()
            falhas = [] if _esperar(app.n8n_ligado, 300) else ["o n8n não voltou a ligar no Node novo"]
    except (SystemExit, OSError, subprocess.SubprocessError) as erro:
        falhas = [str(erro)]
    if falhas:
        if ligado:
            app.parar_n8n(forcar=True)
        if reserva.exists():
            shutil.rmtree(apps.NODE, ignore_errors=True)
            reserva.rename(apps.NODE)
        if ligado:
            app.ligar_n8n()
        _desfeito(item, "; ".join(falhas))
        return
    shutil.rmtree(reserva, ignore_errors=True)
    _ok(item)


def _aplicar_npm(itens: list[dict]) -> None:
    from . import apps
    from .hyperframes import PASTA

    def instalar(lote, campo):
        return _rodar([sistema.npm(), "install", *[f"{i['nome']}@{i[campo]}" for i in lote], "--no-audit", "--no-fund"],
                      cwd=PASTA, timeout=900, env=apps.env_node())

    def subir(lote):
        r = instalar(lote, "nova")
        return "" if r.returncode == 0 else f"npm: {_ultima_linha(r.stderr)}"

    _em_grupo(itens, subir, lambda lote: instalar(lote, "atual"), conferir_animacao)


def _esperar(condicao, segundos: int) -> bool:
    import time
    fim = time.time() + segundos
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(3)
    return False


# --- n8n, Claude Code e desenho no PC ---

def _aplicar_n8n(item: dict) -> None:
    from . import app, apps
    from .instalacao import _n8n_cmd
    ligado = app.n8n_ligado()
    if ligado and not app.parar_n8n():
        item["resultado"] = "fica para depois: perto de um horário de postagem"
        return
    destino = ["--prefix", str(apps.N8N)] if Path(_n8n_cmd() or "").is_relative_to(apps.N8N) else ["-g"]

    def instalar(versao):
        return _rodar([sistema.npm(), "install", *destino, f"n8n@{versao}", "--no-audit", "--no-fund"], timeout=1800,
                      env=apps.env_node())

    r = instalar(item["nova"])
    falhas = [f"npm: {_ultima_linha(r.stderr)}"] if r.returncode else []
    if not falhas:
        versao = (_rodar([_n8n_cmd(), "--version"], timeout=180, env=apps.env_node()).stdout.strip().splitlines()
                  or [""])[-1]
        falhas = [] if versao == item["nova"] else [f"n8n --version deu {versao or 'nada'}"]
    if not falhas and ligado:
        app.ligar_n8n()
        falhas = [] if _esperar(app.n8n_ligado, 300) else ["o n8n não voltou a ligar em 5 minutos"]
    if falhas:
        if ligado:
            app.parar_n8n(forcar=True)
        instalar(item["atual"])
        if ligado:
            app.ligar_n8n()
        _desfeito(item, "; ".join(falhas))
    else:
        _ok(item)


def _aplicar_claude(item: dict) -> None:
    from .leva import _claude
    r = _rodar([_claude(), "update"], timeout=600)
    v = _rodar([_claude(), "--version"], timeout=60)
    if v.returncode == 0:
        _ok(item, f"atualizado ({_ultima_linha(v.stdout)})")
    else:
        item["resultado"] = f"falhou: {_ultima_linha(r.stderr or r.stdout)}"


def _aplicar_sd(item: dict) -> None:
    """Pacote oficial da release (mesmo motor do instalado), conferido pelo SHA-256 que o GitHub publica; o anterior
    fica guardado ao lado e volta se o novo não abrir."""
    import hashlib
    import zipfile
    from . import apps
    pasta = config.MODELOS / "sd"
    pacote = _sd_pacote(_github_ultima("leejet/stable-diffusion.cpp") or {}, pasta)
    if not pacote:
        item["resultado"] = "sem pacote pronto para este sistema"
        return
    nova, reserva = pasta.with_name("sd-nova"), pasta.with_name("sd-anterior")
    shutil.rmtree(nova, ignore_errors=True)
    shutil.rmtree(reserva, ignore_errors=True)
    try:
        zipado = apps._baixar(pacote["browser_download_url"], nova / pacote["name"])
        soma = (pacote.get("digest") or "").removeprefix("sha256:")
        if soma and hashlib.sha256(zipado.read_bytes()).hexdigest() != soma:
            raise OSError("o pacote baixado não confere com o SHA-256 publicado no GitHub")
        with zipfile.ZipFile(zipado) as z:
            for nome in z.namelist():  # nada de caminho para fora da pasta
                if not (nova / nome).resolve().is_relative_to(nova.resolve()):
                    raise OSError(f"caminho estranho no pacote: {nome}")
            z.extractall(nova)
        zipado.unlink()
        exe = next(nova.rglob(sistema.exe("sd-cli")), None)
        if not exe:
            raise OSError("o pacote não tem o sd-cli")
        if not sistema.WINDOWS:
            for arquivo in exe.parent.iterdir():
                arquivo.chmod(arquivo.stat().st_mode | 0o111)
        if _sd_commit(exe.parent) == "?":
            raise OSError("o sd-cli novo não abriu")
        pasta.rename(reserva)
        exe.parent.rename(pasta)
    except (OSError, ValueError, zipfile.BadZipFile) as erro:
        if reserva.exists() and not pasta.exists():
            reserva.rename(pasta)
        shutil.rmtree(nova, ignore_errors=True)
        _desfeito(item, str(erro))
        return
    shutil.rmtree(nova, ignore_errors=True)
    shutil.rmtree(reserva, ignore_errors=True)
    _ok(item, f"atualizado (commit {_sd_commit(pasta)})")


# --- o Python em si (Windows, instalador do python.org só deste usuário) ---

def _preparar_python(item: dict) -> None:
    """Baixa o instalador e confere a assinatura. A troca fica com `trocar_python.ps1`, que o Estúdio dispara quando
    está livre: espera o Estúdio fechar, instala só se nenhum outro programa estiver usando este Python e abre o
    Estúdio de novo."""
    from . import apps
    destino = PYTHON_PRONTO.parent / Path(_instalador_python(item["nova"])).name
    try:
        if not destino.exists():
            apps._baixar(_instalador_python(item["nova"]), destino)
        if "Python Software Foundation" not in apps.assinatura(destino) or not apps.assinatura(destino).startswith(
                "Valid"):
            destino.unlink(missing_ok=True)
            raise OSError("o instalador baixado não tem a assinatura válida da Python Software Foundation")
    except OSError as erro:
        item["resultado"] = f"falhou: {ocultar(erro)}"
        return
    PYTHON_PRONTO.write_text(json.dumps({"versao": item["nova"], "de": item["atual"], "instalador": str(destino)},
                                        ensure_ascii=False), encoding="utf-8")
    item["resultado"] = "pronto: o Estúdio fecha por cerca de 1 minuto para trocar o Python quando estiver livre"


def trocar_python_agora() -> bool:
    """Chamado pelo Estúdio livre: dispara o ajudante que troca o Python e devolve True (o Estúdio então fecha)."""
    try:
        pronto = json.loads(PYTHON_PRONTO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not sistema.WINDOWS or not Path(pronto.get("instalador", "")).exists():
        PYTHON_PRONTO.unlink(missing_ok=True)
        return False
    PYTHON_PRONTO.unlink(missing_ok=True)
    ajudante = config.RAIZ / "darkops" / "trocar_python.ps1"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File",
                      str(ajudante), "-Esperar", str(os.getpid()), "-Instalador", pronto["instalador"],
                      "-Base", sys.base_prefix, "-Raiz", str(config.RAIZ),
                      "-Pythonw", str(pythonw if pythonw.exists() else sys.executable)],
                     cwd=config.RAIZ, close_fds=True,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | 0x01000000)
    return True


# --- tudo junto ---

def aplicar(itens: list[dict], ids: list[str] | None = None, automatico: bool = False) -> list[dict]:
    """Atualiza os itens escolhidos (ou todos os aplicáveis), grupo por grupo, conferindo o app depois de cada um e
    desfazendo o que quebrar. No automático pula a versão que já foi recusada (quebrou antes) e não mexe em nada se o
    app estiver ocupado. Devolve cada item tocado, com `resultado`."""
    from . import integridade
    from . import app
    ja_recusadas = recusadas() if automatico else {}
    escolhidos = [i for i in itens if i["aplicavel"] and (not ids or i["id"] in ids)
                  and ja_recusadas.get(i["id"], {}).get("versao") != i["nova"]]
    if not escolhidos:
        return []
    quem = ocupado()
    if quem:
        for i in escolhidos:
            i["resultado"] = f"fica para depois: o app está rodando `{quem}` agora"
        return escolhidos
    por_id = lambda prefixo: [i for i in escolhidos if i["id"].startswith(prefixo)]  # noqa: E731
    etapas = [(por_id("py:"), _aplicar_python), (por_id("voz:"), _aplicar_voz),
              (por_id("node"), lambda lote: _aplicar_node(lote[0])), (por_id("npm:"), _aplicar_npm),
              (por_id("n8n"), lambda lote: _aplicar_n8n(lote[0])), (por_id("claude"), lambda lote: _aplicar_claude(lote[0])),
              (por_id("sd"), lambda lote: _aplicar_sd(lote[0])), (por_id("python"), lambda lote: _preparar_python(lote[0]))]
    n8n_antes = app.n8n_ligado()
    for lote, fazer in etapas:
        if not lote:
            continue
        try:
            fazer(lote)
        except Exception as erro:  # noqa: BLE001 — um grupo com erro não impede os outros
            for i in lote:
                i.setdefault("resultado", f"falhou: {ocultar(erro)}"[:240])
    if n8n_antes and not app.n8n_ligado():  # nenhum erro no meio deixa a postagem sem o n8n
        app.ligar_n8n()
        _esperar(app.n8n_ligado, 300)
    integridade.registrar_programas()  # a base de SHA-256 passa a ser a dos programas novos
    if any(i.get("atualizado") for i in escolhidos if i["id"].startswith("py:")):
        from .app import SINAL_REINICIO
        SINAL_REINICIO.parent.mkdir(parents=True, exist_ok=True)
        SINAL_REINICIO.write_text("dependencias", encoding="utf-8")  # o Estúdio reabre com os pacotes novos
    return escolhidos
