"""Upload automático para os canais oficiais do projeto (YouTube Data API v3)."""
import json
import os
from pathlib import Path

from . import config

ESCOPOS = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
CLIENT_SECRET = config.RAIZ / "credenciais" / "client_secret.json"  # app OAuth, igual para todos os perfis


def _token_youtube() -> Path:
    from .perfis import carregar
    return carregar().token_youtube
CATEGORIA_EDUCACAO = "27"


def autorizar_youtube(analytics: bool = False, comentarios: bool = False) -> Path:
    """Abre o navegador uma vez para o dono do canal permitir o acesso e salva o token local.
    analytics=True pede também a leitura do YouTube Analytics (minutos assistidos e retenção).
    comentarios=True pede também a permissão de responder comentários (youtube.force-ssl).
    As permissões extras que o token atual já tem continuam: liberar uma não tira a outra."""
    from .comentarios import ESCOPO_COMENTARIOS
    from .estatisticas import ESCOPO_ANALYTICS
    from .monetizacao import ESCOPO_RECEITA
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        raise SystemExit(f"falta {CLIENT_SECRET} (baixe o JSON do cliente OAuth no Google Cloud)")
    escopos = list(ESCOPOS)
    try:
        anteriores = json.loads(_token_youtube().read_text(encoding="utf-8")).get("scopes") or []
    except (OSError, ValueError):
        anteriores = []
    for extra in ([ESCOPO_ANALYTICS, ESCOPO_RECEITA] if analytics else []) + ([ESCOPO_COMENTARIOS] if comentarios else []) \
            + [e for e in anteriores if e in (ESCOPO_ANALYTICS, ESCOPO_RECEITA, ESCOPO_COMENTARIOS)]:
        if extra not in escopos:
            escopos.append(extra)
    fluxo = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), escopos)
    # prompt=consent garante o refresh_token mesmo se o app já foi autorizado antes
    # select_account: deixa escolher a conta do Google do canal deste perfil
    cred = fluxo.run_local_server(port=0, prompt="consent select_account", access_type="offline")
    # só salva se a escolha foi um canal, e um canal que ainda não é de outro perfil: escolher a conta pessoal do
    # Google (sem canal) ou o canal de outro perfil faria a postagem falhar ou sair no canal errado
    escolhido = _canal_do(cred)
    _conferir_dono(escolhido)
    destino = _token_youtube()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(cred.to_json(), encoding="utf-8")
    _guardar_canal(escolhido)
    return destino


SEM_CANAL = ("a conta escolhida não tem canal do YouTube, então nada foi salvo. Na tela do Google, depois de escolher "
             "o Gmail, aparece \"Escolha uma conta ou um canal de marca\": escolha o canal deste perfil (o canal de "
             "marca), não a conta pessoal. Se o canal ainda não existe, crie em https://www.youtube.com/channel_switcher "
             "(Ajustes > Criar as contas) e conecte de novo.")


def _canal_do(cred) -> dict:
    from googleapiclient.discovery import build
    itens = build("youtube", "v3", credentials=cred, cache_discovery=False).channels() \
        .list(part="snippet", mine=True).execute().get("items", [])
    if not itens:
        raise SystemExit(SEM_CANAL)
    return {"id": itens[0]["id"], "nome": itens[0]["snippet"]["title"]}


def _arquivo_canal(perfil) -> Path:
    return perfil.controle / "youtube_canal.json"


def _conferir_dono(escolhido: dict) -> None:
    """Recusa o canal que já está ligado a outro perfil (dois perfis postando no mesmo canal)."""
    from .perfis import carregar, listar
    atual = carregar()
    for outro in listar():
        arquivo = _arquivo_canal(outro)
        if outro.id == atual.id or not arquivo.exists():
            continue
        try:
            dono = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if dono.get("id") == escolhido["id"] and outro.token_youtube.exists():
            raise SystemExit(f"o canal \"{escolhido['nome']}\" já está ligado ao perfil {outro.dados.get('nome')}, "
                             "então nada foi salvo. Conecte de novo e escolha o canal deste perfil.")


def _guardar_canal(escolhido: dict) -> None:
    from .perfis import carregar
    perfil = carregar()
    perfil.controle.mkdir(parents=True, exist_ok=True)
    _arquivo_canal(perfil).write_text(json.dumps(escolhido, ensure_ascii=False) + "\n", encoding="utf-8")


