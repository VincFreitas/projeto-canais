# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Rotina de integridade e segurança da aplicação (todo dia, pelo Estúdio e pelo n8n; `python -m darkops integridade`).

Confere, sem mudar nada:
- arquivos do app: o que mudou em relação à versão do Git (normal para quem mexe no código) e o banco do Git sem
  corrupção;
- segredos: .env, tokens e o JSON do Google fora do Git, nenhuma chave no código versionado, tokens cifrados pelo
  cofre (cofre.py) e, no Linux e no macOS, legíveis só pelo dono;
- programas instalados pelo app (Node, ffmpeg, Chromium, desenho no PC): o SHA-256 de cada executável contra o da
  última conferência. Mudou o arquivo sem mudar a versão, é sinal de arquivo trocado por fora;
- pacotes Python: cada arquivo contra o SHA-256 que o próprio pip gravou no RECORD na instalação;
- falhas conhecidas: OSV.dev (banco aberto de vulnerabilidades) nos pacotes Python e `npm audit` no n8n e no
  HyperFrames;
- o Estúdio aberto recusa Host de fora (DNS rebinding) e POST sem Origin (CSRF);
- créditos de autoria e espaço em disco.

Cada item sai como ok, aviso ou problema, com uma frase. Nenhum valor de segredo aparece na saída: só o arquivo e a
linha."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from importlib import metadata
from pathlib import Path

from . import config, sistema
from .seguranca import ocultar

OK, AVISO, PROBLEMA = "ok", "aviso", "problema"
PASTA = config.RAIZ / "dados" / "rotinas"
BASE_PROGRAMAS = PASTA / "programas.json"
OSV = "https://api.osv.dev/v1"
# formatos de chave e token que nunca podem estar num arquivo versionado
CHAVES = re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}|\bya29\.[A-Za-z0-9._-]{20,}|\b1//0[A-Za-z0-9._-]{20,}|"
                    r"\bEAA[A-Za-z0-9]{30,}|\bIGAA[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|"
                    r"\bAIza[0-9A-Za-z_-]{35}\b|\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{40,}")
SEGREDOS_GIT = (".env", "credenciais/", "token", "client_secret")


def _item(id_: str, titulo: str, situacao: str, texto: str, **extra) -> dict:
    return {"id": id_, "titulo": titulo, "situacao": situacao, "texto": ocultar(texto), **extra}


