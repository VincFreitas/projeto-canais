"""Catálogo de conectores do Estúdio, agrupados por função.

Cada conector diz para que serve, onde se consegue o acesso, se vale para um perfil ou para todos,
e como está agora. Os "em breve" aparecem para mostrar o que existe no mercado, sem fingir que funciona.
"""
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import config

OK, FALTA, OPCIONAL, SEMPRE, EM_BREVE = "ok", "falta", "opcional", "sempre", "em-breve"


@dataclass
class Conector:
    id: str
    nome: str
    funcao: str                      # legenda: o que este conector faz no pipeline
    tipo: str                        # oauth | token | chave | embutido | servico | em_breve
    escopo: str = "todos"            # "perfil" (cada canal conecta o seu) ou "todos"
    chaves: list[tuple[str, str, bool]] = field(default_factory=list)  # (variável, rótulo, é segredo)
    link: str = ""                   # onde conseguir o acesso
    passos: list[str] = field(default_factory=list)
    custo: str = ""


@dataclass
class Grupo:
    id: str
    nome: str
    legenda: str
    conectores: list[Conector]


GRUPOS = [
    Grupo("publicacao", "Publicação",
          "Para onde os vídeos vão. Cada perfil conecta as contas do próprio canal.", [
              Conector("youtube", "YouTube Shorts", "Envia o vídeo aprovado ao canal, com título, descrição, "
                       "fontes e crédito da música.", "oauth", "perfil",
                       link="https://console.cloud.google.com/apis/library/youtube.googleapis.com",
                       passos=["Clique em Conectar: o login do Google abre no navegador.",
                               "Escolha a conta do Google deste canal.",
                               "Em “app não verificado”, vá em Avançado e depois em Acessar, e permita."],
                       custo="Grátis (cota de cerca de 6 envios por dia)"),
              Conector("instagram", "Instagram Reels", "Publica o mesmo vídeo como Reel, com legenda e hashtags.",
                       "token", "perfil", link="https://developers.facebook.com/apps/",
                       passos=["A conta precisa ser Profissional (Criador ou Empresa).",
                               "No app da Meta: Instagram, Configuração da API, Adicionar conta e Gerar token.",
                               "Cole o token abaixo. Ele dura 60 dias."],
                       custo="Grátis"),
              Conector("tiktok", "TikTok", "Postagem direta pela Content Posting API do TikTok.", "em_breve",
                       "perfil", link="https://developers.tiktok.com/products/content-posting-api/",
                       passos=["Exige que o TikTok aprove o app antes de postar em contas públicas."]),
              Conector("facebook", "Facebook Reels", "Publicar também na Página do Facebook ligada ao Instagram.",
                       "em_breve", "perfil", link="https://developers.facebook.com/docs/video-api/guides/reels-publishing"),
          ]),
    Grupo("voz", "Voz (narração)",
          "Transforma o texto do roteiro em fala, com o tempo de cada palavra para a legenda e as animações. "
          "Ordem automática: Azure, depois Edge, e o Piper (offline) se os outros falharem.", [
              Conector("azure", "Azure Speech", "Voz neural oficial da Microsoft. É a principal.", "chave",
                       chaves=[("AZURE_SPEECH_KEY", "Chave", True), ("AZURE_SPEECH_REGION", "Região (ex.: brazilsouth)", False)],
                       link="https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices",
                       passos=["Crie um recurso “Serviço de Fala” no nível Free F0.",
                               "Em Chaves e Ponto de Extremidade, copie a CHAVE 1 e a região."],
                       custo="Grátis até 500 mil caracteres por mês (F0)"),
              Conector("edge", "Microsoft Edge (edge-tts)", "As mesmas vozes do Azure, sem chave. Serviço não "
                       "oficial: às vezes recusa conexões.", "embutido", custo="Grátis, sem cadastro"),
              Conector("piper", "Piper (offline)", "Voz que roda no próprio PC. Reserva: nunca deixa a "
                       "automação sem narração.", "embutido", custo="Grátis, sem internet"),
              Conector("elevenlabs", "ElevenLabs", "Vozes mais naturais e expressivas (opcional).", "chave",
                       chaves=[("ELEVENLABS_API_KEY", "Chave", True), ("ELEVENLABS_VOZ", "ID da voz", False)],
                       link="https://elevenlabs.io/app/settings/api-keys",
                       custo="10 mil créditos grátis por mês; uso comercial a partir de US$ 6"),
          ]),
    Grupo("midia", "Imagens e vídeos",
          "Busca clipes e fotos de licença livre para cada cena. Mídia gerada por IA, desenho e 3D são filtrados.", [
              Conector("pixabay", "Pixabay", "Clipes e fotos grátis, sem crédito obrigatório.", "chave",
                       chaves=[("PIXABAY_API_KEY", "Chave", True)], link="https://pixabay.com/api/docs/",
                       passos=["Crie a conta e copie a chave que aparece na página da API."],
                       custo="Grátis"),
              Conector("pexels", "Pexels", "Outro banco grátis; é consultado antes do Pixabay quando tem chave.",
                       "chave", chaves=[("PEXELS_API_KEY", "Chave", True)], link="https://www.pexels.com/api/",
                       custo="Grátis (novas chaves podem estar pausadas)"),
              Conector("proprios", "Arquivos próprios", "Imagem ou vídeo seu numa cena (campo “arquivo” do roteiro). "
                       "Tem prioridade sobre os bancos.", "embutido", custo="Grátis"),
          ]),
    Grupo("musica", "Música",
          "Trilha de fundo. Só entra música com licença livre registrada; nada de faixa comercial.", [
              Conector("trilhas", "Trilhas geradas", "Trilha animada ou de suspense criada pelo código, com tom e "
                       "andamento diferentes em cada vídeo.", "embutido", custo="Grátis, sem direitos autorais"),
              Conector("biblioteca", "Biblioteca própria", "Músicas em assets/musica/<tema>, liberadas em "
                       "licencas.csv (CC0, CC BY com crédito, YouTube Audio Library).", "embutido",
                       link="https://studio.youtube.com/channel/UC/music", custo="Grátis"),
              Conector("freesound", "Freesound", "Buscar trilhas CC0 por clima automaticamente.", "em_breve",
                       link="https://freesound.org/apiv2/apply"),
          ]),
    Grupo("roteiro", "Roteiros e pesquisa",
          "De onde vêm as ideias e os roteiros com fatos checados.", [
              Conector("claude", "Claude Code", "Pesquisa o nicho, acha os vídeos que bombaram e escreve roteiros com "
                       "fontes (/pesquisar-nicho, /escrever-roteiro, /titulo-thumb).", "servico",
                       link="https://claude.com/claude-code", custo="Conforme o seu plano do Claude"),
              Conector("ytdlp", "Pesquisa no YouTube (yt-dlp)", "Demanda, outliers e transcrições, sem chave.",
                       "embutido", custo="Grátis"),
          ]),
    Grupo("automacao", "Automação",
          "Quem dispara a postagem nos horários, com o PC ligado.", [
              Conector("n8n", "n8n", "Às 12h e às 19h, percorre os perfis ligados e posta o próximo vídeo aprovado.",
                       "servico", link="http://localhost:5678",
                       passos=["Instale com: npm install -g n8n",
                               "Gere o workflow com: python -m darkops n8n-workflow --importar",
                               "Ative o workflow no editor do n8n."],
                       custo="Grátis (roda no seu PC)"),
          ]),
]


