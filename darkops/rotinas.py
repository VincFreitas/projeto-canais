# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Agenda das rotinas automáticas da aplicação (decisão do dono em 2026-11-12).

- integridade: integridade e segurança de tudo (arquivos, segredos, programas, pacotes, falhas conhecidas), todo dia;
- atualizacoes: versões novas de tudo que é de terceiros, todo dia, aplicadas sozinhas com conferência e volta
  automática (terceiros.aplicar; desliga com "atualizar_dependencias_sozinho": false no app.json);
- ferramentas: ferramentas abertas novas que melhorariam o app, toda semana (só sugere; nada é instalado);
- vitrine: os números reais do canal de teste do autor no README e no site, no GitHub, ao ligar o PC e todo dia
  (vitrine.py), e os pull requests do Dependabot com testes verdes juntados na main (repositorio.py); só no PC do autor.

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
    "atualizacoes": {"titulo": "Atualizações de terceiros", "a_cada_h": 24},
    "ferramentas": {"titulo": "Ferramentas novas", "a_cada_h": 24 * 7},
    "vitrine": {"titulo": "GitHub do projeto (números do canal e Dependabot)", "a_cada_h": 24},
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
    return [n for n, r in ROTINAS.items() if aplicavel(n) and agora - estado(n).get("quando_ts", 0) >= r["a_cada_h"] * 3600]


def aplicavel(nome: str) -> bool:
    """A vitrine só existe no PC do autor; as outras rotinas, em todo PC."""
    if nome != "vitrine":
        return True
    from . import vitrine
    try:
        return vitrine.disponivel()
    except Exception:  # noqa: BLE001
        return False


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


def _vencer(nome: str) -> None:
    """Faz a rotina rodar de novo na próxima volta do laço (ex.: integridade depois de trocar pacotes)."""
    dados = estado(nome)
    if dados:
        dados["quando_ts"] = 0
        _arquivo(nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _nuvem_em_dia() -> str:
    """A nuvem recebe o workflow desta versão do app (ações do GitHub novas, por exemplo), só o que mudou."""
    from . import nuvem
    from .perfis import listar
    if not nuvem.configurada() or nuvem.na_nuvem():
        return ""
    try:
        if nuvem.atualizar_workflows([p for p in listar() if p.dados.get("ativo")]):
            return " A nuvem recebeu o workflow novo."
    except Exception as erro:  # noqa: BLE001 — sem internet: tenta amanhã
        return f" A nuvem não recebeu o workflow novo ({ocultar(erro)})."
    return ""


def _troca_do_python() -> str:
    """O que o ajudante que troca o Python (trocar_python.ps1) deixou anotado."""
    arquivo = PASTA / "trocar-python.json"
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    arquivo.unlink(missing_ok=True)
    return f" {dados.get('texto', '')}."


def _atualizacoes() -> dict:
    """Confere tudo de terceiros e aplica sozinha (conferindo o app e desfazendo o que quebrar)."""
    from . import integridade, terceiros
    from .app import ler
    _, falhas = integridade.falhas_python()
    itens = terceiros.verificar(falhas)
    feitos = terceiros.aplicar(itens, automatico=True) if ler().get("atualizar_dependencias_sozinho", True) else []
    atualizados = [i for i in feitos if i.get("atualizado")]
    desfeitos = [i for i in feitos if i.get("desfeito")]
    pendentes = [i for i in itens if i["nova"] and not i.get("atualizado")]
    seg = [i for i in pendentes if i["seguranca"]]
    partes = []
    if atualizados:
        partes.append(f"{len(atualizados)} atualizado(s) sozinho(s)")
    if desfeitos:
        partes.append(f"{len(desfeitos)} voltou(aram) à versão anterior porque quebrava(m) o app")
    if pendentes:
        partes.append(f"{len(pendentes)} pendente(s)" + (f", {len(seg)} de segurança" if seg else ""))
    texto = ("; ".join(partes).capitalize() + ".") if partes else "Tudo de terceiros está na versão mais nova."
    if any(i["id"].startswith("py:") for i in atualizados):
        _vencer("integridade")  # confere de novo as falhas conhecidas, já com os pacotes novos
    r = {"itens": itens, "situacao": "problema" if seg else "aviso" if pendentes or desfeitos else "ok",
         "texto": texto + _nuvem_em_dia() + _troca_do_python()}
    if any(str(i.get("resultado", "")).startswith("fica para depois") for i in feitos):
        r["tentar_em_h"] = 1
    return r


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
            r = _atualizacoes()
        elif nome == "vitrine":
            from . import repositorio, vitrine
            juntados, problemas = repositorio.juntar_dependabot()  # antes: os números entram por cima da main nova
            r = vitrine.atualizar()
            if juntados:
                r["texto"] += f" Dependabot juntado na main: {'; '.join(juntados)}."
            if problemas:
                r["texto"] += f" Dependabot: {'; '.join(problemas)}."
        else:
            from . import ferramentas
            r = ferramentas.buscar()
    except Exception as erro:  # noqa: BLE001 — a rotina nunca derruba quem chamou; o erro vira aviso na tela
        r = {"situacao": "aviso", "texto": f"A rotina falhou: {ocultar(erro)}", "itens": []}
    finally:
        (PASTA / f"{nome}.trava").unlink(missing_ok=True)
    # "tentar_em_h": a rotina ficou para depois (app ocupado) e volta antes do prazo normal
    de_novo_em = r.pop("tentar_em_h", None)
    quando_ts = time.time() - (max(0, ROTINAS[nome]["a_cada_h"] - de_novo_em) * 3600 if de_novo_em else 0)
    r.update({"quando": datetime.now().isoformat(timespec="minutes"), "quando_ts": quando_ts,
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
