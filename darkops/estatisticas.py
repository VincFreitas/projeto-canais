"""Estatísticas dos canais e de cada vídeo, direto das plataformas (APIs oficiais, só leitura).

  python -m darkops estatisticas      atualiza e mostra os números do perfil

YouTube (Data API v3, com o login atual): inscritos, visualizações e vídeos do canal; visualizações, curtidas e
comentários de cada vídeo. Minutos assistidos, duração média, retenção (% assistida) e compartilhamentos vêm da
YouTube Analytics API, que pede a permissão extra yt-analytics.readonly ("Liberar retenção" no Estúdio).
Instagram (graph.instagram.com): seguidores e posts da conta; visualizações, alcance, curtidas, comentários,
compartilhamentos, salvamentos e tempo assistido de cada Reel (pede a permissão de insights do token).
Os vídeos vêm das próprias plataformas, então entram também os que foram postados à mão.
Resultado em controle/estatisticas.json; um resumo por dia vai para controle/estatisticas-historico.jsonl.
"""
import json
import time
from datetime import date
from pathlib import Path

import requests

ESCOPO_ANALYTICS = "https://www.googleapis.com/auth/yt-analytics.readonly"
METRICAS_IG = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
               "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def _youtube(perfil) -> dict:
    from googleapiclient.discovery import build
    from .publicar import _credenciais
    saida = {"conta": {}, "videos": [], "avisos": []}
    cred = _credenciais()
    yt = build("youtube", "v3", credentials=cred, cache_discovery=False)
    canal = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    st = canal["statistics"]
    saida["conta"] = {"nome": canal["snippet"]["title"], "seguidores": int(st.get("subscriberCount", 0)),
                      "visualizacoes": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0))}
    uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
    itens = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute().get("items", [])
    ids = [i["contentDetails"]["videoId"] for i in itens]
    if ids:
        for v in yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute().get("items", []):
            s = v["statistics"]
            saida["videos"].append({
                "plataforma": "youtube", "id": v["id"], "titulo": v["snippet"]["title"],
                "publicado": v["snippet"]["publishedAt"][:10], "url": f"https://youtu.be/{v['id']}",
                "duracao": v["contentDetails"].get("duration", ""),
                "visualizacoes": int(s.get("viewCount", 0)), "curtidas": int(s.get("likeCount", 0)),
                "comentarios": int(s.get("commentCount", 0))})
    # retenção e minutos: só com a permissão extra
    info = json.loads(perfil.token_youtube.read_text(encoding="utf-8")) if perfil.token_youtube.exists() else {}
    if ESCOPO_ANALYTICS not in (info.get("scopes") or []):
        saida["avisos"].append("Minutos assistidos e retenção do YouTube precisam da permissão extra: "
                               "Estúdio > Estatísticas > Liberar retenção do YouTube.")
    elif ids:
        try:
            an = build("youtubeAnalytics", "v2", credentials=cred, cache_discovery=False)
            r = an.reports().query(ids="channel==MINE", startDate="2015-01-01", endDate=date.today().isoformat(),
                                   metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                                           "shares,subscribersGained", dimensions="video",
                                   filters="video==" + ",".join(ids[:200]), maxResults=200).execute()
            colunas = [c["name"] for c in r.get("columnHeaders", [])]
            por_video = {linha[0]: dict(zip(colunas, linha)) for linha in r.get("rows", [])}
            for v in saida["videos"]:
                a = por_video.get(v["id"])
                if a:
                    v.update({"minutos": round(a["estimatedMinutesWatched"]), "duracao_media_s": round(a["averageViewDuration"]),
                              "retencao_pct": round(a["averageViewPercentage"], 1), "compartilhamentos": int(a["shares"]),
                              "inscritos_ganhos": int(a["subscribersGained"])})
        except Exception as erro:  # API não ativada no Google Cloud, cota etc.
            saida["avisos"].append(_explicar_erro_analytics(erro))
    return saida


def _explicar_erro_analytics(erro) -> str:
    """Troca a resposta crua da API por uma instrução do que fazer (com o link certo, quando vier)."""
    import re
    texto = str(getattr(erro, "content", b"").decode("utf-8", "replace") if hasattr(erro, "content") else erro)
    if "accessNotConfigured" in texto or "has not been used in project" in texto:
        link = re.search(r"https://console\.developers\.google\.com/apis/api/youtubeanalytics\.googleapis\.com/overview\?project=\d+", texto)
        return ("YouTube Analytics: a API ainda não está ativada no seu projeto do Google Cloud. Abra "
                f"{link.group(0) if link else 'console.cloud.google.com > APIs e serviços > Biblioteca > YouTube Analytics API'}"
                ", clique em Ativar, espere uns minutos e clique em Atualizar dados.")
    if "insufficientPermissions" in texto or "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in texto:
        return "YouTube Analytics: falta a permissão de leitura; clique em Liberar retenção do YouTube de novo."
    return f"YouTube Analytics: {texto[:200]}"


