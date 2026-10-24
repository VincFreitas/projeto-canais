"""A IA analisa as estatísticas do canal e sugere mudanças; nada muda sem a sua aprovação, uma por uma.

  python -m darkops analisar      gera as sugestões (ficam pendentes em controle/sugestoes.json)

Tipos de sugestão:
- "perfil": muda um campo do padrão do canal (duração, ritmo, velocidade, edição, tema dos cards, horários...).
  Só é aplicada quando você aprova, e só nos campos e valores permitidos abaixo.
- "diretriz": uma orientação para os próximos roteiros ("abra com uma pergunta", "fale de animais").
  Aprovada, entra nas diretrizes do canal, que o /escrever-roteiro e as levas seguem.
"""
import json
import re
import subprocess
import time
import uuid

from . import config


def _validar(perfil, campo: str, valor):
    """Devolve o valor convertido se o campo e o valor forem permitidos, senão None."""
    from .perfis import DURACOES, EDICOES, RITMOS, TAMANHOS_LEGENDA, TEMAS_CARDS
    from .visuais import ESTILOS_IA
    d = perfil.dados
    try:
        if campo == "duracao_s":
            v = int(valor)
            return v if v in DURACOES[d.get("formato", "vertical")] else None
        if campo == "ritmo_corte_s":
            v = int(valor)
            return v if v in RITMOS else None
        if campo == "leva_quantidade":
            v = int(valor)
            return v if 1 <= v <= 14 else None
        if campo == "velocidade":
            return valor if re.match(r"^[+-]\d{1,2}%$", str(valor)) and abs(int(str(valor)[:-1])) <= 25 else None
        if campo == "edicao":
            return valor if valor in EDICOES else None
        if campo == "tema_cards":
            return valor if valor in TEMAS_CARDS else None
        if campo == "legenda_tamanho":
            return valor if valor in TAMANHOS_LEGENDA else None
        if campo == "estilo":
            return valor if valor in ESTILOS_IA or valor == "" else None
        if campo == "horarios":
            lista = [h.strip() for h in (valor if isinstance(valor, list) else str(valor).split(","))]
            return lista if lista and all(re.match(r"^\d{1,2}:\d{2}$", h) for h in lista) else None
        if campo.startswith("persona_"):
            from .perfis import PERSONA
            return str(valor).strip()[:300] if campo in [c for c, _, _ in PERSONA] else None
    except (ValueError, TypeError):
        return None
    return None


CAMPOS = ("duracao_s, ritmo_corte_s, velocidade (ex.: +10%), edicao (simples/leve/pro), tema_cards (padrao/arquivo_frio/"
          "jornal_antigo/moderno_limpo), legenda_tamanho (pequena/media/grande), estilo, horarios (lista HH:MM), "
          "leva_quantidade, persona_narrador, persona_tom, persona_publico, persona_abertura, persona_linguagem, persona_titulos")