def _git(*args: str, timeout: int = 120) -> subprocess.CompletedProcess | None:
    git = shutil.which("git")
    if not git or not (config.RAIZ / ".git").exists():
        return None
    return subprocess.run([git, "-C", str(config.RAIZ), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, **sistema.sem_janela())


# ---------- arquivos do app ----------

def arquivos() -> list[dict]:
    estado = _git("status", "--porcelain=v1", "--untracked-files=no")
    if estado is None:
        return [_item("arquivos", "Arquivos do app", AVISO, "Esta pasta não veio pelo Git: não dá para comparar os "
                      "arquivos com a versão oficial. Baixe com git clone para ter essa conferência.")]
    mudados = [linha[3:] for linha in estado.stdout.splitlines() if linha.strip()]
    sumidos = [m for m, linha in zip(mudados, estado.stdout.splitlines()) if linha[:2].strip() == "D"]
    itens = []
    if sumidos:
        itens.append(_item("arquivos", "Arquivos do app", PROBLEMA,
                           f"{len(sumidos)} arquivo(s) do app sumiram, por exemplo {', '.join(sumidos[:3])}. "
                           "Restaure com: git checkout -- <arquivo>."))
    elif mudados:
        itens.append(_item("arquivos", "Arquivos do app", AVISO,
                           f"{len(mudados)} arquivo(s) diferentes da versão do Git ({', '.join(mudados[:3])}"
                           f"{'...' if len(mudados) > 3 else ''}). Normal se você mexeu no código; se não mexeu, "
                           "confira com git diff."))
    else:
        itens.append(_item("arquivos", "Arquivos do app", OK, "Todos os arquivos batem com a versão do Git."))
    fsck = _git("fsck", "--no-progress", "--connectivity-only", timeout=300)
    if fsck is not None and fsck.returncode != 0:
        itens.append(_item("git", "Banco do Git", PROBLEMA, "O Git achou objetos corrompidos: "
                           + (fsck.stderr or fsck.stdout).strip()[:200]))
    return itens


# ---------- segredos ----------

def _rastreados() -> list[str]:
    r = _git("ls-files", "-z")
    return [f for f in (r.stdout.split("\0") if r else []) if f]


def segredos() -> list[dict]:
    itens = []
    rastreados = _rastreados()
    no_git = [f for f in rastreados if f == ".env" or f.startswith("credenciais/") or "/credenciais/" in f
              or (Path(f).name.startswith(("token", "client_secret")) and f.endswith(".json"))]
    if no_git:
        itens.append(_item("segredos-git", "Segredos fora do Git", PROBLEMA,
                           f"Arquivo de segredo versionado: {', '.join(no_git[:5])}. Tire do Git (git rm --cached) "
                           "e troque a chave ou o token, porque o histórico guarda o valor."))
    elif rastreados:
        env = config.RAIZ / ".env"
        ignorado = _git("check-ignore", "-q", ".env")
        if env.exists() and ignorado is not None and ignorado.returncode != 0:
            itens.append(_item("segredos-git", "Segredos fora do Git", PROBLEMA,
                               "O .env não está no .gitignore: um commit pode levar as chaves para o GitHub."))
        else:
            itens.append(_item("segredos-git", "Segredos fora do Git", OK,
                               ".env, tokens e o JSON do Google estão fora do Git."))
    achados = []
    for nome in rastreados:
        arquivo = config.RAIZ / nome
        try:
            if arquivo.stat().st_size > 2_000_000:
                continue
            texto = arquivo.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            if CHAVES.search(linha):
                achados.append(f"{nome}:{n}")
    if achados:
        itens.append(_item("chaves-codigo", "Chaves no código", PROBLEMA,
                           f"Parece haver chave ou token em arquivo versionado: {', '.join(achados[:5])}. Apague, "
                           "troque a chave no serviço e nunca faça push disso."))
    elif rastreados:
        itens.append(_item("chaves-codigo", "Chaves no código", OK, "Nenhuma chave ou token nos arquivos do app."))
    from . import cofre
    em_claro = cofre.em_claro()
    if em_claro:
        itens.append(_item("cofre", "Tokens cifrados", AVISO,
                           f"{len(em_claro)} segredo(s) ainda sem criptografia no disco. O botão Proteger agora "
                           "cifra com a chave do seu usuário no sistema.", acao="proteger"))
    else:
        itens.append(_item("cofre", "Tokens cifrados", OK, "Tokens, chaves do .env e o JSON do Google estão cifrados."))
    if os.name != "nt":
        abertos = [str(a.relative_to(config.RAIZ)) for a in cofre.arquivos_de_segredo()
                   if a.exists() and a.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO)]
        if abertos:
            itens.append(_item("permissoes", "Permissões dos segredos", AVISO,
                               f"Outros usuários deste computador podem ler {', '.join(abertos[:3])}. O botão "
                               "Proteger agora deixa só para você.", acao="proteger"))
    return itens


# ---------- programas instalados pelo app ----------

