"""CLI: python -m darkops <comando>  (ou .\\dark.ps1 <comando>)."""
import argparse
import json
import os
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


def cmd_comparar_vozes(a):
    from .comparar_vozes import TEXTO, comparar
    for r in comparar(a.texto or TEXTO):
        print(f"{r['motor']:<11} " + (f"{r['arquivo']} ({r['segundos_para_gerar']} s)" if "arquivo" in r
                                      else f"pulado: {r['pulado']}"))


def cmd_vozes_amostras(a):
    from . import vozes
    if getattr(a, "minha_voz", False):
        print(f"sua voz {a.mercado or 'pt-BR'}: {vozes.gerar_minha_amostra(a.mercado or 'pt-BR')['situacao']}")
        return
    if a.motor:
        r = vozes.gerar_paga(a.motor, a.mercado or "pt-BR")
        print(f"{a.motor} {a.mercado}: {r['situacao']}, {r['vozes']} amostras")
        for f in r["falhas"]:
            print(f"  {f}")
        return
    r = vozes.gerar_gratis([a.mercado] if a.mercado else None, a.refazer)
    print(f"{r['geradas']} amostras novas em {vozes.GRATIS.relative_to(vozes.config.RAIZ)}")
    for f in r["falhas"]:
        print(f"  falhou: {f}")


def cmd_efeitos_baixar(a):
    from .efeitos import PASTA, baixar
    for tipo, n in baixar(a.por_tipo).items():
        print(f"{tipo:<8} {n} som(ns) CC0")
    print(f"banco em {PASTA} (licenças em licencas.csv)")


def cmd_autorizar_youtube(a):
    from .publicar import autorizar_youtube, canal
    arquivo = autorizar_youtube(analytics=getattr(a, "analytics", False), comentarios=getattr(a, "comentarios", False))
    print(f"token salvo em {arquivo}")
    from .perfis import carregar
    c = canal()
    print(f"canal autorizado: {c['nome']} ({c['id']})")
    if c["nome"].strip().lower() != str(carregar().dados.get("nome", "")).strip().lower():
        print(f"aviso: o canal se chama \"{c['nome']}\" e o perfil, \"{carregar().dados.get('nome')}\". Se não for o canal "
              "certo, conecte de novo e escolha o canal deste perfil.")


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


def _vai_para(roteiro: dict, plataforma: str) -> bool:
    """O vídeo escolheu as plataformas no Novo vídeo? Sem a lista (roteiros antigos), vale o perfil."""
    return plataforma in roteiro["plataformas"] if "plataformas" in roteiro else True


def cmd_publicar_youtube(a):
    from .fila import ja_publicado, marcar
    from .publicar import enviar_youtube, metadados_youtube
    _, roteiro, slug, video = _roteiro_e_video(a.roteiro)
    from .perfis import carregar
    if not carregar().dados.get("youtube", True) or not _vai_para(roteiro, "youtube"):
        print("youtube desligado neste perfil ou fora das plataformas deste vídeo: pulando")
        _resultado({"slug": slug, "youtube": None, "pulado": True})
        return
    video_id = ja_publicado(slug, "youtube")
    if video_id:
        print(f"já publicado antes: https://youtu.be/{video_id}")
    else:
        from .descricao import para_publicar
        meta = metadados_youtube(roteiro, video, para_publicar(carregar(), Path(a.roteiro).resolve()))
        if not a.privacidade:
            from .perfis import carregar
            a.privacidade = carregar().dados.get("privacidade_youtube", "private")
        from . import nuvem
        if nuvem.simulando():
            print(f"[simulação] publicaria no YouTube: '{meta['titulo']}' ({a.privacidade})")
            _resultado({"slug": slug, "youtube": None, "simulado": True})
            return
        # na nuvem, segunda trava: o PC pode ter postado sem conseguir avisar a fila
        video_id = nuvem.ja_no_youtube(meta["titulo"]) if nuvem.na_nuvem() else None
        if video_id:
            print(f"já está no canal (postado pelo PC): https://youtu.be/{video_id}")
        else:
            print(f"publicando '{meta['titulo']}' ({a.privacidade})")
            from .mercados import de as mercado_de
            # o roteiro escrito para um mercado vale mais que o perfil (o canal pode ter trocado de região depois)
            idioma = mercado_de({**carregar().dados, **{k: roteiro[k] for k in ("mercado",) if k in roteiro}})["youtube"]
            from .visuais import ESTILOS_SINTETICOS
            # imagem realista de IA (estilo do roteiro ou do canal) marca "conteúdo alterado ou sintético" sozinha
            estilo = roteiro.get("estilo") or carregar().dados.get("estilo")
            sintetico = bool(roteiro.get("sintetico")) or estilo in ESTILOS_SINTETICOS
            video_id = enviar_youtube(video, meta["titulo"], meta["descricao"], meta["tags"],
                                      a.privacidade, sintetico, idioma)
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
    from .perfis import carregar
    from .producao import carregar as carregar_roteiro
    previo = carregar_roteiro(Path(a.roteiro).resolve())
    # vídeo longo ou sem o Instagram na lista: pula sem erro (antes de exigir o vertical)
    if not carregar().dados.get("instagram", True) or not _vai_para(previo, "instagram")             or previo.get("formato", "longo") != "vertical":
        print("instagram desligado, fora das plataformas deste vídeo ou vídeo longo: pulando")
        _resultado({"slug": previo.get("slug") or Path(a.roteiro).stem, "instagram": None, "pulado": True})
        return
    _, roteiro, slug, video = _roteiro_e_video(a.roteiro, "vertical")
    midia_id = ja_publicado(slug, "instagram")
    if midia_id:
        print(f"já publicado antes: mídia {midia_id}")
    else:
        from . import nuvem
        from .descricao import para_publicar
        legenda = legenda_instagram(roteiro, video, para_publicar(carregar(), Path(a.roteiro).resolve()))
        if nuvem.simulando():
            print(f"[simulação] publicaria o Reel {video.name}: {legenda.splitlines()[0] if legenda else ''}")
            _resultado({"slug": slug, "instagram": None, "simulado": True})
            return
        midia_id = nuvem.ja_no_instagram(legenda) if nuvem.na_nuvem() else None
        if midia_id:
            print(f"já está no perfil (postado pelo PC): mídia {midia_id}")
        else:
            print(f"publicando Reel de {video.name}")
            try:
                midia_id = publicar_reel(video, legenda)
            except (SystemExit, OSError, ValueError) as erro:
                # o Instagram não segura a fila: o vídeo segue no YouTube e o próximo horário recebe o próximo vídeo
                from .fila import registrar_falha
                from .seguranca import ocultar
                registrar_falha("Publicar no Instagram", ocultar(str(erro)))
                marcar(slug, "instagram", "erro")
                from . import whatsapp
                whatsapp.falhou(carregar(), "Publicar no Instagram", str(erro))
                print(f"o Instagram falhou ({ocultar(str(erro))}); registrado em falhas.log, a fila continua")
                _resultado({"slug": slug, "instagram": None, "erro": True})
                return
        marcar(slug, "instagram", midia_id)
        print(f"pronto: mídia {midia_id}")
    _resultado({"slug": slug, "instagram": midia_id})


