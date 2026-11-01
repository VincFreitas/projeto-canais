"""Contas por login: o usuário só entra na conta dele, e o projeto coleta e configura o resto sozinho.

  python -m darkops conectar-github     login com código no navegador; cria os repositórios de fila (privado) e de
                                        passagem do Instagram (público) e grava NUVEM_REPO, NUVEM_TOKEN e NUVEM_VIDEOS_REPO
  python -m darkops conectar-azure      login com código no navegador; cria o recurso de voz GRÁTIS (F0) e grava a chave
  Instagram: botão "Entrar com Instagram" no Estúdio (OAuth do Instagram Login, token de 60 dias renovado sozinho)

Criar contas (Gmail, Instagram, Azure, GitHub) e fazer login continua com o usuário: aqui só entram os passos depois
do login. GitHub CLI e Azure CLI ficam em dados/apps (portáteis, conferidos antes de usar), com a configuração deles
dentro da pasta do projeto, longe do AppData.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

from . import config
from .apps import PASTA, _baixar, assinatura

GH_DIR = PASTA / "gh"
GH_EXE = GH_DIR / "bin" / "gh.exe"
GH_CONFIG = PASTA / "gh-config"
# o Azure CLI tem arquivos com caminho de mais de 130 letras: dentro de uma pasta de projeto funda (ex.: Área de
# Trabalho no OneDrive) passaria do limite de 260 do Windows. Fica numa pasta curta no perfil do usuário (fora do
# AppData, que o terminal do app Claude desvia).
CURTA = Path.home() / ".projeto-canais"
AZ_DIR = CURTA / "azure-cli"
AZ_CMD = AZ_DIR / "bin" / "az.cmd"
AZ_CONFIG = CURTA / "azure-config"
AZ_ZIP = "https://aka.ms/installazurecliwindowszipx64"  # zip oficial da Microsoft

REPO_FILA = "projeto-canais-fila"          # privado: fila e estado da nuvem
REPO_PASSAGEM = "projeto-canais-videos"    # público: o Instagram baixa o vídeo dali (fica só enquanto a Meta baixa)
GRUPO_AZURE = "projeto-canais"
REGIAO_AZURE = "brazilsouth"


def salvar_env(novos: dict) -> None:
    """Troca (ou acrescenta) as variáveis no .env e no processo atual."""
    arquivo = config.RAIZ / ".env"
    linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
    for chave, valor in novos.items():
        linhas = [l for l in linhas if not re.match(rf"^\s*{chave}\s*=", l)]
        linhas.append(f"{chave}={valor}")
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    os.environ.update(novos)


def _abrir(url: str) -> None:
    print(f"abrindo {url} no navegador (se não abrir, abra você)")
    webbrowser.open(url)


# ---------- GitHub ----------

def instalar_gh() -> str:
    """GitHub CLI portátil da release oficial, conferido pelo SHA-256 que a própria API do GitHub publica."""
    if GH_EXE.exists():
        return str(GH_EXE)
    with urllib.request.urlopen("https://api.github.com/repos/cli/cli/releases/latest", timeout=60) as r:
        release = json.load(r)
    asset = next(a for a in release["assets"] if a["name"].endswith("_windows_amd64.zip"))
    print(f"baixando o GitHub CLI {release['tag_name']} (cerca de 15 MB)...")
    zip_ = _baixar(asset["browser_download_url"], PASTA / asset["name"])
    esperado = (asset.get("digest") or "").removeprefix("sha256:")
    if not esperado or hashlib.sha256(zip_.read_bytes()).hexdigest() != esperado:
        zip_.unlink(missing_ok=True)
        raise SystemExit("o GitHub CLI baixado não confere com o SHA-256 publicado pelo GitHub; descartado")
    shutil.rmtree(GH_DIR, ignore_errors=True)
    with zipfile.ZipFile(zip_) as z:
        z.extractall(GH_DIR)
    zip_.unlink()
    return str(GH_EXE)


def _gh(*args: str, entrada: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    env = {**os.environ, "GH_CONFIG_DIR": str(GH_CONFIG), "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1"}
    return subprocess.run([str(GH_EXE), *args], input=entrada, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout)


def _api_github(token: str, metodo: str, caminho: str, dados: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(f"https://api.github.com{caminho}", method=metodo,
                                 data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "projeto-canais"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read() or b"{}")


def _repo(token: str, dono: str, nome: str, privado: bool) -> str:
    status, dados = _api_github(token, "GET", f"/repos/{dono}/{nome}")
    if status == 200:
        if dados.get("private") != privado:
            raise SystemExit(f"{dono}/{nome} já existe, mas {'público' if dados.get('private') is False else 'privado'}: "
                             f"ele precisa ser {'privado' if privado else 'público'}. Mude em Settings do repositório.")
        return dados["full_name"]
    status, dados = _api_github(token, "POST", "/user/repos", {
        "name": nome, "private": privado, "auto_init": True,
        "description": "Fila da nuvem do Projeto Canais" if privado else
                       "Passagem de vídeos do Projeto Canais: cada vídeo fica aqui só enquanto o Instagram baixa"})
    if status != 201:
        raise SystemExit(f"o GitHub não criou {nome}: {dados.get('message', status)}")
    print(f"criado: {dados['full_name']} ({'privado' if privado else 'público'})")
    return dados["full_name"]


def conectar_github() -> dict:
    """Login no GitHub com código no navegador; depois cria os dois repositórios e grava tudo no .env."""
    instalar_gh()
    if _gh("auth", "status", "--hostname", "github.com").returncode != 0:
        print("Entre na sua conta do GitHub: vai aparecer um código de 8 letras logo abaixo.")
        print("Copie o código, cole na página que vai abrir e autorize o 'GitHub CLI'.")
        _abrir("https://github.com/login/device")
        # escopos: repo (criar e usar os repositórios), workflow (enviar o workflow da nuvem)
        proc = subprocess.Popen([str(GH_EXE), "auth", "login", "--hostname", "github.com", "--git-protocol", "https",
                                 "--web", "--scopes", "repo,workflow"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                env={**os.environ, "GH_CONFIG_DIR": str(GH_CONFIG), "NO_COLOR": "1",
                                     "GH_BROWSER": "cmd /c rem"})  # o navegador já foi aberto acima
        proc.stdin.write("\n")
        proc.stdin.flush()
        for linha in proc.stdout:
            print(linha.rstrip(), flush=True)
        if proc.wait(timeout=900) != 0:
            raise SystemExit("o login no GitHub não terminou: clique de novo em Entrar com o GitHub")
    token = _gh("auth", "token", "--hostname", "github.com").stdout.strip()
    if not token:
        raise SystemExit("o GitHub CLI não devolveu o acesso; clique de novo em Entrar com o GitHub")
    status, eu = _api_github(token, "GET", "/user")
    if status != 200:
        raise SystemExit("o acesso do GitHub foi recusado; clique de novo em Entrar com o GitHub")
    dono = eu["login"]
    print(f"conta do GitHub: {dono}")
    fila = _repo(token, dono, REPO_FILA, privado=True)
    passagem = _repo(token, dono, REPO_PASSAGEM, privado=False)
    salvar_env({"NUVEM_REPO": fila, "NUVEM_TOKEN": token, "NUVEM_VIDEOS_REPO": passagem})
    print("ok: fila e passagem do Instagram prontas; a nuvem será preparada em seguida")
    return {"fila": fila, "passagem": passagem}


# ---------- Azure (voz) ----------

def instalar_az() -> str:
    """Azure CLI portátil (zip oficial da Microsoft, cerca de 90 MB). Integridade pelo Content-MD5 que o servidor
    manda; o Python de dentro precisa da assinatura da Python Software Foundation."""
    if AZ_CMD.exists():
        return str(AZ_CMD)
    print("baixando o Azure CLI (cerca de 90 MB)...")
    with urllib.request.urlopen(AZ_ZIP, timeout=900) as r:
        md5 = r.headers.get("Content-MD5", "")
        destino = CURTA / "azure-cli.zip"
        CURTA.mkdir(parents=True, exist_ok=True)
        with destino.open("wb") as f:
            shutil.copyfileobj(r, f)
    if not md5 or base64.b64encode(hashlib.md5(destino.read_bytes()).digest()).decode() != md5:
        destino.unlink(missing_ok=True)
        raise SystemExit("o Azure CLI baixado não confere com o servidor da Microsoft; descartado")
    shutil.rmtree(AZ_DIR, ignore_errors=True)
    with zipfile.ZipFile(destino) as z:
        z.extractall(AZ_DIR)
    destino.unlink()
    if "Python Software Foundation" not in assinatura(AZ_DIR / "python.exe"):
        shutil.rmtree(AZ_DIR, ignore_errors=True)
        raise SystemExit("o Python do Azure CLI não tem a assinatura esperada; descartado")
    return str(AZ_CMD)


def _az(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    env = {**os.environ, "AZURE_CONFIG_DIR": str(AZ_CONFIG), "AZURE_CORE_COLLECT_TELEMETRY": "false",
           "AZURE_CORE_ONLY_SHOW_ERRORS": "true"}
    return subprocess.run([str(AZ_CMD), *args, "--only-show-errors"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout)


def _az_json(*args: str, timeout: int = 300):
    proc = _az(*args, "-o", "json", timeout=timeout)
    if proc.returncode != 0:
        from .seguranca import ocultar
        raise SystemExit(f"Azure: {ocultar(proc.stderr.strip()[-400:] or 'falhou')}")
    return json.loads(proc.stdout or "null")


def conectar_azure() -> dict:
    """Login no Azure com código; cria (ou reaproveita) o recurso de voz GRÁTIS F0 e grava a chave no .env.
    Nunca cria o nível pago (S0): sem F0 disponível, para e explica."""
    instalar_az()
    if _az("account", "show").returncode != 0:
        print("Entre na sua conta da Microsoft (Azure): o código aparece logo abaixo.")
        _abrir("https://login.microsoft.com/device")
        env = {**os.environ, "AZURE_CONFIG_DIR": str(AZ_CONFIG), "AZURE_CORE_COLLECT_TELEMETRY": "false"}
        proc = subprocess.Popen([str(AZ_CMD), "login", "--use-device-code", "--only-show-errors", "-o", "none"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", env=env)
        for linha in proc.stdout:
            print(linha.rstrip(), flush=True)
        if proc.wait(timeout=900) != 0:
            raise SystemExit("o login no Azure não terminou: clique de novo em Entrar com a Microsoft")
    assinaturas = [a for a in _az_json("account", "list") if a.get("state") == "Enabled"]
    if not assinaturas:
        raise SystemExit("sua conta da Microsoft ainda não tem uma assinatura do Azure. Crie a conta grátis em "
                         "https://azure.microsoft.com/free (é com você: pede cartão só para verificar identidade) "
                         "e clique de novo em Entrar com a Microsoft")
    _az("account", "set", "--subscription", assinaturas[0]["id"])
    print(f"assinatura do Azure: {assinaturas[0].get('name')}")
    # um F0 de voz por assinatura: reaproveita o que já existir (de qualquer grupo ou região)
    existentes = [c for c in _az_json("cognitiveservices", "account", "list")
                  if c.get("kind") == "SpeechServices" and (c.get("sku") or {}).get("name") == "F0"]
    if existentes:
        recurso = existentes[0]
        print(f"reaproveitando o recurso de voz grátis {recurso['name']}")
    else:
        _az("provider", "register", "--namespace", "Microsoft.CognitiveServices", "--wait", timeout=600)
        _az_json("group", "create", "--name", GRUPO_AZURE, "--location", REGIAO_AZURE)
        nome = f"projeto-canais-voz-{secrets.token_hex(3)}"
        print(f"criando o recurso de voz grátis (F0) {nome} em {REGIAO_AZURE}...")
        recurso = _az_json("cognitiveservices", "account", "create", "--name", nome, "--resource-group", GRUPO_AZURE,
                           "--kind", "SpeechServices", "--sku", "F0", "--location", REGIAO_AZURE, "--yes", timeout=600)
    if (recurso.get("sku") or {}).get("name") != "F0":  # trava: nunca guarda chave de recurso pago
        raise SystemExit("o recurso de voz não ficou no nível grátis F0; nada foi salvo")
    grupo = recurso.get("resourceGroup") or recurso["id"].split("/resourceGroups/")[1].split("/")[0]
    chaves = _az_json("cognitiveservices", "account", "keys", "list", "--name", recurso["name"],
                      "--resource-group", grupo)
    from .chaves import validar
    regiao = recurso.get("location", REGIAO_AZURE)
    ok, texto = validar("AZURE_SPEECH_KEY", chaves["key1"], {"AZURE_SPEECH_REGION": regiao})
    if ok is False:
        raise SystemExit(f"a chave criada não passou no teste: {texto}")
    salvar_env({"AZURE_SPEECH_KEY": chaves["key1"], "AZURE_SPEECH_REGION": regiao})
    print(f"ok: chave da voz salva (recurso {recurso['name']}, nível grátis F0, região {regiao})")
    return {"recurso": recurso["name"], "regiao": regiao}


# ---------- Instagram (OAuth do Instagram Login) ----------

INSTAGRAM_ESCOPOS = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_insights"
# página do site que só repassa o "code" para o Estúdio deste PC (a Meta exige endereço https)
INSTAGRAM_RETORNO_PADRAO = "https://vincfreitas.github.io/projeto-canais/instagram.html"
_ESTADOS: dict[str, tuple[str, float]] = {}  # estado -> (perfil, quando); o cookie SameSite=Strict não volta da Meta


def instagram_retorno() -> str:
    return os.getenv("INSTAGRAM_RETORNO", "").strip() or INSTAGRAM_RETORNO_PADRAO


def instagram_url(perfil: str, porta: int) -> str:
    """Endereço de login do Instagram. O estado leva a porta do Estúdio (a página de retorno precisa dela) e um
    segredo de uso único, conferido na volta."""
    app_id = os.getenv("INSTAGRAM_APP_ID", "").strip()
    if not app_id:
        raise SystemExit("falta o ID do app do Instagram (INSTAGRAM_APP_ID)")
    estado = f"{porta}.{secrets.token_urlsafe(24)}"
    _ESTADOS[estado] = (perfil, time.time())
    return "https://www.instagram.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": app_id, "redirect_uri": instagram_retorno(), "response_type": "code",
        "scope": INSTAGRAM_ESCOPOS, "state": estado, "force_reauth": "true"})


def instagram_perfil_do_estado(estado: str) -> str | None:
    """Perfil que pediu o login; o estado vale uma vez e por 15 minutos."""
    perfil, quando = _ESTADOS.pop(estado, (None, 0.0))
    return perfil if perfil and time.time() - quando < 900 else None


def instagram_trocar_codigo(codigo: str) -> str:
    """code -> token curto -> token de longa duração (60 dias)."""
    import requests
    app_id, segredo = os.getenv("INSTAGRAM_APP_ID", "").strip(), os.getenv("INSTAGRAM_APP_SECRET", "").strip()
    if not (app_id and segredo):
        raise SystemExit("falta o ID ou a chave secreta do app do Instagram")
    curto = requests.post("https://api.instagram.com/oauth/access_token", timeout=30, data={
        "client_id": app_id, "client_secret": segredo, "grant_type": "authorization_code",
        "redirect_uri": instagram_retorno(), "code": codigo}).json()
    if "access_token" not in curto:
        raise SystemExit(f"o Instagram recusou o login: {curto.get('error_message') or curto.get('error', curto)}")
    longo = requests.get("https://graph.instagram.com/access_token", timeout=30, params={
        "grant_type": "ig_exchange_token", "client_secret": segredo, "access_token": curto["access_token"]}).json()
    if "access_token" not in longo:
        raise SystemExit(f"o Instagram não deu o token de 60 dias: {longo.get('error', longo)}")
    return longo["access_token"]
