"""Situação da monetização de cada canal: se já ganha, quanto, e o que falta para entrar no Programa de Parcerias.

YouTube: os números vêm da YouTube Analytics API, junto com as estatísticas (Atualizar dados).
- Progresso: horas de exibição de vídeos longos nos últimos 365 dias e visualizações de Shorts nos últimos 90
  (dimensão creatorContentType). É uma estimativa: o YouTube só conta as "qualificadas" (vídeos públicos, sem
  anúncios pagos, sem o feed de Shorts nas horas), então o número oficial do YouTube Studio pode ser um pouco menor.
- Receita: estimatedRevenue e playbackBasedCpm, que pedem a permissão yt-analytics-monetary.readonly (o mesmo
  botão que libera a retenção). Receita acima de zero nos últimos 90 dias = canal monetizado.
Instagram: presentes, assinaturas e bônus não têm API; o Estúdio só mostra onde conferir.

Requisitos: support.google.com/youtube/answer/72851 (conferido em 2026-11-02) e answer/12843009 (mudança de
2027-02-01). Revise se o YouTube mudar as regras.
"""
from datetime import date, timedelta

ESCOPO_RECEITA = "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"
FONTE = "https://support.google.com/youtube/answer/72851"
MUDANCA_2027 = date(2027, 2, 1)


def requisitos(hoje: date | None = None) -> dict:
    """Metas do Programa de Parcerias do YouTube na data. A partir de 2027-02-01, a entrada fica mais exigente."""
    hoje = hoje or date.today()
    completo = ({"inscritos": 1000, "horas": 8000, "shorts": 20_000_000} if hoje >= MUDANCA_2027
                else {"inscritos": 1000, "horas": 4000, "shorts": 10_000_000})
    return {
        "completo": {**completo, "nome": "Programa completo (anúncios nos vídeos e nos Shorts)"},
        "inicial": {"inscritos": 500, "horas": 3000, "shorts": 3_000_000,
                    "nome": "Nível inicial (Clubes de canais, Super Thanks, Super Chat, Shopping)"},
        "fonte": FONTE,
    }


def _somar(resposta: dict, tipos: tuple[str, ...], coluna: str) -> float:
    cols = [c["name"] for c in resposta.get("columnHeaders", [])]
    if "creatorContentType" not in cols or coluna not in cols:
        return 0.0
    i_tipo, i_val = cols.index("creatorContentType"), cols.index(coluna)
    norm = lambda v: str(v).upper().replace("_", "")  # noqa: E731  (a API já devolveu SHORTS e shorts)
    alvo = {norm(x) for x in tipos}
    return sum(float(l[i_val] or 0) for l in resposta.get("rows", []) if norm(l[i_tipo]) in alvo)


