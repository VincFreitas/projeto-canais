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


def cmd_autorizar_youtube(_):
    from .publicar import autorizar_youtube, canal
    arquivo = autorizar_youtube()
    print(f"token salvo em {arquivo}")
    c = canal()
    print(f"canal autorizado: {c['nome']} ({c['id']})")


def _resultado(dados: dict) -> None:
    """Última linha da saída, lida pelo workflow do n8n."""
    print("RESULTADO " + json.dumps(dados, ensure_ascii=False), flush=True)


def _roteiro_e_video(arquivo: str, formato_exigido: str | None = None):
    from .producao import carregar
    caminho = Path(arquivo).resolve()
    roteiro = carregar(caminho)
    formato = roteiro.get("formato", "longo")
    if formato_exigido and formato != formato_exigido:
        sys.exit(f"precisa de roteiro {formato_exigido}, este é {formato}")
    slug = roteiro.get("slug") or caminho.stem
    video = config.SAIDA / f"{slug}-{formato}.mp4"
    if not video.exists():
        sys.exit(f"vídeo não encontrado: {video} (rode produzir antes)")
    return caminho, roteiro, slug, video


def cmd_publicar_youtube(a):
    from .fila import ja_publicado, marcar
    from .publicar import enviar_youtube, metadados_youtube
    _, roteiro, slug, video = _roteiro_e_video(a.roteiro)
    video_id = ja_publicado(slug, "youtube")
    if video_id:
        print(f"já publicado antes: https://youtu.be/{video_id}")
    else:
        meta = metadados_youtube(roteiro, video)
        print(f"publicando '{meta['titulo']}' ({a.privacidade})")
        video_id = enviar_youtube(video, meta["titulo"], meta["descricao"], meta["tags"],
                                  a.privacidade, bool(roteiro.get("sintetico")))
        marcar(slug, "youtube", video_id)
        print(f"pronto: https://youtu.be/{video_id}")
    _resultado({"slug": slug, "youtube": video_id, "url": f"https://youtu.be/{video_id}"})


def cmd_conta_instagram(_):
    from .instagram import conta
    c = conta()
    print(f"token válido: @{c['username']} ({c['user_id']})")


def cmd_publicar_instagram(a):
    from .fila import ja_publicado, marcar
    from .instagram import legenda_instagram, publicar_reel
    _, roteiro, slug, video = _roteiro_e_video(a.roteiro, "vertical")
    midia_id = ja_publicado(slug, "instagram")
    if midia_id:
        print(f"já publicado antes: mídia {midia_id}")
    else:
        print(f"publicando Reel de {video.name}")
        midia_id = publicar_reel(video, legenda_instagram(roteiro, video))
        marcar(slug, "instagram", midia_id)
        print(f"pronto: mídia {midia_id}")
    _resultado({"slug": slug, "instagram": midia_id})


def cmd_fila_proximo(_):
    from .fila import proximo, restantes
    caminho = proximo()
    if not caminho:
        _resultado({"vazia": True, "restantes": 0})
        return
    _resultado({"vazia": False, "roteiro": str(caminho), "restantes": restantes()})


def cmd_fila_produzir(a):
    from .producao import produzir
    video = produzir(Path(a.roteiro))
    from .render import duracao
    _resultado({"video": str(video), "duracao_s": round(duracao(video), 1)})


def cmd_fila_concluir(a):
    from .fila import concluir
    from .render import duracao
    caminho, roteiro, _, video = _roteiro_e_video(a.roteiro)
    _resultado(concluir(caminho, roteiro, duracao(video)))


def cmd_registrar_falha(a):
    from .fila import registrar_falha
    registrar_falha(a.etapa, a.mensagem)
    _resultado({"registrado": True})


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

    s = sub.add_parser("autorizar-youtube", help="autoriza o canal uma vez pelo navegador e salva o token")
    s.set_defaults(fn=cmd_autorizar_youtube)

    s = sub.add_parser("publicar-youtube", help="envia o vídeo produzido de um roteiro ao YouTube")
    s.add_argument("roteiro")
    s.add_argument("--privacidade", default="private", choices=["private", "unlisted", "public"])
    s.set_defaults(fn=cmd_publicar_youtube)

    s = sub.add_parser("conta-instagram", help="confere o token do Instagram")
    s.set_defaults(fn=cmd_conta_instagram)

    s = sub.add_parser("publicar-instagram", help="publica o vídeo vertical de um roteiro como Reel")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_publicar_instagram)

    s = sub.add_parser("fila-proximo", help="próximo roteiro de roteiros/fila (saída JSON para o n8n)")
    s.set_defaults(fn=cmd_fila_proximo)

    s = sub.add_parser("fila-produzir", help="produz um roteiro e devolve o vídeo em JSON")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_fila_produzir)

    s = sub.add_parser("fila-concluir", help="move o roteiro publicado e anota em controle/testes.csv")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_fila_concluir)

    s = sub.add_parser("registrar-falha", help="anota um erro do workflow em controle/falhas.log")
    s.add_argument("--etapa", required=True)
    s.add_argument("--mensagem", required=True)
    s.set_defaults(fn=cmd_registrar_falha)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no console do Windows
    main()
