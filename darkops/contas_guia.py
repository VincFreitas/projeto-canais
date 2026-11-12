"""Guia de criação das contas do canal: o que criar, em que ordem, com nomes sugeridos e o link de cada passo.

Criar contas continua com o usuário (termos do Google e da Meta, SMS, CAPTCHA). O Estúdio só sugere os nomes a
partir do nome do canal, abre a página certa de cada passo e confere o que já está pronto.
Os nomes sugeridos podem já estar em uso: o próprio site avisa, e aí vale tentar o próximo da lista.
"""
import json
import os
import re
import time
import unicodedata

from . import config, mercados

# sufixos que soam naturais para o público de cada língua
SUFIXOS = {"pt": ["oficial", "canal", "tv"], "en": ["official", "tv", "hq"], "es": ["oficial", "canal", "tv"],
           "fr": ["officiel", "tv", "chaine"], "de": ["offiziell", "tv", "kanal"], "it": ["ufficiale", "tv", "canale"]}
REPO_FILA, REPO_PASSAGEM = "projeto-canais-fila", "projeto-canais-videos"
NOME_REPO = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
MANUAIS = ("gmail", "youtube_canal", "instagram_conta")  # sem como conferir sozinho: o usuário marca "Já fiz"

# Bloqueio do Google ao criar conta ("o dispositivo usado para ler o QR code foi usado muitas vezes"). O Google não
# divulga o prazo; relatos falam em 24 h, às vezes 48 h, raramente semanas. A espera sobe a cada bloqueio seguido.
# Vale para o PC todo (é o celular que fica bloqueado, não o canal).
ESPERAS_H = [24, 48, 168]
BLOQUEIO = config.RAIZ / "dados" / "bloqueio-google.json"


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
    # o app do Google e o da Meta valem para todos os canais: o nome é do projeto, nunca de um canal
    projeto = _unicos(["projeto-canais", "projeto-canais-app", "projeto-canais-publicador"], 6, 30,
                      lambda x: x[0].isalpha() and re.fullmatch(r"[a-z][a-z0-9-]*", x) is not None)
    nome = " ".join(p.capitalize() for p in palavras)
    return {
        "gmail": [f"{g}@gmail.com" for g in gmail],
        "youtube_nome": [dados.get("nome") or nome],
        "youtube_handle": [f"@{h}" for h in handles if "." not in h or len(h) >= 3],
        "instagram": [f"@{h}" for h in handles],
        "google_projeto": projeto,
        # o Google e a Meta recusam nome de app com a marca deles (YouTube, Google, Instagram, Facebook, Meta)
        "google_app": ["Projeto Canais", "Projeto Canais Publicador"],
        "meta_app": ["Projeto Canais", "Projeto Canais Publicador"],
        "github": _unicos([traco, junto, f"{traco}-{s[0]}", f"{junto}-{s[1]}"], 3, 39,
                          lambda x: re.fullmatch(r"[a-z0-9][a-z0-9-]*", x) is not None),
        "apelido": [f"+{junto}", f"+{junto}.ig"],  # vai entre o seu nome e o @gmail.com
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


# ---------- bloqueio do Google na criação de conta ----------

def registrar_bloqueio(agora: float | None = None) -> dict:
    """O usuário avisou que o Google bloqueou. Um bloqueio novo dentro da espera anterior conta como seguido."""
    agora = agora or time.time()
    antes = situacao_bloqueio(agora)
    vezes = (antes["vezes"] + 1) if antes else 1
    BLOQUEIO.parent.mkdir(parents=True, exist_ok=True)
    BLOQUEIO.write_text(json.dumps({"vezes": vezes, "em": agora}) + "\n", encoding="utf-8")
    return situacao_bloqueio(agora) or {}


def limpar_bloqueio() -> None:
    BLOQUEIO.unlink(missing_ok=True)


def situacao_bloqueio(agora: float | None = None) -> dict | None:
    """Quando dá para tentar de novo. Some sozinho 7 dias depois de liberar (aí a contagem recomeça do 24 h)."""
    try:
        dados = json.loads(BLOQUEIO.read_text(encoding="utf-8"))
        vezes, em = max(int(dados["vezes"]), 1), float(dados["em"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    agora = agora or time.time()
    espera_h = ESPERAS_H[min(vezes, len(ESPERAS_H)) - 1]
    ate = em + espera_h * 3600
    if agora > ate + 7 * 86400:
        return None
    falta = max(ate - agora, 0)
    return {"vezes": vezes, "espera_h": espera_h, "ate": ate, "liberado": falta == 0,
            "falta": f"{int(falta // 3600)} h {int(falta % 3600 // 60):02d} min"}


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
        {"id": "gmail", "titulo": "E-mail do canal (Gmail, opcional)", "vale": "por canal",
         "feito": feitos.get("gmail", False),
         "texto": "Um Gmail só deste canal deixa as contas separadas, mas não é obrigatório: o canal do YouTube pode "
                  "ser um canal de marca no Gmail que você já usa, e o Instagram aceita um apelido do seu e-mail "
                  "(seuemail+canal@gmail.com chega na sua caixa normal). Para entrar sem digitar senha, crie uma chave "
                  "de acesso (passkey) na conta do Google: o login vira a digital ou o PIN do Windows.",
         "aviso": "Atenção: o Google limita quantas contas um mesmo celular confirma. Se aparecer \"Tente usar outro "
                  "dispositivo para fazer a verificação\", pare de tentar (cada tentativa pode alongar a espera) e "
                  "marque abaixo: o Estúdio calcula quando tentar de novo. Enquanto isso, siga pelo canal de marca.",
         "bloqueio": situacao_bloqueio(),
         "nomes": [("E-mail", n["gmail"]), ("Apelido do seu e-mail (Instagram)", n["apelido"])],
         "links": [("Criar o Gmail", "https://accounts.google.com/signup"),
                   ("Entrar sem senha (chave de acesso)", "https://myaccount.google.com/signinoptions/passkeys")]},
    ]
    if yt:
        lista.append({
            "id": "youtube_canal", "titulo": "Canal do YouTube", "vale": "por canal",
            "feito": feitos.get("youtube_canal", False) or token_yt,
            "texto": "Entre no YouTube com o Gmail do canal, ou com o seu e crie um canal de marca (não pede "
                     "verificação de conta nova). Use o nome abaixo e depois escolha o @. Para enviar thumbnail "
                     "própria e vídeos com mais de 15 minutos, confirme o canal pelo celular. Ao conectar no "
                     "Estúdio, escolha este canal na tela \"Escolha uma conta ou um canal de marca\", e não a "
                     "conta pessoal.",
            "nomes": [("Nome do canal", n["youtube_nome"]), ("@ do YouTube", n["youtube_handle"])],
            "links": [("Criar canal de marca", "https://www.youtube.com/channel_switcher"),
                      ("Criar o canal (Gmail novo)", "https://www.youtube.com/create_channel"),
                      ("Escolher o @", "https://www.youtube.com/handle"),
                      ("Confirmar pelo celular", "https://www.youtube.com/verify")]})
    if ig:
        lista.append({
            "id": "instagram_conta", "titulo": "Conta do Instagram", "vale": "por canal",
            "feito": feitos.get("instagram_conta", False) or token_ig,
            "texto": "Jeito mais rápido: no app do Instagram do celular, toque no seu nome no alto do perfil > "
                     "Adicionar conta do Instagram > Criar nova conta. Ela aproveita os dados da conta que você já "
                     "tem, então em geral não pede e-mail nem telefone novos. Ou crie com o Gmail do canal. Depois, no app do Instagram, mude para conta "
                     "Profissional (Criador ou Empresa) e deixe pública: sem isso a postagem automática não funciona. "
                     "Se o app da Meta já existe (de outro canal), não crie outro: adicione esta conta nele, em "
                     "Instagram > Configuração da API com login do Instagram > 1. Gerar tokens de acesso > Adicionar conta.",
            "nomes": [("Nome de usuário", n["instagram"])],
            "links": [("Criar a conta", "https://www.instagram.com/accounts/emailsignup/"),
                      ("Adicionar no app da Meta", "https://developers.facebook.com/apps/"),
                      ("Como mudar para Profissional", "https://help.instagram.com/502981923235522")]})
    if yt:
        lista.append({
            "id": "google_app", "titulo": "App do Google (postar no YouTube)", "vale": "uma vez, para todos os canais",
            "feito": CLIENT_SECRET.exists(),
            "texto": "Um app só para todos os canais: crie uma vez; os próximos canais usam o mesmo (com o app em modo "
                     "de teste, acrescente o Gmail de cada canal em Público > Usuários de teste). Logado com um Gmail seu: crie o projeto, ative a YouTube Data API v3, preencha a marca do app "
                     "(público Externo; ponha o Gmail do canal como usuário de teste), adicione os escopos "
                     "youtube.upload e youtube.readonly e crie o cliente \"App para computador\". Baixe o JSON: "
                     "o Estúdio pega o arquivo sozinho da pasta Downloads. Com o Claude Code e o Claude no Chrome, "
                     "a skill /conectar-contas faz estas telas por você. O app serve a todos os canais: dê o nome do "
                     "projeto (não o de um canal) e use um e-mail seu como e-mail de suporte, porque os dois aparecem "
                     "no login de todos os canais. Para trocar depois: Marca do app (passo 3). Ao conectar, o Google mostra \"O Google não "
                     "verificou este app\": é o seu próprio app; clique em Avançado > Acessar (não seguro). Para "
                     "esse aviso sumir, peça a verificação do app (passo 7), que leva alguns dias e pede a "
                     "política de privacidade do site, o domínio confirmado no Search Console e um vídeo curto "
                     "mostrando o login.",
            "nomes": [("Nome do projeto", n["google_projeto"]), ("Nome do app", n["google_app"])],
            "links": [("1. Criar o projeto", "https://console.cloud.google.com/projectcreate"),
                      ("2. Ativar a API", "https://console.cloud.google.com/apis/library/youtube.googleapis.com"),
                      ("3. Marca do app", "https://console.cloud.google.com/auth/branding"),
                      ("4. Público e testes", "https://console.cloud.google.com/auth/audience"),
                      ("5. Escopos", "https://console.cloud.google.com/auth/scopes"),
                      ("6. Criar o cliente", "https://console.cloud.google.com/auth/clients/create"),
                      ("7. Pedir a verificação (tira o aviso)", "https://console.cloud.google.com/auth/verification"),
                      ("Confirmar o domínio do site", "https://search.google.com/search-console")]})
    if ig:
        lista.append({
            "id": "meta_app", "titulo": "App da Meta (postar no Instagram)", "vale": "uma vez, para todos os canais",
            "feito": bool(env.get("INSTAGRAM_APP_ID")),
            "texto": "Um app só para todos os canais: crie uma vez, no primeiro canal; os outros entram no mesmo app. "
                     "Crie o app (nome sem Instagram, Facebook nem Meta), escolha o caso de uso \"Gerenciar mensagens e "
                     "conteúdo no Instagram\" (ou \"Outro\" > tipo \"Empresa\"), adicione a conta do canal em \"1. Gerar "
                     "tokens de acesso\", cole o endereço de retorno na etapa 3 e copie o ID e a chave do app do "
                     "Instagram. O passo a passo detalhado, tela por tela, está no card do Instagram em Ajustes > Contas. "
                     "Com o Claude Code e o Claude no Chrome, a skill /conectar-contas faz estas telas por você; "
                     "a chave secreta você copia e aperta Colar no Estúdio.",
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
    for s in lista:  # o que se repete a cada canal novo e o que se faz uma vez só
        s["grupo"] = "canal" if s["vale"] == "por canal" else "instalacao"
    return lista