def coletar_youtube(analytics, escopos: list[str], hoje: date | None = None) -> dict:
    """Horas, Shorts e receita pela YouTube Analytics API (o serviço `analytics` já autenticado)."""
    hoje = hoje or date.today()
    saida: dict = {"atualizado": hoje.isoformat(), "avisos": []}
    longos = ("VIDEO_ON_DEMAND", "LIVE_STREAM")
    r365 = analytics.reports().query(ids="channel==MINE", startDate=(hoje - timedelta(days=365)).isoformat(),
                                     endDate=hoje.isoformat(), metrics="estimatedMinutesWatched,views",
                                     dimensions="creatorContentType").execute()
    r90 = analytics.reports().query(ids="channel==MINE", startDate=(hoje - timedelta(days=90)).isoformat(),
                                    endDate=hoje.isoformat(), metrics="views",
                                    dimensions="creatorContentType").execute()
    saida["horas_365d"] = int(round(_somar(r365, longos, "estimatedMinutesWatched") / 60))
    saida["shorts_90d"] = int(_somar(r90, ("SHORTS",), "views"))
    if ESCOPO_RECEITA not in escopos:
        saida["receita"] = None
        saida["avisos"].append("Para ver se o canal já ganha e quanto, libere também a leitura da receita: "
                               "clique em Liberar retenção e receita do YouTube.")
        return saida
    try:
        for chave, dias in (("28d", 28), ("90d", 90), ("365d", 365)):
            r = analytics.reports().query(ids="channel==MINE", startDate=(hoje - timedelta(days=dias)).isoformat(),
                                          endDate=hoje.isoformat(),
                                          metrics="estimatedRevenue,views,playbackBasedCpm").execute()
            linha = (r.get("rows") or [[0, 0, 0]])[0]
            receita, views, cpm = float(linha[0] or 0), float(linha[1] or 0), float(linha[2] or 0)
            saida.setdefault("receita", {})[chave] = {
                "valor": round(receita, 2), "rpm": round(receita / views * 1000, 2) if views else 0.0,
                "cpm": round(cpm, 2)}
    except Exception as erro:  # canal fora do programa costuma responder 403 nas métricas de receita
        saida["receita"] = None
        texto = str(getattr(erro, "content", b"").decode("utf-8", "replace") if hasattr(erro, "content") else erro)
        if "403" in str(erro) or "forbidden" in texto.lower():
            saida["avisos"].append("O YouTube não liberou os números de receita: normalmente o canal ainda não "
                                   "está no Programa de Parcerias.")
        else:
            saida["avisos"].append(f"Receita do YouTube: {texto[:160]}")
    return saida


def situacao(conta: dict, mon: dict | None, hoje: date | None = None) -> dict:
    """O que a tela Resultados mostra: monetizado (e quanto rende) ou o que falta, com barras de progresso."""
    req = requisitos(hoje)
    mon = mon or {}
    inscritos = int(conta.get("seguidores") or 0)
    horas, shorts = mon.get("horas_365d"), mon.get("shorts_90d")
    receita = mon.get("receita")
    monetizado = bool(receita and (receita.get("90d", {}).get("valor", 0) > 0))

    def barra(rotulo, atual, meta, unidade):
        atual_n = atual if atual is not None else 0
        return {"rotulo": rotulo, "atual": atual, "meta": meta, "unidade": unidade,
                "pct": min(round(atual_n / meta * 100) if meta else 0, 100), "ok": atual is not None and atual_n >= meta,
                "falta": max(meta - atual_n, 0) if atual is not None else None}

    niveis = []
    for chave in ("inicial", "completo"):
        r = req[chave]
        b_insc = barra("Inscritos", inscritos, r["inscritos"], "inscritos")
        b_horas = barra("Horas de exibição em vídeos longos (365 dias)", horas, r["horas"], "horas")
        b_shorts = barra("Visualizações de Shorts (90 dias)", shorts, r["shorts"], "visualizações")
        atingiu = b_insc["ok"] and (b_horas["ok"] or b_shorts["ok"])
        niveis.append({"chave": chave, "nome": r["nome"], "barras": [b_insc, b_horas, b_shorts], "atingiu": atingiu,
                       "caminho": "horas" if (b_horas["pct"] >= b_shorts["pct"]) else "shorts"})
    checklist = [
        "Verificação em duas etapas ligada na Conta do Google do canal",
        "Recursos avançados do YouTube liberados (YouTube Studio > Configurações > Canal > Qualificação de recursos)",
        "Nenhum aviso ativo das Diretrizes da Comunidade",
        "Seguir as políticas de monetização (conteúdo original, sem reaproveitamento em massa)",
        "Conta do AdSense para YouTube ligada ao canal (o YouTube Studio pede na hora de se inscrever)",
    ]
    return {"monetizado": monetizado, "receita": receita, "niveis": niveis, "checklist": checklist,
            "sem_analytics": horas is None, "fonte": req["fonte"],
            "aviso_2027": (hoje or date.today()) < MUDANCA_2027,
            "inscrever": "https://studio.youtube.com/channel/UC/monetization"}
