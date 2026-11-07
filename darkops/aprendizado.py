"""Aprendizado automático: a cada 15 vídeos no ar, o canal descobre o que funcionou e se ajusta sozinho.

Ciclo:
  1. Todo canal novo começa com uma leva de 15 vídeos (LEVA_INICIAL).
  2. Quando 15 vídeos novos estão publicados há pelo menos DIAS_NO_AR dias, `python -m darkops aprender`
     (o n8n roda todo dia às 20h) busca os números nas plataformas e ranqueia os vídeos do ciclo.
  3. O terço de cima é "funcionou"; o de baixo, "não funcionou". A IA compara os dois grupos e propõe mudanças
     tiradas SÓ do que funcionou (nunca copia o que foi mal).
  4. As mudanças são aplicadas sozinhas (decisão do dono em 2026-10-31), sempre validadas pelos mesmos campos e
     valores permitidos da análise manual, e ficam registradas com o valor anterior: `aprender-desfazer` (ou o botão
     Desfazer no Estúdio) volta tudo do último ciclo.

Tudo fica em perfis/<id>/controle/aprendizado.json; a tela é Estúdio > Resultados > O que funcionou.
"""
import json
import re
import subprocess
import time
from datetime import date, datetime

LEVA_INICIAL = 15
DIAS_NO_AR = 2
MINIMO_COM_DADOS = 6   # menos que isso com visualizações, não dá para separar o que funcionou
ROTULOS = {"duracao_s": "duração (s)", "ritmo_corte_s": "corte de cena (s)", "velocidade": "velocidade da voz",
           "edicao": "edição", "tema_cards": "tema dos cards", "legenda_tamanho": "legenda", "estilo": "estilo das imagens",
           "horarios": "horários", "leva_quantidade": "vídeos por leva"}


def _arquivo(perfil):
    return perfil.controle / "aprendizado.json"