def _programas() -> dict[str, Path]:
    """Executáveis que o app baixou (fora do pip). Chromium: o do Playwright, numa pasta com a versão no nome."""
    from . import apps
    node = apps.node_exe()
    achados: dict[str, Path | None] = {"node": Path(node) if node else None}
    try:
        from . import hyperframes
        for nome in ("ffmpeg", "ffprobe"):
            achados[f"{nome} (HyperFrames)"] = hyperframes.PASTA / "bin" / sistema.exe(nome)
    except ImportError:
        pass
    achados["desenho no PC (sd.cpp)"] = config.MODELOS / "sd" / sistema.exe("sd-cli")
    for chrome in sorted(apps.PLAYWRIGHT.glob("chromium*/chrome-*/" + sistema.exe("chrome")))[-1:] + \
            sorted(apps.PLAYWRIGHT.glob("chromium_headless_shell*/chrome-*/" + sistema.exe("headless_shell")))[-1:]:
        achados[f"Chromium ({chrome.parts[-3]})"] = chrome
    return {k: v for k, v in achados.items() if v is not None and v.exists()}


def _sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _versao(nome: str, exe: Path) -> str:
    if nome.startswith("Chromium"):
        return exe.parts[-3]  # a pasta tem o número da versão (chromium-1194)
    flag = "-version" if "ffmpeg" in nome or "ffprobe" in nome else "--version"
    try:
        r = subprocess.run([str(exe), flag], capture_output=True, text=True, timeout=30, errors="replace",
                           **sistema.sem_janela())
        return (r.stdout or r.stderr).strip().splitlines()[0][:80] if (r.stdout or r.stderr).strip() else "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def programas(gravar: bool = True) -> list[dict]:
    base = json.loads(BASE_PROGRAMAS.read_text(encoding="utf-8")) if BASE_PROGRAMAS.exists() else {}
    nova, trocados, atualizados = {}, [], []
    for nome, exe in _programas().items():
        soma, versao = _sha256(exe), _versao(nome, exe)
        nova[nome] = {"sha256": soma, "versao": versao, "caminho": str(exe.relative_to(config.RAIZ))
                      if exe.is_relative_to(config.RAIZ) else exe.name}
        antes = base.get(nome)
        if antes and antes["sha256"] != soma:
            (atualizados if antes.get("versao") != versao else trocados).append(nome)
    itens = []
    if os.name == "nt" and "node" in nova:  # Windows: a assinatura digital do Node tem de ser da OpenJS Foundation
        from . import apps
        if "OpenJS Foundation" not in apps.assinatura(Path(apps.node_exe() or "node.exe")):
            itens.append(_item("assinatura-node", "Assinatura do Node.js", PROBLEMA,
                               "O node.exe do app não tem a assinatura da OpenJS Foundation. Apague dados/apps/node "
                               "e rode instalar-apps de novo."))
    if trocados:
        itens.append(_item("programas", "Programas instalados", PROBLEMA,
                           f"{', '.join(trocados)}: o arquivo mudou sem mudar a versão. Pode ser troca por fora do "
                           "app. Apague a pasta do programa em dados/apps e rode instalar-apps de novo."))
        for nome in trocados:  # a base guarda o valor antigo até alguém resolver
            nova[nome] = base[nome]
    else:
        extra = f" Atualizados desde a última conferência: {', '.join(atualizados)}." if atualizados else ""
        itens.append(_item("programas", "Programas instalados", OK,
                           f"{len(nova)} programa(s) conferidos pelo SHA-256.{extra}" if nova else
                           "Nenhum programa baixado pelo app ainda."))
    if gravar and nova:
        PASTA.mkdir(parents=True, exist_ok=True)
        BASE_PROGRAMAS.write_text(json.dumps(nova, ensure_ascii=False, indent=2), encoding="utf-8")
    return itens


def registrar_programas() -> None:
    """Depois que o próprio app instala ou atualiza um programa, a base passa a ser a nova."""
    BASE_PROGRAMAS.unlink(missing_ok=True)
    programas(gravar=True)


# ---------- pacotes Python ----------