def cmd_fila_proximo(_):
    from . import nuvem
    from .fila import proximo, restantes
    from .perfis import atual, carregar
    perfil = carregar()
    if nuvem.configurada() and not nuvem.na_nuvem():
        try:
            nuvem.sincronizar(perfil, enviar_videos=False)  # pega o que a nuvem postou enquanto o PC estava desligado
        except (SystemExit, OSError) as erro:
            print(f"aviso: sem contato com a nuvem agora ({erro}); seguindo só com o PC")
    quem = nuvem.slot_atendido(perfil)
    if quem:
        print(f"este horário já foi atendido ({quem}): nada a postar")
        _resultado({"perfil": atual(), "vazia": True, "restantes": restantes(), "atendido_por": quem})
        return
    caminho = proximo()
    if not caminho:
        _resultado({"perfil": atual(), "vazia": True, "restantes": 0})
        return
    _resultado({"perfil": atual(), "vazia": False, "roteiro": str(caminho), "restantes": restantes()})


def cmd_perfis_ativos(a):
    """Perfis com postagem ligada. Com --na-hora (gatilho de 30 em 30 minutos do n8n, ou a agenda da nuvem), só os
    que acabaram de chegar a um horário de postagem no fuso do seu mercado (12:00 em Nova York, 12:00 em Lisboa...)."""
    from .mercados import slot_na_hora
    from .nuvem import JANELA_SLOT_H
    from .perfis import listar
    na_hora = a.na_hora or os.environ.get("DARKOPS_NA_HORA") == "1"
    # no PC o gatilho é exato (30 min); a agenda do GitHub Actions pode atrasar, então a nuvem aceita a janela toda
    janela = 30 if a.na_hora else JANELA_SLOT_H * 60
    _resultado({"perfis": [p.id for p in listar() if p.dados.get("ativo")
                           and (not na_hora or slot_na_hora(p.dados, janela_min=janela))]})


def cmd_mercados(_):
    from .mercados import MERCADOS
    for cod, m in MERCADOS.items():
        print(f"{cod:<7} {m['nome']:<36} voz {m['vozes'][0]:<34} horário de {m['cidade']}")


def cmd_tendencias(args):
    from .perfis import carregar
    from .tendencias import em_alta
    for a in em_alta(carregar(args.perfil).dados if args.perfil else {"mercado": args.mercado}, args.quantidade):
        print(f"{a['assunto']} ({a['buscas']} buscas)")
        for m in a["materias"][:3]:
            print(f"   · {m['titulo'][:110]} ({m['veiculo']})")


def cmd_perfis(_):
    from .perfis import listar
    for p in listar():
        d = p.dados
        print(f"{p.id:<24} {d['nome']:<24} {d['arroba']:<20} {'ativo' if d.get('ativo') else 'pausado'}")