def ler(perfil) -> dict:
    try:
        return json.loads(_arquivo(perfil).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar(perfil, dados: dict) -> None:
    perfil.controle.mkdir(parents=True, exist_ok=True)
    _arquivo(perfil).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _publicados(perfil) -> list[dict]:
    """Roteiros publicados, na ordem em que foram ao ar (uma linha por roteiro, com a data do testes.csv)."""
    from .fila import historico
    vistos, saida = set(), []
    for linha in historico(perfil):
        nome = linha.get("roteiro")
        if nome and nome not in vistos:
            vistos.add(nome)
            saida.append({"arquivo": nome, "data": linha.get("data_publicacao", ""), "titulo": linha.get("video", ""),
                          "duracao_s": linha.get("duracao_s", "")})
    return saida


def progresso(perfil) -> dict:
    """Quantos vídeos do ciclo atual já estão no ar e quando a próxima análise roda."""
    publicados = _publicados(perfil)
    ja = ler(perfil).get("analisados", 0)
    ciclo = publicados[ja:]
    faltam = max(0, LEVA_INICIAL - len(ciclo))
    pronto_em = None
    if not faltam:
        ultimo = datetime.strptime(ciclo[LEVA_INICIAL - 1]["data"], "%Y-%m-%d").date()
        pronto_em = date.fromordinal(ultimo.toordinal() + DIAS_NO_AR)
    return {"no_ar": min(len(ciclo), LEVA_INICIAL), "meta": LEVA_INICIAL, "faltam": faltam,
            "pronto_em": pronto_em.isoformat() if pronto_em else None,
            "pronto": not faltam and pronto_em <= date.today(), "ciclos": len(ler(perfil).get("ciclos", []))}


# ---------- ranking ----------

def _videos_do_ciclo(perfil, arquivos: list[str], estat: dict) -> list[dict]:
    """Junta YouTube e Instagram de cada roteiro do ciclo e acrescenta o que o roteiro tinha (para a comparação)."""
    slug_de = {}
    for nome in arquivos:
        caminho = perfil.publicados / nome
        try:
            roteiro = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            roteiro = {}
        slug_de[roteiro.get("slug") or caminho.stem] = (nome, roteiro)
    por_slug: dict[str, dict] = {}
    for plataforma, dados in (estat.get("plataformas") or {}).items():
        for v in dados.get("videos", []):
            slug = v.get("roteiro")
            if slug not in slug_de:
                continue
            item = por_slug.setdefault(slug, {"slug": slug, "titulo": v.get("titulo"), "links": {},
                                              "visualizacoes": 0, "curtidas": 0, "comentarios": 0,
                                              "compartilhamentos": 0, "retencoes": [], "ids": [],
                                              "negativos": 0, "positivos": 0, "classificados": 0, "perguntas": 0,
                                              "correcoes": 0})
            item["links"][plataforma] = v.get("url")
            item["ids"].append(v["id"])
            r = v.get("comentarios_resumo") or {}
            if r.get("positivos_pct") is not None:  # o que o público disse (comentarios.py)
                n = r["coletados"] - r.get("spam", 0)  # a porcentagem já é sem o spam
                item["classificados"] += n
                item["positivos"] += round(r["positivos_pct"] * n / 100)
                item["negativos"] += round(r["negativos_pct"] * n / 100)
            item["perguntas"] += r.get("perguntas", 0)
            item["correcoes"] += r.get("correcoes", 0)
            for chave in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos"):
                item[chave] += v.get(chave) or 0
            if v.get("retencao_pct") is not None:
                item["retencoes"].append(v["retencao_pct"])
    saida = []
    for slug, item in por_slug.items():
        nome, roteiro = slug_de[slug]
        cenas = roteiro.get("cenas") or []
        retencoes = item.pop("retencoes")
        n = item.pop("classificados")
        pos, neg = item.pop("positivos"), item.pop("negativos")
        item["positivos_pct"] = round(100 * pos / n) if n else None
        item["negativos_pct"] = round(100 * neg / n) if n else None
        retencao = round(sum(retencoes) / len(retencoes), 1) if retencoes else None
        meta = roteiro.get("metadados") or {}
        saida.append({**item, "retencao_pct": retencao, "arquivo": nome,
                      "titulo": roteiro.get("titulo") or item["titulo"],
                      "gancho": str((cenas[0].get("texto") or cenas[0].get("narracao") or "") if cenas else "")[:200],
                      "cenas": len(cenas), "velocidade": roteiro.get("velocidade"),
                      "duracao_s": meta.get("duracao_s") or roteiro.get("duracao_s"),
                      "tags": (meta.get("youtube") or {}).get("tags", [])[:8] if isinstance(meta.get("youtube"), dict) else []})
    return saida


def _pontuar(videos: list[dict]) -> list[dict]:
    """Nota de 0 a 100 pela posição em cada métrica (robusto a um vídeo que explode): visualizações pesam 50%,
    retenção 30% (quando existe) e engajamento (curtidas, comentários x2, compartilhamentos x3 por visualização) 20%.
    Comentários negativos (quando a triagem de comentarios.py já classificou) não contam como engajamento."""
    def posicao(valores: list[float]) -> list[float]:
        ordem = sorted(valores)
        return [100 * ordem.index(v) / max(1, len(ordem) - 1) for v in valores]

    vis = posicao([v["visualizacoes"] for v in videos])
    eng = posicao([(v["curtidas"] + 2 * v["comentarios"] * (1 - (v.get("negativos_pct") or 0) / 100)
                    + 3 * v["compartilhamentos"]) / max(1, v["visualizacoes"])
                   for v in videos])
    com_ret = all(v["retencao_pct"] is not None for v in videos)
    ret = posicao([v["retencao_pct"] for v in videos]) if com_ret else [0] * len(videos)
    for v, a, b, c in zip(videos, vis, ret, eng):
        v["nota"] = round(0.5 * a + 0.3 * b + 0.2 * c if com_ret else 0.7 * a + 0.3 * c)
    return sorted(videos, key=lambda v: v["nota"], reverse=True)


# ---------- IA ----------

def _pedir_ia(perfil, bons: list[dict], ruins: list[dict]) -> dict | None:
    from .analise import CAMPOS, _bloco_comentarios
    from .leva import _claude, rodar_claude
    if not _claude():
        return None
    d = perfil.dados
    config_canal = {k: d.get(k) for k in ("nicho", "formato", "duracao_s", "ritmo_corte_s", "velocidade", "edicao",
                                          "tema_cards", "estilo", "horarios", "diretrizes") if d.get(k) is not None}
    resumo = lambda vs: [{k: v.get(k) for k in ("titulo", "gancho", "duracao_s", "cenas", "velocidade", "nota",  # noqa: E731
                                               "visualizacoes", "retencao_pct", "curtidas", "comentarios",
                                               "positivos_pct", "negativos_pct", "perguntas", "correcoes",
                                               "compartilhamentos", "tags")} for v in vs]
    pedido = (
        "Você é analista de um canal de vídeos curtos. Os vídeos abaixo são do mesmo ciclo de publicação, separados "
        "pela nota (visualizações, retenção e engajamento). Compare o grupo que FUNCIONOU com o que NÃO FUNCIONOU e "
        "descubra o padrão: tema, tipo de gancho, duração, ritmo, título. Não invente números.\n"
        "Depois proponha de 1 a 5 mudanças para os próximos vídeos usando APENAS o que funcionou: cada mudança precisa "
        "citar os vídeos que funcionaram que a justificam. Nunca proponha repetir algo que só aparece no grupo que "
        "não funcionou.\n"
        "Responda APENAS com um JSON: {\"resumo\": \"2 a 4 frases\", \"funcionou\": [\"padrão com evidência\"], "
        "\"nao_funcionou\": [\"padrão com evidência\"], \"mudancas\": [{\"tipo\": \"perfil\" ou \"diretriz\", "
        "\"campo\": \"(só perfil)\", \"valor\": \"...\", \"motivo\": \"...\"}]}\n"
        f"Campos que podem mudar (tipo perfil): {CAMPOS}. Mudança de conteúdo dos roteiros (temas, ganchos, títulos) é "
        "tipo diretriz, com a orientação em valor.\n"
        f"Configuração atual: {json.dumps(config_canal, ensure_ascii=False)}\n"
        f"FUNCIONOU: {json.dumps(resumo(bons), ensure_ascii=False)}\n"
        f"NÃO FUNCIONOU: {json.dumps(resumo(ruins), ensure_ascii=False)}"
        + _bloco_comentarios(perfil, {i for v in bons + ruins for i in v.get("ids", [])})
    )
    try:
        proc = rodar_claude(pedido, timeout=6 * 60)  # sem ferramentas: só os números que vão no pedido
        bloco = re.search(r"\{.*\}", proc.stdout, re.S)
        return json.loads(bloco.group(0)) if bloco else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, SystemExit, OSError):
        return None