def _instagram(perfil) -> dict:
    from .instagram import GRAPH, token
    saida = {"conta": {}, "videos": [], "avisos": []}
    tk = token()
    me = requests.get(f"{GRAPH}/me", params={"fields": "username,followers_count,media_count", "access_token": tk},
                      timeout=30).json()
    if "error" in me:
        raise RuntimeError(me["error"].get("message"))
    saida["conta"] = {"nome": "@" + me.get("username", ""), "seguidores": me.get("followers_count"),
                      "videos": me.get("media_count")}
    midias = requests.get(f"{GRAPH}/me/media", timeout=30, params={
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
        "limit": 50, "access_token": tk}).json().get("data", [])
    sem_insights = None
    for m in midias:
        if m.get("media_product_type") != "REELS" and m.get("media_type") != "VIDEO":
            continue
        v = {"plataforma": "instagram", "id": m["id"], "titulo": (m.get("caption") or "").split("\n")[0][:90],
             "publicado": (m.get("timestamp") or "")[:10], "url": m.get("permalink"),
             "curtidas": m.get("like_count", 0), "comentarios": m.get("comments_count", 0)}
        if not sem_insights:
            r = requests.get(f"{GRAPH}/{m['id']}/insights", timeout=30,
                             params={"metric": ",".join(METRICAS_IG), "access_token": tk}).json()
            if "error" in r:
                sem_insights = r["error"].get("message", "sem permissão de insights")
            else:
                valores = {i["name"]: (i.get("values") or [{}])[0].get("value", i.get("total_value", {}).get("value"))
                           for i in r.get("data", [])}
                v.update({"visualizacoes": valores.get("views"), "alcance": valores.get("reach"),
                          "compartilhamentos": valores.get("shares"), "salvos": valores.get("saved"),
                          "duracao_media_s": round((valores.get("ig_reels_avg_watch_time") or 0) / 1000, 1),
                          "minutos": round((valores.get("ig_reels_video_view_total_time") or 0) / 60000)})
        saida["videos"].append(v)
    if sem_insights:
        saida["avisos"].append(f"Instagram: as métricas de cada Reel pedem a permissão de insights no token "
                               f"(instagram_business_manage_insights). Resposta: {sem_insights[:160]}")
    return saida


def coletar(perfil) -> dict:
    """Busca tudo nas plataformas ligadas no perfil e grava em controle/estatisticas.json."""
    resultado = {"atualizado": time.strftime("%Y-%m-%d %H:%M"), "plataformas": {}}
    for nome, funcao, ligado in (("youtube", _youtube, perfil.dados.get("youtube") and perfil.token_youtube.exists()),
                                 ("instagram", _instagram, perfil.dados.get("instagram") and perfil.token_instagram.exists())):
        if not ligado:
            continue
        try:
            resultado["plataformas"][nome] = funcao(perfil)
        except BaseException as erro:  # SystemExit dos helpers também: uma plataforma não derruba a outra
            from .seguranca import ocultar
            resultado["plataformas"][nome] = {"conta": {}, "videos": [], "avisos": [f"não deu para ler: {ocultar(erro)[:200]}"]}
    from .seguranca import ocultar
    for dados in resultado["plataformas"].values():  # nenhum token vai parar no arquivo ou na tela
        dados["avisos"] = [ocultar(x) for x in dados["avisos"]]
    _ligar_roteiros(perfil, resultado)
    perfil.controle.mkdir(parents=True, exist_ok=True)
    (perfil.controle / "estatisticas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    with (perfil.controle / "estatisticas-historico.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"data": date.today().isoformat(), **{
            p: {"seguidores": d["conta"].get("seguidores"), "visualizacoes": sum(v.get("visualizacoes") or 0 for v in d["videos"])}
            for p, d in resultado["plataformas"].items()}}, ensure_ascii=False) + "\n")
    return resultado


def _ligar_roteiros(perfil, resultado: dict) -> None:
    """Liga cada vídeo ao roteiro que o publicou (estado.json guarda o id de cada plataforma)."""
    from .fila import ler_estado
    por_id = {ids.get(p): slug for slug, ids in ler_estado(perfil).items() for p in ("youtube", "instagram") if ids.get(p)}
    for dados in resultado["plataformas"].values():
        for v in dados["videos"]:
            v["roteiro"] = por_id.get(v["id"])


def ler(perfil) -> dict:
    arquivo = perfil.controle / "estatisticas.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def totais(dados: dict) -> dict:
    """Somas por plataforma para os cartões do topo da guia."""
    saida = {}
    for p, d in (dados.get("plataformas") or {}).items():
        vids = d["videos"]
        com_ret = [v["retencao_pct"] for v in vids if v.get("retencao_pct") is not None]
        saida[p] = {**d["conta"], "n_videos": len(vids),
                    "visualizacoes_videos": sum(v.get("visualizacoes") or 0 for v in vids),
                    "curtidas": sum(v.get("curtidas") or 0 for v in vids),
                    "comentarios": sum(v.get("comentarios") or 0 for v in vids),
                    "compartilhamentos": sum(v.get("compartilhamentos") or 0 for v in vids),
                    "minutos": sum(v.get("minutos") or 0 for v in vids),
                    "retencao_media": round(sum(com_ret) / len(com_ret), 1) if com_ret else None}
    return saida