def pacotes_python(python: str | None = None) -> list[dict]:
    """Confere cada arquivo dos pacotes instalados contra o SHA-256 do RECORD que o pip gravou na instalação."""
    alterados, sumidos, total = [], [], 0
    for dist in metadata.distributions():
        for arquivo in dist.files or []:
            if not arquivo.hash or arquivo.hash.mode != "sha256":
                continue
            local = Path(str(dist.locate_file(arquivo)))
            total += 1
            try:
                dados = local.read_bytes()
            except FileNotFoundError:
                sumidos.append(dist.metadata["Name"])
                continue
            except OSError:
                continue
            esperado = base64.urlsafe_b64decode(arquivo.hash.value + "=" * (-len(arquivo.hash.value) % 4))
            if hashlib.sha256(dados).digest() != esperado:
                alterados.append(f"{dist.metadata['Name']}/{arquivo}")
    itens = []
    if alterados:
        itens.append(_item("pacotes", "Pacotes Python", PROBLEMA,
                           f"{len(alterados)} arquivo(s) de pacote diferentes do que o pip instalou "
                           f"({', '.join(alterados[:3])}). Reinstale: python -m pip install --force-reinstall "
                           "-r requirements.txt."))
    elif sumidos:
        itens.append(_item("pacotes", "Pacotes Python", AVISO,
                           f"Arquivos faltando em {', '.join(sorted(set(sumidos))[:4])}. Reinstale os pacotes."))
    else:
        itens.append(_item("pacotes", "Pacotes Python", OK, f"{total} arquivos de pacotes conferidos pelo SHA-256."))
    chk = subprocess.run([python or sys.executable, "-m", "pip", "check"], capture_output=True, text=True,
                         timeout=120, errors="replace", **sistema.sem_janela())
    if chk.returncode != 0 and "No broken" not in chk.stdout:
        itens.append(_item("pip-check", "Dependências Python", AVISO,
                           "Pacotes com versão incompatível: " + chk.stdout.strip().splitlines()[0][:160]))
    return itens


