"""Descrição e tags de cada vídeo: escritas por você ou criadas pela IA, com as regras de alcance de cada plataforma.

  python -m darkops descricao <roteiro.json> [--refazer]   cria (pela IA) a descrição e as tags que estiverem no modo automático

Ficam num arquivo ao lado, perfis/<id>/controle/descricoes/<roteiro>.json, para não marcar a prévia como
desatualizada a cada ajuste de texto. As regras seguem docs/viralizacao.md:
- 1ª linha com a palavra principal e o gancho (o Instagram corta a legenda em ~125 caracteres);
- de 3 a 5 hashtags no fim (o Instagram aceita no máximo 5; o YouTube ignora todas acima de 60);
- tags do YouTube só com termos do vídeo (pesam pouco; servem para grafias erradas comuns), até 500 caracteres;
- nada de lista de palavras-chave na descrição (o YouTube trata como spam).
"""
import json
import re
import subprocess
from pathlib import Path

from . import config

LIMITE_LINHA_1 = 125
MAX_HASHTAGS = 5
MAX_TAGS_CHARS = 500
MODOS = {"ia": "A IA cria automaticamente", "manual": "Eu escrevo"}
# palavras comuns que não dizem o assunto do vídeo (ficam fora das tags e da checagem do título)
GENERICAS = {"dentro", "fora", "sozinho", "sozinha", "lugar", "mesmo", "mesma", "coisa", "coisas", "sempre", "nunca",
             "agora", "depois", "antes", "tudo", "nada", "parte", "jeito", "forma", "vezes", "todo", "toda", "isso",
             "você", "então", "esse", "essa", "quando", "porque", "pronto", "comenta", "acabou"}


def _arquivo(perfil, roteiro_nome: str) -> Path:
    return perfil.controle / "descricoes" / (Path(roteiro_nome).stem + ".json")


def ler(perfil, roteiro_nome: str) -> dict:
    caminho = _arquivo(perfil, roteiro_nome)
    dados = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    return {"descricao_modo": "ia", "tags_modo": "ia", "descricao": "", "tags": [], "hashtags": [], **dados}


def salvar(perfil, roteiro_nome: str, dados: dict) -> None:
    caminho = _arquivo(perfil, roteiro_nome)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({**ler(perfil, roteiro_nome), **dados}, ensure_ascii=False, indent=2), encoding="utf-8")


def _limpar_tags(texto_ou_lista) -> list[str]:
    itens = texto_ou_lista if isinstance(texto_ou_lista, list) else re.split(r"[,\n]", texto_ou_lista or "")
    tags = []
    for t in itens:
        t = t.strip().lstrip("#").strip()
        if t and t.lower() not in [x.lower() for x in tags]:
            tags.append(t[:60])
    return tags


def _limpar_hashtags(itens) -> list[str]:
    saida = []
    for h in itens or []:
        h = "#" + re.sub(r"[^\wÀ-ÿ]", "", str(h).lstrip("#"))
        if len(h) > 1 and h.lower() not in [x.lower() for x in saida]:
            saida.append(h)
    return saida[:MAX_HASHTAGS]


def checar(descricao: str, tags: list[str], hashtags: list[str]) -> list[str]:
    """Avisos sobre os limites e as boas práticas (vazia = tudo certo)."""
    avisos = []
    linha_1 = (descricao or "").strip().splitlines()[0] if (descricao or "").strip() else ""
    if not linha_1:
        avisos.append("a descrição está vazia")
    elif len(linha_1) > LIMITE_LINHA_1:
        avisos.append(f"a 1ª linha tem {len(linha_1)} caracteres; o Instagram corta em ~{LIMITE_LINHA_1}")
    no_texto = re.findall(r"#\w+", descricao or "")
    if len(set(no_texto) | set(hashtags)) > MAX_HASHTAGS:
        avisos.append(f"mais de {MAX_HASHTAGS} hashtags: o Instagram não aceita e o excesso não ajuda no YouTube")
    if len(", ".join(tags)) > MAX_TAGS_CHARS:
        avisos.append(f"as tags passam de {MAX_TAGS_CHARS} caracteres (limite do YouTube)")
    if len(re.findall(r",", descricao or "")) > 25:
        avisos.append("a descrição parece uma lista de palavras-chave (o YouTube trata como spam)")
    return avisos


