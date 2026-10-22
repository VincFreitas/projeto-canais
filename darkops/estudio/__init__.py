"""Estúdio: painel local (http://127.0.0.1:8765) para conectar contas, montar a fila, gerar prévias,
aprovar e acompanhar a postagem automática de cada perfil.

Só aceita conexões do próprio PC. Tarefas pesadas (gerar vídeo, publicar, conectar o YouTube) rodam
como processos da CLI (`python -m darkops --perfil ...`), os mesmos que o n8n usa.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from .. import config
from .. import fila as fila_mod
from ..perfis import ID_VALIDO, PADRAO, carregar, criar, listar, slug

PYTHON = sys.executable
ARQUIVO_VALIDO = re.compile(r"^[\w.-]+\.json$")
CHAVES = [
    ("AZURE_SPEECH_KEY", "Azure Speech (chave)", True),
    ("AZURE_SPEECH_REGION", "Azure Speech (região, ex.: brazilsouth)", False),
    ("PIXABAY_API_KEY", "Pixabay", True),
    ("PEXELS_API_KEY", "Pexels", True),
    ("ELEVENLABS_API_KEY", "ElevenLabs (opcional)", True),
]
VOZES = ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural",
         "pt-BR-MacerioMultilingualNeural", "en-US-AndrewMultilingualNeural", "es-MX-JorgeNeural"]
JOBS: dict[str, dict] = {}

app = Flask(__name__)
app.secret_key = os.urandom(16)


# ---------- segurança: só o próprio PC ----------

@app.before_request
def _so_local():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)
    if request.method == "POST":
        origem = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if origem and not re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?(/|$)", origem):
            abort(403)


# ---------- utilidades ----------

def _perfil(pid: str):
    if not ID_VALIDO.match(pid):
        abort(404)
    p = carregar(pid)
    if not p.arquivo.exists():
        abort(404)
    return p


def _arquivo_fila(p, nome: str) -> Path:
    if not ARQUIVO_VALIDO.match(nome):
        abort(404)
    caminho = p.fila / nome
    if not caminho.exists():
        abort(404)
    return caminho


def _ler(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _gravar(caminho: Path, dados: dict) -> None:
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _video(dados: dict, caminho: Path) -> Path:
    slug_ = dados.get("slug") or caminho.stem
    return config.SAIDA / f"{slug_}-{dados.get('formato', 'vertical')}.mp4"


def _situacao(caminho: Path) -> dict:
    """Estado de um roteiro: sem prévia, prévia desatualizada, prévia pronta, aprovado."""
    dados = _ler(caminho)
    video = _video(dados, caminho)
    if not video.exists():
        estado = "sem-previa"
    elif video.stat().st_mtime < caminho.stat().st_mtime - 1:
        estado = "desatualizada"
    else:
        estado = "pronta"
    return {"arquivo": caminho.name, "dados": dados, "video": video.name if video.exists() else None,
            "estado": estado, "aprovado": bool(dados.get("aprovado"))}


def _env() -> dict:
    arquivo = config.RAIZ / ".env"
    valores = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                if v.strip():
                    valores[k.strip()] = v.strip()
    return valores


def _salvar_env(novos: dict) -> None:
    """Troca (ou acrescenta) as chaves no .env, sem duplicar linhas."""
    arquivo = config.RAIZ / ".env"
    linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
    for chave, valor in novos.items():
        linhas = [l for l in linhas if not re.match(rf"^\s*{chave}\s*=", l)]
        linhas.append(f"{chave}={valor}")
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _n8n_online() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:5678/healthz", timeout=0.6) as r:
            return r.status == 200
    except OSError:
        return False


def _conexoes(p) -> dict:
    arquivo = p.controle / "conexoes.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def _proximos_horarios(p, quantidade: int = 4) -> list[str]:
    horarios = sorted(p.dados.get("horarios", ["12:00", "19:00"]))
    agora, saida, dia = datetime.now(), [], 0
    while len(saida) < quantidade and dia < 10:
        data = (agora + timedelta(days=dia)).date()
        for h in horarios:
            hh, mm = map(int, h.split(":"))
            momento = datetime(data.year, data.month, data.day, hh, mm)
            if momento > agora:
                saida.append(momento.strftime("%d/%m %H:%M"))
        dia += 1
    return saida[:quantidade]


def _cli(perfil: str, *args: str) -> list[str]:
    return [PYTHON, "-m", "darkops", "--perfil", perfil, *args]


def _rodar_agora(perfil: str, *args: str, timeout: int = 60) -> tuple[bool, str]:
    proc = subprocess.run(_cli(perfil, *args), cwd=config.RAIZ, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout,
                          env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def _iniciar_job(p, titulo: str, comandos: list[list[str]]) -> str:
    """Roda comandos da CLI em sequência num processo de fundo; o log fica em controle/jobs/."""
    job_id = uuid.uuid4().hex[:10]
    pasta = p.controle / "jobs"
    pasta.mkdir(parents=True, exist_ok=True)
    log = pasta / f"{job_id}.log"
    JOBS[job_id] = {"id": job_id, "perfil": p.id, "titulo": titulo, "estado": "rodando",
                    "inicio": time.time(), "log": str(log)}

    def trabalhar():
        with log.open("w", encoding="utf-8") as saida:
            for args in comandos:
                saida.write(f"$ darkops {' '.join(args)}\n")
                saida.flush()
                proc = subprocess.run(_cli(p.id, *args), cwd=config.RAIZ, stdout=saida,
                                      stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
                if proc.returncode != 0:
                    JOBS[job_id]["estado"] = "falhou"
                    return
        JOBS[job_id]["estado"] = "concluido"

    threading.Thread(target=trabalhar, daemon=True).start()
    return job_id


@app.context_processor
def _contexto():
    return {"perfis": listar(), "agora": datetime.now()}


# ---------- perfis e chaves ----------

@app.get("/")
def inicio():
    perfis = listar()
    return redirect(url_for("painel", pid=perfis[0].id if perfis else PADRAO)) if perfis \
        else redirect(url_for("perfis_pagina"))


@app.get("/perfis")
def perfis_pagina():
    return render_template("perfis.html")


@app.post("/perfis/novo")
def perfil_novo():
    nome = request.form.get("nome", "").strip()
    if not nome:
        flash("Dê um nome ao canal.", "erro")
        return redirect(url_for("perfis_pagina"))
    pid = slug(nome)
    try:
        criar(pid, {"nome": nome, "arroba": request.form.get("arroba", "").strip() or f"@{pid.replace('-', '')}",
                    "nicho": request.form.get("nicho", "").strip(),
                    "descricao": request.form.get("descricao", "").strip()})
    except SystemExit as erro:
        flash(str(erro), "erro")
        return redirect(url_for("perfis_pagina"))
    flash(f"Perfil {nome} criado. Agora conecte as contas.", "ok")
    return redirect(url_for("conexoes", pid=pid))


@app.route("/chaves", methods=["GET", "POST"])
def chaves():
    if request.method == "POST":
        novos = {k: request.form[k].strip() for k, _, _ in CHAVES if request.form.get(k, "").strip()}
        if novos:
            _salvar_env(novos)
            flash(f"Salvo: {', '.join(novos)}. Vale para os próximos vídeos.", "ok")
        return redirect(url_for("chaves"))
    env = _env()
    return render_template("chaves.html", chaves=[(k, rotulo, segredo, k in env,
                                                   "" if segredo else env.get(k, "")) for k, rotulo, segredo in CHAVES])


# ---------- painel do perfil ----------

@app.get("/p/<pid>")
def painel(pid):
    p = _perfil(pid)
    itens = [_situacao(c) for c in fila_mod.roteiros(p)]
    from .conectores import resumo
    online = _n8n_online()
    return render_template("painel.html", p=p, d=p.dados, itens=itens, conexoes=_conexoes(p),
                           resumo=resumo(p, _conexoes(p), online),
                           aprovados=sum(1 for i in itens if i["aprovado"]), n8n=online,
                           horarios=_proximos_horarios(p), historico=fila_mod.historico(p)[-6:][::-1],
                           falhas=fila_mod.falhas(p, 5)[::-1], env=_env())


@app.route("/p/<pid>/configurar", methods=["GET", "POST"])
def configurar(pid):
    p = _perfil(pid)
    if request.method == "POST":
        f = request.form
        horarios = [h.strip() for h in f.get("horarios", "").split(",") if re.match(r"^\d{1,2}:\d{2}$", h.strip())]
        p.salvar({"nome": f.get("nome", "").strip() or p.dados["nome"],
                  "arroba": f.get("arroba", "").strip() or p.dados["arroba"],
                  "nicho": f.get("nicho", "").strip(), "descricao": f.get("descricao", "").strip(),
                  "voz": f.get("voz") or p.dados["voz"], "layout": f.get("layout") or "post",
                  "musica": f.get("musica") or "animada",
                  # pixel e cartoon têm a pulga narradora; clipes reais não
                  "estilo": f.get("estilo", ""), "narrador": f.get("estilo") in ("pixel", "cartoon"),
                  "privacidade_youtube": f.get("privacidade_youtube") or "public",
                  "horarios": horarios or p.dados["horarios"],
                  "youtube": bool(f.get("youtube")), "instagram": bool(f.get("instagram"))})
        foto = request.files.get("avatar")
        if foto and foto.filename:
            from PIL import Image, ImageOps
            img = ImageOps.exif_transpose(Image.open(foto.stream)).convert("RGB")
            img.thumbnail((512, 512))
            img.save(p.pasta / "avatar.png")
        flash("Perfil salvo.", "ok")
        return redirect(url_for("configurar", pid=pid))
    return render_template("configurar.html", p=p, d=p.dados, vozes=VOZES)


@app.get("/p/<pid>/avatar")
def avatar(pid):
    p = _perfil(pid)
    if p.avatar:
        return send_file(p.avatar)
    from ..narrador import _desenhar, _pixelar
    pixel = p.dados.get("estilo") == "pixel"
    destino = p.controle / ("pulga-avatar-pixel.png" if pixel else "pulga-avatar.png")
    p.controle.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        pulga = _desenhar(0.4, 0.15, 400)
        (_pixelar(pulga, 10) if pixel else pulga).save(destino)
    return send_file(destino)


@app.post("/p/<pid>/ativar")
def ativar(pid):
    p = _perfil(pid)
    p.salvar({"ativo": not p.dados.get("ativo")})
    flash("Postagem automática " + ("ligada." if p.dados["ativo"] else "pausada."), "ok")
    return redirect(request.referrer or url_for("painel", pid=pid))


# ---------- conexões ----------

@app.get("/p/<pid>/conexoes")
def conexoes(pid):
    from .conectores import GRUPOS, estado
    p = _perfil(pid)
    con, online, env = _conexoes(p), _n8n_online(), _env()
    grupos = [{"g": g, "itens": [{"c": c, "estado": estado(c, p, con, online),
                                  "valores": {k: ("" if segredo else env.get(k, "")) for k, _, segredo in c.chaves},
                                  "salvas": {k: bool(env.get(k)) for k, _, _ in c.chaves}}
                                 for c in g.conectores]} for g in GRUPOS]
    return render_template("conexoes.html", p=p, d=p.dados, conexoes=con, grupos=grupos,
                           tem_client=(config.RAIZ / "credenciais" / "client_secret.json").exists())


@app.post("/p/<pid>/conexoes/chaves")
def salvar_chaves_conector(pid):
    _perfil(pid)
    permitidas = {k for k, _, _ in CHAVES} | {"ELEVENLABS_VOZ"}
    novos = {k: v.strip() for k, v in request.form.items() if k in permitidas and v.strip()}
    if novos:
        _salvar_env(novos)
        flash(f"Salvo: {', '.join(novos)}. Vale para todos os perfis.", "ok")
    return redirect(url_for("conexoes", pid=pid) + "#" + request.form.get("ancora", ""))


@app.post("/p/<pid>/conexoes/youtube")
def conectar_youtube(pid):
    p = _perfil(pid).preparar()
    job = _iniciar_job(p, "Conectar YouTube", [["autorizar-youtube"]])
    flash("Abrimos o login do Google no navegador. Escolha a conta do canal e permita o acesso.", "ok")
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("conexoes", pid=pid)))


@app.post("/p/<pid>/conexoes/instagram")
def conectar_instagram(pid):
    p = _perfil(pid).preparar()
    valor = request.form.get("token", "").strip()
    if valor:
        p.token_instagram.write_text(valor, encoding="utf-8")
    return redirect(url_for("testar_conexoes", pid=pid), code=307)


@app.post("/p/<pid>/conexoes/testar")
def testar_conexoes(pid):
    p = _perfil(pid)
    estado = {}
    if p.token_youtube.exists():
        try:
            proc = subprocess.run([PYTHON, "-c", "from darkops.publicar import canal; print(canal()['nome'])"],
                                  cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=40,
                                  env={**os.environ, "DARKOPS_PERFIL": pid, "PYTHONIOENCODING": "utf-8"})
            estado["youtube"] = {"ok": proc.returncode == 0,
                                 "texto": proc.stdout.strip() or proc.stderr.strip().splitlines()[-1][:200]}
        except subprocess.TimeoutExpired:
            estado["youtube"] = {"ok": False, "texto": "tempo esgotado"}
    if p.token_instagram.exists():
        ok, saida = _rodar_agora(pid, "conta-instagram", timeout=40)
        estado["instagram"] = {"ok": ok, "texto": (saida.splitlines() or [""])[-1][:200]}
    estado["testado_em"] = datetime.now().strftime("%d/%m %H:%M")
    p.controle.mkdir(parents=True, exist_ok=True)
    (p.controle / "conexoes.json").write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
    flash("Conexões testadas.", "ok")
    return redirect(url_for("conexoes", pid=pid))


# ---------- fila e roteiros ----------

@app.get("/p/<pid>/fila")
def fila(pid):
    p = _perfil(pid)
    return render_template("fila.html", p=p, d=p.dados, itens=[_situacao(c) for c in fila_mod.roteiros(p)])


@app.post("/p/<pid>/fila/<nome>/mover/<direcao>")
def mover(pid, nome, direcao):
    p = _perfil(pid)
    lista = fila_mod.roteiros(p)
    atual = _arquivo_fila(p, nome)
    i = lista.index(atual)
    j = i - 1 if direcao == "cima" else i + 1
    if 0 <= j < len(lista):
        a, b = lista[i], lista[j]
        pa, pb = a.name[:3], b.name[:3]
        if pa.isdigit() and pb.isdigit():
            temp = a.with_name("tmp-" + a.name)
            a.rename(temp)
            b.rename(b.with_name(pa + b.name[3:]))
            temp.rename(a.with_name(pb + a.name[3:]))
    return redirect(url_for("fila", pid=pid))


@app.post("/p/<pid>/fila/<nome>/aprovar")
def aprovar(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    situacao = _situacao(caminho)
    dados = situacao["dados"]
    if not dados.get("aprovado") and situacao["estado"] != "pronta":
        flash("Gere e assista a prévia antes de aprovar.", "erro")
    else:
        dados["aprovado"] = not dados.get("aprovado")
        _gravar(caminho, dados)
        os.utime(config.SAIDA / situacao["video"]) if situacao["video"] else None  # prévia continua em dia
        flash("Aprovado: entra na postagem automática." if dados["aprovado"] else "Aprovação retirada.", "ok")
    return redirect(request.referrer or url_for("fila", pid=pid))


@app.post("/p/<pid>/fila/<nome>/arquivar")
def arquivar(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    destino = p.pasta / "arquivados"
    destino.mkdir(exist_ok=True)
    caminho.rename(destino / caminho.name)
    flash(f"{nome} saiu da fila (está em perfis/{pid}/arquivados).", "ok")
    return redirect(url_for("fila", pid=pid))


@app.post("/p/<pid>/fila/<nome>/previa")
def previa(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    job = _iniciar_job(p, f"Prévia de {nome}", [["fila-produzir", str(caminho)]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("ver", pid=pid, nome=nome)))


@app.post("/p/<pid>/fila/<nome>/publicar")
def publicar_agora(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    if not _ler(caminho).get("aprovado"):
        flash("Só dá para publicar um vídeo aprovado.", "erro")
        return redirect(url_for("ver", pid=pid, nome=nome))
    comandos = [["fila-produzir", str(caminho)]]
    if p.dados.get("youtube", True):
        comandos.append(["publicar-youtube", str(caminho)])
    if p.dados.get("instagram", True):
        comandos.append(["publicar-instagram", str(caminho)])
    comandos.append(["fila-concluir", str(caminho)])
    job = _iniciar_job(p, f"Publicar {nome}", comandos)
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("historico", pid=pid)))


@app.get("/p/<pid>/fila/<nome>")
def ver(pid, nome):
    p = _perfil(pid)
    return render_template("ver.html", p=p, d=p.dados, s=_situacao(_arquivo_fila(p, nome)))


@app.route("/p/<pid>/fila/<nome>/editar", methods=["GET", "POST"])
def editar(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    if request.method == "POST":
        f = request.form
        if f.get("modo") == "json":
            try:
                dados = json.loads(f.get("json", ""))
            except json.JSONDecodeError as erro:
                flash(f"JSON inválido: {erro}", "erro")
                return render_template("editar.html", p=p, d=p.dados, nome=nome, r=dados,
                                       bruto=f.get("json", ""))
        else:
            dados["manchete"] = f.get("manchete", "").strip()
            dados["titulo"] = f.get("titulo", "").strip() or dados.get("titulo")
            meta = dados.setdefault("metadados", {})
            meta.setdefault("youtube_shorts", {})["titulo"] = f.get("titulo_yt", "").strip()
            ig = meta.setdefault("instagram", {})
            ig["legenda"] = f.get("legenda_ig", "").strip()
            ig["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in f.get("hashtags", "").split() if h]
            dados["fontes"] = [l.strip() for l in f.get("fontes", "").splitlines() if l.strip()]
            for i, cena in enumerate(dados.get("cenas", [])):
                cena["texto"] = f.get(f"texto_{i}", cena["texto"]).strip()
                cena["visual"] = f.get(f"visual_{i}", cena.get("visual", "")).strip()
                for campo in ("destaque", "destaque_em"):
                    valor = f.get(f"{campo}_{i}", "").strip()
                    if valor:
                        cena[campo] = valor
                    else:
                        cena.pop(campo, None)
                tipo = f.get(f"tipo_{i}")
                if tipo in ("video", "foto"):
                    cena["tipo_visual"] = tipo
        dados["aprovado"] = False  # mudou: precisa de prévia nova e aprovação de novo
        _gravar(caminho, dados)
        flash("Roteiro salvo. Gere a prévia de novo antes de aprovar.", "ok")
        return redirect(url_for("ver", pid=pid, nome=nome))
    return render_template("editar.html", p=p, d=p.dados, nome=nome, r=dados,
                           bruto=json.dumps(dados, ensure_ascii=False, indent=2))


@app.route("/p/<pid>/novo", methods=["GET", "POST"])
def novo(pid):
    p = _perfil(pid)
    if request.method == "POST":
        f = request.form
        manchete = f.get("manchete", "").strip()
        cenas = []
        for linha in f.get("cenas", "").splitlines():
            partes = [x.strip() for x in linha.split("|")]
            if not partes[0]:
                continue
            cena = {"texto": partes[0], "visual": partes[1] if len(partes) > 1 else ""}
            if len(partes) > 2 and partes[2]:
                cena["destaque"] = partes[2]
            cenas.append(cena)
        if not manchete or not cenas:
            flash("Preencha a manchete e pelo menos uma cena.", "erro")
            return render_template("novo.html", p=p, d=p.dados, f=f)
        numeros = [int(c.name[:3]) for c in fila_mod.roteiros(p) if c.name[:3].isdigit()]
        numero = max(numeros + [0]) + 1
        s = slug(f.get("titulo") or manchete)
        roteiro = {
            "slug": s, "titulo": f.get("titulo", "").strip() or manchete, "manchete": manchete,
            "idioma": p.dados.get("idioma", "pt"), "formato": "vertical", "velocidade": "+10%",
            "tipo_visual": "video", "fontes": [l.strip() for l in f.get("fontes", "").splitlines() if l.strip()],
            "cenas": cenas,
            "metadados": {"youtube_shorts": {"titulo": f.get("titulo", "").strip() or manchete},
                          "instagram": {"legenda": f"{manchete}. Você sabia? Segue a {p.dados['arroba']} para mais.",
                                        "hashtags": ["#curiosidades", "#vocesabia"]}},
            "aprovado": False,
        }
        destino = p.fila / f"{numero:03d}-{s}.json"
        _gravar(destino, roteiro)
        flash("Roteiro criado no fim da fila. Revise e gere a prévia.", "ok")
        return redirect(url_for("ver", pid=pid, nome=destino.name))
    return render_template("novo.html", p=p, d=p.dados, f={})


# ---------- vídeos, tarefas e histórico ----------

@app.get("/midia/<nome>")
def midia(nome):
    if not re.match(r"^[\w.-]+\.mp4$", nome):
        abort(404)
    caminho = config.SAIDA / nome
    if not caminho.exists():
        abort(404)
    return send_file(caminho, mimetype="video/mp4", conditional=True)


@app.get("/p/<pid>/tarefa/<job>")
def acompanhar(pid, job):
    p = _perfil(pid)
    return render_template("tarefa.html", p=p, d=p.dados, job=JOBS.get(job), job_id=job,
                           voltar=request.args.get("voltar") or url_for("painel", pid=pid))


@app.get("/tarefa/<job>.json")
def tarefa_json(job):
    info = JOBS.get(job)
    if not info:
        return jsonify({"estado": "desconhecido", "log": ""})
    texto = Path(info["log"]).read_text(encoding="utf-8", errors="replace") if Path(info["log"]).exists() else ""
    return jsonify({"estado": info["estado"], "log": texto[-6000:],
                    "segundos": int(time.time() - info["inicio"])})


@app.get("/p/<pid>/historico")
def historico(pid):
    p = _perfil(pid)
    return render_template("historico.html", p=p, d=p.dados, linhas=fila_mod.historico(p)[::-1],
                           falhas=fila_mod.falhas(p, 50)[::-1])


def rodar(porta: int = 8765, abrir: bool = True) -> None:
    import socket
    porta = int(os.environ.get("PORT", porta))  # o preview do Claude Code pode escolher a porta
    url = f"http://127.0.0.1:{porta}"
    # no Windows dois servidores conseguem ocupar a mesma porta e responder misturado: não abre outro
    with socket.socket() as teste:
        if teste.connect_ex(("127.0.0.1", porta)) == 0:
            print(f"O Estúdio já está aberto em {url}")
            if abrir:
                webbrowser.open(url)
            return
    print(f"Estúdio em {url} (Ctrl+C para fechar)")
    if abrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=porta, debug=False, threaded=True)