def _credenciais():
    """Token da variável YOUTUBE_TOKEN (GitHub Actions) ou do arquivo local."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    bruto = os.getenv("YOUTUBE_TOKEN", "").strip()
    if bruto:
        info = json.loads(bruto)
    elif _token_youtube().exists():
        info = json.loads(_token_youtube().read_text(encoding="utf-8"))
    else:
        raise SystemExit("sem token do YouTube: rode '.\\dark.ps1 autorizar-youtube' ou defina YOUTUBE_TOKEN")
    # usa as permissões que o token tem (com a do Analytics, se foi liberada); pedir menos tiraria a do Analytics
    cred = Credentials.from_authorized_user_info(info, info.get("scopes") or ESCOPOS)
    if not cred.valid:
        cred.refresh(Request())
    return cred


def _servico():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credenciais(), cache_discovery=False)


def canal() -> dict:
    """Nome e ID do canal autorizado (confere se o token é do canal certo)."""
    resposta = _servico().channels().list(part="snippet", mine=True).execute()
    itens = resposta.get("items", [])
    if not itens:
        raise SystemExit("o token salvo é de uma conta sem canal do YouTube: em Ajustes > Contas, conecte o YouTube "
                         "de novo e escolha o canal deste perfil (o canal de marca), não a conta pessoal")
    escolhido = {"id": itens[0]["id"], "nome": itens[0]["snippet"]["title"]}
    _guardar_canal(escolhido)  # perfis conectados antes desta conferência passam a ter o canal anotado
    return escolhido


def metadados_youtube(roteiro: dict, video: Path | None = None, texto: dict | None = None) -> dict:
    """Título, descrição e tags a partir do bloco 'metadados' do roteiro. 'texto' (descricao.para_publicar) traz a
    descrição, as tags e as hashtags do vídeo, escritas por você ou pela IA, e tem prioridade."""
    vertical = roteiro.get("formato", "longo") == "vertical"
    meta = (roteiro.get("metadados") or {}).get("youtube_shorts" if vertical else "youtube") or {}
    titulo = meta.get("titulo") or roteiro.get("titulo", roteiro.get("slug", "vídeo"))
    if vertical and "#shorts" not in titulo.lower():
        titulo = f"{titulo} #shorts"
    texto = texto or {}
    hashtags = texto.get("hashtags") or meta.get("hashtags") or []
    descricao = texto.get("descricao") or meta.get("descricao") or roteiro.get("titulo", "")
    if hashtags:
        descricao = f"{descricao}\n\n{' '.join(hashtags)}"
    fontes = roteiro.get("fontes") or []
    if fontes and not all(f in descricao for f in fontes):  # a IA já costuma pôr as fontes no texto
        descricao += "\n\nFontes:\n" + "\n".join(f"- {f}" for f in fontes)
    if video:
        from .musica import credito
        if credito(video):
            descricao += f"\n\n{credito(video)}"
    tags = texto.get("tags") or meta.get("tags") or [h.lstrip("#") for h in hashtags]
    return {"titulo": titulo[:100], "descricao": descricao[:5000], "tags": tags}


def enviar_youtube(video: Path, titulo: str, descricao: str, tags: list[str],
                   privacidade: str = "private", sintetico: bool = False, idioma: str = "pt-BR") -> str:
    """Envia o vídeo e devolve o ID. Projeto sem auditoria do Google: o YouTube trava como privado."""
    from googleapiclient.http import MediaFileUpload

    corpo = {
        "snippet": {"title": titulo, "description": descricao, "tags": tags,
                    "categoryId": CATEGORIA_EDUCACAO,
                    # língua do título/descrição e do áudio: o YouTube usa as duas para mostrar o vídeo na região certa
                    "defaultLanguage": idioma, "defaultAudioLanguage": idioma},
        "status": {"privacyStatus": privacidade, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": sintetico},
    }
    midia = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    pedido = _servico().videos().insert(part="snippet,status", body=corpo, media_body=midia)
    resposta = None
    while resposta is None:
        progresso, resposta = pedido.next_chunk()
        if progresso:
            print(f"  enviando {int(progresso.progress() * 100)}%")
    return resposta["id"]