def cmd_diagnostico(a):
    from .autoria import versao_cli
    from .instalacao import diagnostico
    if a.json:  # para agentes de IA e scripts: só o JSON, sem texto em volta
        print(json.dumps([{"item": i, "pronto": ok, "como": fazer} for i, ok, fazer in diagnostico()], ensure_ascii=False))
        return
    print(versao_cli() + "\n")
    faltando = 0
    for item, pronto, fazer in diagnostico():
        print(f"{'OK ' if pronto else 'FALTA'}  {item}" + ("" if pronto else f"\n        -> {fazer}"))
        faltando += not pronto
    print(f"\n{'Tudo pronto.' if not faltando else f'{faltando} item(ns) para configurar.'}")


def cmd_progresso(a):
    from .autoria import versao_cli
    from .plataformas import base, calcular, pendencias
    if a.json:
        def etapa(e):
            return {"nome": e.nome, "feita": e.feita, "como": e.como, "link": e.link}
        print(json.dumps({"base": [etapa(e) for e in base()],
                          "plataformas": [{"id": r.id, "nome": r.nome, "situacao": r.situacao,
                                           "etapas": [etapa(e) for e in r.etapas]} for r in calcular()],
                          "pendencias_do_modo_guiado": [etapa(e) for e in pendencias()]}, ensure_ascii=False))
        return
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


def cmd_leva(a):
    from . import leva
    from .perfis import carregar
    perfil = carregar()
    quantidade = min(a.quantidade or int(perfil.dados.get("leva_quantidade", 7)), leva.LIMITE_LEVA)
    if a.se_faltar and not leva.precisa_reabastecer(perfil):
        print(f"fila com {len(list(perfil.fila.glob('*.json')))} vídeo(s); reabastecimento não necessário")
        return
    est = leva.estimar(perfil.dados, quantidade)
    print(f"leva de {quantidade} vídeo(s): {est['texto']}. {est['aviso']}")
    if a.fundo:
        faltam = leva.em_segundo_plano(perfil, quantidade)
        print(f"produção pausada até terminar a configuração do canal (falta: {'; '.join(faltam)})" if faltam
              else "leva iniciada em segundo plano (log em controle/leva-ultima.log)")
        return
    leva.criar(perfil, quantidade, a.tema or "")


def cmd_descricao(a):
    from .descricao import checar, gerar
    from .perfis import carregar
    d = gerar(carregar(), Path(a.roteiro).resolve(), refazer=a.refazer)
    print(f"descrição ({d['descricao_modo']}, {d.get('gerado_por', 'manual')}):\n{d['descricao']}\n")
    print(f"tags ({d['tags_modo']}): {', '.join(d['tags'])}\nhashtags: {' '.join(d['hashtags'])}")
    for aviso in checar(d["descricao"], d["tags"], d["hashtags"]):
        print(f"  aviso: {aviso}")


def cmd_abrir(_):
    from .app import abrir
    abrir()


def cmd_atalhos(a):
    from .app import atalhos
    for linha in atalhos(a.area_de_trabalho and not a.remover, a.menu_iniciar and not a.remover,
                         a.barra_de_tarefas and not a.remover):
        print(linha)


def cmd_atualizar(a):
    from .app import atualizar, verificar
    if a.verificar:
        r = verificar()
        if not r.get("ok"):
            sys.exit(r["motivo"])
        print("versão nova disponível:" if r["ha_novidade"] else "o Projeto Canais está atualizado")
        for m in r.get("novos", []):
            print(f"  - {m}")
        return
    r = atualizar()
    if r.get("atualizado"):
        n = r["novidade"]
        print(f"atualizado: v{n['de']} -> v{n['para']}")
        for m in n["mudancas"]:
            print(f"  - {m}")
        from . import whatsapp
        whatsapp.avisar_versao()
        print("se o Estúdio estiver aberto, ele reinicia sozinho")
    elif r.get("motivo"):
        sys.exit(r["motivo"])
    else:
        print("o Projeto Canais já está na versão mais nova")


def cmd_atualizar_dependencias(a):
    from .app import dependencias
    for i in dependencias(aplicar=a.aplicar):
        extra = i.get("resultado") or i.get("obs") or ""
        nova = f" -> {i['nova']}" if i.get("nova") else ""
        print(f"{i['tipo']:14} {i['nome']:24} {i['atual']}{nova}  {extra}")
    if not a.aplicar:
        print("\npara atualizar: python -m darkops atualizar-dependencias --aplicar")


def cmd_roteiro_auditar(a):
    """Confere gancho, estrutura (problema, solução, prova) e CTA do roteiro. A leva roda até sair sem erro."""
    from .auditoria import relatorio
    passou = True
    for nome in a.roteiros:
        ok, texto = relatorio(Path(nome))
        print(texto)
        passou = passou and ok
    sys.exit(0 if passou else 1)


