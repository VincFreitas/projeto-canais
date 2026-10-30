"""Modo nuvem: a reserva da postagem no GitHub Actions, para o canal postar mesmo com o PC desligado.

Os dois modos trabalham juntos:
  PC      n8n local às 12:00 e 19:00 (produz, publica e registra)
  nuvem   GitHub Actions às 12:20 e 19:20, rodando o mesmo workflow do n8n, num repositório PRIVADO de fila

O repositório de fila (NUVEM_REPO no .env) guarda, por perfil, o perfil.json, os roteiros aprovados com vídeo
pronto (o vídeo vai como arquivo da release "fila"), o estado.json (IDs já publicados) e o slots.json (qual
horário já foi atendido e por quem). Antes de postar, cada lado confere esse estado e, na nuvem, também a
própria plataforma: o mesmo vídeo nunca sai duas vezes e o mesmo horário nunca recebe dois vídeos.

O token do GitHub (NUVEM_TOKEN) é criado pela pessoa, com acesso só ao repositório de fila, e fica no .env.
As credenciais do YouTube e do Instagram vão como Secrets do repositório (criptografadas pelo GitHub).
"""
import base64
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config
from .seguranca import ocultar

API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
TAG = "fila"
BRASILIA = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019
JANELA_SLOT_H = 3                          # um post até 3 h depois do horário ainda conta para aquele horário
CODIGO = "VincFreitas/projeto-canais"
ID_WORKFLOW = "nuvemcanais0001"


# ---------- configuração ----------

def configurada() -> bool:
    return bool(os.getenv("NUVEM_REPO") and os.getenv("NUVEM_TOKEN"))


def na_nuvem() -> bool:
    """Rodando no GitHub Actions (o workflow define DARKOPS_NUVEM=1)."""
    return os.getenv("DARKOPS_NUVEM") == "1"


def simulando() -> bool:
    return os.getenv("DARKOPS_SIMULAR") == "1"


def _repo() -> str:
    repo = os.getenv("NUVEM_REPO", "").strip().removeprefix("https://github.com/").strip("/")
    if not re.match(r"^[\w.-]+/[\w.-]+$", repo):
        raise SystemExit("NUVEM_REPO precisa ser dono/repositório (ex.: VincFreitas/projeto-canais-fila)")
    return repo


# ---------- GitHub API ----------

