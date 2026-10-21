"""Fila de roteiros da postagem automática (orquestrada pelo n8n).

roteiros/fila/*.json         -> próximos vídeos, em ordem alfabética (use prefixo 001-, 002-...)
roteiros/publicados/*.json   -> já publicados nas duas plataformas
controle/estado.json         -> IDs já publicados por slug (evita postar duas vezes num retry)
controle/testes.csv          -> uma linha por plataforma, para o /revisar-desempenho
controle/falhas.log          -> erros registrados pelo workflow
"""
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from . import config

FILA = config.ROTEIROS / "fila"
PUBLICADOS = config.ROTEIROS / "publicados"
CONTROLE = config.RAIZ / "controle"
ESTADO = CONTROLE / "estado.json"
TESTES = CONTROLE / "testes.csv"
FALHAS = CONTROLE / "falhas.log"
PLATAFORMAS = ("youtube", "instagram")
URLS = {"youtube": "https://youtu.be/{}", "instagram": "https://www.instagram.com/pulgadosaber/"}


def _ler_estado() -> dict:
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}


def _gravar_estado(estado: dict) -> None:
    CONTROLE.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def proximo() -> Path | None:
    FILA.mkdir(parents=True, exist_ok=True)
    return next(iter(sorted(FILA.glob("*.json"))), None)


def restantes() -> int:
    return len(list(FILA.glob("*.json"))) if FILA.exists() else 0


def ja_publicado(slug: str, plataforma: str) -> str | None:
    return _ler_estado().get(slug, {}).get(plataforma)


def marcar(slug: str, plataforma: str, midia_id: str) -> None:
    estado = _ler_estado()
    estado.setdefault(slug, {})[plataforma] = midia_id
    _gravar_estado(estado)


def concluir(caminho: Path, roteiro: dict, duracao_s: float | None = None) -> dict:
    """Move o roteiro para publicados/ e anota cada plataforma em testes.csv."""
    slug = roteiro.get("slug") or caminho.stem
    ids = _ler_estado().get(slug, {})
    faltando = [p for p in PLATAFORMAS if not ids.get(p)]
    if faltando:
        raise SystemExit(f"{slug} ainda não foi publicado em: {', '.join(faltando)}")
    hoje = datetime.now().strftime("%Y-%m-%d")
    with TESTES.open("a", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        for plataforma in PLATAFORMAS:
            escritor.writerow([hoje, plataforma, "Pulga do Saber", roteiro.get("titulo", slug),
                               URLS[plataforma].format(ids[plataforma]), caminho.name, "curiosidades",
                               "", roteiro.get("formato", "vertical"),
                               f"{duracao_s:.0f}" if duracao_s else ""] + [""] * 9)
    PUBLICADOS.mkdir(parents=True, exist_ok=True)
    destino = PUBLICADOS / caminho.name
    shutil.move(str(caminho), destino)
    return {"slug": slug, "ids": ids, "movido_para": str(destino), "restantes": restantes()}


def registrar_falha(etapa: str, mensagem: str) -> None:
    CONTROLE.mkdir(parents=True, exist_ok=True)
    with FALHAS.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} [{etapa}] {mensagem.strip()}\n")