def cmd_palco_testar(a):
    """Desenha alguns quadros de cada cena do palco, sem gravar vídeo: acusa erro no módulo antes da produção.
    É o único comando Python que a leva automática pode rodar (em vez de qualquer código)."""
    import numpy as np
    from .palco import Contexto, _carregar, _historia
    roteiro = json.loads(Path(a.roteiro).read_text(encoding="utf-8"))
    modulo = (config.RAIZ / roteiro["palco"]).resolve()
    if not modulo.is_relative_to((config.RAIZ / "cenas").resolve()):
        sys.exit("o palco precisa estar em cenas/")
    if modulo.suffix == ".js":  # palco 3D: desenha no Chromium e confere peças e âncoras
        from .palco_web import testar
        problemas = testar(modulo, roteiro["cenas"])
        print("\n".join(problemas) or f"{len(roteiro['cenas'])} cenas ok")
        sys.exit(1 if problemas else 0)
    mod = _carregar(modulo)
    mundo = tuple(getattr(mod, "MUNDO", (216, 384)))
    erros = 0
    for i, _ in enumerate(roteiro["cenas"], 1):
        antes, entradas, acoes = _historia(roteiro["cenas"], i, [], 4.0)
        try:
            for t in (0.0, 1.5, 3.5):
                mod.desenhar(Contexto(np.zeros((mundo[1], mundo[0], 3), np.float32), t, t, i, entradas, acoes, antes))
            print(f"cena {i}: ok")
        except Exception as erro:
            erros += 1
            print(f"cena {i}: ERRO {type(erro).__name__}: {erro}")
    sys.exit(1 if erros else 0)


def cmd_estatisticas(_):
    from .estatisticas import coletar, totais
    from .perfis import carregar
    r = coletar(carregar())
    for plataforma, t in totais(r).items():
        print(f"{plataforma}: {t.get('nome')} · seguidores {t.get('seguidores')} · {t['n_videos']} vídeos · "
              f"{t['visualizacoes_videos']} visualizações · {t['curtidas']} curtidas · {t['comentarios']} comentários")
    for d in r["plataformas"].values():
        for aviso in d["avisos"]:
            print(f"  aviso: {aviso}")


def cmd_comentarios(a):
    """Coleta e triagem dos comentários; com --todos, cada perfil ativo (o n8n roda a cada 3 horas)."""
    import os
    from . import comentarios
    from .perfis import carregar, listar
    perfis = [p for p in listar() if p.dados.get("ativo")] if a.todos else [carregar()]
    for p in perfis:
        os.environ["DARKOPS_PERFIL"] = p.id  # tokens e helpers do perfil certo
        r = comentarios.ciclo(p, ia=not a.sem_ia)
        print(f"{p.id}: {r['total']} comentário(s), {r['classificados']} classificado(s) agora, "
              f"{r['esperando']} esperando resposta, {r['respondidos_auto']} respondido(s) no automático")
        for aviso in r["avisos"]:
            print(f"  aviso: {aviso}")


def cmd_comentario_responder(a):
    from . import comentarios
    from .perfis import carregar
    c = comentarios.responder(carregar(), a.id, a.texto)
    print(f"ok: respondido no {c['plataforma']}: {c['resposta']}")


def cmd_analisar(_):
    from .analise import analisar
    from .perfis import carregar
    r = analisar(carregar())
    print(r.get("resumo", ""))
    for s in r.get("sugestoes", []):
        print(f"- [{s['estado']}] {s['titulo']}: {s['motivo']}")


def cmd_ajustar_canal(a):
    from .canal_ia import propor
    from .perfis import carregar
    proposta = propor(carregar(), a.pedido)
    print(proposta["resumo"])
    for m in proposta["mudancas"]:
        print(f"- {m['campo']}: {m['antes']!r} -> {m['depois']!r}")
    print("proposta pendente: aplique ou descarte no Estúdio (Ajustes)")


def cmd_conferir(a):
    from .conferir import conferir, salvar
    from .perfis import carregar
    perfil = carregar()
    resultado = conferir(Path(a.video), perfil.dados.get("duracao_s"))  # o botão do Estúdio usa a duração do vídeo
    print(f"{resultado['video']}: {resultado['duracao_s']} s, {resultado['resolucao']}")
    for x in resultado["achados"]:
        print(f"  {x['nivel'].upper():5} {x['texto']}")
    salvar(resultado, perfil)


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
    from . import nuvem
    from .fila import concluir
    from .perfis import carregar
    from .render import duracao
    caminho, roteiro, slug, video = _roteiro_e_video(a.roteiro)
    if nuvem.simulando():
        print(f"[simulação] {caminho.name} sairia da fila e ocuparia este horário")
        _resultado({"slug": slug, "simulado": True})
        return
    resultado = concluir(caminho, roteiro, duracao(video))
    perfil = carregar()
    nuvem.registrar_slot(perfil, slug)
    from . import whatsapp
    whatsapp.postado(perfil, roteiro, caminho, resultado["ids"], "GitHub (nuvem)" if nuvem.na_nuvem() else "PC")
    if nuvem.configurada() and not nuvem.na_nuvem():
        try:
            nuvem.sincronizar(perfil)  # avisa a nuvem já, para ela não repetir este horário
        except (SystemExit, OSError) as erro:
            print(f"aviso: não consegui avisar a nuvem agora ({erro}); ela confere na plataforma antes de postar")
    _resultado(resultado)


