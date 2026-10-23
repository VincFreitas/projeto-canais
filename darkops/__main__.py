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
        buscas, idioma, nome = a.busca, a.idioma, a.nome or "avulso"
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
    from .perfis import carregar
    if not carregar().dados.get("youtube", True):
        print("youtube desligado neste perfil: pulando")
        _resultado({"slug": slug, "youtube": None, "pulado": True})
        return
    video_id = ja_publicado(slug, "youtube")
    if video_id:
        print(f"já publicado antes: https://youtu.be/{video_id}")
    else:
        meta = metadados_youtube(roteiro, video)
        if not a.privacidade:
            from .perfis import carregar
            a.privacidade = carregar().dados.get("privacidade_youtube", "private")
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
    from .perfis import carregar
    if not carregar().dados.get("instagram", True):
        print("instagram desligado neste perfil: pulando")
        _resultado({"slug": slug, "instagram": None, "pulado": True})
        return
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
    from .perfis import atual
    caminho = proximo()
    if not caminho:
        _resultado({"perfil": atual(), "vazia": True, "restantes": 0})
        return
    _resultado({"perfil": atual(), "vazia": False, "roteiro": str(caminho), "restantes": restantes()})


def cmd_perfis_ativos(_):
    from .perfis import listar
    _resultado({"perfis": [p.id for p in listar() if p.dados.get("ativo")]})


def cmd_perfis(_):
    from .perfis import listar
    for p in listar():
        d = p.dados
        print(f"{p.id:<24} {d['nome']:<24} {d['arroba']:<20} {'ativo' if d.get('ativo') else 'pausado'}")


def cmd_diagnostico(_):
    from .autoria import versao_cli
    from .instalacao import diagnostico
    print(versao_cli() + "\n")
    faltando = 0
    for item, pronto, fazer in diagnostico():
        print(f"{'OK ' if pronto else 'FALTA'}  {item}" + ("" if pronto else f"\n        -> {fazer}"))
        faltando += not pronto
    print(f"\n{'Tudo pronto.' if not faltando else f'{faltando} item(ns) para configurar.'}")


def cmd_progresso(_):
    from .autoria import versao_cli
    from .plataformas import base, calcular
    print(versao_cli() + "\n")

    def barra(feitas: int, total: int) -> str:
        cheio = round(10 * feitas / total) if total else 0
        return f"[{'#' * cheio}{'.' * (10 - cheio)}] {feitas}/{total}"

    def etapas(lista) -> None:
        for e in lista:
            print(f"    {'OK ' if e.feita else 'FALTA'}  {e.nome}" + ("" if e.feita or not e.como else f"\n           -> {e.como}"))

    comum = base()
    print(f"Base (todas as plataformas)  {barra(sum(e.feita for e in comum), len(comum))}")
    etapas(comum)
    for r in calcular():
        resumo = barra(r.feitas, len(r.etapas)) if r.automatica else "só postagem manual"
        print(f"\n{r.nome}  {resumo}  ({r.situacao})")
        etapas(r.etapas)


def cmd_referencia(a):
    from . import referencia
    from .perfis import carregar
    analises = []
    for url in a.url:
        print(f"analisando: {url}")
        try:
            r = referencia.analisar(url)
        except Exception as erro:  # um link quebrado não derruba os outros
            print(f"  falhou: {erro}")
            continue
        print(f"  {r['titulo']} ({r['canal']}): {r['duracao_s']:.0f}s, {r['formato']}, "
              f"{r['cortes_por_min']} cortes/min, {r['segundos_por_corte']} s por corte, "
              f"{r['palavras_por_min'] or '?'} palavras/min")
        analises.append(r)
    if not analises:
        sys.exit("nenhuma referência pôde ser analisada")
    destino = referencia.salvar(carregar(), analises)
    print(f"proposta: {referencia.proposta(analises)}\nsalvo em {destino}")


def cmd_n8n_workflow(a):
    from .instalacao import gerar_workflow
    gerar_workflow(importar=a.importar)


def cmd_estudio(a):
    from .estudio import rodar
    rodar(porta=a.porta, abrir=not a.sem_navegador)


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
    from .autoria import ROTULO, VERSAO
    p = argparse.ArgumentParser(prog="dark", description=f"Pesquisa e produção de canais dark. {ROTULO}")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSAO}")
    p.add_argument("--perfil", help="id do perfil (pasta em perfis/); padrão: pulga-do-saber")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("perfis", help="lista os perfis")
    s.set_defaults(fn=cmd_perfis)

    s = sub.add_parser("perfis-ativos", help="perfis com postagem ligada (saída JSON para o n8n)")
    s.set_defaults(fn=cmd_perfis_ativos)

    s = sub.add_parser("diagnostico", help="o que está pronto e o que falta configurar")
    s.set_defaults(fn=cmd_diagnostico)

    s = sub.add_parser("referencia", help="mede o estilo de vídeos de referência e propõe o padrão do perfil")
    s.add_argument("url", nargs="+")
    s.set_defaults(fn=cmd_referencia)

    s = sub.add_parser("progresso", help="progresso da configuração de cada plataforma (YouTube, Instagram...)")
    s.set_defaults(fn=cmd_progresso)

    s = sub.add_parser("n8n-workflow", help="gera n8n/workflow.json para esta pasta (e importa com --importar)")
    s.add_argument("--importar", action="store_true")
    s.set_defaults(fn=cmd_n8n_workflow)

    s = sub.add_parser("estudio", help="abre o Estúdio (painel local no navegador)")
    s.add_argument("--porta", type=int, default=8765)
    s.add_argument("--sem-navegador", action="store_true")
    s.set_defaults(fn=cmd_estudio)

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
    s.add_argument("--nome", help="pasta em pesquisa/ para uma busca avulsa (padrão: avulso)")
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
    s.add_argument("--privacidade", default=None, choices=["private", "unlisted", "public"],
                   help="padrão: o configurado no perfil")
    s.set_defaults(fn=cmd_publicar_youtube)

    s = sub.add_parser("conta-instagram", help="confere o token do Instagram")
    s.set_defaults(fn=cmd_conta_instagram)

    s = sub.add_parser("publicar-instagram", help="publica o vídeo vertical de um roteiro como Reel")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_publicar_instagram)

    s = sub.add_parser("fila-proximo", help="próximo roteiro aprovado da fila do perfil (saída JSON para o n8n)")
    s.set_defaults(fn=cmd_fila_proximo)

    s = sub.add_parser("fila-produzir", help="produz um roteiro e devolve o vídeo em JSON")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_fila_produzir)

    s = sub.add_parser("fila-concluir", help="move o roteiro publicado e anota no testes.csv do perfil")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_fila_concluir)

    s = sub.add_parser("registrar-falha", help="anota um erro do workflow em controle/falhas.log")
    s.add_argument("--etapa", required=True)
    s.add_argument("--mensagem", required=True)
    s.set_defaults(fn=cmd_registrar_falha)

    a = p.parse_args()
    if a.perfil:
        import os
        os.environ["DARKOPS_PERFIL"] = a.perfil
    a.fn(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no console do Windows
    main()
