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
from .. import autoria, plataformas
from ..perfis import (DURACOES, FONTES_LEGENDA, FORMATOS, ID_VALIDO, MODELO, MOTORES_VOZ, PADRAO, RITMOS,
                      TAMANHOS_LEGENDA, TEMAS_CARDS, TIPOS_VISUAL, campos_canal, campos_padrao, carregar, criar, listar,
                      nomes_plataformas, rotulo_duracao, slug)

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


# ---------- modo guiado: enquanto a configuração não termina, só as telas de configurar ----------

# telas que esperam a configuração pronta; o resto (progresso, conexões, chaves, perfis, sobre) fica livre
TRAVADAS = {"inicio", "painel", "fila", "ver", "editar", "novo", "historico"}


def _guia_pendente() -> list:
    if os.getenv("DARKOPS_MODO_GUIADO", "1").strip() == "0":
        return []
    return plataformas.pendencias()


@app.before_request
def _modo_guiado():
    if request.endpoint in TRAVADAS and request.method == "GET" and _guia_pendente():
        if request.endpoint != "inicio":
            flash("Modo guiado: termine a configuração para liberar esta tela. Siga o próximo passo abaixo.", "erro")
        return redirect(url_for("progresso"))


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
    return {"perfis": listar(), "agora": datetime.now(), "formatos": FORMATOS,
            "duracoes": DURACOES, "rotulo_duracao": rotulo_duracao, "nomes_plataformas": nomes_plataformas,
            "estimar_leva": _estimar_leva, "autoria": autoria, "creditos_removidos": autoria.creditos_removidos(),
            "guiado": request.endpoint and bool(_guia_pendente()), "travadas": TRAVADAS}


# ---------- perfis e chaves ----------

@app.get("/")
def inicio():
    perfis = listar()
    return redirect(url_for("painel", pid=perfis[0].id if perfis else PADRAO)) if perfis \
        else redirect(url_for("perfis_pagina"))


@app.get("/perfis")
def perfis_pagina():
    return render_template("perfis.html", modelo=MODELO, status=plataformas.calcular(novo=True))


@app.get("/progresso")
def progresso():
    return render_template("progresso.html", base=plataformas.base(), redes=plataformas.calcular(),
                           pendentes=_guia_pendente())


@app.route("/sobre", methods=["GET", "POST"])
def sobre():
    if request.method == "POST":
        # o Estúdio roda no PC de quem testa: a sugestão vira uma issue pré-preenchida no repositório do autor
        f = request.form
        texto = f.get("texto", "").strip()
        if not texto:
            flash("Escreva a sugestão antes de enviar.", "erro")
            return redirect(url_for("sobre") + "#sugestao")
        tipo = f.get("tipo") or "Ideia"
        redes = sorted({nomes_plataformas(p.dados) for p in listar()} - {""})
        corpo = (f"{texto}\n\n---\nTipo: {tipo}\nNome: {f.get('nome', '').strip() or 'não informado'}\n"
                 f"Versão: {autoria.VERSAO}\nPlataformas dos perfis: {'; '.join(redes) or 'nenhuma'}\n"
                 f"Configuração pendente: {len(_guia_pendente())} etapa(s)\nSistema: {sys.platform}")
        titulo = f"[{tipo}] {texto.splitlines()[0][:70]}"
        from urllib.parse import urlencode
        return redirect(f"{autoria.REPOSITORIO}/issues/new?{urlencode({'title': titulo, 'body': corpo})}")
    return render_template("sobre.html")


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
                    "descricao": request.form.get("descricao", "").strip(), **campos_canal(request.form)})
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
                  "horarios": horarios or p.dados["horarios"], **campos_canal(f), **campos_padrao(f)})
        foto = request.files.get("avatar")
        if foto and foto.filename:
            from PIL import Image, ImageOps
            img = ImageOps.exif_transpose(Image.open(foto.stream)).convert("RGB")
            img.thumbnail((512, 512))
            img.save(p.pasta / "avatar.png")
        flash("Perfil salvo.", "ok")
        return redirect(url_for("configurar", pid=pid))
    return render_template("configurar.html", p=p, d=p.dados, vozes=VOZES, status=plataformas.calcular(p),
                           motores_voz=MOTORES_VOZ, tipos_visual=TIPOS_VISUAL, ritmos=RITMOS,
                           tamanhos_legenda=TAMANHOS_LEGENDA, fontes_legenda=FONTES_LEGENDA, temas_cards=TEMAS_CARDS,
                           tem_elevenlabs=bool(_env().get("ELEVENLABS_API_KEY")), ref=_referencias(p))