def cmd_nuvem(a):
    from . import nuvem
    from .perfis import carregar, listar
    if a.acao == "preparar":
        print("perfis prontos:", ", ".join(nuvem.preparar_actions(Path(a.fila).resolve())) or "nenhum")
        return
    if a.acao == "devolver":
        print("devolvidos:", ", ".join(nuvem.devolver_actions(Path(a.fila).resolve())) or "nenhum")
        return
    if not nuvem.configurada():
        sys.exit("a nuvem não está configurada: preencha NUVEM_REPO e NUVEM_TOKEN (Estúdio > Ajustes > Contas)")
    if a.acao == "configurar":
        r = nuvem.configurar([p for p in listar() if p.dados.get("ativo")] or [carregar()])
        print(f"nuvem pronta em {r['repo']}; segredos: {', '.join(r['segredos'])}")
        for pid, f in r["filas"].items():
            print(f"  {pid}: {len(f['enviados'])} vídeo(s) enviado(s), {len(f['concluidos_aqui'])} concluído(s) aqui")
    elif a.acao == "sincronizar":
        print(json.dumps(nuvem.sincronizar(carregar()), ensure_ascii=False))
    elif a.acao == "agenda":
        mudou = nuvem.atualizar_agenda([p for p in listar() if p.dados.get("ativo")] or [carregar()])
        print("agenda da nuvem " + ("atualizada" if mudou else "já estava certa"))
    elif a.acao == "segredos":
        print("segredos atualizados:", ", ".join(nuvem.enviar_segredos(listar())))
    elif a.acao == "instagram":
        # prova real sem postar: a Meta baixa o vídeo pelo link de passagem e processa, mas nada é publicado
        from .fila import proximo
        from .instagram import publicar_reel
        roteiro = proximo()
        if not roteiro:
            sys.exit("nenhum vídeo aprovado na fila para testar")
        _, _, _, video = _roteiro_e_video(str(roteiro), "vertical")
        conteiner = publicar_reel(video, "teste (não publicado)", publicar=False)
        print(f"ok: a Meta baixou e processou {video.name} pelo link de passagem (contêiner {conteiner}, não publicado)")
    elif a.acao == "testar":
        nuvem.disparar(simular=True)
        print("workflow da nuvem iniciado em simulação; veja em Actions no repositório de fila")
    else:
        print(json.dumps(nuvem.status(carregar()), ensure_ascii=False))


def cmd_registrar_falha(a):
    from . import whatsapp
    from .fila import registrar_falha
    from .perfis import carregar
    registrar_falha(a.etapa, a.mensagem)
    whatsapp.falhou(carregar(), a.etapa, a.mensagem)
    _resultado({"registrado": True})


def cmd_aprender(a):
    """O n8n roda todo dia: cada canal ativo com 15 vídeos novos no ar há 2 dias tem o ciclo analisado e ajustado."""
    from . import aprendizado
    from .perfis import carregar, listar
    perfis = [carregar()] if a.perfil_unico or a.forcar else [p for p in listar() if p.dados.get("ativo")]
    for p in perfis:
        r = aprendizado.rodar(p, forcar=a.forcar)
        if "esperando" in r:
            e = r["esperando"]
            print(f"{p.id}: {e['no_ar']}/{e['meta']} vídeos do ciclo no ar" +
                  (f"; análise em {e['pronto_em']}" if e["pronto_em"] else ""))
        else:
            print(f"{p.id}: ciclo {r['numero']} analisado ({r['com_dados']} vídeo(s) com números), "
                  f"{len(r['mudancas'])} mudança(s) aplicada(s)")
            print(r.get("resumo", ""))


def cmd_conectar_github(a):
    from . import contas
    contas.conectar_github(a.fila or contas.REPO_FILA, a.passagem or contas.REPO_PASSAGEM)


def cmd_conectar_azure(_):
    from . import contas
    contas.conectar_azure()


def cmd_instalar_apps(a):
    from . import apps
    falhas = apps.instalar_tudo(claude=not a.sem_claude, n8n=not a.sem_n8n, logon=not a.sem_logon)
    if falhas:
        raise SystemExit(f"falhou: {', '.join(falhas)} (rode de novo: python -m darkops instalar-apps)")
    print("Programas prontos. Fica com você só o que é conta: o login do Claude Code (rode: claude) e as chaves e "
          "contas das plataformas, no Estúdio.")


def cmd_aprender_desfazer(_):
    from . import aprendizado
    from .perfis import carregar
    print(f"{aprendizado.desfazer(carregar())} mudança(s) desfeita(s)")