# ---------- ciclo ----------

def _aplicar(perfil, mudancas: list[dict]) -> list[dict]:
    """Valida e aplica; devolve só as aplicadas, com o valor anterior para o Desfazer."""
    from .analise import _validar
    aplicadas, novos = [], {}
    diretrizes = list(perfil.dados.get("diretrizes") or [])
    for m in mudancas[:5]:
        tipo = m.get("tipo") if m.get("tipo") in ("perfil", "diretriz") else "diretriz"
        motivo = str(m.get("motivo", ""))[:500]
        if tipo == "perfil":
            campo = str(m.get("campo", ""))
            valor = _validar(perfil, campo, m.get("valor"))
            if valor is None or valor == perfil.dados.get(campo) or campo in novos:
                continue  # fora do permitido ou sem efeito: não entra
            novos[campo] = valor
            aplicadas.append({"tipo": "perfil", "campo": campo, "antes": perfil.dados.get(campo), "depois": valor,
                              "motivo": motivo})
        else:
            texto = str(m.get("valor") or "").strip()[:300]
            if not texto or texto in diretrizes:
                continue
            diretrizes.append(texto)
            aplicadas.append({"tipo": "diretriz", "valor": texto, "motivo": motivo})
    if any(a["tipo"] == "diretriz" for a in aplicadas):
        novos["diretrizes"] = diretrizes[-20:]
    if novos:
        perfil.salvar(novos)
    return aplicadas