def _baixar_json(url: str, corpo: dict | None = None, timeout: int = 60):
    pedido = urllib.request.Request(url, data=json.dumps(corpo).encode() if corpo is not None else None,
                                    headers={"Content-Type": "application/json", "User-Agent": "projeto-canais"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return json.load(r)


def falhas_python() -> tuple[list[dict], dict[str, list[str]]]:
    """Falhas conhecidas (OSV.dev) nas versões instaladas. Devolve os itens e {pacote: [ids]} para atualizações."""
    pacotes = sorted({(d.metadata["Name"].lower(), d.version) for d in metadata.distributions()
                      if d.metadata["Name"]})
    try:
        resposta = _baixar_json(f"{OSV}/querybatch", {"queries": [
            {"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pacotes]})
    except Exception as erro:  # noqa: BLE001 — sem internet: a próxima rotina tenta de novo
        return [_item("falhas-python", "Falhas conhecidas (Python)", AVISO,
                      f"Não consegui consultar o OSV.dev agora ({erro}).")], {}
    por_pacote = {}
    for (nome, _), r in zip(pacotes, resposta.get("results", [])):
        ids = [v["id"] for v in r.get("vulns") or []]
        if ids:
            por_pacote[nome] = ids
    if not por_pacote:
        return [_item("falhas-python", "Falhas conhecidas (Python)", OK,
                      f"{len(pacotes)} pacotes sem falha conhecida no OSV.dev.")], {}
    lista = "; ".join(f"{n} ({', '.join(ids[:2])}{'...' if len(ids) > 2 else ''})" for n, ids in por_pacote.items())
    return [_item("falhas-python", "Falhas conhecidas (Python)", PROBLEMA,
                  f"{len(por_pacote)} pacote(s) com falha conhecida: {lista[:300]}. Atualize em Saúde do app > "
                  "Atualizações.", acao="atualizar")], por_pacote


def falhas_npm() -> list[dict]:
    from . import apps
    try:
        from .hyperframes import PASTA as HF
    except ImportError:
        HF = None
    npm = sistema.npm()
    if not npm:
        return []
    itens = []
    for nome, pasta in (("n8n", apps.N8N), ("HyperFrames", HF)):
        if not pasta or not (pasta / "package-lock.json").exists():
            continue
        try:
            r = subprocess.run([npm, "audit", "--json", "--omit=dev"], cwd=pasta, capture_output=True, text=True,
                               timeout=300, encoding="utf-8", errors="replace", env=apps.env_node(),
                               **sistema.sem_janela())
            meta = json.loads(r.stdout or "{}").get("metadata", {}).get("vulnerabilities", {})
        except (OSError, subprocess.SubprocessError, ValueError) as erro:
            itens.append(_item(f"npm-{nome}", f"Falhas conhecidas ({nome})", AVISO, f"npm audit falhou: {erro}"))
            continue
        graves = meta.get("critical", 0), meta.get("high", 0)
        texto = f"{graves[0]} crítica(s), {graves[1]} alta(s), {meta.get('moderate', 0)} moderada(s)"
        # aviso, nunca problema: são dependências internas do pacote, que só somem na versão nova dele (o n8n escuta
        # só em 127.0.0.1); "problema" deixaria a Saúde do app vermelha para sempre e ninguém olharia mais
        situacao = AVISO if graves[0] or graves[1] else OK
        itens.append(_item(f"npm-{nome}", f"Falhas conhecidas ({nome})", situacao,
                           f"npm audit: {texto}." + (" Atualize o pacote em Atualizações; o que depende do "
                                                      "autor do pacote só some na versão nova." if situacao != OK else "")))
    return itens


# ---------- Estúdio ----------

def estudio(porta: int | None = None) -> list[dict]:
    """Com o Estúdio aberto, testa de verdade as duas travas: Host de fora e POST sem Origin precisam dar 403."""
    porta = porta or int(os.environ.get("PORT", 8765))
    base = f"http://127.0.0.1:{porta}"
    from . import ambiente
    if ambiente.atual() == "servidor":
        return [_item("estudio", "Proteções do Estúdio", PROBLEMA,
                      "DARKOPS_AMBIENTE=servidor está ligado. Esse modo continua bloqueado: tire do .env.")]
    try:
        urllib.request.urlopen(base + "/versao.json", timeout=5).read()
    except Exception:  # noqa: BLE001
        return [_item("estudio", "Proteções do Estúdio", OK, "Estúdio fechado agora; testado na próxima vez.")]
    falhas = []
    for nome, pedido in (("Host de fora", urllib.request.Request(base + "/", headers={"Host": "exemplo.invalid"})),
                         ("POST sem Origin", urllib.request.Request(base + "/configuracoes", data=b"acao=x"))):
        try:
            urllib.request.urlopen(pedido, timeout=10)
            falhas.append(nome)
        except urllib.error.HTTPError as erro:
            if erro.code != 403:
                falhas.append(f"{nome} ({erro.code})")
        except OSError:
            pass
    if falhas:
        return [_item("estudio", "Proteções do Estúdio", PROBLEMA,
                      f"O Estúdio aceitou: {', '.join(falhas)}. Feche o Estúdio e atualize o app.")]
    return [_item("estudio", "Proteções do Estúdio", OK, "Recusa Host de fora e POST sem Origin, como deve.")]


def outros() -> list[dict]:
    from .autoria import creditos_removidos
    itens = []
    faltando = creditos_removidos()
    itens.append(_item("autoria", "Créditos de autoria", AVISO if faltando else OK,
                       f"Faltando: {', '.join(faltando)}." if faltando else "LICENSE, README e cabeçalhos no lugar."))
    livre = shutil.disk_usage(config.RAIZ).free / 1e9
    itens.append(_item("disco", "Espaço em disco", AVISO if livre < 5 else OK,
                       f"{livre:.0f} GB livres" + (": a produção de vídeo pode falhar. Libere espaço ou apague obra/."
                                                    if livre < 5 else ".")))
    return itens


def verificar(rede: bool = True) -> dict:
    itens = arquivos() + segredos() + programas() + pacotes_python()
    if rede:
        falhas, _ = falhas_python()
        itens += falhas + falhas_npm()
    itens += estudio() + outros()
    return {"itens": itens}
