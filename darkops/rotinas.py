# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Agenda das rotinas automáticas da aplicação (decisão do dono em 2026-11-12).

- integridade: integridade e segurança de tudo (arquivos, segredos, programas, pacotes, falhas conhecidas), todo dia;
- atualizacoes: versões novas de tudo que é de terceiros, toda semana (só avisa; aplicar é com o clique do dono);
- ferramentas: ferramentas abertas novas que melhorariam o app, toda semana (só sugere; nada é instalado).

Quem dispara: o laço do Estúdio (_vigiar_rotinas, a cada 10 min) e o n8n (`rotinas --vencidas`, de madrugada). Uma
trava impede duas execuções da mesma rotina ao mesmo tempo, e nada roda perto de um horário de postagem. O resultado
de cada uma fica em dados/rotinas/<nome>.json e aparece em Saúde do app."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime

from . import config
from .seguranca import ocultar

PASTA = config.RAIZ / "dados" / "rotinas"
ROTINAS = {
    "integridade": {"titulo": "Integridade e segurança", "a_cada_h": 24},
    "atualizacoes": {"titulo": "Atualizações de terceiros", "a_cada_h": 24 * 7},
    "ferramentas": {"titulo": "Ferramentas novas", "a_cada_h": 24 * 7},
}
TRAVA_MAX_S = 2 * 3600


def _arquivo(nome: str):
    return PASTA / f"{nome}.json"


def estado(nome: str) -> dict:
    try:
        return json.loads(_arquivo(nome).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ligadas() -> bool:
    from .app import ler
    return bool(ler().get("rotinas_ligadas", True))


def vencidas(agora: float | None = None) -> list[str]:
    agora = agora or time.time()
    return [n for n, r in ROTINAS.items() if agora - estado(n).get("quando_ts", 0) >= r["a_cada_h"] * 3600]


def _perto_de_postar() -> bool:
    from .mercados import perto_de_postar
    from .perfis import listar
    try:
        return perto_de_postar([p.dados for p in listar() if p.dados.get("ativo")], antes_min=20, depois_min=50)
    except Exception:  # noqa: BLE001
        return False


def _travar(nome: str) -> bool:
    PASTA.mkdir(parents=True, exist_ok=True)
    trava = PASTA / f"{nome}.trava"
    try:
        if trava.exists() and time.time() - trava.stat().st_mtime < TRAVA_MAX_S:
            return False
        trava.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError:
        return False


def _situacao(itens: list[dict]) -> str:
    s = {i.get("situacao") for i in itens}
    return "problema" if "problema" in s else "aviso" if "aviso" in s else "ok"


def rodar(nome: str) -> dict:
    """Roda uma rotina agora e grava o resultado."""
    if nome not in ROTINAS:
        raise SystemExit(f"rotina desconhecida: {nome} (use {', '.join(ROTINAS)})")
    if not _travar(nome):
        return {"situacao": "aviso", "texto": "Essa rotina já está rodando."}
    inicio = time.time()
    try:
        if nome == "integridade":
            from . import integridade
            r = integridade.verificar()
            r["situacao"] = _situacao(r["itens"])
            problemas = sum(i["situacao"] == "problema" for i in r["itens"])
            avisos = sum(i["situacao"] == "aviso" for i in r["itens"])
            r["texto"] = (f"{problemas} problema(s) e {avisos} aviso(s)." if problemas or avisos
                          else "Tudo certo: arquivos, segredos, programas e pacotes conferidos.")
        elif nome == "atualizacoes":
            from . import integridade, terceiros
            _, falhas = integridade.falhas_python()
            itens = terceiros.verificar(falhas)
            novas = [i for i in itens if i["nova"]]
            seg = [i for i in novas if i["seguranca"]]
            r = {"itens": itens, "situacao": "problema" if seg else "aviso" if novas else "ok",
                 "texto": (f"{len(novas)} atualização(ões), {len(seg)} de segurança." if novas
                           else "Tudo de terceiros está na versão mais nova.")}
        else:
            from . import ferramentas
            r = ferramentas.buscar()
    except Exception as erro:  # noqa: BLE001 — a rotina nunca derruba quem chamou; o erro vira aviso na tela
        r = {"situacao": "aviso", "texto": f"A rotina falhou: {ocultar(erro)}", "itens": []}
    finally:
        (PASTA / f"{nome}.trava").unlink(missing_ok=True)
    r.update({"quando": datetime.now().isoformat(timespec="minutes"), "quando_ts": time.time(),
              "duracao_s": round(time.time() - inicio, 1)})
    _arquivo(nome).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    return r


def rodar_vencidas(forcar_horario: bool = False) -> list[tuple[str, dict]]:
    """Roda as rotinas que passaram do prazo, se as rotinas estão ligadas e não é hora de postar."""
    if not ligadas() or (not forcar_horario and _perto_de_postar()):
        return []
    return [(n, rodar(n)) for n in vencidas()]


def resumo() -> dict:
    """O que a lateral do Estúdio mostra: há problema em alguma rotina?"""
    estados = {n: estado(n) for n in ROTINAS}
    problemas = [ROTINAS[n]["titulo"] for n, e in estados.items() if e.get("situacao") == "problema"]
    return {"problemas": problemas, "estados": estados}
