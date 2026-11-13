# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Lobby do Estúdio: a primeira tela ao abrir. Visão geral de todos os canais antes de entrar em um.

Junta o que já existe em cada perfil (fila, estado, estatisticas.json, horários) sem chamar API nenhuma:
abrir o Estúdio tem que ser rápido. Os números das plataformas são os da última vez em "Atualizar dados".
"""
from datetime import date, datetime

DICAS = [
    "Aprove os vídeos com 2 ou 3 dias de folga: a fila nunca fica vazia num feriado ou numa viagem.",
    "Os 3 primeiros segundos decidem o vídeo. Se a retenção cair cedo, troque o gancho (docs/ganchos.md tem 21 fórmulas).",
    "Título e capa precisam ser entregues no vídeo: promessa sem entrega derruba a retenção e pode virar conteúdo enganoso.",
    "Todo fato precisa de fonte. Lenda se conta como lenda (\"dizem que\"), nunca como verdade.",
    "Conteúdo original rende mais e não é desmonetizado: nunca reescreva o roteiro de outro canal.",
    "Responda os primeiros comentários de cada vídeo: conversa no começo ajuda o vídeo a ser mostrado para mais gente.",
    "A cada 14 vídeos no ar, o canal aprende sozinho o que funcionou (Resultados > O que funcionou).",
    "Compartilhamentos pesam muito no Reels: termine o vídeo convidando a mandar para alguém.",
    "Poste sempre nos mesmos horários: o público se acostuma, e o Estúdio já faz isso pelo fuso do canal.",
    "Ligue a nuvem de reserva: ela posta mesmo com o PC desligado.",
    "Imagem realista feita por IA precisa da marca \"conteúdo alterado ou sintético\" no YouTube Studio.",
    "Para monetizar, foque no que falta em Resultados > Monetização: inscritos primeiro, depois horas ou Shorts.",
    "Um app do Google e um app da Meta servem para todos os canais: canal novo só conecta as próprias contas.",
    "Músicas só da lista livre (assets/musica/licencas.csv): faixa comercial derruba o vídeo.",
]


def _numero_youtube_instagram(estat: dict) -> dict:
    plat = estat.get("plataformas") or {}
    yt, ig = plat.get("youtube") or {}, plat.get("instagram") or {}
    return {"inscritos": (yt.get("conta") or {}).get("seguidores"),
            "seguidores_ig": (ig.get("conta") or {}).get("seguidores"),
            "visualizacoes": sum(v.get("visualizacoes") or 0 for d in plat.values() for v in d.get("videos", [])),
            "mon_yt": yt.get("monetizacao"), "atualizado": estat.get("atualizado")}


def _progresso_monetizacao(mon: dict | None) -> dict | None:
    """Resumo curto: monetizado, ou % do nível inicial (o melhor caminho: horas ou Shorts)."""
    if not mon:
        return None
    if mon.get("monetizado"):
        r = (mon.get("receita") or {}).get("28d") or {}
        return {"monetizado": True, "texto": f"monetizado · US$ {r.get('valor', 0):.2f} em 28 dias"}
    inicial = next((n for n in mon.get("niveis", []) if n["chave"] == "inicial"), None)
    if not inicial:
        return None
    insc, horas, shorts = inicial["barras"]
    pct = round((insc["pct"] + max(horas["pct"], shorts["pct"])) / 2)
    return {"monetizado": False, "pct": pct,
            "texto": f"{pct}% do nível inicial · faltam {insc['falta'] or 0} inscritos"}


def dados() -> dict:
    from .. import estatisticas as est
    from .. import fila as fila_mod
    from ..aparencia import garantir
    from ..perfis import listar
    from . import _n8n_online, _proximos_horarios, _situacao
    canais, atencao, proximos = [], [], []
    tot = {"canais": 0, "ativos": 0, "publicados": 0, "aprovados": 0, "esperando": 0, "inscritos": 0,
           "seguidores_ig": 0, "visualizacoes": 0}
    for p in listar():
        d = p.dados
        garantir(p)
        itens = [_situacao(c) for c in fila_mod.roteiros(p)]
        aprovados = sum(1 for i in itens if i["aprovado"])
        esperando = sum(1 for i in itens if i["estado"] == "pronta" and not i["aprovado"])
        publicados = len(fila_mod.historico(p))
        numeros = _numero_youtube_instagram(est.ler(p))
        horarios = _proximos_horarios(p, 2) if d.get("ativo") else []
        criando = (p.controle / "leva.trava").exists()
        # só falha das últimas 48 h pede atenção (o log guarda tudo)
        recentes = []
        for linha in fila_mod.falhas(p, 5):
            try:
                if (datetime.now() - datetime.strptime(linha[:19], "%Y-%m-%d %H:%M:%S")).total_seconds() < 48 * 3600:
                    recentes.append(linha)
            except ValueError:
                continue
        falhas = recentes
        canais.append({"id": p.id, "nome": d.get("nome"), "arroba": d.get("arroba"), "nicho": d.get("nicho"),
                       "ativo": bool(d.get("ativo")), "aprovados": aprovados, "esperando": esperando,
                       "publicados": publicados, "proximo": horarios[0] if horarios else None, "criando": criando,
                       "youtube": p.token_youtube.exists() if d.get("youtube", True) else None,
                       "instagram": p.token_instagram.exists() if d.get("instagram", True) else None,
                       "mon": _progresso_monetizacao(numeros["mon_yt"]), **numeros})
        tot["canais"] += 1
        tot["ativos"] += bool(d.get("ativo"))
        tot["publicados"] += publicados
        tot["aprovados"] += aprovados
        tot["esperando"] += esperando
        tot["inscritos"] += numeros["inscritos"] or 0
        tot["seguidores_ig"] += numeros["seguidores_ig"] or 0
        tot["visualizacoes"] += numeros["visualizacoes"]
        for h in horarios:
            proximos.append({"quando": h, "canal": d.get("nome"), "id": p.id})
        # o que pede atenção, do mais urgente ao menos
        if esperando:
            atencao.append({"nivel": "acao", "id": p.id, "texto": f"{d.get('nome')}: {esperando} vídeo(s) esperando sua aprovação",
                            "link": "painel"})
        if d.get("ativo") and aprovados < max(int(d.get("leva_minimo") or 3), 1) and not criando:
            atencao.append({"nivel": "aviso", "id": p.id, "texto": f"{d.get('nome')}: só {aprovados} vídeo(s) aprovado(s) na fila",
                            "link": "painel"})
        if (d.get("youtube", True) and not p.token_youtube.exists()) or (d.get("instagram", True) and not p.token_instagram.exists()):
            atencao.append({"nivel": "aviso", "id": p.id, "texto": f"{d.get('nome')}: falta conectar contas",
                            "link": "contas_criar"})
        if falhas:
            ultima = falhas[-1]
            etapa = ultima[21:ultima.index("]")] if "]" in ultima else "postagem"
            atencao.append({"nivel": "erro", "id": p.id, "link": "painel",
                            "texto": f"{d.get('nome')}: falhou em \"{etapa}\" em {ultima[8:10]}/{ultima[5:7]} às {ultima[11:16]}"})
    if canais and not _n8n_online():
        atencao.insert(0, {"nivel": "erro", "id": None, "texto": "O n8n está desligado: as postagens do PC não saem.",
                           "link": None})
    proximos.sort(key=lambda x: datetime.strptime(x["quando"], "%d/%m %H:%M").replace(year=date.today().year))
    dica = DICAS[date.today().toordinal() % len(DICAS)]
    outras = [DICAS[(date.today().toordinal() + k) % len(DICAS)] for k in (1, 2)]
    return {"canais": canais, "totais": tot, "atencao": atencao, "proximos": proximos[:6], "dica": dica,
            "outras_dicas": outras, "hoje": datetime.now()}
