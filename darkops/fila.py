"""Fila de roteiros da postagem automática (orquestrada pelo n8n), por perfil.

perfis/<id>/fila/*.json        próximos vídeos, em ordem alfabética (prefixo 001-, 002-...)
                               só sai o primeiro com "aprovado": true (aprovação no Estúdio)
perfis/<id>/publicados/*.json  já publicados
perfis/<id>/controle/          estado.json (IDs por slug, evita postar duas vezes num retry),
                               testes.csv (uma linha por plataforma) e falhas.log
"""
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from .perfis import Perfil, carregar

PLATAFORMAS = ("youtube", "instagram")
CABECALHO = ("data_publicacao;plataforma;canal;video;url;roteiro;nicho;mecanismo_origem;formato;duracao_s;"
             "impressoes;ctr_pct;views_48h;views_7d;retencao_media_pct;retencao_30s_pct;inscritos_ganhos;"
             "decisao;observacoes")


def _perfil(perfil: Perfil | str | None) -> Perfil:
    return perfil if isinstance(perfil, Perfil) else carregar(perfil)


def ler_estado(perfil=None) -> dict:
    arquivo = _perfil(perfil).controle / "estado.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def _gravar_estado(perfil: Perfil, estado: dict) -> None:
    perfil.controle.mkdir(parents=True, exist_ok=True)
    (perfil.controle / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")


def roteiros(perfil=None) -> list[Path]:
    p = _perfil(perfil)
    p.fila.mkdir(parents=True, exist_ok=True)
    return sorted(p.fila.glob("*.json"))


def aprovado(caminho: Path) -> bool:
    try:
        return bool(json.loads(caminho.read_text(encoding="utf-8")).get("aprovado"))
    except (OSError, json.JSONDecodeError):
        return False


def plataformas_ativas(perfil=None) -> tuple[str, ...]:
    dados = _perfil(perfil).dados
    return tuple(p for p in PLATAFORMAS if dados.get(p, True))


def proximo(perfil=None) -> Path | None:
    """Primeiro roteiro aprovado da fila; nada se o perfil estiver pausado."""
    p = _perfil(perfil)
    if not p.dados.get("ativo"):
        return None
    return next((r for r in roteiros(p) if aprovado(r)), None)


def restantes(perfil=None) -> int:
    return sum(1 for r in roteiros(perfil) if aprovado(r))


def ja_publicado(slug: str, plataforma: str, perfil=None) -> str | None:
    return ler_estado(perfil).get(slug, {}).get(plataforma)


def marcar(slug: str, plataforma: str, midia_id: str, perfil=None) -> None:
    p = _perfil(perfil)
    estado = ler_estado(p)
    estado.setdefault(slug, {})[plataforma] = midia_id
    _gravar_estado(p, estado)


def url(plataforma: str, midia_id: str, perfil=None) -> str:
    if midia_id == "erro":
        return "falhou (ver falhas.log)"  # tentativa registrada: não trava a fila
    if plataforma == "youtube":
        return f"https://youtu.be/{midia_id}"
    arroba = _perfil(perfil).dados.get("arroba", "").lstrip("@")
    return f"https://www.instagram.com/{arroba}/"


def concluir(caminho: Path, roteiro: dict, duracao_s: float | None = None, perfil=None) -> dict:
    """Move o roteiro para publicados/ e anota cada plataforma em testes.csv."""
    p = _perfil(perfil)
    slug = roteiro.get("slug") or caminho.stem
    ids = ler_estado(p).get(slug, {})
    # só contam as plataformas deste vídeo (escolhidas no Novo vídeo) e o Instagram só em vídeo vertical
    alvo = [x for x in plataformas_ativas(p) if x in roteiro.get("plataformas", [x])
            and not (x == "instagram" and roteiro.get("formato", "longo") != "vertical")]
    faltando = [x for x in alvo if not ids.get(x)]
    if faltando:
        raise SystemExit(f"{slug} ainda não foi publicado em: {', '.join(faltando)}")
    testes = p.controle / "testes.csv"
    novo = not testes.exists()
    hoje = datetime.now().strftime("%Y-%m-%d")
    with testes.open("a", encoding="utf-8", newline="") as f:
        if novo:
            f.write(CABECALHO + "\n")
        escritor = csv.writer(f, delimiter=";")
        for plataforma in alvo:
            escritor.writerow([hoje, plataforma, p.dados.get("nome"), roteiro.get("titulo", slug),
                               url(plataforma, ids[plataforma], p), caminho.name, p.dados.get("nicho", ""),
                               "", roteiro.get("formato", "vertical"),
                               f"{duracao_s:.0f}" if duracao_s else ""] + [""] * 9)
    p.publicados.mkdir(parents=True, exist_ok=True)
    destino = p.publicados / caminho.name
    shutil.move(str(caminho), destino)
    return {"perfil": p.id, "slug": slug, "ids": ids, "movido_para": str(destino), "restantes": restantes(p)}


def registrar_falha(etapa: str, mensagem: str, perfil=None) -> None:
    p = _perfil(perfil)
    p.controle.mkdir(parents=True, exist_ok=True)
    with (p.controle / "falhas.log").open("a", encoding="utf-8") as f:
        from .seguranca import ocultar
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} [{etapa}] {ocultar(mensagem.strip())}\n")


def historico(perfil=None) -> list[dict]:
    testes = _perfil(perfil).controle / "testes.csv"
    if not testes.exists():
        return []
    with testes.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def falhas(perfil=None, ultimas: int = 20) -> list[str]:
    arquivo = _perfil(perfil).controle / "falhas.log"
    if not arquivo.exists():
        return []
    return arquivo.read_text(encoding="utf-8").splitlines()[-ultimas:]
