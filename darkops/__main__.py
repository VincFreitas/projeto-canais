"""CLI: python -m darkops <comando>  (ou .\\dark.ps1 <comando>)."""
import argparse
import json
import sys
from pathlib import Path

from . import config


def cmd_demanda(a):
    from .pesquisa import demanda, pasta_do_dia
    idioma = config.nicho(a.nicho)["idioma"] if a.nicho else a.idioma
    termos = a.termo or config.nicho(a.nicho)["buscas"]
    linhas = []
    for termo in termos:
        print(f"== {termo}")
        resultado = demanda(termo, idioma, expandir=not a.rapido)
        for sugestao, n in resultado[: a.top]:
            print(f"  {n:>3}  {sugestao}")
        linhas += [f"| {termo} | {s} | {n} |" for s, n in resultado[: a.top]]
    pasta = pasta_do_dia(a.nicho or "avulso")
    arquivo = pasta / "demanda.md"
    arquivo.write_text("| termo | sugestão do YouTube | recorrência |\n|---|---|---|\n" + "\n".join(linhas) + "\n",
                       encoding="utf-8")
    print(f"\nsalvo em {arquivo}")


def cmd_outliers(a):
    from .pesquisa import outliers
    if a.nicho:
        n = config.nicho(a.nicho)
        buscas, idioma, nome = a.busca or n["buscas"], n["idioma"], a.nicho
    elif a.busca:
        buscas, idioma, nome = a.busca, a.idioma, "avulso"
    else:
        sys.exit("informe --nicho ou --busca")
    pasta = outliers(nome, buscas, idioma, por_busca=a.por_busca, min_views=a.min_views,
                     top=a.top, detalhar=a.detalhar)
    print((pasta / "outliers.md").read_text(encoding="utf-8"))
    print(f"salvo em {pasta}")


def cmd_transcrever(a):
    from .pesquisa import transcrever
    alvo = Path(a.alvo)
    if alvo.suffix == ".json" and alvo.exists():
        videos = json.loads(alvo.read_text(encoding="utf-8"))[: a.top]
        urls, destino = [v["url"] for v in videos], alvo.parent / "transcricoes"
    else:
        urls, destino = [a.alvo], config.PESQUISA / "avulso" / "transcricoes"
    for url in urls:
        arquivo = transcrever(url, destino, a.idioma)
        if arquivo:
            print(f"  ok: {arquivo}")


def cmd_produzir(a):
    from .producao import produzir
    legenda = False if a.sem_legenda else None
    for roteiro in a.roteiro:
        produzir(Path(roteiro), legenda=legenda)


def cmd_vozes(a):
    from .narracao import listar_vozes
    for v in listar_vozes(a.prefixo):
        print(v)


def cmd_nichos(_):
    for nome, n in config.nichos().items():
        print(f"{nome:<22} [{n['idioma']}] {n['descricao']}")


def main():
    p = argparse.ArgumentParser(prog="dark", description="Pesquisa e produção de canais dark")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("nichos", help="lista os nichos de config/nichos.json")
    s.set_defaults(fn=cmd_nichos)

    s = sub.add_parser("demanda", help="mapa de demanda pelo autocomplete do YouTube")
    s.add_argument("termo", nargs="*")
    s.add_argument("--nicho")
    s.add_argument("--idioma", default="pt")
    s.add_argument("--top", type=int, default=25)
    s.add_argument("--rapido", action="store_true", help="sem expansões a-z")
    s.set_defaults(fn=cmd_demanda)

    s = sub.add_parser("outliers", help="vídeos muito acima da mediana do próprio canal")
    s.add_argument("--nicho")
    s.add_argument("--busca", action="append", help="pode repetir; substitui as buscas do nicho")
    s.add_argument("--idioma", default="pt")
    s.add_argument("--por-busca", type=int, default=30)
    s.add_argument("--min-views", type=int, default=10_000)
    s.add_argument("--top", type=int, default=30)
    s.add_argument("--detalhar", type=int, default=15, help="quantos buscam data e views/dia (lento)")
    s.set_defaults(fn=cmd_outliers)

    s = sub.add_parser("transcrever", help="transcrição de um vídeo ou dos top de um outliers.json")
    s.add_argument("alvo", help="URL do vídeo ou caminho de outliers.json")
    s.add_argument("--top", type=int, default=5)
    s.add_argument("--idioma", default="pt")
    s.set_defaults(fn=cmd_transcrever)

    s = sub.add_parser("produzir", help="gera vídeo, thumbnail e metadados a partir de roteiro(s) JSON")
    s.add_argument("roteiro", nargs="+")
    s.add_argument("--sem-legenda", action="store_true")
    s.set_defaults(fn=cmd_produzir)

    s = sub.add_parser("vozes", help="lista vozes do edge-tts")
    s.add_argument("prefixo", nargs="?", default="pt-BR")
    s.set_defaults(fn=cmd_vozes)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no console do Windows
    main()