def _pedir(metodo: str, caminho: str, dados=None, binario: bytes | None = None, tipo: str = "",
           base: str = API, aceitar: str = "application/vnd.github+json"):
    url = caminho if caminho.startswith("http") else f"{base}{caminho}"
    corpo = binario if binario is not None else (json.dumps(dados).encode() if dados is not None else None)
    cab = {"Authorization": f"Bearer {os.getenv('NUVEM_TOKEN', '')}", "Accept": aceitar,
           "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "projeto-canais"}
    if corpo is not None:
        cab["Content-Type"] = tipo or "application/json"
    req = urllib.request.Request(url, data=corpo, headers=cab, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            texto = r.read()
            return r.status, (json.loads(texto) if texto and "json" in r.headers.get("Content-Type", "") else texto)
    except urllib.error.HTTPError as erro:
        texto = erro.read().decode("utf-8", "replace")
        if erro.code in (404, 409, 422):
            return erro.code, texto
        raise SystemExit(ocultar(f"GitHub respondeu {erro.code} em {metodo} {caminho.split('?')[0]}: {texto[:300]}"))


def conferir_acesso() -> dict:
    status, dados = _pedir("GET", f"/repos/{_repo()}")
    if status != 200:
        raise SystemExit(f"não achei o repositório {_repo()} com esse token (confira o nome e o acesso do token)")
    if not dados.get("private"):
        raise SystemExit(f"o repositório {_repo()} é público: a fila precisa de um repositório PRIVADO")
    return dados


def _ler(caminho: str) -> tuple[str | None, str | None]:
    status, dados = _pedir("GET", f"/repos/{_repo()}/contents/{urllib.parse.quote(caminho)}")
    if status != 200:
        return None, None
    return base64.b64decode(dados["content"]).decode("utf-8"), dados["sha"]


def _gravar(caminho: str, texto: str, mensagem: str) -> bool:
    """Grava se mudou. Devolve True quando escreveu."""
    atual, sha = _ler(caminho)
    if atual == texto:
        return False
    dados = {"message": mensagem, "content": base64.b64encode(texto.encode("utf-8")).decode()}
    if sha:
        dados["sha"] = sha
    _pedir("PUT", f"/repos/{_repo()}/contents/{urllib.parse.quote(caminho)}", dados)
    return True


def _apagar(caminho: str, mensagem: str) -> None:
    _, sha = _ler(caminho)
    if sha:
        _pedir("DELETE", f"/repos/{_repo()}/contents/{urllib.parse.quote(caminho)}", {"message": mensagem, "sha": sha})


def _listar(pasta: str) -> list[str]:
    status, dados = _pedir("GET", f"/repos/{_repo()}/contents/{urllib.parse.quote(pasta)}")
    return [d["name"] for d in dados if d["type"] == "file"] if status == 200 and isinstance(dados, list) else []


def _release() -> dict:
    status, dados = _pedir("GET", f"/repos/{_repo()}/releases/tags/{TAG}")
    if status == 200:
        return dados
    _gravar("LEIA-ME.md", "# Fila do Projeto Canais\n\nRepositório privado criado pelo Estúdio. Não edite à mão.\n",
            "fila: criar")  # a release precisa de pelo menos um commit
    _, dados = _pedir("POST", f"/repos/{_repo()}/releases",
                      {"tag_name": TAG, "name": "Vídeos aprovados", "body": "Vídeos prontos esperando a vez de postar."})
    return dados


def _assets() -> dict[str, dict]:
    rel = _release()
    _, lista = _pedir("GET", f"/repos/{_repo()}/releases/{rel['id']}/assets?per_page=100")
    return {a["name"]: a for a in (lista if isinstance(lista, list) else [])}


def _enviar_video(nome: str, video: Path) -> None:
    rel = _release()
    _pedir("POST", f"{UPLOADS}/repos/{_repo()}/releases/{rel['id']}/assets?name={urllib.parse.quote(nome)}",
           binario=video.read_bytes(), tipo="video/mp4")


def _apagar_asset(asset: dict) -> None:
    _pedir("DELETE", f"/repos/{_repo()}/releases/assets/{asset['id']}")


def _segredo(nome: str, valor: str) -> None:
    from nacl import encoding, public
    _, chave = _pedir("GET", f"/repos/{_repo()}/actions/secrets/public-key")
    caixa = public.SealedBox(public.PublicKey(chave["key"].encode(), encoding.Base64Encoder()))
    cifrado = base64.b64encode(caixa.encrypt(valor.encode("utf-8"))).decode()
    _pedir("PUT", f"/repos/{_repo()}/actions/secrets/{nome}", {"encrypted_value": cifrado, "key_id": chave["key_id"]})


def nome_segredo(pid: str) -> str:
    return "PERFIL_" + re.sub(r"[^A-Z0-9]", "_", pid.upper())


def nome_asset(pid: str, video: str) -> str:
    return f"{pid}__{video}"


# ---------- horários (slots) ----------

def slot_atual(horarios: list[str], agora: datetime | None = None) -> str | None:
    """O horário de postagem da vez (o último que já passou), se ainda estiver dentro da janela."""
    agora = (agora or datetime.now(BRASILIA)).astimezone(BRASILIA)
    candidatos = []
    for dia in (agora.date() - timedelta(days=1), agora.date()):
        for h in horarios:
            hh, mm = map(int, h.split(":"))
            momento = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=BRASILIA)
            if momento <= agora:
                candidatos.append(momento)
    if not candidatos:
        return None
    ultimo = max(candidatos)
    return ultimo.strftime("%Y-%m-%d %H:%M") if agora - ultimo <= timedelta(hours=JANELA_SLOT_H) else None


def _slots_arquivo(perfil) -> Path:
    return perfil.controle / "slots.json"


def ler_slots(perfil) -> dict:
    arquivo = _slots_arquivo(perfil)
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def slot_atendido(perfil) -> str | None:
    """Quem já postou no horário da vez ('pc' ou 'nuvem'), ou None."""
    slot = slot_atual(perfil.dados.get("horarios", ["12:00", "19:00"]))
    return ler_slots(perfil).get(slot, {}).get("por") if slot else None


def registrar_slot(perfil, slug: str) -> None:
    slot = slot_atual(perfil.dados.get("horarios", ["12:00", "19:00"]))
    if not slot:
        return  # publicação fora de horário (ex.: "Publicar agora"): não ocupa a vez de ninguém
    slots = ler_slots(perfil)
    slots.setdefault(slot, {"slug": slug, "por": "nuvem" if na_nuvem() else "pc"})
    limite = (datetime.now(BRASILIA) - timedelta(days=30)).strftime("%Y-%m-%d")
    slots = {k: v for k, v in slots.items() if k >= limite}  # guarda só o último mês
    perfil.controle.mkdir(parents=True, exist_ok=True)
    _slots_arquivo(perfil).write_text(json.dumps(slots, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- conferência na própria plataforma (segunda trava, na nuvem) ----------

def ja_no_youtube(titulo: str) -> str | None:
    """ID do vídeo se um upload recente do canal já tem esse título."""
    from .publicar import _servico
    yt = _servico()
    canal = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
    itens = yt.playlistItems().list(part="snippet", playlistId=uploads, maxResults=15).execute().get("items", [])
    alvo = titulo.strip().lower()
    return next((i["snippet"]["resourceId"]["videoId"] for i in itens if i["snippet"]["title"].strip().lower() == alvo), None)


def ja_no_instagram(legenda: str) -> str | None:
    """ID da mídia se um post recente começa com a mesma primeira linha da legenda."""
    import requests
    from .instagram import token
    inicio = legenda.strip().splitlines()[0][:80].strip().lower() if legenda.strip() else ""
    if not inicio:
        return None
    r = requests.get("https://graph.instagram.com/me/media", timeout=30,
                     params={"fields": "id,caption", "limit": 15, "access_token": token()})
    if r.status_code != 200:
        return None
    return next((m["id"] for m in r.json().get("data", []) if (m.get("caption") or "").strip().lower().startswith(inicio)), None)


# ---------- PC: sincronizar com a nuvem ----------

def _local(perfil, nome: str) -> Path:
    return {"estado.json": perfil.controle / "estado.json", "slots.json": _slots_arquivo(perfil)}[nome]


def _mesclar(a: dict, b: dict) -> dict:
    saida = {k: dict(v) if isinstance(v, dict) else v for k, v in a.items()}
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(saida.get(k), dict):
            saida[k] = {**v, **saida[k]}  # o que já está anotado aqui prevalece; o resto vem do outro lado
        else:
            saida.setdefault(k, v)
    return saida


def _pronto(caminho: Path) -> tuple[dict, Path] | None:
    """Roteiro aprovado com vídeo em dia (o mesmo critério da prévia pronta do Estúdio)."""
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    slug = dados.get("slug") or caminho.stem
    video = config.SAIDA / f"{slug}-{dados.get('formato', 'vertical')}.mp4"
    if not dados.get("aprovado") or not video.exists() or video.stat().st_mtime < caminho.stat().st_mtime - 1:
        return None
    return dados, video


def sincronizar(perfil, enviar_videos: bool = True) -> dict:
    """Uma sincronização por vez: aprovar vários vídeos seguidos dispara várias, e elas brigariam entre si.
    Quem chega com outra rodando só pede "de novo"; a que está rodando repete até ninguém mais pedir."""
    trava, de_novo = perfil.controle / "nuvem.trava", perfil.controle / "nuvem.de-novo"
    perfil.controle.mkdir(parents=True, exist_ok=True)
    if trava.exists() and time.time() - trava.stat().st_mtime < 30 * 60:
        de_novo.touch()
        return {"concluidos_aqui": [], "enviados": [], "retirados": [], "adiado": True}
    trava.write_text(str(os.getpid()), encoding="utf-8")
    try:
        while True:
            de_novo.unlink(missing_ok=True)
            resumo = _sincronizar(perfil, enviar_videos)
            if not de_novo.exists():
                return resumo
    finally:
        trava.unlink(missing_ok=True)


def _sincronizar(perfil, enviar_videos: bool = True) -> dict:
    """Junta o estado do PC com o da nuvem, conclui aqui o que a nuvem já postou e manda os aprovados para lá."""
    from . import fila as fila_mod
    from .render import duracao
    base = f"perfis/{perfil.id}"
    resumo = {"concluidos_aqui": [], "enviados": [], "retirados": []}

    # 1. estado e horários: os dois lados somam o que cada um publicou
    for nome in ("estado.json", "slots.json"):
        remoto, _ = _ler(f"{base}/controle/{nome}")
        arquivo = _local(perfil, nome)
        local = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
        junto = _mesclar(local, json.loads(remoto) if remoto else {})
        perfil.controle.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(junto, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. o que a nuvem já publicou sai da fila daqui (mesmo caminho do "Registrar publicação" do n8n)
    for caminho in fila_mod.roteiros(perfil):
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        slug = dados.get("slug") or caminho.stem
        if fila_mod.ler_estado(perfil).get(slug):
            video = config.SAIDA / f"{slug}-{dados.get('formato', 'vertical')}.mp4"
            try:
                fila_mod.concluir(caminho, dados, duracao(video) if video.exists() else None, perfil)
                resumo["concluidos_aqui"].append(caminho.name)
            except SystemExit:
                pass  # publicado só em parte: continua na fila para a próxima tentativa

    # 3. o estado somado volta para a nuvem
    for nome in ("estado.json", "slots.json"):
        arquivo = _local(perfil, nome)
        if arquivo.exists():
            _gravar(f"{base}/controle/{nome}", arquivo.read_text(encoding="utf-8"), f"{perfil.id}: {nome}")
    _gravar(f"{base}/perfil.json", perfil.arquivo.read_text(encoding="utf-8"), f"{perfil.id}: perfil")

    if not enviar_videos:
        return resumo

    # 4. a fila da nuvem = os aprovados com vídeo pronto, na mesma ordem
    assets = _assets()
    prontos = {}
    for caminho in fila_mod.roteiros(perfil):
        achado = _pronto(caminho)
        if achado:
            prontos[caminho.name] = (caminho, *achado)
    for nome, (caminho, dados, video) in prontos.items():
        _gravar(f"{base}/fila/{nome}", caminho.read_text(encoding="utf-8"), f"{perfil.id}: fila {nome}")
        desc = perfil.controle / "descricoes" / nome
        if desc.exists():
            _gravar(f"{base}/controle/descricoes/{nome}", desc.read_text(encoding="utf-8"), f"{perfil.id}: descrição")
        asset = assets.get(nome_asset(perfil.id, video.name))
        if asset and asset["size"] != video.stat().st_size:
            _apagar_asset(asset)
            asset = None
        if not asset:
            _enviar_video(nome_asset(perfil.id, video.name), video)
            resumo["enviados"].append(nome)

    # 5. o que deixou de estar aprovado (ou já saiu) não fica na nuvem
    for nome in _listar(f"{base}/fila"):
        if nome not in prontos:
            _apagar(f"{base}/fila/{nome}", f"{perfil.id}: tirar {nome} da fila")
            resumo["retirados"].append(nome)
    usados = {nome_asset(perfil.id, v.name) for _, _, v in prontos.values()}
    for nome, asset in assets.items():
        if nome.startswith(f"{perfil.id}__") and nome not in usados:
            _apagar_asset(asset)
    return resumo


def enviar_segredos(perfis) -> list[str]:
    """Credenciais de cada perfil (e o app OAuth do Google) como Secrets do repositório de fila."""
    enviados = []
    client = config.RAIZ / "credenciais" / "client_secret.json"
    if client.exists():
        _segredo("CLIENT_SECRET", client.read_text(encoding="utf-8"))
        enviados.append("CLIENT_SECRET")
    for p in perfis:
        dados = {}
        if p.token_youtube.exists():
            dados["token_youtube"] = p.token_youtube.read_text(encoding="utf-8")
        if p.token_instagram.exists():
            dados["token_instagram"] = p.token_instagram.read_text(encoding="utf-8").strip()
        if dados:
            _segredo(nome_segredo(p.id), json.dumps(dados))
            enviados.append(nome_segredo(p.id))
    return enviados


def workflow_actions() -> str:
    return (config.RAIZ / "n8n" / "nuvem.actions.yml").read_text(encoding="utf-8")


def workflow_n8n_nuvem() -> str:
    """O mesmo workflow do PC, adaptado ao Linux do GitHub Actions: sem produzir vídeo (já vem pronto) e sem
    reabastecer a fila (criar vídeos fica no PC)."""
    w = json.loads((config.RAIZ / "n8n" / "workflow.modelo.json").read_text(encoding="utf-8"))
    fora = {"Produzir vídeo", "Reabastecer fila"}
    w["nodes"] = [n for n in w["nodes"] if n["name"] not in fora]
    con = w["connections"]
    for nome in fora:
        con.pop(nome, None)
    con["Fila vazia?"]["main"][1] = [{"node": "Publicar no YouTube", "type": "main", "index": 0}]
    con["Registrar publicação"]["main"][0] = []
    for n in w["nodes"]:
        if n["type"] == "n8n-nodes-base.scheduleTrigger":
            n["parameters"]["rule"]["interval"][0]["expression"] = "20 12,19 * * *"  # só para quem abrir o editor
        cmd = n.get("parameters", {}).get("command")
        if cmd:
            n["parameters"]["command"] = cmd.replace("cd /d __PASTA__", "cd __PASTA__")
    w.update({"name": "Canais dark - reserva na nuvem (GitHub Actions)", "id": ID_WORKFLOW, "active": False})
    texto = json.dumps(w, ensure_ascii=False, indent=2)
    return texto.replace("__PASTA__", "$GITHUB_WORKSPACE/codigo").replace("__PYTHON__", "python")


def configurar(perfis) -> dict:
    """Prepara o repositório de fila: workflow do Actions, workflow do n8n, release, segredos e a fila de cada perfil."""
    conferir_acesso()
    _release()
    _gravar(".github/workflows/postar.yml", workflow_actions(), "nuvem: workflow do Actions")
    _gravar("n8n-nuvem.json", workflow_n8n_nuvem(), "nuvem: workflow do n8n")
    segredos = enviar_segredos(perfis)
    filas = {p.id: sincronizar(p) for p in perfis}
    return {"repo": _repo(), "segredos": segredos, "filas": filas}


def disparar(simular: bool = True) -> None:
    """Roda o workflow da nuvem agora (no teste, em simulação: mostra o que faria sem publicar)."""
    ramo = conferir_acesso().get("default_branch", "main")
    status_, texto = _pedir("POST", f"/repos/{_repo()}/actions/workflows/postar.yml/dispatches",
                            {"ref": ramo, "inputs": {"simular": "true" if simular else "false"}})
    if status_ not in (200, 204):
        raise SystemExit(f"não consegui rodar o workflow da nuvem ({status_}): {str(texto)[:200]}")


def status(perfil) -> dict:
    """Para o Estúdio: quantos vídeos a nuvem tem, quantos dias isso cobre e quem postou por último."""
    if not configurada():
        return {"configurada": False}
    slots = ler_slots(perfil)
    ultimo = max(slots.items(), default=(None, {}))
    por_dia = max(len(perfil.dados.get("horarios", ["12:00", "19:00"])), 1)
    try:
        na_fila = len(_listar(f"perfis/{perfil.id}/fila"))
        erro = ""
    except SystemExit as e:
        na_fila, erro = 0, str(e)
    return {"configurada": True, "repo": os.getenv("NUVEM_REPO"), "na_fila": na_fila,
            "dias": round(na_fila / por_dia, 1), "ultimo_slot": ultimo[0], "ultimo_por": ultimo[1].get("por"),
            "erro": erro}


# ---------- nuvem: preparar o ambiente do Actions e devolver o resultado ----------

def preparar_actions(fila_dir: Path) -> list[str]:
    """No Actions: monta perfis/ a partir do repositório de fila, grava as credenciais dos Secrets e baixa os vídeos."""
    import subprocess
    if not na_nuvem():
        raise SystemExit("nuvem-preparar só roda no GitHub Actions: no PC ele apagaria os perfis locais")
    segredos = json.loads(os.getenv("SEGREDOS") or "{}")
    if segredos.get("CLIENT_SECRET"):
        (config.RAIZ / "credenciais").mkdir(exist_ok=True)
        (config.RAIZ / "credenciais" / "client_secret.json").write_text(segredos["CLIENT_SECRET"], encoding="utf-8")
    prontos = []
    for origem in sorted((fila_dir / "perfis").glob("*")):
        if not (origem / "perfil.json").exists():
            continue
        destino = config.RAIZ / "perfis" / origem.name
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(origem, destino)
        cred = json.loads(segredos.get(nome_segredo(origem.name)) or "{}")
        (destino / "credenciais").mkdir(exist_ok=True)
        if cred.get("token_youtube"):
            (destino / "credenciais" / "token_youtube.json").write_text(cred["token_youtube"], encoding="utf-8")
        if cred.get("token_instagram"):
            (destino / "credenciais" / "token_instagram.txt").write_text(cred["token_instagram"], encoding="utf-8")
        prontos.append(origem.name)
    # só os perfis montados aqui voltam para a fila: se a preparação não rodou, o devolver não copia nada
    (config.RAIZ / "dados").mkdir(exist_ok=True)
    (config.RAIZ / "dados" / "nuvem-preparados.json").write_text(json.dumps(prontos), encoding="utf-8")
    config.SAIDA.mkdir(exist_ok=True)
    pasta = config.RAIZ / "dados" / "fila-videos"
    pasta.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["gh", "release", "download", TAG, "--dir", str(pasta), "--clobber", "--repo",
                        os.environ["GITHUB_REPOSITORY"]], check=False)
    except FileNotFoundError:
        print("gh não encontrado: os vídeos não foram baixados")
    agora = time.time()
    for arquivo in pasta.glob("*__*.mp4"):
        video = config.SAIDA / arquivo.name.split("__", 1)[1]
        shutil.move(str(arquivo), video)
        os.utime(video, (agora, agora))  # o vídeo vem pronto: não é prévia desatualizada
    return prontos


def devolver_actions(fila_dir: Path) -> list[str]:
    """No Actions: copia de volta para o repositório de fila o que mudou (fila, publicados, estado, horários)."""
    import subprocess
    if not na_nuvem():
        raise SystemExit("nuvem-devolver só roda no GitHub Actions")
    marca = config.RAIZ / "dados" / "nuvem-preparados.json"
    preparados = set(json.loads(marca.read_text(encoding="utf-8"))) if marca.exists() else set()
    mudou = []
    for perfil_dir in sorted((config.RAIZ / "perfis").glob("*")):
        destino = fila_dir / "perfis" / perfil_dir.name
        if perfil_dir.name not in preparados or not destino.exists():
            continue  # sem preparação, aqui está a cópia do repositório público: não pode ir para a fila
        for sub in ("fila", "publicados"):
            alvo = destino / sub
            if alvo.exists():
                shutil.rmtree(alvo)
            if (perfil_dir / sub).exists():
                shutil.copytree(perfil_dir / sub, alvo)
        for nome in ("estado.json", "slots.json", "testes.csv", "falhas.log"):
            arquivo = perfil_dir / "controle" / nome
            if arquivo.exists():
                (destino / "controle").mkdir(parents=True, exist_ok=True)
                shutil.copy2(arquivo, destino / "controle" / nome)
        mudou.append(perfil_dir.name)
        # o vídeo que já foi publicado sai da release
        for publicado in (perfil_dir / "publicados").glob("*.json") if (perfil_dir / "publicados").exists() else []:
            dados = json.loads(publicado.read_text(encoding="utf-8"))
            nome = nome_asset(perfil_dir.name, f"{dados.get('slug') or publicado.stem}-{dados.get('formato', 'vertical')}.mp4")
            try:
                subprocess.run(["gh", "release", "delete-asset", TAG, nome, "--yes", "--repo",
                                os.environ["GITHUB_REPOSITORY"]], check=False, capture_output=True)
            except FileNotFoundError:
                pass
    return mudou