def cmd_whatsapp(a):
    from . import whatsapp
    if a.acao == "testar":
        print(f"ok: mensagem de teste enviada pelo número {whatsapp.testar()}")
    elif a.acao == "resumo":
        whatsapp.resumo_do_dia()
        print("resumo enviado (ou guardado até a próxima mensagem do dono)")
    elif a.acao == "versao":
        print("aviso da versão nova enviado" if whatsapp.avisar_versao() else
              "nenhuma versão nova para avisar (ou guardada até a próxima mensagem do dono)")
    elif a.acao == "n8n":
        from .instalacao import gerar_workflow_whatsapp
        gerar_workflow_whatsapp(importar=True)
    else:
        estado = whatsapp.ler_estado()
        print(json.dumps({"situacao": whatsapp.situacao(), "recebe_comandos": whatsapp.recebe_comandos(),
                          "janela_aberta": whatsapp.janela_aberta(), "avisos_guardados": len(estado.get("pendentes", [])),
                          "tunel": estado.get("tunel", ""), "erro": estado.get("tunel_erro", "")}, ensure_ascii=False))


def cmd_whatsapp_receber(a):
    """Chamado pelo n8n quando chega uma mensagem (o porteiro já conferiu a assinatura da Meta)."""
    import re as _re
    from . import whatsapp
    if a.arquivo == "verificar":
        _resultado({"ok": True})
        return
    nome = _re.sub(r"[^\w.-]", "", a.arquivo)
    arquivo = whatsapp.ENTRADA / nome
    if not nome.endswith(".json") or not arquivo.exists():
        sys.exit("entrega do WhatsApp não encontrada")
    _resultado({"tratadas": whatsapp.receber(arquivo)})


def cmd_identidade(a):
    from . import identidade
    from .perfis import carregar
    perfil = carregar()
    if a.acao == "gerar":
        _resultado(identidade.gerar(perfil))
    elif a.acao == "aprovar":
        _resultado(identidade.aprovar(perfil, a.por or ""))
    elif a.acao == "pacote":
        _resultado(identidade.pacote(perfil))
    elif a.acao == "bloco":  # um pedaço do pacote, cru, para a skill colar na página
        pacote = json.loads((identidade.pasta(perfil) / "pacote.json").read_text(encoding="utf-8"))
        bloco = pacote["arquivos"][a.arquivo]["blocos"][a.numero]
        print(bloco["dados"])
        print(f"SHA8 {bloco['sha8']}", file=sys.stderr)
    elif a.acao == "aplicada":
        if a.plataforma not in ("youtube", "instagram"):
            raise SystemExit("use --plataforma youtube ou --plataforma instagram")
        _resultado(identidade.marcar_aplicada(perfil, a.plataforma))
    else:
        _resultado({"estado": identidade.estado(perfil), "pasta": str(identidade.pasta(perfil))})


def cmd_nichos(_):
    for nome, n in config.nichos().items():
        print(f"{nome:<22} [{n['idioma']}] {n['descricao']}")


