"""Guia de criação das contas do canal: o que criar, em que ordem, com nomes sugeridos e o link de cada passo.

Criar contas continua com o usuário (termos do Google e da Meta, SMS, CAPTCHA). O Estúdio só sugere os nomes a
partir do nome do canal, abre a página certa de cada passo e confere o que já está pronto.
Os nomes sugeridos podem já estar em uso: o próprio site avisa, e aí vale tentar o próximo da lista.
"""
import json
import os
import re
import unicodedata

from . import config, mercados

# sufixos que soam naturais para o público de cada língua
SUFIXOS = {"pt": ["oficial", "canal", "tv"], "en": ["official", "tv", "hq"], "es": ["oficial", "canal", "tv"],
           "fr": ["officiel", "tv", "chaine"], "de": ["offiziell", "tv", "kanal"], "it": ["ufficiale", "tv", "canale"]}
REPO_FILA, REPO_PASSAGEM = "projeto-canais-fila", "projeto-canais-videos"
NOME_REPO = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
MANUAIS = ("gmail", "youtube_canal", "instagram_conta")  # sem como conferir sozinho: o usuário marca "Já fiz"


def _palavras(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", texto)


def _unicos(lista, minimo: int, maximo: int, valido=None) -> list[str]:
    vistos, saida = set(), []
    for item in lista:
        item = item.strip(".-_")
        if minimo <= len(item) <= maximo and item not in vistos and (valido is None or valido(item)):
            vistos.add(item)
            saida.append(item)
    return saida[:5]


def sugestoes(dados: dict) -> dict:
    """Nomes para cada conta, todos derivados do nome e do @ do canal (nada de outro canal)."""
    palavras = _palavras(dados.get("nome")) or ["meucanal"]
    junto, ponto, traco = "".join(palavras), ".".join(palavras), "-".join(palavras)
    arroba = re.sub(r"[^a-z0-9._]", "", str(dados.get("arroba") or "").lower().lstrip("@"))
    s = SUFIXOS.get(mercados.de(dados)["idioma"], SUFIXOS["en"])
    handles = _unicos([arroba, junto, f"{junto}.{s[0]}", f"{junto}{s[2]}", f"{junto}_{s[1]}", f"{ponto}"], 3, 30)
    gmail = _unicos([ponto, junto, f"{junto}.{s[0]}", f"{junto}{s[1]}", f"{s[1]}.{junto}"], 6, 30,
                    lambda x: ".." not in x and x[0].isalnum())
    projeto = _unicos([f"{traco}-canais", f"{traco}-publicador", "projeto-canais", f"{junto}-app"], 6, 30,
                      lambda x: x[0].isalpha() and re.fullmatch(r"[a-z][a-z0-9-]*", x) is not None)
    nome = " ".join(p.capitalize() for p in palavras)
    return {
        "gmail": [f"{g}@gmail.com" for g in gmail],
        "youtube_nome": [dados.get("nome") or nome],
        "youtube_handle": [f"@{h}" for h in handles if "." not in h or len(h) >= 3],
        "instagram": [f"@{h}" for h in handles],
        "google_projeto": projeto,
        # o Google e a Meta recusam nome de app com a marca deles (YouTube, Google, Instagram, Facebook, Meta)
        "google_app": _unicos([f"{nome} Publicador", f"{nome} Studio", "Projeto Canais"], 3, 40),
        "meta_app": _unicos([f"{nome} Publicador", f"{nome} Reels", "Projeto Canais Publicador"], 3, 40),
        "github": _unicos([traco, junto, f"{traco}-{s[0]}", f"{junto}-{s[1]}"], 3, 39,
                          lambda x: re.fullmatch(r"[a-z0-9][a-z0-9-]*", x) is not None),
        "repo_fila": [REPO_FILA, f"{traco}-fila"],
        "repo_passagem": [REPO_PASSAGEM, f"{traco}-videos"],
    }


# ---------- o que já está pronto ----------

def _marcas_arquivo(perfil):
    return perfil.controle / "contas.json"


def marcas(perfil) -> dict:
    arquivo = _marcas_arquivo(perfil)
    try:
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    except ValueError:
        return {}


def marcar(perfil, passo: str, feito: bool) -> None:
    if passo not in MANUAIS:
        raise ValueError(passo)
    atual = {**marcas(perfil), passo: bool(feito)}
    perfil.controle.mkdir(parents=True, exist_ok=True)
    _marcas_arquivo(perfil).write_text(json.dumps(atual, indent=2) + "\n", encoding="utf-8")


def _env() -> dict:
    from dotenv import dotenv_values
    return {**dotenv_values(config.RAIZ / ".env"), **{k: v for k, v in os.environ.items() if k.startswith(
        ("NUVEM_", "INSTAGRAM_", "AZURE_"))}}


# ---------- os passos ----------

def passos(dados: dict, perfil=None) -> list[dict]:
    """A lista de passos na ordem em que o usuário faz. Sem `perfil` (assistente do canal novo), ninguém está feito
    ainda, a não ser o que vale para todos os canais e já foi configurado."""
    from .publicar import CLIENT_SECRET
    n = sugestoes(dados)
    env = _env()
    feitos = marcas(perfil) if perfil else {}
    yt, ig = dados.get("youtube", True), dados.get("instagram", True)
    token_yt = bool(perfil and perfil.token_youtube.exists())
    token_ig = bool(perfil and perfil.token_instagram.exists())
    lista = [
        {"id": "gmail", "titulo": "E-mail do canal (Gmail)", "vale": "por canal", "feito": feitos.get("gmail", False),
         "texto": "Um Gmail só deste canal. Ele vira a conta do YouTube e recebe os avisos das outras contas. "
                  "Use um número de celular seu para confirmar.",
         "nomes": [("E-mail", n["gmail"])],
         "links": [("Criar o Gmail", "https://accounts.google.com/signup")]},
    ]
    if yt:
        lista.append({
            "id": "youtube_canal", "titulo": "Canal do YouTube", "vale": "por canal",
            "feito": feitos.get("youtube_canal", False) or token_yt,
            "texto": "Entre no YouTube com o Gmail do canal e crie o canal com o nome abaixo. Depois escolha o @ "
                     "(identificador). Para enviar thumbnail própria e vídeos com mais de 15 minutos, confirme "
                     "o canal pelo celular.",
            "nomes": [("Nome do canal", n["youtube_nome"]), ("@ do YouTube", n["youtube_handle"])],
            "links": [("Criar o canal", "https://www.youtube.com/create_channel"),
                      ("Escolher o @", "https://www.youtube.com/handle"),
                      ("Confirmar pelo celular", "https://www.youtube.com/verify")]})
    if ig:
        lista.append({
            "id": "instagram_conta", "titulo": "Conta do Instagram", "vale": "por canal",
            "feito": feitos.get("instagram_conta", False) or token_ig,
            "texto": "Crie a conta com o Gmail do canal. Depois, no app do Instagram, mude para conta "
                     "Profissional (Criador ou Empresa): sem isso a postagem automática não funciona.",
            "nomes": [("Nome de usuário", n["instagram"])],
            "links": [("Criar a conta", "https://www.instagram.com/accounts/emailsignup/"),
                      ("Como mudar para Profissional", "https://help.instagram.com/502981923235522")]})
    if yt:
        lista.append({
            "id": "google_app", "titulo": "App do Google (postar no YouTube)", "vale": "uma vez, para todos os canais",
            "feito": CLIENT_SECRET.exists(),
            "texto": "Logado com um Gmail seu: crie o projeto, ative a YouTube Data API v3, preencha a marca do app "
                     "(público Externo; ponha o Gmail do canal como usuário de teste), adicione os escopos "
                     "youtube.upload e youtube.readonly e crie o cliente \"App para computador\". Baixe o JSON e "
                     "salve como credenciais/client_secret.json.",
            "nomes": [("Nome do projeto", n["google_projeto"]), ("Nome do app", n["google_app"])],
            "links": [("1. Criar o projeto", "https://console.cloud.google.com/projectcreate"),
                      ("2. Ativar a API", "https://console.cloud.google.com/apis/library/youtube.googleapis.com"),
                      ("3. Marca do app", "https://console.cloud.google.com/auth/branding"),
                      ("4. Público e testes", "https://console.cloud.google.com/auth/audience"),
                      ("5. Escopos", "https://console.cloud.google.com/auth/scopes"),
                      ("6. Criar o cliente", "https://console.cloud.google.com/auth/clients/create")]})
    if ig:
        lista.append({
            "id": "meta_app", "titulo": "App da Meta (postar no Instagram)", "vale": "uma vez, para todos os canais",
            "feito": bool(env.get("INSTAGRAM_APP_ID")),
            "texto": "Crie o app com o caso de uso \"Gerenciar mensagens e conteúdo no Instagram\". O nome não pode "
                     "ter Instagram, Facebook nem Meta. Depois cole o ID e a chave secreta em Ajustes > Contas.",
            "nomes": [("Nome do app", n["meta_app"])],
            "links": [("Criar o app", "https://developers.facebook.com/apps/creation/"),
                      ("Seus apps", "https://developers.facebook.com/apps/")]})
    lista.append({
        "id": "github", "titulo": "GitHub (nuvem e passagem do Instagram)", "vale": "uma vez, para todos os canais",
        "feito": bool(env.get("NUVEM_REPO")),
        "texto": "Com a conta criada, o botão \"Entrar com o GitHub\" cria sozinho os dois repositórios com os nomes "
                 "abaixo: o privado guarda a fila da postagem na nuvem e o público só passa o vídeo para o Instagram.",
        "nomes": [("Usuário (se ainda não tiver conta)", n["github"]), ("Repositório privado (fila)", n["repo_fila"]),
                  ("Repositório público (passagem)", n["repo_passagem"])],
        "links": [("Criar a conta", "https://github.com/signup")],
        "repos": True})
    lista.append({
        "id": "azure", "titulo": "Microsoft (voz grátis do Azure)", "vale": "uma vez, para todos os canais (opcional)",
        "feito": bool(env.get("AZURE_SPEECH_KEY")),
        "texto": "Opcional: sem ela, a voz usa o Edge. Crie a conta da Microsoft e a conta grátis do Azure; "
                 "depois o botão \"Entrar com a Microsoft\" cria a chave da voz no nível grátis.",
        "nomes": [],
        "links": [("Criar a conta da Microsoft", "https://signup.live.com/"),
                  ("Conta grátis do Azure", "https://azure.microsoft.com/free")]})
    return lista