def _regras(roteiro: dict, perfil) -> dict:
    """Versão sem IA: usada quando o Claude Code não está disponível."""
    from .entrada import _conteudo, _tema
    texto = " ".join(c.get("texto", "") for c in roteiro.get("cenas", []))
    tema = _tema(texto)
    titulo = roteiro.get("titulo") or roteiro.get("manchete") or ""
    primeira = (roteiro.get("manchete") or titulo).strip()
    resumo = roteiro.get("cenas", [{}])[0].get("texto", "").strip()
    linhas = [primeira[:LIMITE_LINHA_1], "", resumo, "", f"Segue {perfil.dados.get('arroba', '')} para mais curiosidades."]
    fontes = roteiro.get("fontes") or []
    if fontes:
        linhas += ["", "Fontes:"] + [f"- {f}" for f in fontes]
    from collections import Counter
    # as palavras que mais se repetem dizem o assunto melhor que as mais compridas
    contagem = Counter(p for p in _conteudo(texto) if p not in GENERICAS)
    palavras = list(dict.fromkeys([tema] + [p for p, _ in contagem.most_common(12)]))[:8]
    nicho = (perfil.dados.get("nicho") or "curiosidades").split(",")[0].strip()
    hashtags = _limpar_hashtags([nicho, tema, "vocesabia"])
    return {"descricao": "\n".join(linhas), "tags": _limpar_tags([titulo, nicho] + palavras), "hashtags": hashtags}


def _com_ia(roteiro: dict, perfil) -> dict | None:
    from .leva import _claude
    from .perfis import resumo_persona
    claude = _claude()
    if not claude:
        return None
    falas = "\n".join(c.get("texto", "") for c in roteiro.get("cenas", []))
    pedido = (
        "Escreva a descrição, as tags e as hashtags para publicar este vídeo curto no YouTube e no Instagram. "
        "Responda APENAS com um JSON: {\"descricao\": \"...\", \"tags\": [\"...\"], \"hashtags\": [\"#...\"]}.\n"
        f"Regras: a 1ª linha da descrição tem até {LIMITE_LINHA_1} caracteres, traz a palavra que as pessoas buscariam "
        "e um gancho que dá vontade de assistir, sem entregar a resposta; depois 2 ou 3 frases que resumem o que o vídeo "
        "ensina, uma chamada para comentar ou mandar para alguém, e as fontes abaixo. Nada de lista de palavras-chave, "
        "nada de promessa que o vídeo não cumpre. Tags: de 8 a 15 termos do assunto, do mais específico ao mais geral, "
        f"incluindo grafias erradas comuns, até {MAX_TAGS_CHARS} caracteres no total. Hashtags: de 3 a 5, ligadas ao "
        f"assunto (nunca mais de {MAX_HASHTAGS}). Português do Brasil.\n"
        + (f"Personalidade do canal: {resumo_persona(perfil.dados)}\n" if resumo_persona(perfil.dados) else "")
        + f"Canal: {perfil.dados.get('nome')} ({perfil.dados.get('arroba')}), nicho {perfil.dados.get('nicho')}.\n"
        f"Título: {roteiro.get('titulo')}\nNarração:\n{falas}\nFontes: {', '.join(roteiro.get('fontes') or []) or 'nenhuma'}"
    )
    try:
        proc = subprocess.run([claude, "-p", pedido], cwd=config.RAIZ, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=5 * 60)
        bloco = re.search(r"\{.*\}", proc.stdout, re.S)
        dados = json.loads(bloco.group(0)) if bloco else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    if not dados or not dados.get("descricao"):
        return None
    return {"descricao": str(dados["descricao"]).strip(), "tags": _limpar_tags(dados.get("tags", [])),
            "hashtags": _limpar_hashtags(dados.get("hashtags", []))}


def gerar(perfil, caminho: Path, refazer: bool = False) -> dict:
    """Preenche o que estiver no modo automático e ainda vazio (ou tudo, com refazer)."""
    atual = ler(perfil, caminho.name)
    precisa_desc = atual["descricao_modo"] == "ia" and (refazer or not atual["descricao"])
    precisa_tags = atual["tags_modo"] == "ia" and (refazer or not atual["tags"])
    if not (precisa_desc or precisa_tags):
        return atual
    roteiro = json.loads(caminho.read_text(encoding="utf-8"))
    novo = _com_ia(roteiro, perfil)
    origem = "claude" if novo else "regras"
    novo = novo or _regras(roteiro, perfil)
    mudancas = {"gerado_por": origem}
    if precisa_desc:
        mudancas["descricao"] = novo["descricao"]
    if precisa_tags:
        mudancas["tags"], mudancas["hashtags"] = novo["tags"], novo["hashtags"]
    salvar(perfil, caminho.name, mudancas)
    return ler(perfil, caminho.name)


def para_publicar(perfil, caminho: Path) -> dict:
    """O que a publicação usa: garante que nada vá ao ar sem descrição (gera na hora se faltar)."""
    dados = gerar(perfil, caminho)
    if not dados["descricao"].strip():
        dados = {**dados, **_regras(json.loads(caminho.read_text(encoding="utf-8")), perfil)}
    return dados