def rodar(perfil, forcar: bool = False) -> dict:
    """Roda o ciclo se ele estiver pronto (ou `forcar`). Devolve o ciclo gravado, ou {"esperando": ...}."""
    prog = progresso(perfil)
    if not prog["pronto"] and not forcar:
        return {"esperando": prog}
    from .estatisticas import coletar
    publicados = _publicados(perfil)
    estado = ler(perfil)
    ja = estado.get("analisados", 0)
    ciclo_arquivos = [p["arquivo"] for p in publicados[ja:ja + LEVA_INICIAL]] or [p["arquivo"] for p in publicados[-LEVA_INICIAL:]]
    estat = coletar(perfil)
    videos = [v for v in _videos_do_ciclo(perfil, ciclo_arquivos, estat) if v["visualizacoes"] > 0]
    ciclo = {"quando": time.strftime("%Y-%m-%d %H:%M"), "numero": len(estado.get("ciclos", [])) + 1,
             "videos_no_ciclo": len(ciclo_arquivos), "com_dados": len(videos), "funcionou": [], "nao_funcionou": [],
             "padroes_bons": [], "padroes_ruins": [], "mudancas": [], "desfeito": False}
    if len(videos) < MINIMO_COM_DADOS:
        ciclo["resumo"] = (f"Só {len(videos)} vídeo(s) do ciclo têm números nas plataformas (mínimo {MINIMO_COM_DADOS}). "
                           "Confira se as contas estão conectadas e tente de novo em alguns dias. Nada foi mudado.")
    else:
        ranking = _pontuar(videos)
        terco = max(2, len(ranking) // 3)
        bons, ruins = ranking[:terco], ranking[-terco:]
        resposta = _pedir_ia(perfil, bons, ruins)
        ciclo.update({"funcionou": bons, "nao_funcionou": ruins})
        if not resposta:
            ciclo["resumo"] = "A IA não respondeu agora; o ranking está abaixo e nada foi mudado. Tente de novo mais tarde."
        else:
            ciclo.update({"resumo": str(resposta.get("resumo", ""))[:1200],
                          "padroes_bons": [str(x)[:300] for x in resposta.get("funcionou", [])][:6],
                          "padroes_ruins": [str(x)[:300] for x in resposta.get("nao_funcionou", [])][:6],
                          "mudancas": _aplicar(perfil, resposta.get("mudancas") or [])})
    estado.setdefault("ciclos", []).append(ciclo)
    if ciclo["mudancas"] or len(videos) >= MINIMO_COM_DADOS:
        estado["analisados"] = ja + len(ciclo_arquivos)  # o próximo ciclo conta 15 vídeos a partir daqui
    _gravar(perfil, estado)
    _avisar(perfil, ciclo)
    return ciclo


def _avisar(perfil, ciclo: dict) -> None:
    from . import whatsapp
    linhas = [f"🧠 *{perfil.dados['nome']}*: análise dos {ciclo['videos_no_ciclo']} vídeos do ciclo {ciclo['numero']}."]
    if ciclo["funcionou"]:
        linhas.append("Funcionou: " + "; ".join(v["titulo"] for v in ciclo["funcionou"][:3]))
    if ciclo["mudancas"]:
        linhas.append("Mudei sozinho, com base só no que funcionou:")
        for m in ciclo["mudancas"]:
            linhas.append(f"• {ROTULOS.get(m['campo'], m['campo'])}: {m['antes']} → {m['depois']}" if m["tipo"] == "perfil"
                          else f"• Roteiros: {m['valor']}")
        linhas.append("Para voltar atrás: Estúdio > Resultados > O que funcionou > Desfazer.")
    else:
        linhas.append(ciclo.get("resumo", "Nada foi mudado."))
    whatsapp.enviar("\n".join(linhas))


def desfazer(perfil) -> int:
    """Volta as mudanças do último ciclo (campos para o valor anterior; diretrizes acrescentadas saem)."""
    estado = ler(perfil)
    ciclo = next((c for c in reversed(estado.get("ciclos", [])) if c["mudancas"] and not c["desfeito"]), None)
    if not ciclo:
        return 0
    novos = {m["campo"]: m["antes"] for m in ciclo["mudancas"] if m["tipo"] == "perfil"}
    tirar = {m["valor"] for m in ciclo["mudancas"] if m["tipo"] == "diretriz"}
    if tirar:
        novos["diretrizes"] = [x for x in perfil.dados.get("diretrizes") or [] if x not in tirar]
    perfil.salvar(novos)
    ciclo.update({"desfeito": True, "desfeito_em": time.strftime("%Y-%m-%d %H:%M")})
    _gravar(perfil, estado)
    return len(ciclo["mudancas"])
