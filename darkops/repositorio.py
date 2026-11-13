# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""O repositório no GitHub, mantido pelo PC do autor (rotina diária "vitrine", junto com os números do canal).

Junta sozinho os pull requests do Dependabot com todos os testes verdes (decisão do dono em 2026-11-13: atualizar é
autônomo). O job juntar-dependabot do testes.yml já junta de lá, mas o GitHub não deixa o robô do Actions mexer em
arquivo de workflow; esses (ações do GitHub novas) chegam aqui, com a conta do autor.

Tudo é feito direto sobre o origin/main, sem tocar na pasta de trabalho: a junção é montada pelo `git merge-tree`, vira
um commit com os dois pais e é enviada. Com conflito ou teste vermelho, nada acontece."""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request

from . import config, sistema
from .seguranca import ocultar

RAMO = "main"
CONCLUSOES_OK = {"success", "skipped", "neutral"}


def git(*args: str, entrada: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", input=entrada, env=env, timeout=300, **sistema.sem_janela())


def repo() -> str:
    """dono/nome do origin no GitHub ("" se não for GitHub)."""
    url = git("remote", "get-url", "origin").stdout.strip()
    achado = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", url)
    return achado.group(1) if achado else ""


def _api(caminho: str):
    pedido = urllib.request.Request(f"https://api.github.com/repos/{repo()}{caminho}",
                                    headers={"User-Agent": "projeto-canais", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.load(r)


def avancar_local(base: str, commit: str) -> None:
    """Se a pasta estava no `base`, avança junto para o `commit` (fast-forward), a menos que alguém esteja editando
    aqui um dos arquivos que mudaram. O resto do trabalho em andamento fica como está."""
    if git("rev-parse", "HEAD").stdout.strip() != base:
        return
    mudaram = git("diff", "--name-only", base, commit).stdout.split()
    if mudaram and git("status", "--porcelain", "--", *mudaram).stdout.strip():
        return
    git("merge", "--ff-only", "--quiet", commit)


def _testes_verdes(sha: str) -> bool:
    execucoes = _api(f"/commits/{sha}/check-runs?per_page=100").get("check_runs", [])
    testes = [r for r in execucoes if r.get("name") != "Juntar a atualização do Dependabot"]
    return bool(testes) and all(r["status"] == "completed" and r.get("conclusion") in CONCLUSOES_OK for r in testes)


def juntar_dependabot() -> tuple[list[str], list[str]]:
    """Junta na main os pull requests abertos do Dependabot com os testes verdes. Devolve (juntados, problemas)."""
    juntados, problemas = [], []
    try:
        abertos = [p for p in _api("/pulls?state=open&per_page=50") if p["user"]["login"] == "dependabot[bot]"]
    except Exception as erro:  # noqa: BLE001 — sem internet ou limite da API: tenta amanhã
        return [], [f"não consegui listar os pull requests ({ocultar(erro)})"]
    for pr in abertos:
        numero, titulo = pr["number"], pr["title"]
        try:
            if not _testes_verdes(pr["head"]["sha"]):
                continue
        except Exception:  # noqa: BLE001
            continue
        local = f"refs/projeto-canais/pr-{numero}"
        git("fetch", "--quiet", "origin", f"+refs/heads/{RAMO}:refs/remotes/origin/{RAMO}",
            f"+refs/pull/{numero}/head:{local}")
        base = git("rev-parse", f"origin/{RAMO}").stdout.strip()
        cabeca = git("rev-parse", local).stdout.strip()
        try:
            if cabeca != pr["head"]["sha"]:
                continue  # o Dependabot refez o pull request no meio: espera os testes do novo
            junta = git("merge-tree", "--write-tree", base, cabeca)
            if junta.returncode != 0:
                problemas.append(f"#{numero} tem conflito com a main; o Dependabot refaz sozinho")
                continue
            arvore = junta.stdout.split()[0]
            if arvore == git("rev-parse", f"{base}^{{tree}}").stdout.strip():
                continue  # a main já tem tudo o que ele traz: o Dependabot fecha o pull request sozinho
            commit = git("commit-tree", arvore, "-p", base, "-p", cabeca, "-m",
                         f"Junta a atualização do Dependabot: {titulo} (#{numero})\n\n"
                         "Testes verdes nos três sistemas e nos três navegadores; juntado pela rotina do PC do autor."
                         ).stdout.strip()
            envio = git("push", "origin", f"{commit}:refs/heads/{RAMO}")
            if envio.returncode != 0:
                problemas.append(f"#{numero}: o GitHub recusou ({ocultar(envio.stderr.strip())[-160:]})")
                continue
            avancar_local(base, commit)
            juntados.append(f"#{numero} {titulo}")
        finally:
            git("update-ref", "-d", local)
    return juntados, problemas
