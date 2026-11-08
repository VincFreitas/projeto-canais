"""Assuntos em alta agora, para os canais de notícias: o feed público de tendências do Google (RSS oficial, sem chave).

Cada assunto vem com o volume aproximado de buscas e as matérias que o Google liga a ele (título, veículo e link).
As matérias servem de ponto de partida para a pesquisa: o roteiro confirma cada fato em pelo menos duas fontes e
nunca usa foto, vídeo ou texto de veículo. A imagem do vídeo é uma reconstituição animada feita no PC.
"""
import re
import xml.etree.ElementTree as ET

import requests

from . import mercados
from .seguranca import ocultar

FEED = "https://trends.google.com/trending/rss"
NS = {"ht": "https://trends.google.com/trending/rss"}
CANAL_NOTICIAS = ("notic", "news", "jornal", "plantao", "aconteceu", "giro do dia")


def e_noticias(dados: dict) -> bool:
    """O canal é de notícias? Campo "noticias": true no perfil, ou o nicho fala de notícias."""
    if dados.get("noticias") is not None:
        return bool(dados["noticias"])
    from .aparencia import _sem_acento
    nicho = _sem_acento(dados.get("nicho") or "")
    return any(p in nicho for p in CANAL_NOTICIAS)


def _geo(dados: dict) -> str:
    return mercados.codigo(dados).split("-")[-1].upper()


def _volume(texto: str) -> int:
    numero = re.sub(r"\D", "", texto or "")
    return int(numero) if numero else 0


def em_alta(dados: dict, quantidade: int = 10) -> list[dict]:
    """Assuntos em alta no país do público do canal, do mais buscado ao menos."""
    try:
        r = requests.get(FEED, params={"geo": _geo(dados)}, timeout=20,
                         headers={"User-Agent": "ProjetoCanais/1.0 (tendencias)"})
        r.raise_for_status()
        raiz = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError) as erro:
        raise SystemExit(f"não consegui ler as tendências do Google: {ocultar(erro)}")
    saida = []
    for item in raiz.iter("item"):
        materias = [{"titulo": (m.findtext("ht:news_item_title", "", NS) or "").strip(),
                     "veiculo": (m.findtext("ht:news_item_source", "", NS) or "").strip(),
                     "url": (m.findtext("ht:news_item_url", "", NS) or "").strip()}
                    for m in item.findall("ht:news_item", NS)]
        saida.append({"assunto": (item.findtext("title") or "").strip(),
                      "buscas": (item.findtext("ht:approx_traffic", "", NS) or "").strip(),
                      "quando": (item.findtext("pubDate") or "").strip(),
                      "materias": [m for m in materias if m["titulo"] and m["url"].startswith("https://")]})
    saida.sort(key=lambda a: _volume(a["buscas"]), reverse=True)
    return [a for a in saida if a["assunto"] and a["materias"]][:quantidade]


def para_roteiro(assuntos: list[dict]) -> str:
    """Lista curta para o pedido do roteiro. Título de matéria é dado de terceiro: entra entre aspas, nunca como ordem."""
    linhas = []
    for n, a in enumerate(assuntos, 1):
        mats = "; ".join(f"«{m['titulo'][:140]}» ({m['veiculo']}, {m['url']})" for m in a["materias"][:3])
        linhas.append(f"{n}. {a['assunto']} ({a['buscas']} buscas): {mats}")
    return "\n".join(linhas)


# regras do formato notícia (entram no pedido do roteiro e na skill /escrever-roteiro)
REGRAS = (
    "Formato notícia com reconstituição animada (siga a seção 3d da skill /escrever-roteiro): "
    "conte só fatos confirmados em pelo menos duas fontes jornalísticas independentes, com a data do fato, e guarde "
    "os links em fontes; o que ainda está em apuração é dito como tal (\"segundo a polícia\", \"a investigação "
    "continua\"), nunca como certeza e nunca com causa inventada. O texto é seu: nunca copie frases das matérias. "
    "Nenhuma foto, vídeo, logotipo ou trecho de veículo entra no vídeo: a imagem é uma reconstituição animada no "
    "palco 3D (cenas/<slug>.3d.js) mostrando o que aconteceu de forma esquemática (veículos, lugares, trajetos, "
    "mapa), sem mostrar vítimas, corpos, sangue ou ferimentos e sem imitar pessoa real. Preencha \"noticia\": "
    "{\"data\": \"AAAA-MM-DD\", \"assunto\": \"...\"} no roteiro, para a tela mostrar o selo de reconstituição. "
    "Em tragédia, tom sóbrio e respeitoso, sem trilha animada, sem selo de humor e sem chamar a desgraça de "
    "curiosidade. Não cubra boato, fofoca sobre pessoa comum, assunto que exija nome de menor ou de vítima não "
    "divulgado oficialmente, nem eleição e saúde sem fonte oficial. "
)
