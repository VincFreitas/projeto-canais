"""Auditoria do roteiro antes de ir para a fila: gancho, estrutura e voz do canal.

Três checagens, as mesmas que um roteirista faria:
- Gancho: a 1ª fala cabe nos 3 primeiros segundos, não começa com abertura genérica ("oi", "hoje eu trago",
  "neste vídeo") e cria tensão (pergunta, número, contraste ou algo que parece errado).
- Estrutura: Gancho, Problema, Solução, Prova e CTA. A prova é um dado, nome, data ou fonte; o CTA do fim pede
  uma ação com palavra-chave ("Comenta NAZCA").
- Voz: o canal tem uma voz própria. referencias_de_voz devolve as narrações dos vídeos que mais funcionaram, para
  o pedido de roteiro imitar o ritmo e o jeito de falar do próprio canal (não o de outro canal).

Uso: python -m darkops roteiro-auditar perfis/<perfil>/fila/<arquivo>.json (sai com erro se algo estiver fora).
"""
import json
import re
from pathlib import Path

# 3 segundos de fala: a voz fala ~2,5 palavras por segundo
GANCHO_MAX_PALAVRAS = 14
GENERICOS = ("oi", "olá", "ola", "fala galera", "e aí", "e ai", "hoje eu", "hoje vamos", "hoje vou", "neste vídeo",
             "nesse vídeo", "no vídeo de hoje", "você sabia", "voce sabia", "bem-vindo", "bem vindo", "seja bem",
             "vamos falar", "eu trago", "trago pra vocês", "trago para vocês", "sabia que")
TENSAO = re.compile(r"\?|\d|\b(nunca|ninguém|ninguem|sem|mas|errado|impossível|impossivel|segredo|ninguém sabe|"
                    r"proibid|mistério|misterio|sumiu|desapareceu|até hoje|ate hoje|por que|como)\b", re.I)
CTA = re.compile(r"\b(comenta|comente|escreve|escreva|manda|salva|salve|segue|siga|compartilha)\b", re.I)
PALAVRA_CHAVE = re.compile(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,}\b")
PROVA = re.compile(r"\d|\b(mil|cem|cento|milhões|milhoes|metros|toneladas|anos|séculos|seculos|graus|segundo|pesquisa|estudo|arqueólog|cientista|registro|documento|teste|confirm|"
                   r"descobri|encontr|mediu|datação|datacao)\w*", re.I)


def _fala(cena: dict) -> str:
    return str(cena.get("texto") or cena.get("narracao") or "").strip()


def _primeira_frase(texto: str) -> str:
    return re.split(r"(?<=[.!?…])\s", texto, maxsplit=1)[0]


def auditar(roteiro: dict) -> list[dict]:
    """Lista de problemas: {"parte", "nivel" ("erro" trava, "aviso" só informa), "texto"}."""
    cenas = roteiro.get("cenas") or []
    falas = [_fala(c) for c in cenas if _fala(c)]
    problemas: list[dict] = []
    if not falas:
        return [{"parte": "roteiro", "nivel": "erro", "texto": "o roteiro não tem fala"}]

    # 1. gancho
    gancho = _primeira_frase(falas[0])
    inicio = gancho.lower().strip("\"'“ ")
    generico = next((g for g in GENERICOS if inicio.startswith(g)), None)
    if generico:
        problemas.append({"parte": "gancho", "nivel": "erro",
                          "texto": f"abertura genérica (\"{generico}...\"): comece pelo fato estranho, pela pergunta "
                                   "ou pelo número"})
    if len(gancho.split()) > GANCHO_MAX_PALAVRAS:
        problemas.append({"parte": "gancho", "nivel": "aviso",
                          "texto": f"a 1ª frase tem {len(gancho.split())} palavras (passa dos 3 segundos); corte "
                                   f"para até {GANCHO_MAX_PALAVRAS}"})
    if not TENSAO.search(falas[0]):
        problemas.append({"parte": "gancho", "nivel": "aviso",
                          "texto": "a 1ª cena não tem tensão (pergunta, número, contraste ou algo que parece "
                                   "errado)"})

    # 2. estrutura: problema e solução no meio, prova com dado, CTA com palavra-chave no fim
    meio = " ".join(falas[1:-1])
    if len(falas) >= 4 and not re.search(r"\b(mas|só que|so que|problema|então|entao|por isso|o truque|"
                                         r"a resposta|o segredo)\b", meio, re.I):
        problemas.append({"parte": "estrutura", "nivel": "aviso",
                          "texto": "o meio não marca a virada (problema → solução): use \"mas\", \"então\", "
                                   "\"o truque é\""})
    if not PROVA.search(meio) or not roteiro.get("fontes"):
        problemas.append({"parte": "prova", "nivel": "erro" if not roteiro.get("fontes") else "aviso",
                          "texto": "falta a prova: um dado, nome, data ou teste, com o link em \"fontes\""})
    fim = falas[-1]
    if not CTA.search(fim):
        problemas.append({"parte": "cta", "nivel": "erro",
                          "texto": "o fim não pede ação: termine com \"Comenta PALAVRA...\" ou \"Salva pra...\""})
    elif re.search(r"\b(comenta|comente|escreve|escreva)\b", fim, re.I) and not PALAVRA_CHAVE.search(fim):
        problemas.append({"parte": "cta", "nivel": "aviso",
                          "texto": "o CTA de comentário não tem palavra-chave em MAIÚSCULAS (ex.: Comenta NAZCA)"})
    return problemas


def referencias_de_voz(perfil, quantidade: int = 3, limite: int = 700) -> list[str]:
    """Narrações dos vídeos do canal que mais funcionaram (nota do aprendizado), para o roteiro novo soar como o
    canal. Sem números ainda, usa os últimos publicados."""
    from .aprendizado import _pontuar, _publicados, _videos_do_ciclo
    from .estatisticas import ler
    publicados = _publicados(perfil)
    arquivos = [p["arquivo"] for p in publicados]
    videos = _videos_do_ciclo(perfil, arquivos, ler(perfil)) if arquivos else []
    escolhidos = [v["arquivo"] for v in _pontuar(videos)[:quantidade]] if len(videos) >= 2 else arquivos[-quantidade:]
    saida = []
    for nome in escolhidos:
        try:
            roteiro = json.loads((perfil.publicados / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        texto = " ".join(_fala(c) for c in roteiro.get("cenas") or [])
        if texto:
            saida.append(texto[:limite])
    return saida


def relatorio(caminho: Path) -> tuple[bool, str]:
    """(passou, texto para mostrar). Passa quando não há nenhum "erro"."""
    roteiro = json.loads(caminho.read_text(encoding="utf-8"))
    problemas = auditar(roteiro)
    if not problemas:
        return True, f"{caminho.name}: gancho, estrutura e CTA ok"
    linhas = [f"{caminho.name}:"] + [f"  {p['nivel'].upper():5} {p['parte']}: {p['texto']}" for p in problemas]
    return not any(p["nivel"] == "erro" for p in problemas), "\n".join(linhas)