@app.post("/p/<pid>/referencia")
def referencia_analisar(pid):
    p = _perfil(pid)
    urls = [u.strip() for u in request.form.get("urls", "").split() if re.match(r"^https?://\S+$", u.strip())][:5]
    if not urls:
        flash("Cole pelo menos um link de vídeo (YouTube, Shorts, Instagram...).", "erro")
        return redirect(url_for("configurar", pid=pid) + "#referencia")
    job = _iniciar_job(p, "Aprender com referência", [["referencia", *urls]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("configurar", pid=pid) + "#referencia"))


@app.post("/p/<pid>/referencia/aplicar")
def referencia_aplicar(pid):
    from .. import referencia
    p = _perfil(pid)
    sugestao = referencia.ler(p).get("proposta") or {}
    novos = {k: sugestao[k] for k in ("formato", "duracao_s", "ritmo_corte_s", "velocidade") if k in sugestao}
    if novos:
        p.salvar(novos)
        flash("Padrão da referência aplicado no perfil: " + ", ".join(f"{k} = {v}" for k, v in novos.items()), "ok")
    return redirect(url_for("configurar", pid=pid) + "#referencia")


@app.get("/p/<pid>/referencia/<vid>.jpg")
def referencia_folha(pid, vid):
    _perfil(pid)
    from .. import referencia
    folha = referencia.PASTA / vid / "folha.jpg"
    if not re.match(r"^[\w-]{3,40}$", vid) or not folha.exists():
        abort(404)
    return send_file(folha, mimetype="image/jpeg")


def _estimar_leva(dados: dict, quantidade: int) -> dict:
    from ..leva import estimar
    return estimar(dados, quantidade)


@app.post("/p/<pid>/leva")
def criar_leva(pid):
    """Salva a quantidade escolhida e cria a leva num processo de fundo (pode levar horas)."""
    from ..leva import LIMITE_LEVA, _claude
    p = _perfil(pid)
    try:
        quantidade = min(max(int(request.form.get("leva_quantidade", 7)), 1), LIMITE_LEVA)
    except ValueError:
        quantidade = 7
    if not _claude():
        flash("A leva precisa do Claude Code instalado neste PC (claude.com/claude-code).", "erro")
        return redirect(url_for("configurar", pid=pid))
    p.salvar({"leva_quantidade": quantidade})
    job = _iniciar_job(p, f"Leva de {quantidade} vídeo(s)", [["leva", "--quantidade", str(quantidade)]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("fila", pid=pid)))


@app.get("/tema-card/<nome>.png")
def tema_card(nome):
    """Amostra de um card de comparação no tema pedido (para escolher na aba Perfil)."""
    import io
    from ..animacoes import TEMAS, quadro_teste
    if nome not in TEMAS:
        abort(404)
    exemplo = {"tipo": "comparacao", "titulo": "Vênus", "unidade": "dias", "tema": nome,
               "itens": [{"rotulo": "Dia", "valor": 243}, {"rotulo": "Ano", "valor": 225}]}
    img = quadro_teste(exemplo, 1080, 1920, 2.5, 4.0)
    img.thumbnail((360, 360))
    saida = io.BytesIO()
    img.save(saida, "PNG")
    saida.seek(0)
    return send_file(saida, mimetype="image/png", max_age=3600)


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
    from .. import conferir
    s = _situacao(_arquivo_fila(p, nome))
    return render_template("ver.html", p=p, d=p.dados, s=s, conferencia=conferir.ler(p, s["video"]) if s.get("video") else {})


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


# ---------- editor de cenas (na prévia) ----------

def _visual_atual(dados: dict, nome: str, i: int) -> Path | None:
    """Imagem ou clipe que a última prévia usou na cena i (1, 2, ...), se existir."""
    slug_ = dados.get("slug") or Path(nome).stem
    pasta = config.OBRA / slug_ / dados.get("formato", "vertical") / "visuais"
    candidatos = [c for c in pasta.glob(f"{i:02d}*") if c.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".mp4")
                  and "animacao" not in c.name and "narrador" not in c.name and "pulado" not in c.name
                  and "bruto" not in c.name] if pasta.exists() else []
    return max(candidatos, key=lambda c: c.stat().st_mtime) if candidatos else None


