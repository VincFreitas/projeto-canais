# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Lançador do n8n fora do Windows (macOS e Linux). No Windows continua o n8n/n8n.ps1, que faz a mesma coisa.

Mesmo ambiente do n8n.ps1: só em 127.0.0.1, fuso de Brasília nos gatilhos, sem telemetria, nó Execute Command
liberado (o editor só escuta no próprio PC), execuções antigas limpas, módulos sem uso desligados (só os nomes que a
versão instalada conhece) e o cache de módulos do n8n/acelerar.cjs. O n8n sobe numa sessão própria
(start_new_session) e continua rodando depois que o Estúdio fecha, para postar às 12h e às 19h."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from . import config

SEM_USO = ("agents", "agent-evals", "insights", "chat-hub", "mcp", "mcp-discovery", "mcp-registry", "instance-ai",
           "workflow-builder", "quick-connect", "data-table", "inbox", "otel")
LOG = config.RAIZ / "dados" / "n8n.log"


def ambiente(n8n: str) -> dict:
    from . import apps
    env = apps.env_node()
    env.update({"N8N_LISTEN_ADDRESS": "127.0.0.1", "N8N_HOST": "localhost", "N8N_PORT": "5678",
                "N8N_PROTOCOL": "http", "WEBHOOK_URL": "http://localhost:5678/",
                "GENERIC_TIMEZONE": "America/Sao_Paulo", "TZ": "America/Sao_Paulo",
                "N8N_DIAGNOSTICS_ENABLED": "false", "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
                "N8N_PERSONALIZATION_ENABLED": "false", "NODES_EXCLUDE": '["n8n-nodes-base.localFileTrigger"]',
                "PYTHONIOENCODING": "utf-8", "EXECUTIONS_DATA_PRUNE": "true", "EXECUTIONS_DATA_MAX_AGE": "336"})
    modulos = Path(n8n).resolve().parent.parent  # node_modules
    lista = modulos / "@n8n" / "backend-common" / "dist" / "modules" / "modules.config.js"
    if lista.exists():
        conhecidos = set(re.findall(r"'([a-z0-9-]+)'", lista.read_text(encoding="utf-8", errors="ignore")))
        env["N8N_DISABLED_MODULES"] = ",".join(m for m in SEM_USO if m in conhecidos)
    pacote, trava = modulos / "n8n" / "package.json", modulos / ".package-lock.json"
    if pacote.exists() and trava.exists():
        versao = json.loads(pacote.read_text(encoding="utf-8"))["version"]
        chave = f"{versao}-{int(trava.stat().st_mtime)}"
        caches = config.RAIZ / "dados" / "cache"
        caches.mkdir(parents=True, exist_ok=True)
        for velho in caches.glob("n8n-modulos-*.json"):
            if velho.name != f"n8n-modulos-{chave}.json":
                velho.unlink(missing_ok=True)
        env["DARKOPS_CACHE_N8N"] = str(caches / f"n8n-modulos-{chave}.json")
        env["NODE_OPTIONS"] = f'--require "{(config.RAIZ / "n8n" / "acelerar.cjs").as_posix()}"'
    return env


def ligar(n8n: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("ab") as saida:
        subprocess.Popen([n8n, "start"], cwd=config.RAIZ, env=ambiente(n8n), stdin=subprocess.DEVNULL,
                         stdout=saida, stderr=subprocess.STDOUT, start_new_session=True)


def pids_na_porta(porta: int = 5678) -> list[int]:
    """Quem escuta na porta (lsof no macOS e no Linux)."""
    try:
        r = subprocess.run(["lsof", "-ti", f"tcp:{porta}", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    return [int(p) for p in r.stdout.split() if p.isdigit()]