def _pedir_ia(perfil, estat: dict) -> dict | None:
    from .leva import _claude, rodar_claude
    if not _claude():
        return None
    d = perfil.dados
    config_canal = {k: d.get(k) for k in ("nicho", "formato", "duracao_s", "ritmo_corte_s", "velocidade", "edicao",
                                          "tema_cards", "estilo", "horarios", "diretrizes") if d.get(k) is not None}
    pedido = (
        "Você é analista de um canal de vídeos curtos. Analise as estatísticas abaixo (YouTube e Instagram) e sugira de "
        "1 a 6 mudanças concretas, cada uma com o motivo baseado nos números (cite o vídeo ou a métrica). Use as regras "
        "de alcance do projeto: gancho em 1 a 2 s, retenção, envios e comentários pesam muito. Não invente números e "
        "diga quando a amostra for pequena demais para concluir.\n"
        "Responda APENAS com um JSON: {\"resumo\": \"3 a 5 frases\", \"sugestoes\": [{\"titulo\": \"...\", "
        "\"motivo\": \"...\", \"tipo\": \"perfil\" ou \"diretriz\", \"campo\": \"(só para perfil)\", \"valor\": \"...\"}]}\n"
        f"Campos que podem mudar (tipo perfil): {CAMPOS}. Para mudanças de conteúdo dos roteiros, use tipo diretriz "
        "com o texto da orientação em valor.\n"
        f"Configuração atual: {json.dumps(config_canal, ensure_ascii=False)}\n"
        f"Estatísticas: {json.dumps(estat, ensure_ascii=False)[:12000]}"
    )
    try:
        proc = rodar_claude(pedido, timeout=6 * 60)  # sem ferramentas: só lê os números que vão no pedido
        bloco = re.search(r"\{.*\}", proc.stdout, re.S)
        return json.loads(bloco.group(0)) if bloco else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def analisar(perfil) -> dict:
    from .estatisticas import coletar, ler
    estat = ler(perfil) or coletar(perfil)
    videos = [v for d in estat.get("plataformas", {}).values() for v in d["videos"]]
    com_dados = [v for v in videos if (v.get("visualizacoes") or 0) > 0]
    if len(com_dados) < 2:
        resultado = {"gerado": time.strftime("%Y-%m-%d %H:%M"), "sugestoes": [],
                     "resumo": f"Ainda não há dados suficientes: {len(com_dados)} vídeo(s) com visualizações. "
                               "A análise começa a valer a partir de 2 ou 3 vídeos publicados com alguns dias no ar."}
    else:
        resposta = _pedir_ia(perfil, estat) or {"resumo": "O Claude Code não respondeu; tente de novo mais tarde.",
                                                "sugestoes": []}
        sugestoes = []
        for s in resposta.get("sugestoes", [])[:6]:
            tipo = s.get("tipo") if s.get("tipo") in ("perfil", "diretriz") else "diretriz"
            item = {"id": uuid.uuid4().hex[:8], "titulo": str(s.get("titulo", ""))[:120],
                    "motivo": str(s.get("motivo", ""))[:600], "tipo": tipo, "estado": "pendente"}
            if tipo == "perfil":
                valor = _validar(perfil, str(s.get("campo", "")), s.get("valor"))
                if valor is None:
                    continue  # campo ou valor fora do permitido: a sugestão é descartada
                item.update({"campo": s["campo"], "valor": valor, "valor_atual": perfil.dados.get(s["campo"])})
            else:
                item["valor"] = str(s.get("valor") or s.get("titulo", ""))[:300]
            sugestoes.append(item)
        resultado = {"gerado": time.strftime("%Y-%m-%d %H:%M"), "resumo": str(resposta.get("resumo", ""))[:1500],
                     "sugestoes": sugestoes}
    (perfil.controle / "sugestoes.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


def ler_sugestoes(perfil) -> dict:
    arquivo = perfil.controle / "sugestoes.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def decidir(perfil, sugestao_id: str, aprovar: bool) -> dict | None:
    """Aprova (e aplica) ou recusa uma sugestão. Devolve a sugestão decidida."""
    dados = ler_sugestoes(perfil)
    item = next((s for s in dados.get("sugestoes", []) if s["id"] == sugestao_id and s["estado"] == "pendente"), None)
    if not item:
        return None
    if aprovar:
        if item["tipo"] == "perfil":
            valor = _validar(perfil, item["campo"], item["valor"])
            if valor is None:
                return None
            perfil.salvar({item["campo"]: valor})
        else:
            diretrizes = list(perfil.dados.get("diretrizes") or [])
            if item["valor"] not in diretrizes:
                perfil.salvar({"diretrizes": (diretrizes + [item["valor"]])[-20:]})
    item.update({"estado": "aprovada" if aprovar else "recusada", "decidido": time.strftime("%Y-%m-%d %H:%M")})
    (perfil.controle / "sugestoes.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return item