@app.get("/p/<pid>/fila/<nome>/visual/<int:i>")
def visual_cena(pid, nome, i):
    p = _perfil(pid)
    dados = _ler(_arquivo_fila(p, nome))
    cena = (dados.get("cenas") or [])[i - 1] if 0 < i <= len(dados.get("cenas") or []) else None
    if cena and cena.get("arquivo"):  # arquivo enviado do PC
        caminho = (p.fila / cena["arquivo"]).resolve()
        if caminho.is_relative_to(p.fila.resolve()) and caminho.exists():
            return send_file(caminho)
    atual = _visual_atual(dados, nome, i)
    if not atual:
        abort(404)
    return send_file(atual)


@app.post("/p/<pid>/fila/<nome>/cena/<int:i>")
def editar_cena(pid, nome, i):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    cenas = dados.get("cenas") or []
    if not 0 < i <= len(cenas):
        abort(404)
    cena, f = cenas[i - 1], request.form
    acao = f.get("acao", "salvar")
    busca = f.get("visual", "").strip()
    if busca and busca != cena.get("visual"):
        cena["visual"], cena["variante"] = busca, 0
        cena.pop("arquivo", None)
    if f.get("tipo_visual") in ("foto", "video"):
        cena["tipo_visual"] = f["tipo_visual"]
    if f.get("movimento") in ("aproxima", "afasta", "panoramica_direita", "panoramica_esquerda"):
        cena["movimento"] = f["movimento"]
    elif f.get("movimento") == "auto":
        cena.pop("movimento", None)
    if acao == "outra":  # próxima opção da mesma busca
        cena["variante"] = int(cena.get("variante", 0)) + 1
        cena.pop("arquivo", None)
    elif acao == "banco":  # volta a usar a busca em vez do arquivo enviado
        cena.pop("arquivo", None)
    arquivo = request.files.get("arquivo")
    if arquivo and arquivo.filename:
        extensao = Path(arquivo.filename).suffix.lower()
        if extensao not in (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"):
            flash("Envie uma imagem (jpg, png, webp) ou um vídeo (mp4, mov).", "erro")
            return redirect(url_for("ver", pid=pid, nome=nome) + f"#cena{i}")
        pasta = p.fila / "midia"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{Path(nome).stem}-{i:02d}{extensao}"
        arquivo.save(destino)
        cena["arquivo"] = f"midia/{destino.name}"
    dados["aprovado"] = False  # mudou: precisa de prévia nova e aprovação de novo
    _gravar(caminho, dados)
    flash(f"Cena {i} atualizada. Gere a prévia de novo: só as cenas alteradas são refeitas.", "ok")
    return redirect(url_for("ver", pid=pid, nome=nome) + f"#cena{i}")


@app.post("/p/<pid>/fila/<nome>/conferir")
def conferir_video(pid, nome):
    from .. import conferir
    p = _perfil(pid)
    s = _situacao(_arquivo_fila(p, nome))
    if not s.get("video"):
        flash("Gere a prévia antes de conferir.", "erro")
        return redirect(url_for("ver", pid=pid, nome=nome))
    resultado = conferir.conferir(config.SAIDA / s["video"], p.dados.get("duracao_s"))
    conferir.salvar(resultado, p)
    return redirect(url_for("ver", pid=pid, nome=nome) + "#conferencia")


@app.post("/p/<pid>/fila/<nome>/legenda")
def alternar_legenda(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    dados["legenda"] = not dados.get("legenda", p.dados.get("legenda", True))
    dados["aprovado"] = False
    _gravar(caminho, dados)
    flash(f"Legenda {'ligada' if dados['legenda'] else 'desligada'} neste vídeo. Gere a prévia de novo.", "ok")
    return redirect(url_for("ver", pid=pid, nome=nome))


# ---------- lotes para gerador externo (Google Flow, Gemini, ChatGPT...) ----------

DOWNLOADS = Path.home() / "Downloads"
EXT_IMAGEM = (".jpg", ".jpeg", ".png", ".webp")
TAMANHO_LOTE = 20


def _prompts(p, dados: dict) -> list[str]:
    """Um prompt por cena: estilo + personagem fixo + o que se vê na cena (ilustração ou, sem ela, a fala)."""
    from ..visuais import ESTILOS_IA
    estilo = dados.get("estilo") or p.dados.get("estilo") or ""
    base = ESTILOS_IA.get(estilo, "Illustration for a short educational video. No text, no letters, no watermark. ")
    formato = "vertical 9:16" if dados.get("formato", "vertical") == "vertical" else "horizontal 16:9"
    personagem = (dados.get("personagem") or "").strip()
    return [f"{base}{personagem + ' ' if personagem else ''}Scene: {(c.get('ilustracao') or c['texto']).strip()} "
            f"Aspect ratio {formato}." for c in dados.get("cenas", [])]


def _baixadas_desde(momento: float) -> list[Path]:
    if not DOWNLOADS.exists():
        return []
    novas = [f for f in DOWNLOADS.iterdir() if f.is_file() and f.suffix.lower() in EXT_IMAGEM
             and f.stat().st_mtime > momento and not f.name.endswith((".crdownload", ".part"))]
    return sorted(novas, key=lambda f: f.stat().st_mtime)


@app.get("/p/<pid>/fila/<nome>/lotes")
def lotes(pid, nome):
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    if request.args.get("comecar") or not dados.get("lote_aberto_em"):
        dados["lote_aberto_em"] = time.time()  # só valem as imagens baixadas daqui para a frente
        _gravar(caminho, dados)
    prompts = _prompts(p, dados)
    blocos = [list(enumerate(prompts, 1))[i:i + TAMANHO_LOTE] for i in range(0, len(prompts), TAMANHO_LOTE)]
    faltam = [i for i, c in enumerate(dados.get("cenas", []), 1) if not c.get("arquivo")]
    return render_template("lotes.html", p=p, d=p.dados, nome=nome, r=dados, blocos=blocos, faltam=faltam,
                           pasta=str(DOWNLOADS))


@app.get("/p/<pid>/fila/<nome>/lotes/novas.json")
def lotes_novas(pid, nome):
    p = _perfil(pid)
    dados = _ler(_arquivo_fila(p, nome))
    novas = _baixadas_desde(float(dados.get("lote_aberto_em", time.time())))
    return jsonify({"novas": [f.name for f in novas],
                    "faltam": sum(1 for c in dados.get("cenas", []) if not c.get("arquivo"))})


@app.post("/p/<pid>/fila/<nome>/lotes/importar")
def lotes_importar(pid, nome):
    """Põe as imagens baixadas, na ordem em que chegaram, nas cenas que ainda não têm arquivo."""
    import shutil
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    novas = _baixadas_desde(float(dados.get("lote_aberto_em", time.time())))
    vazias = [c for c in dados.get("cenas", []) if not c.get("arquivo")]
    pasta = p.fila / "midia"
    pasta.mkdir(parents=True, exist_ok=True)
    usadas = 0
    for cena, arquivo in zip(vazias, novas):
        i = dados["cenas"].index(cena) + 1
        destino = pasta / f"{Path(nome).stem}-{i:02d}{arquivo.suffix.lower()}"
        shutil.copy2(arquivo, destino)
        cena["arquivo"] = f"midia/{destino.name}"
        usadas += 1
    if usadas:
        ultima = novas[usadas - 1].stat().st_mtime
        dados["lote_aberto_em"] = ultima  # a próxima importação começa depois da última usada
        dados["imagens_ia"] = True
        if request.form.get("realistas"):
            dados["sintetico"] = True
        dados["aprovado"] = False
        _gravar(caminho, dados)
    restam = len(vazias) - usadas
    flash(f"{usadas} imagem(ns) importada(s) para as cenas." + (f" Faltam {restam}." if restam > 0 else
          " Todas as cenas têm imagem: gere a prévia."), "ok" if usadas else "erro")
    return redirect(url_for("lotes", pid=pid, nome=nome))


def _descoberta(p) -> dict:
    """Última busca de assuntos fortes deste perfil: termo, pasta e os vídeos achados (se já terminou)."""
    marca = p.controle / "descobrir.json"
    if not marca.exists():
        return {}
    dados = json.loads(marca.read_text(encoding="utf-8"))
    arquivo = Path(dados["pasta"]) / "outliers.json"
    dados["videos"] = json.loads(arquivo.read_text(encoding="utf-8"))[:12] if arquivo.exists() else []
    return dados


@app.post("/p/<pid>/descobrir")
def descobrir(pid):
    from ..pesquisa import pasta_do_dia
    p = _perfil(pid)
    termo = request.form.get("termo", "").strip()[:80]
    if not termo:
        flash("Escreva o nicho ou o assunto para pesquisar.", "erro")
        return redirect(url_for("novo", pid=pid))
    nome = f"estudio-{slug(termo)}"
    pasta = pasta_do_dia(nome)
    (pasta / "outliers.json").unlink(missing_ok=True)  # resultado velho do mesmo dia não se mistura
    p.controle.mkdir(parents=True, exist_ok=True)
    (p.controle / "descobrir.json").write_text(json.dumps({"termo": termo, "pasta": str(pasta)}, ensure_ascii=False),
                                               encoding="utf-8")
    job = _iniciar_job(p, f"Assuntos fortes: {termo}",
                       [["outliers", "--busca", termo, "--idioma", p.dados.get("idioma", "pt"), "--nome", nome,
                         "--por-busca", "25", "--top", "12", "--detalhar", "6"]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("novo", pid=pid) + "#assuntos"))


def _criar_roteiro(p, manchete: str, titulo: str, cenas: list[dict], fontes: str, **extra) -> Path:
    """Grava um roteiro novo no fim da fila do perfil (sem aprovação) e devolve o caminho."""
    numeros = [int(c.name[:3]) for c in fila_mod.roteiros(p) if c.name[:3].isdigit()]
    numero = max(numeros + [0]) + 1
    titulo = titulo.strip() or manchete
    s = slug(titulo)
    formato = p.dados.get("formato", "vertical")
    roteiro = {
        "slug": s, "titulo": titulo, "manchete": manchete,
        "idioma": p.dados.get("idioma", "pt"), "formato": formato, "velocidade": "+10%",
        "tipo_visual": "video", "fontes": [l.strip() for l in fontes.splitlines() if l.strip()],
        "cenas": cenas,
        "metadados": {("youtube_shorts" if formato == "vertical" else "youtube"): {"titulo": titulo},
                      "instagram": {"legenda": f"{manchete}. Você sabia? Segue a {p.dados['arroba']} para mais.",
                                    "hashtags": ["#curiosidades", "#vocesabia"]}},
        "aprovado": False, **extra,
    }
    destino = p.fila / f"{numero:03d}-{s}.json"
    _gravar(destino, roteiro)
    return destino


@app.post("/p/<pid>/novo/roteiro")
def novo_de_roteiro(pid):
    """Roteiro pronto colado: o Estúdio divide em cenas pelo ritmo do canal."""
    from ..entrada import cenas_de_texto
    p = _perfil(pid)
    f = request.form
    manchete, texto = f.get("manchete", "").strip(), f.get("texto", "").strip()
    if not manchete or not texto:
        flash("Preencha a manchete e cole o roteiro.", "erro")
        return redirect(url_for("novo", pid=pid) + "#pronto")
    destino = _criar_roteiro(p, manchete, f.get("titulo", ""), cenas_de_texto(texto, p.dados.get("ritmo_corte_s", 4)),
                             f.get("fontes", ""))
    flash("Roteiro dividido em cenas e colocado no fim da fila. Confira as buscas de imagem no editor de cenas.", "ok")
    return redirect(url_for("ver", pid=pid, nome=destino.name))


@app.post("/p/<pid>/novo/narracao")
def novo_de_narracao(pid):
    """Narração pronta enviada: transcreve com o Azure, corta em cenas e usa a própria voz no vídeo."""
    from ..entrada import cenas_de_narracao
    p = _perfil(pid)
    f = request.form
    manchete, arquivo = f.get("manchete", "").strip(), request.files.get("audio")
    if not manchete or not arquivo or not arquivo.filename:
        flash("Preencha a manchete e escolha o arquivo de áudio.", "erro")
        return redirect(url_for("novo", pid=pid) + "#pronto")
    extensao = Path(arquivo.filename).suffix.lower()
    if extensao not in (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac", ".webm"):
        flash("Envie o áudio em mp3, wav, m4a, ogg, aac, flac ou webm.", "erro")
        return redirect(url_for("novo", pid=pid) + "#pronto")
    nome = slug(f.get("titulo") or manchete)
    pasta = p.fila / "midia"
    pasta.mkdir(parents=True, exist_ok=True)
    original = pasta / f"{nome}-narracao{extensao}"
    arquivo.save(original)
    try:
        cenas = cenas_de_narracao(original, p.dados.get("idioma", "pt"), p.dados.get("ritmo_corte_s", 4), pasta, nome)
    except SystemExit as erro:
        flash(str(erro), "erro")
        return redirect(url_for("novo", pid=pid) + "#pronto")
    destino = _criar_roteiro(p, manchete, f.get("titulo", ""), cenas, f.get("fontes", ""),
                             narracao_original=f"midia/{original.name}")
    flash(f"Narração transcrita em {len(cenas)} cenas e colocada no fim da fila. Confira o texto e as imagens.", "ok")
    return redirect(url_for("ver", pid=pid, nome=destino.name))


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
            return render_template("novo.html", p=p, d=p.dados, f=f, descoberta=_descoberta(p))
        destino = _criar_roteiro(p, manchete, f.get("titulo", ""), cenas, f.get("fontes", ""))
        flash("Roteiro criado no fim da fila. Revise e gere a prévia.", "ok")
        return redirect(url_for("ver", pid=pid, nome=destino.name))
    return render_template("novo.html", p=p, d=p.dados, f={}, descoberta=_descoberta(p))


def _referencias(p) -> dict:
    from .. import referencia
    return referencia.ler(p)


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


@app.route("/p/<pid>/identidade", methods=["GET", "POST"])
def identidade_pagina(pid):
    """Foto, capa, marca d'água e textos das contas: prévia, edição e aprovação de quem está testando."""
    from .. import identidade
    p = _perfil(pid)
    pasta = identidade.pasta(p)
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "gerar":
            job = _iniciar_job(p, "Gerar identidade visual", [["identidade", "gerar"]])
            return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("identidade_pagina", pid=pid)))
        if acao in ("salvar", "aprovar"):
            textos = {k: request.form.get(k, "").replace("\r\n", "\n").strip()
                      for k in ("bio_instagram", "descricao_youtube", "titulo_capa", "subtitulo_capa")}
            if len(textos["bio_instagram"]) > identidade.BIO_MAX:
                flash(f"A bio do Instagram aceita até {identidade.BIO_MAX} caracteres.", "erro")
                return redirect(url_for("identidade_pagina", pid=pid))
            atual = json.loads((pasta / "textos.json").read_text(encoding="utf-8")) if (pasta / "textos.json").exists() else {}
            if not atual or textos["titulo_capa"] != atual.get("titulo_capa") or textos["subtitulo_capa"] != atual.get("subtitulo_capa"):
                identidade.gerar(p, textos)  # a capa muda junto com os textos dela
            else:
                (pasta / "textos.json").write_text(json.dumps(textos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if acao == "aprovar":
                identidade.aprovar(p, request.form.get("por", "").strip())
                flash("Identidade aprovada. Para aplicar nas contas, peça ao Claude: /identidade-visual", "ok")
            else:
                flash("Textos salvos. Revise e aprove quando estiver bom.", "ok")
        return redirect(url_for("identidade_pagina", pid=pid))
    textos = json.loads((pasta / "textos.json").read_text(encoding="utf-8")) if (pasta / "textos.json").exists() \
        else identidade.textos_padrao(p)
    return render_template("identidade.html", p=p, d=p.dados, textos=textos, estado=identidade.estado(p),
                           gerada=(pasta / "capa-youtube.png").exists(), bio_max=identidade.BIO_MAX,
                           versao=int((pasta / "capa-youtube.png").stat().st_mtime) if (pasta / "capa-youtube.png").exists() else 0)


@app.get("/p/<pid>/marca/<arquivo>")
def marca_arquivo(pid, arquivo):
    from .. import identidade
    p = _perfil(pid)
    if arquivo not in ("foto-perfil.png", "capa-youtube.png", "marca-dagua.png"):
        abort(404)
    return send_file(identidade.pasta(p) / arquivo)


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