def _env() -> dict:
    valores = {}
    arquivo = config.RAIZ / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                if v.strip():
                    valores[k.strip()] = v.strip()
    return valores


def _liberadas() -> int:
    try:
        from ..musica import _liberadas
        return len(_liberadas())
    except Exception:
        return 0


def estado(c: Conector, perfil, conexoes: dict, n8n_online: bool) -> tuple[str, str]:
    """(situação, texto curto) de um conector para este perfil."""
    env = _env()
    if c.tipo == "em_breve":
        return EM_BREVE, "em breve"
    if c.id == "youtube":
        teste = conexoes.get("youtube")
        if teste:
            return (OK, f"conectado: {teste['texto']}") if teste["ok"] else (FALTA, "erro: reconecte")
        return (OK, "conectado (não testado)") if perfil.token_youtube.exists() else (FALTA, "não conectado")
    if c.id == "instagram":
        teste = conexoes.get("instagram")
        if teste:
            return (OK, "conectado") if teste["ok"] else (FALTA, "erro: token vencido?")
        return (OK, "token salvo (não testado)") if perfil.token_instagram.exists() else (FALTA, "não conectado")
    if c.tipo == "chave":
        if all(env.get(k) for k, _, _ in c.chaves[:1]):
            return OK, "configurada"
        return (OPCIONAL, "opcional") if c.id in ("elevenlabs", "pexels") else (FALTA, "falta a chave")
    if c.id == "piper":
        modelos = list((config.RAIZ / "assets" / "vozes").glob("*.onnx"))
        return (SEMPRE, "pronto") if modelos else (FALTA, "rode o instalador")
    if c.id == "biblioteca":
        n = _liberadas()
        return (OK, f"{n} faixa{'s' if n != 1 else ''} liberada{'s' if n != 1 else ''}") if n else (OPCIONAL, "vazia")
    if c.id == "claude":
        return (OK, "instalado") if shutil.which("claude") else (OPCIONAL, "não encontrado")
    if c.id == "n8n":
        if n8n_online:
            return OK, "rodando"
        instalado = shutil.which("n8n") or Path(os.environ.get("APPDATA", ""), "npm", "n8n.cmd").exists()
        return (FALTA, "instalado, mas desligado") if instalado else (FALTA, "não instalado")
    return SEMPRE, "sempre disponível"


def resumo(perfil, conexoes: dict, n8n_online: bool) -> list[dict]:
    """Por grupo: quantos estão prontos e se falta algo essencial (para o card do Início)."""
    saida = []
    for g in GRUPOS:
        estados = [estado(c, perfil, conexoes, n8n_online) for c in g.conectores if c.tipo != "em_breve"]
        prontos = sum(1 for s, _ in estados if s in (OK, SEMPRE))
        essencial = {"publicacao": ("youtube", "instagram"), "voz": ("azure", "edge", "piper"),
                     "midia": ("pixabay", "pexels"), "automacao": ("n8n",)}.get(g.id)
        if essencial:
            situacoes = {c.id: estado(c, perfil, conexoes, n8n_online)[0] for c in g.conectores}
            alguma = any(situacoes.get(x) in (OK, SEMPRE) for x in essencial)
            todas = all(situacoes.get(x) in (OK, SEMPRE) for x in essencial)
            nivel = OK if (todas if g.id == "publicacao" else alguma) else FALTA
        else:
            nivel = OK
        saida.append({"grupo": g, "prontos": prontos, "total": len(estados), "nivel": nivel})
    return saida
