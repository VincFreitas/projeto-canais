# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Aprovação automática (decisão do dono em 2026-11-13: "100% automático", no lugar de "nada vai ao ar sem a sua
aprovação"). Com "aprovacao_automatica" ligada no perfil, o vídeo com prévia pronta entra na postagem sozinho se
passar em todas as conferências:

1. conferência técnica do vídeo (conferir.py): nenhum erro (tela preta, sem áudio, passa do limite do Shorts...);
2. revisão visual da IA nos quadros (revisao_visual.py): nota a partir de NOTA_MIN e nenhum erro;
3. roteiro: a auditoria do texto sem erro (auditoria.py); corte de live: streamer com autorização registrada.

O que não passa fica na fila esperando o dono, com o motivo em "aprovacao_automatica" no roteiro (o Início mostra).
O dono continua podendo tirar a aprovação, editar ou recusar qualquer vídeo antes do horário."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import config
from .seguranca import ocultar

NOTA_MIN = 7


def ligada(perfil) -> bool:
    return bool(perfil.dados.get("aprovacao_automatica"))


def _video(dados: dict, caminho: Path) -> Path:
    return config.SAIDA / f"{dados.get('slug') or caminho.stem}-{dados.get('formato', 'vertical')}.mp4"


def _conferencias(perfil, video: Path, duracao_alvo) -> dict:
    """Conferência técnica refeita agora; a revisão visual guardada vale se for desta prévia (senão roda de novo)."""
    from . import conferir
    guardado = conferir.ler(perfil, video.name)
    arquivo = perfil.controle / "conferencias" / f"{video.stem}.json"
    visual = guardado.get("visual") if arquivo.exists() and arquivo.stat().st_mtime >= video.stat().st_mtime - 1 else None
    atual = conferir.conferir(video, duracao_alvo)
    if visual:
        atual["visual"] = visual
    conferir.salvar(atual, perfil)
    return atual


def avaliar(perfil, caminho: Path, revisar: bool = True) -> list[str]:
    """Motivos para NÃO aprovar sozinho ([] = pode aprovar). revisar=False não chama a IA (só usa o que já existe)."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    video = _video(dados, caminho)
    if not video.exists():
        return ["a prévia ainda não foi gerada"]
    if video.stat().st_mtime < caminho.stat().st_mtime - 1:
        return ["o roteiro mudou depois da prévia: falta gerar a prévia de novo"]
    motivos = []
    if dados.get("tipo") == "corte":
        from .cortes import pode_aprovar
        motivo = pode_aprovar(perfil, caminho, dados)
        if motivo:
            motivos.append(motivo)
    else:
        from .auditoria import auditar
        erros = [p for p in auditar(dados, perfil.dados) if p.get("nivel") == "erro"]
        motivos += [f"roteiro: {p['texto']}" for p in erros[:3]]
    alvo = None if dados.get("tipo") == "corte" else perfil.dados.get("duracao_s")
    atual = _conferencias(perfil, video, alvo)
    motivos += [f"vídeo: {a['texto']}" for a in atual.get("achados") or [] if a.get("nivel") == "erro"]
    visual = atual.get("visual")
    if not visual and revisar:
        from . import revisao_visual
        try:
            visual = revisao_visual.revisar(perfil, caminho, video)
        except (SystemExit, OSError, ValueError) as erro:
            motivos.append(f"a revisão visual da IA não rodou ({ocultar(str(erro))[:120]})")
    if visual:
        nota = visual.get("nota")
        if not isinstance(nota, (int, float)) or nota < NOTA_MIN:
            motivos.append(f"revisão visual com nota {nota} (precisa de {NOTA_MIN} ou mais)")
        motivos += [f"imagem: {a['texto']}" for a in visual.get("achados") or [] if a.get("nivel") == "erro"]
    elif not revisar:
        motivos.append("falta a revisão visual da IA")
    return motivos


def aprovar_sozinho(perfil, caminho: Path, revisar: bool = True) -> bool | None:
    """Aprova se a aprovação automática estiver ligada e o vídeo passar em tudo. None = desligada ou já aprovado."""
    if not ligada(perfil) or not caminho.exists():
        return None
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if dados.get("aprovado"):
        return None
    try:
        motivos = avaliar(perfil, caminho, revisar)
    except Exception as erro:  # noqa: BLE001 — na dúvida, espera o dono
        motivos = [f"a conferência não rodou ({ocultar(str(erro))[:120]})"]
    dados = json.loads(caminho.read_text(encoding="utf-8"))  # a autorização de um corte pode ter sido anotada agora
    agora = time.strftime("%Y-%m-%d %H:%M")
    if motivos:
        dados["aprovacao_automatica"] = {"quando": agora, "resultado": "esperando o dono", "motivos": motivos[:6]}
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        _manter_previa(dados, caminho)
        return False
    dados["aprovado"] = True
    dados["aprovacao_automatica"] = {"quando": agora, "resultado": "aprovado sozinho"}
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    _manter_previa(dados, caminho)
    _nuvem(perfil)
    return True


def _manter_previa(dados: dict, caminho: Path) -> None:
    """Gravar o resultado no roteiro não pode deixar a prévia "desatualizada" no Estúdio."""
    video = _video(dados, caminho)
    if video.exists():
        os.utime(video)


def _nuvem(perfil) -> None:
    from . import nuvem
    try:
        if nuvem.configurada() and not nuvem.na_nuvem():
            nuvem.sincronizar(perfil)  # a reserva na nuvem passa a ter este vídeo
    except (SystemExit, OSError) as erro:
        print(ocultar(f"  nuvem: sincroniza depois ({erro})"))


def pendentes(perfil, revisar: bool = True) -> list[tuple[str, bool]]:
    """Passa pela fila: cada vídeo com prévia pronta e ainda sem aprovação é avaliado uma vez por prévia."""
    if not ligada(perfil):
        return []
    from .fila import roteiros
    saida = []
    for caminho in roteiros(perfil):
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        video = _video(dados, caminho)
        if dados.get("aprovado") or not video.exists():
            continue
        feito = (dados.get("aprovacao_automatica") or {}).get("quando")
        if feito and time.mktime(time.strptime(feito, "%Y-%m-%d %H:%M")) >= video.stat().st_mtime - 90:
            continue  # esta prévia já foi avaliada (o resultado está no roteiro)
        r = aprovar_sozinho(perfil, caminho, revisar)
        if r is not None:
            saida.append((caminho.name, r))
    return saida
