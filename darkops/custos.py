"""Quanto a IA custa por vídeo: cada chamada do Claude Code (leva.rodar_claude) anota custo, tokens e tempo.

O Claude Code devolve, com --output-format json, o custo da chamada no preço da API (total_cost_usd). Quem usa um
plano do Claude (Pro ou Max) não paga esse valor: a chamada sai do limite do plano. O número serve para comparar e
para quem roda com chave de API. Fica em dados/custos.jsonl (fora do Git), uma linha por chamada, sem o texto.

REFERENCIA são as médias medidas em 2026-11-11 nas levas reais do projeto (transcrições do Claude Code), para a tela
e o README terem um número antes de o PC ter histórico próprio."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import time

from . import config

ARQUIVO = config.RAIZ / "dados" / "custos.jsonl"

# o que cada vídeo chama na leva; a prancha só em canal com "motor_cena": "prancha", o carrossel só com Instagram
POR_VIDEO = ("roteiro", "descricao", "visual", "carrossel")
EXTRAS = ("prancha",)

# médias por chamada, em dólar no preço da API, medidas em 2026-11-11 (19 roteiros, 21 descrições, 8 revisões
# visuais, 7 carrosséis e 10 pranchas); minutos é o tempo da chamada do Claude, sem a montagem do vídeo
REFERENCIA = {
    "roteiro": {"custo": 1.96, "minutos": 10.3, "modelo": "Opus 5.5"},
    "descricao": {"custo": 0.10, "minutos": 0.4, "modelo": "Haiku 4.5"},
    "visual": {"custo": 0.16, "minutos": 0.4, "modelo": "Sonnet 5"},
    "carrossel": {"custo": 0.11, "minutos": 0.6, "modelo": "Sonnet 5"},
    "prancha": {"custo": 3.25, "minutos": 13.9, "modelo": "Opus 5.5"},
    "data": "2026-11-11",
}


def registrar(proc: subprocess.CompletedProcess, tarefa: str) -> subprocess.CompletedProcess:
    """Lê a resposta JSON do Claude Code, anota o custo e põe em stdout só o texto (o que os chamadores esperam).
    Se a resposta não for JSON (versão antiga do Claude Code), devolve o processo como veio."""
    try:
        dados = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return proc
    if not isinstance(dados, dict) or "result" not in dados:
        return proc
    uso = dados.get("usage") or {}
    linha = {"data": time.strftime("%Y-%m-%d %H:%M"), "tarefa": tarefa or "outra",
             "perfil": os.environ.get("DARKOPS_PERFIL", ""), "custo_usd": round(float(dados.get("total_cost_usd") or 0), 4),
             "tokens": sum(int(uso.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                            "cache_read_input_tokens", "output_tokens")),
             "segundos": round((dados.get("duration_ms") or 0) / 1000), "erro": bool(dados.get("is_error"))}
    try:
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        with ARQUIVO.open("a", encoding="utf-8") as saida:
            saida.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except OSError:
        pass  # anotar o custo nunca derruba a chamada
    return subprocess.CompletedProcess(proc.args, proc.returncode, str(dados.get("result") or ""), proc.stderr)


def _medias() -> dict[str, dict]:
    """Média de custo e tempo por tarefa no histórico deste PC (só chamadas sem erro)."""
    por: dict[str, list[dict]] = {}
    try:
        linhas = ARQUIVO.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for texto in linhas:
        try:
            item = json.loads(texto)
        except ValueError:
            continue
        if not item.get("erro") and item.get("custo_usd"):
            por.setdefault(item.get("tarefa", "outra"), []).append(item)
    return {t: {"custo": statistics.mean(i["custo_usd"] for i in v), "minutos": statistics.mean(i["segundos"] for i in v) / 60,
                "n": len(v)} for t, v in por.items()}


def resumo() -> dict:
    """Custo por vídeo: do histórico deste PC quando há roteiros anotados, senão a referência medida no projeto."""
    medias = _medias()
    proprio = medias.get("roteiro", {}).get("n", 0) >= 3
    base = medias if proprio else REFERENCIA

    def soma(tarefas):
        return round(sum(base.get(t, REFERENCIA.get(t, {})).get("custo", 0) for t in tarefas), 2)

    return {"fonte": "este PC" if proprio else f"medição do projeto em {REFERENCIA['data']}",
            "roteiros": medias.get("roteiro", {}).get("n", 0),
            "por_video": soma(POR_VIDEO), "com_prancha": soma(POR_VIDEO + EXTRAS),
            "por_tarefa": {t: round(base.get(t, REFERENCIA.get(t, {})).get("custo", 0), 2) for t in POR_VIDEO + EXTRAS}}