def main():
    from .janelas import esconder
    esconder()  # aberto pelo atalho (pythonw): nenhum comando chamado daqui pisca uma janela de prompt
    from .autoria import ROTULO, VERSAO
    p = argparse.ArgumentParser(prog="dark", description=f"Pesquisa e produção de canais dark. {ROTULO}")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSAO}")
    p.add_argument("--perfil", help="id do perfil (pasta em perfis/); padrão: pulga-do-saber")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("perfis", help="lista os perfis")
    s.set_defaults(fn=cmd_perfis)

    s = sub.add_parser("perfis-ativos", help="perfis com postagem ligada (saída JSON para o n8n)")
    s.add_argument("--na-hora", action="store_true", help="só os que chegaram agora a um horário (fuso do mercado)")
    s.set_defaults(fn=cmd_perfis_ativos)

    s = sub.add_parser("tendencias", help="assuntos em alta agora no país do público (pauta dos canais de notícias)")
    s.add_argument("--mercado", default="pt-BR")
    s.add_argument("--quantidade", type=int, default=10)
    s.set_defaults(fn=cmd_tendencias)
    s = sub.add_parser("mercados", help="línguas e regiões de público disponíveis para os canais")
    s.set_defaults(fn=cmd_mercados)

    s = sub.add_parser("diagnostico", help="o que está pronto e o que falta configurar")
    s.add_argument("--json", action="store_true", help="saída em JSON (para agentes de IA e scripts)")
    s.set_defaults(fn=cmd_diagnostico)

    s = sub.add_parser("leva", help="cria vários vídeos de uma vez (roteiro pelo Claude Code + prévia)")
    s.add_argument("--quantidade", type=int)
    s.add_argument("--se-faltar", action="store_true", help="só cria se a fila estiver no mínimo do perfil")
    s.add_argument("--fundo", action="store_true", help="roda num processo separado e volta na hora")
    s.add_argument("--tema", help="assunto do vídeo (sem ele, o Claude escolhe um tema forte)")
    s.set_defaults(fn=cmd_leva)

    s = sub.add_parser("descricao", help="cria pela IA a descrição e as tags do vídeo que estiverem no modo automático")
    s.add_argument("roteiro")
    s.add_argument("--refazer", action="store_true")
    s.set_defaults(fn=cmd_descricao)

    s = sub.add_parser("conferir", help="confere o vídeo pronto: tela preta, silêncio, volume, duração e resolução")
    s.add_argument("video")
    s.set_defaults(fn=cmd_conferir)

    s = sub.add_parser("referencia", help="mede o estilo de vídeos de referência e propõe o padrão do perfil")
    s.add_argument("url", nargs="+")
    s.set_defaults(fn=cmd_referencia)

    s = sub.add_parser("progresso", help="progresso da configuração de cada plataforma (YouTube, Instagram...)")
    s.add_argument("--json", action="store_true", help="saída em JSON (para agentes de IA e scripts)")
    s.set_defaults(fn=cmd_progresso)

    s = sub.add_parser("n8n-workflow", help="gera n8n/workflow.json para esta pasta (e importa com --importar)")
    s.add_argument("--importar", action="store_true")
    s.set_defaults(fn=cmd_n8n_workflow)

    s = sub.add_parser("estudio", help="abre o Estúdio (painel local no navegador)")
    s.add_argument("--porta", type=int, default=8765)
    s.add_argument("--sem-navegador", action="store_true")
    s.set_defaults(fn=cmd_estudio)

    s = sub.add_parser("identidade", help="foto, capa, marca d'água e bio das contas (gerar, aprovar, pacote, aplicada)")
    s.add_argument("acao", nargs="?", default="estado", choices=["estado", "gerar", "aprovar", "pacote", "bloco", "aplicada"])
    s.add_argument("--plataforma", help="com 'aplicada': youtube ou instagram")
    s.add_argument("--por", help="com 'aprovar': quem aprovou")
    s.add_argument("--arquivo", choices=["foto", "marca", "capa"], help="com 'bloco'")
    s.add_argument("--numero", type=int, default=0, help="com 'bloco': número do pedaço (0, 1, 2...)")
    s.set_defaults(fn=cmd_identidade)

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

    s = sub.add_parser("efeitos-baixar", help="baixa efeitos sonoros CC0 do Openverse para assets/efeitos")
    s.add_argument("--por-tipo", type=int, default=6)
    s.set_defaults(fn=cmd_efeitos_baixar)

    s = sub.add_parser("comparar-vozes", help="gera o mesmo trecho em cada motor de voz para ouvir lado a lado")
    s.add_argument("--texto")
    s.set_defaults(fn=cmd_comparar_vozes)

    s = sub.add_parser("vozes-amostras", help="amostras das vozes para escolher a voz do canal (grátis ou, com a chave, pagas)")
    s.add_argument("--mercado", help="só um público, ex.: pt-BR")
    s.add_argument("--motor", choices=["gemini", "chirp", "elevenlabs"], help="opção paga (precisa da chave)")
    s.add_argument("--minha-voz", action="store_true", help="amostra da sua própria voz (gravação em dados/minha-voz)")
    s.add_argument("--refazer", action="store_true")
    s.set_defaults(fn=cmd_vozes_amostras)

    s = sub.add_parser("autorizar-youtube", help="autoriza o canal uma vez pelo navegador e salva o token")
    s.add_argument("--analytics", action="store_true", help="também libera minutos assistidos e retenção")
    s.add_argument("--comentarios", action="store_true", help="também libera responder comentários")
    s.set_defaults(fn=cmd_autorizar_youtube)

    s = sub.add_parser("comentarios", help="busca os comentários novos, classifica pela IA e rascunha respostas")
    s.add_argument("--todos", action="store_true", help="todos os perfis ativos (o que o n8n roda)")
    s.add_argument("--sem-ia", action="store_true", help="só busca, sem classificar nem responder")
    s.set_defaults(fn=cmd_comentarios)

    s = sub.add_parser("comentario-responder", help="publica a resposta de um comentário (o rascunho aprovado)")
    s.add_argument("id")
    s.add_argument("--texto", help="outra resposta no lugar do rascunho")
    s.set_defaults(fn=cmd_comentario_responder)

    s = sub.add_parser("abrir", help="abre o Estúdio (o que o atalho da Área de Trabalho roda)")
    s.set_defaults(fn=cmd_abrir)

    s = sub.add_parser("atalhos", help="cria (ou remove) os atalhos do Projeto Canais no Windows")
    s.add_argument("--area-de-trabalho", action="store_true")
    s.add_argument("--menu-iniciar", action="store_true")
    s.add_argument("--barra-de-tarefas", action="store_true", help="cria no Menu Iniciar e explica como fixar")
    s.add_argument("--remover", action="store_true")
    s.set_defaults(fn=cmd_atalhos)

    s = sub.add_parser("atualizar", help="busca a versão nova no GitHub e atualiza esta pasta")
    s.add_argument("--verificar", action="store_true", help="só mostra se há versão nova")
    s.set_defaults(fn=cmd_atualizar)

    s = sub.add_parser("atualizar-dependencias", help="verifica (e atualiza) pacotes Python, yt-dlp, n8n e Claude Code")
    s.add_argument("--aplicar", action="store_true")
    s.set_defaults(fn=cmd_atualizar_dependencias)

    s = sub.add_parser("roteiro-auditar", help="confere gancho, estrutura e CTA de roteiros (sai com erro se faltar algo)")
    s.add_argument("roteiros", nargs="+")
    s.set_defaults(fn=cmd_roteiro_auditar)

    s = sub.add_parser("palco-testar", help="desenha alguns quadros de cada cena do palco de um roteiro (sem gravar)")
    s.add_argument("roteiro")
    s.set_defaults(fn=cmd_palco_testar)

    s = sub.add_parser("estatisticas", help="busca nas plataformas os números do canal e de cada vídeo")
    s.set_defaults(fn=cmd_estatisticas)

    for acao, ajuda in [("configurar", "prepara o repositório privado de fila (workflow, segredos e vídeos)"),
                        ("sincronizar", "troca o estado com a nuvem e envia os vídeos aprovados"),
                        ("segredos", "reenvia os tokens do YouTube e do Instagram para a nuvem"),
                        ("status", "quantos vídeos a nuvem tem e quem postou por último"),
                        ("agenda", "acerta os horários da nuvem com o fuso do mercado de cada canal"),
                        ("testar", "roda o workflow da nuvem agora, em simulação (não publica)"),
                        ("instagram", "testa o link de passagem do Instagram sem publicar nada"),
                        ("preparar", "(usado no GitHub Actions) monta a fila, os vídeos e as credenciais"),
                        ("devolver", "(usado no GitHub Actions) devolve o estado para o repositório de fila")]:
        s = sub.add_parser(f"nuvem-{acao}", help=ajuda)
        s.add_argument("--fila", default=".", help="pasta do repositório de fila (só no Actions)")
        s.set_defaults(fn=cmd_nuvem, acao=acao)

    s = sub.add_parser("ajustar-canal", help="a IA transforma a descrição do canal em mudanças do perfil (pede aprovação)")
    s.add_argument("pedido")
    s.set_defaults(fn=cmd_ajustar_canal)

    s = sub.add_parser("analisar", help="a IA analisa as estatísticas e sugere mudanças (cada uma pede aprovação)")
    s.set_defaults(fn=cmd_analisar)

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

    s = sub.add_parser("aprender", help="analisa o que funcionou a cada 15 vídeos no ar e ajusta o canal sozinho")
    s.add_argument("--forcar", action="store_true", help="analisa agora, mesmo sem completar o ciclo")
    s.add_argument("--perfil-unico", action="store_true", help="só o perfil de --perfil (sem isso: todos os ativos)")
    s.set_defaults(fn=cmd_aprender)

    s = sub.add_parser("conectar-github", help="login no GitHub; cria os repositórios da nuvem e da passagem do Instagram")
    s.add_argument("--fila", default="", help="nome do repositório privado da fila (padrão projeto-canais-fila)")
    s.add_argument("--passagem", default="", help="nome do repositório público de passagem (padrão projeto-canais-videos)")
    s.set_defaults(fn=cmd_conectar_github)

    s = sub.add_parser("conectar-azure", help="login na Microsoft; cria o recurso de voz grátis (F0) e salva a chave")
    s.set_defaults(fn=cmd_conectar_azure)

    s = sub.add_parser("instalar-apps", help="instala sozinho o Node.js, o n8n e o Claude Code (na pasta do projeto)")
    s.add_argument("--sem-claude", action="store_true")
    s.add_argument("--sem-n8n", action="store_true")
    s.add_argument("--sem-logon", action="store_true", help="não liga o n8n junto com o Windows")
    s.set_defaults(fn=cmd_instalar_apps)

    s = sub.add_parser("aprender-desfazer", help="volta as mudanças da última análise automática")
    s.set_defaults(fn=cmd_aprender_desfazer)

    s = sub.add_parser("whatsapp", help="WhatsApp do dono: testar, status, resumo, versao (avisa a versão nova) ou n8n (importa o workflow de comandos)")
    s.add_argument("acao", choices=["testar", "status", "resumo", "versao", "n8n"], nargs="?", default="status")
    s.set_defaults(fn=cmd_whatsapp)

    s = sub.add_parser("whatsapp-receber", help="processa uma mensagem recebida do WhatsApp (chamado pelo n8n)")
    s.add_argument("--arquivo", required=True)
    s.set_defaults(fn=cmd_whatsapp_receber)

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
    if sys.stdout is None or sys.stderr is None:  # pythonw (atalho, reinício): sem console, vai para um registro
        registro = config.RAIZ / "dados" / "estudio.log"
        registro.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(registro, "a", encoding="utf-8", buffering=1)
    else:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos no console do Windows
    main()
