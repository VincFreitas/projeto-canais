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
from .. import ambiente, aparencia, autoria, canal_ia, mercados, plataformas, seguranca
from .. import nuvem as canal_nuvem
from ..perfis import (DURACOES, FONTES_LEGENDA, FORMATOS, ID_VALIDO, MODELO, MOTORES_VOZ, PADRAO, RITMOS,
                      TAMANHOS_LEGENDA, TEMAS_CARDS, TIPOS_VISUAL, EDICOES, PERSONA, PLATAFORMAS, campos_video, campos_canal, campos_padrao, carregar, criar, listar,
                      nomes_plataformas, rotulo_duracao, slug)

PYTHON = sys.executable
ARQUIVO_VALIDO = re.compile(r"^[\w.-]+\.json$")
CHAVES = [
    ("AZURE_SPEECH_KEY", "Azure Speech (chave)", True),
    ("AZURE_SPEECH_REGION", "Azure Speech (região, ex.: brazilsouth)", False),
    ("PIXABAY_API_KEY", "Pixabay", True),
    ("PEXELS_API_KEY", "Pexels", True),
    ("ELEVENLABS_API_KEY", "ElevenLabs (opcional)", True),
    ("GOOGLE_TTS_API_KEY", "Google Text-to-Speech, vozes Chirp 3 HD (opcional)", True),
    ("GEMINI_API_KEY", "Gemini TTS (opcional)", True),
]
JOBS: dict[str, dict] = {}

app = Flask(__name__)
app.secret_key = ambiente.chave_secreta()
app.config.update(
    MAX_CONTENT_LENGTH=512 * 1024 * 1024,  # maior envio aceito (vídeo ou narração): 512 MB
    **ambiente.config_flask(),             # cookie de sessão: SameSite=Strict, HttpOnly (e Secure no modo servidor)
)
LOCAL = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$")


# ---------- segurança: só o próprio PC ----------

@app.before_request
def _so_local():
    # 1) só conexões do próprio PC
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(403)
    # 2) DNS rebinding: um site pode apontar o próprio domínio para 127.0.0.1; o Host denuncia
    if not LOCAL.match(request.host or ""):
        abort(403)
    # 3) CSRF: toda ação (POST) precisa vir de uma página do próprio Estúdio
    if request.method == "POST":
        origem = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if not ambiente.origem_permitida(origem):
            abort(403)


@app.after_request
def _cabecalhos(resposta):
    """Cabeçalhos do OWASP: sem moldura em outro site (clickjacking), sem adivinhar tipo de arquivo, sem vazar o
    endereço em links externos e sem carregar scripts de fora."""
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("Referrer-Policy", "same-origin")  # no-referrer faria o navegador mandar Origin: null
    resposta.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
                                "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                                "frame-ancestors 'none'; form-action 'self' https://github.com https://www.instagram.com; base-uri 'none'")
    return resposta


@app.errorhandler(413)
def _grande_demais(_):
    flash("Arquivo grande demais: o limite de envio é 512 MB.", "erro")
    return redirect(request.referrer or url_for("inicio"))


# ---------- modo guiado: enquanto a configuração não termina, só as telas de configurar ----------

# telas que esperam a configuração pronta; o resto (progresso, conexões, chaves, perfis, sobre) fica livre
TRAVADAS = {"inicio", "painel", "fila", "ver", "editar", "novo", "historico"}


def _guia_pendente() -> list:
    # lido do .env a cada vez: desligar em Configurações (ou no .env) vale na hora, sem reiniciar o Estúdio
    if str(_env().get("DARKOPS_MODO_GUIADO") or os.getenv("DARKOPS_MODO_GUIADO", "1")).strip() == "0":
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


def _salvar_conferindo(novos: dict) -> None:
    """Testa cada chave no serviço antes de salvar: a recusada não entra no .env, e a pessoa vê o motivo na hora."""
    from ..chaves import validar
    env = {**_env(), **{k: v for k, v in novos.items() if not k.endswith("_KEY")}}  # região vale para o teste
    for nome in [k for k in novos if k.endswith("_KEY")]:
        ok, texto = validar(nome, novos[nome], env)
        if ok is False:
            novos.pop(nome)
            flash(texto, "erro")
        elif texto:
            flash(texto, "ok" if ok else "aviso")
    if novos:
        _salvar_env(novos)


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
    # os horários são no fuso do mercado do canal (12:00 de Nova York num canal para os EUA)
    agora, saida, dia = datetime.now(mercados.fuso(p.dados)).replace(tzinfo=None), [], 0
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
    from .tarefas import descrever
    JOBS[job_id] = {"id": job_id, "perfil": p.id, "titulo": titulo, "estado": "rodando",
                    "inicio": time.time(), "log": str(log), **descrever(p.dados, comandos)}

    def trabalhar():
        with log.open("w", encoding="utf-8") as saida:
            for args in comandos:
                saida.write(f"$ darkops {' '.join(args)}\n")
                saida.flush()
                proc = subprocess.run(_cli(p.id, *args), cwd=config.RAIZ, stdout=saida,
                                      stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
                if proc.returncode != 0:
                    JOBS[job_id].update(estado="falhou", fim=time.time())
                    return
        JOBS[job_id].update(estado="concluido", fim=time.time())

    threading.Thread(target=trabalhar, daemon=True).start()
    return job_id


@app.context_processor
def _contexto():
    from .. import __version__
    from ..palavra import GANCHOS
    return {"perfis": listar(), "agora": datetime.now(), "formatos": FORMATOS, "versao_app": __version__,
            "duracoes": DURACOES, "rotulo_duracao": rotulo_duracao, "nomes_plataformas": nomes_plataformas,
            "estimar_leva": _estimar_leva, "novidade": _novidade(), "lista_plataformas": PLATAFORMAS, "rotulo_video": _rotulo_video, "autoria": autoria, "creditos_removidos": autoria.creditos_removidos(),
            "guiado": request.endpoint and bool(_guia_pendente()), "travadas": TRAVADAS, "avancado": _avancado(),
            "whatsapp_ligado": _whatsapp_ligado(), "whatsapp_visivel": _whatsapp_visivel(), "ganchos": GANCHOS}


def _whatsapp_ligado() -> bool:
    from .. import whatsapp
    return whatsapp.configurado()


def _whatsapp_visivel() -> bool:
    """WhatsApp desligado (DARKOPS_WHATSAPP sem 1): some da barra, da abertura, do lobby e do Novo canal."""
    from .. import whatsapp
    return whatsapp.ligado()


def _avancado() -> bool:
    """Modo avançado: mostra todas as telas e opções. Desligado, o Estúdio fica só com o essencial."""
    return _env().get("DARKOPS_AVANCADO") == "1"


@app.post("/avancado")
def alternar_avancado():
    _salvar_env({"DARKOPS_AVANCADO": "0" if _avancado() else "1"})
    return redirect(request.referrer or url_for("inicio"))


# ---------- perfis e chaves ----------

@app.get("/")
def inicio():
    """Lobby: visão geral de todos os canais, pendências e dicas (lobby.py); sem canal, vai criar o primeiro."""
    if not listar():
        return redirect(url_for("perfis_pagina"))
    from .lobby import dados
    return render_template("lobby.html", lobby=dados())


@app.get("/perfis")
def perfis_pagina():
    return render_template("perfis.html", modelo=MODELO, status=plataformas.calcular(novo=True), nichos=config.nichos(),
                           mercados=mercados.opcoes(), mercado_padrao=mercados.PADRAO,
                           catalogo_vozes=_catalogo_vozes(), voz_padrao=mercados.MERCADOS[mercados.PADRAO]["vozes"][0])


@app.post("/perfis/sugerir")
def sugerir_nomes():
    """Nomes, @ e bio para o canal novo: pede ao Claude Code (sem ferramentas, só texto); sem ele, sugestões prontas."""
    from ..perfis import sugerir_nomes as sugerir
    pedido = request.get_json(silent=True) or {}
    mercado = pedido.get("mercado") if pedido.get("mercado") in mercados.MERCADOS else mercados.PADRAO
    return jsonify(sugerir(str(pedido.get("nicho", ""))[:80], str(pedido.get("formato", "vertical")), mercado))


@app.get("/perfis/contas-previa")
def contas_previa():
    """Passo Contas do assistente: os passos e os nomes sugeridos para o canal que ainda vai ser criado."""
    from ..contas_guia import passos
    a = request.args
    dados = {"nome": a.get("nome", "")[:60], "arroba": a.get("arroba", "")[:31],
             "mercado": a.get("mercado") if a.get("mercado") in mercados.MERCADOS else mercados.PADRAO,
             "youtube": a.get("youtube") == "1", "instagram": a.get("instagram") == "1"}
    return render_template("_contas_passos.html", passos=passos(dados), p=None, manuais=())


@app.get("/p/<pid>/contas")
def contas_criar(pid):
    """Aba Contas do canal: o passo a passo para criar cada conta, com nomes e links."""
    from ..contas_guia import MANUAIS, passos
    p = _perfil(pid)
    lista = passos(p.dados, p)
    return render_template("contas_criar.html", p=p, d=p.dados, passos=lista, manuais=MANUAIS,
                           feitos=sum(1 for s in lista if s["feito"]))


@app.post("/p/<pid>/contas/bloqueio")
def contas_bloqueio(pid):
    """O Google recusou a verificação (celular usado muitas vezes): guarda quando foi e mostra quando tentar de novo."""
    from ..contas_guia import limpar_bloqueio, marcar, registrar_bloqueio
    p = _perfil(pid)
    if request.form.get("acao") == "limpar":
        limpar_bloqueio()
        marcar(p, "gmail", True)
        flash("Bloqueio limpo e Gmail marcado como feito.", "ok")
    else:
        s = registrar_bloqueio()
        flash(f"Anotado. Estimativa: tente de novo daqui a {s['espera_h']} h. Não insista antes: cada tentativa pode "
              "alongar a espera. Enquanto isso, crie o canal de marca no Gmail que você já usa.", "ok")
    return redirect(url_for("contas_criar", pid=pid) + "#conta-gmail")


@app.post("/p/<pid>/contas/<passo>")
def contas_marcar(pid, passo):
    from ..contas_guia import MANUAIS, marcar, marcas
    p = _perfil(pid)
    if passo not in MANUAIS:
        abort(404)
    marcar(p, passo, not marcas(p).get(passo, False))
    return redirect(url_for("contas_criar", pid=pid) + f"#conta-{passo}")


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
    from .. import custos
    return render_template("sobre.html", custo=custos.resumo())


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
    from .. import leva
    from ..aprendizado import LEVA_INICIAL
    canal = carregar(pid)
    if not leva._claude():  # sem o Claude Code a leva falharia escondida, com o aviso de "sendo criados" na tela
        flash(f"Canal {nome} criado, mas os vídeos não começaram: falta o Claude Code, que escreve os roteiros. "
              f"Instale em claude.com/claude-code, faça login e crie a leva inicial de {LEVA_INICIAL} vídeos em Ajustes.", "erro")
        return redirect(url_for("conexoes", pid=pid))
    faltam = leva.em_segundo_plano(canal, LEVA_INICIAL)  # todo canal começa com 14 vídeos; depois deles vem a 1ª análise
    if faltam:
        flash(f"Canal {nome} criado. Os {LEVA_INICIAL} primeiros vídeos começam sozinhos quando a configuração do canal "
              f"terminar (falta: {'; '.join(faltam)}). Crie as contas do canal.", "ok")
        return redirect(url_for("contas_criar", pid=pid))
    est = leva.estimar(canal.dados, LEVA_INICIAL)
    flash(f"Canal {nome} criado. Os {LEVA_INICIAL} primeiros vídeos já estão sendo criados ({est['texto']}); deixe o PC "
          "ligado. Enquanto isso, crie as contas do canal.", "ok")
    return redirect(url_for("contas_criar", pid=pid))


@app.route("/chaves", methods=["GET", "POST"])
def chaves():
    if request.method == "POST":
        _salvar_conferindo({k: request.form[k].strip() for k, _, _ in CHAVES if request.form.get(k, "").strip()})
        return redirect(url_for("chaves"))
    env = _env()
    return render_template("chaves.html", chaves=[(k, rotulo, segredo, k in env,
                                                   "" if segredo else env.get(k, "")) for k, rotulo, segredo in CHAVES])


# ---------- amostras de voz (Novo canal e Ajustes) ----------

@app.get("/vozes/amostra/<origem>/<cod>/<arquivo>")
def voz_amostra(origem, cod, arquivo):
    from .. import vozes
    pasta = {"gratis": vozes.GRATIS, "pagas": vozes.PAGAS}.get(origem)
    if not pasta or cod not in mercados.MERCADOS or not vozes.NOME_SEGURO.match(arquivo) \
            or not arquivo.endswith(".mp3") or not (pasta / cod / arquivo).is_file():
        abort(404)
    return send_file(pasta / cod / arquivo, mimetype="audio/mpeg", max_age=3600)


@app.get("/vozes/pagas/<cod>")
def voz_pagas(cod):
    from .. import vozes
    if cod not in mercados.MERCADOS:
        abort(404)
    return jsonify(vozes.pagas(cod))


@app.post("/vozes/minha")
def voz_minha():
    """Recebe a gravação da voz do dono (gravada no navegador ou enviada do PC) e gera a amostra clonada."""
    import tempfile
    from .. import vozes
    cod = request.form.get("mercado", "")
    arquivo = request.files.get("arquivo")
    if cod not in mercados.MERCADOS or not arquivo:
        return jsonify(ok=False, erro="Grave ou escolha um áudio."), 400
    if request.form.get("consentimento") != "1":
        return jsonify(ok=False, erro="Confirme que a gravação é a sua voz."), 400
    if not vozes.propria(cod)["disponivel"]:
        return jsonify(ok=False, erro="O Chatterbox não está instalado neste PC."), 400
    with tempfile.TemporaryDirectory() as pasta:
        origem = Path(pasta) / "gravacao"
        arquivo.save(origem)
        try:
            duracao = vozes.salvar_minha_voz(origem)
        except SystemExit as erro:
            return jsonify(ok=False, erro=str(erro))
    vozes.gerar_minha_amostra_em_segundo_plano(cod)
    return jsonify(ok=True, duracao=round(duracao))


@app.get("/vozes/minha/<cod>")
def voz_minha_estado(cod):
    from .. import vozes
    if cod not in mercados.MERCADOS:
        abort(404)
    return jsonify(vozes.propria(cod))


@app.post("/vozes/gerar")
def voz_gerar():
    """Gera as amostras de uma opção paga. Se vier a chave, testa no serviço e salva no .env antes."""
    from .. import vozes
    from ..chaves import validar
    dados = request.get_json(silent=True) or {}
    motor, cod, chave = dados.get("motor"), dados.get("mercado"), str(dados.get("chave") or "").strip()
    if motor not in vozes.PAGOS or cod not in mercados.MERCADOS:
        return jsonify(ok=False, erro="opção inválida"), 400
    nome = vozes.PAGOS[motor]["chave"]
    if chave:
        ok, texto = validar(nome, chave, _env())
        if ok is False:
            return jsonify(ok=False, erro=texto)
        _salvar_env({nome: chave})
    elif not _env().get(nome):
        return jsonify(ok=False, erro=f"Cole a chave da {vozes.PAGOS[motor]['rotulo']} para gerar as amostras.")
    vozes.gerar_paga_em_segundo_plano(motor, cod)
    return jsonify(ok=True)


def _catalogo_vozes() -> dict:
    from .. import vozes
    return {"mercados": {cod: vozes.catalogo(cod) for cod in mercados.MERCADOS},
            "regras": vozes.REGRAS_TEMA, "rotulos": vozes.ROTULOS_TEMA}


# ---------- painel do perfil ----------

def _leva_espera(p) -> str:
    """Leva parada esperando o limite do plano do Claude renovar: quando volta (no relógio do PC)."""
    from .. import leva
    guardada = leva.adiada(p)
    volta = float(guardada.get("retomar_em") or 0)
    if not volta or volta < time.time():
        return ""
    return f"{guardada.get('quantidade', 1)} vídeo(s) às {datetime.fromtimestamp(volta).strftime('%H:%M')}"


@app.get("/p/<pid>")
def painel(pid):
    p = _perfil(pid)
    itens = [_situacao(c) for c in fila_mod.roteiros(p)]
    from .conectores import resumo
    online = _n8n_online()
    return render_template("painel.html", p=p, d=p.dados, itens=itens, conexoes=_conexoes(p), leva_espera=_leva_espera(p),
                           resumo=resumo(p, _conexoes(p), online),
                           aprovados=sum(1 for i in itens if i["aprovado"]), n8n=online,
                           horarios=_proximos_horarios(p), historico=fila_mod.historico(p)[-6:][::-1],
                           falhas=fila_mod.falhas(p, 5)[::-1], env=_env(), nuvem_ligada=canal_nuvem.configurada(),
                           criando=(p.controle / "leva.trava").exists() or any(
                               j["perfil"] == p.id and j["estado"] == "rodando" for j in JOBS.values()))


@app.route("/p/<pid>/configurar", methods=["GET", "POST"])
def configurar(pid):
    p = _perfil(pid)
    if request.method == "POST":
        f = request.form
        horarios = [h.strip() for h in f.get("horarios", "").split(",") if re.match(r"^\d{1,2}:\d{2}$", h.strip())]
        horarios = [h for h in horarios if int(h.split(":")[0]) < 24 and int(h.split(":")[1]) < 60]
        agenda_antes = (mercados.codigo(p.dados), p.dados.get("horarios"))
        voz_antes = (p.dados.get("motor_voz"), p.dados.get("voz"))
        p.salvar({"nome": f.get("nome", "").strip() or p.dados["nome"],
                  "arroba": f.get("arroba", "").strip() or p.dados["arroba"],
                  "nicho": f.get("nicho", "").strip(), "descricao": f.get("descricao", "").strip(),
                  "voz": f.get("voz") or p.dados["voz"], "layout": f.get("layout") or "post",
                  "musica": f.get("musica") or "animada",
                  # pixel e cartoon têm a pulga narradora; clipes reais não
                  "estilo": f.get("estilo", ""), "narrador": f.get("estilo") in ("pixel", "cartoon") and p.id == aparencia.PULGA,
                  "privacidade_youtube": f.get("privacidade_youtube") or "public",
                  "horarios": horarios or p.dados["horarios"], **campos_canal(f), **campos_padrao(f)})
        foto = request.files.get("avatar")
        if foto and foto.filename:
            from PIL import Image, ImageOps
            img = ImageOps.exif_transpose(Image.open(foto.stream)).convert("RGB")
            img.thumbnail((512, 512))
            img.save(p.pasta / "avatar.png")
        if voz_antes != (p.dados.get("motor_voz"), p.dados.get("voz")):
            _refazer_previas_com_voz_nova(p)
        if f.get("atualizar_contas"):  # YouTube pela API; Instagram com a bio pronta para colar (atualizar_contas.py)
            from .. import atualizar_contas
            for r in atualizar_contas.atualizar(p):
                flash(r["texto"], "ok" if r["ok"] else "erro")
        if agenda_antes != (mercados.codigo(p.dados), p.dados.get("horarios")) and canal_nuvem.configurada():
            _iniciar_job(p, "Acertar os horários da nuvem", [["nuvem-agenda"]])  # o Actions roda no fuso novo
        m = mercados.de(p.dados)
        flash(f"Perfil salvo. Público: {m['nome']}; posta no horário de {m['cidade']}.", "ok")
        return redirect(url_for("configurar", pid=pid))
    return render_template("configurar.html", p=p, d=p.dados, status=plataformas.calcular(p),
                           mercados=mercados.MERCADOS, mercado=mercados.codigo(p.dados),
                           motores_voz=MOTORES_VOZ, tipos_visual=TIPOS_VISUAL, ritmos=RITMOS,
                           tamanhos_legenda=TAMANHOS_LEGENDA, fontes_legenda=FONTES_LEGENDA, temas_cards=TEMAS_CARDS, edicoes=EDICOES, persona=PERSONA,
                           tem_elevenlabs=bool(_env().get("ELEVENLABS_API_KEY")), ref=_referencias(p),
                           catalogo_vozes=_catalogo_vozes(),
                           proposta=canal_ia.ler(p), rotulos=canal_ia.ROTULOS, resumo=_resumo_contas(p),
                           exclusao=_plano_exclusao(p), contas=_contas_do_canal(p))


def _contas_do_canal(p) -> dict:
    from .. import atualizar_contas
    return atualizar_contas.situacao(p)


@app.post("/p/<pid>/contas-atualizadas")
def contas_atualizadas(pid):
    """O dono colou a bio nova no Instagram: some o aviso de Ajustes."""
    from .. import atualizar_contas
    atualizar_contas.instagram_feito(_perfil(pid))
    flash("Anotado: a bio do Instagram está em dia.", "ok")
    return redirect(url_for("configurar", pid=pid))


def _plano_exclusao(p) -> dict:
    from ..excluir import plano
    return plano(p)


@app.post("/p/<pid>/excluir")
def excluir_canal(pid):
    """Excluir canal (Ajustes, lá embaixo): só com o nome do canal digitado no aviso. Apaga do app, revoga o acesso do
    app ao YouTube, apaga o token do Instagram e tira o canal da nuvem (darkops/excluir.py)."""
    from ..excluir import excluir
    p = _perfil(pid)
    nome = (p.dados.get("nome") or p.id).strip()
    if request.form.get("confirmacao", "").strip().casefold() != nome.casefold():
        flash(f"Para excluir, digite o nome do canal exatamente: {nome}", "erro")
        return redirect(url_for("configurar", pid=pid) + "#excluir")
    if any(j["perfil"] == p.id and j["estado"] == "rodando" for j in JOBS.values()):
        flash("Este canal tem uma tarefa rodando agora. Espere ela terminar e tente de novo.", "erro")
        return redirect(url_for("configurar", pid=pid) + "#excluir")
    try:
        passos = excluir(p)
    except (SystemExit, OSError) as erro:
        flash(f"Não consegui excluir o canal: {seguranca.ocultar(str(erro))[:200]}", "erro")
        return redirect(url_for("configurar", pid=pid) + "#excluir")
    flash(f"Canal {nome} excluído. " + " · ".join(passos), "ok")
    return redirect(url_for("inicio"))


def _refazer_previas_com_voz_nova(p) -> None:
    """Trocou a voz: as prévias ainda não aprovadas são refeitas com ela (as aprovadas e as postadas ficam como estão)."""
    pendentes = [c for c in fila_mod.roteiros(p) if not fila_mod.aprovado(c)]
    if pendentes:
        _iniciar_job(p, f"Refazer {len(pendentes)} prévias com a voz nova",
                     [["fila-produzir", str(c)] for c in pendentes])
        flash(f"Voz trocada. As {len(pendentes)} prévias que esperam aprovação estão sendo refeitas com a voz nova; "
              "os vídeos já aprovados e os postados continuam como estão.", "ok")


def _resumo_contas(p) -> list:
    from .conectores import resumo
    return resumo(p, _conexoes(p), _n8n_online())


@app.post("/p/<pid>/ajustar")
def ajustar_canal(pid):
    """"Mude o canal falando": a IA propõe as mudanças em segundo plano; a pessoa aplica ou descarta."""
    p = _perfil(pid)
    pedido = request.form.get("pedido", "").strip()[:1500]
    if not pedido:
        flash("Escreva como você quer o canal.", "erro")
        return redirect(url_for("configurar", pid=pid))
    job = _iniciar_job(p, "A IA está ajustando o canal", [["ajustar-canal", "--", pedido]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("configurar", pid=pid) + "#proposta"))


@app.post("/p/<pid>/ajustar/<decisao>")
def decidir_ajuste(pid, decisao):
    p = _perfil(pid)
    n = canal_ia.decidir(p, decisao == "aplicar")
    flash(f"Pronto: {n} ajuste(s) aplicado(s) no canal." if decisao == "aplicar" else "Proposta descartada.", "ok")
    return redirect(url_for("configurar", pid=pid))


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


def _rotulo_video(r: dict, d: dict) -> str:
    """'Curto · 60s · YouTube, Instagram': o tipo, a duração e as plataformas de um vídeo da fila."""
    formato = r.get("formato") or d.get("formato", "vertical")
    partes = ["Curto" if formato == "vertical" else "Longo"]
    if r.get("duracao_alvo_s"):
        partes.append(rotulo_duracao(int(r["duracao_alvo_s"])))
    escolhidas = r["plataformas"] if "plataformas" in r else [k for k, _ in PLATAFORMAS if d.get(k)]
    partes.append(", ".join(n for k, n in PLATAFORMAS if k in escolhidas) or "sem plataforma")
    return " · ".join(partes)


def _estimar_leva(dados: dict, quantidade: int) -> dict:
    from ..leva import estimar
    return estimar(dados, quantidade)


@app.post("/p/<pid>/leva")
def criar_leva(pid):
    """Salva a quantidade escolhida e cria a leva num processo de fundo (pode levar horas)."""
    from ..leva import _claude, par
    p = _perfil(pid)
    try:
        quantidade = par(request.form.get("leva_quantidade"), 4)  # sempre par: 2 vídeos por dia
    except ValueError:
        quantidade = 4
    if not _claude():
        flash("A leva precisa do Claude Code instalado neste PC (claude.com/claude-code).", "erro")
        return redirect(url_for("configurar", pid=pid))
    if request.form.get("base") == "anteriores":  # Novo vídeo, sem tema: segue a linha dos vídeos anteriores
        from ..leva import SEGUIR_ANTERIORES
        formato = request.form.get("formato") if request.form.get("formato") in ("vertical", "longo") else ""
        rotulo = {"vertical": " curtos", "longo": " longos"}.get(formato, "")
        job = _iniciar_job(p, f"Mais {quantidade} vídeo(s){rotulo} a partir dos anteriores",
                           [["leva", "--quantidade", str(quantidade), "--tema", SEGUIR_ANTERIORES,
                             *(["--formato", formato] if formato else [])]])
        return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("novo", pid=pid)))
    p.salvar({"leva_quantidade": quantidade})
    job = _iniciar_job(p, f"Leva de {quantidade} vídeo(s)", [["leva", "--quantidade", str(quantidade)]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("fila", pid=pid)))


@app.post("/p/<pid>/criar")
def criar_video(pid):
    """Novo vídeo em uma linha: o Claude escreve o roteiro sobre o tema (ou escolhe um) e gera a prévia."""
    from ..leva import _claude
    p = _perfil(pid)
    if not _claude():
        flash("Para criar vídeos sozinho, instale o Claude Code neste PC (claude.com/claude-code).", "erro")
        return redirect(url_for("novo", pid=pid))
    tema = " ".join(request.form.get("tema", "").split())[:200]
    partes = request.form.get("partes", "1")
    if partes in ("2", "4"):  # série em partes (darkops/serie.py): o tema vira vídeos ligados que saem em ordem
        job = _iniciar_job(p, f"Série de {partes} partes: {tema}" if tema else
                           f"Série de {partes} partes com tema escolhido pela IA",
                           [["leva", "--quantidade", partes, "--serie", partes, *([f"--tema={tema}"] if tema else [])]])
        return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("painel", pid=pid)))
    job = _iniciar_job(p, f"Novo vídeo: {tema}" if tema else "Novo vídeo com tema escolhido pela IA",
                       [["leva", "--quantidade", "1", *([f"--tema={tema}"] if tema else [])]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("painel", pid=pid)))


def _novidade():
    from .. import app as app_local
    return app_local.novidade_pendente()


@app.get("/versao.json")
def versao_json():
    """A aba aberta pergunta a versão de tempos em tempos e recarrega quando o Estúdio reinicia atualizado."""
    from .. import __version__
    return jsonify({"versao": __version__})


# ---------- aplicativo instalável (PWA): manifesto e service worker na raiz, para valer no Estúdio inteiro ----------

@app.get("/manifest.webmanifest")
def manifesto():
    return jsonify({
        "name": "Projeto Canais", "short_name": "Canais", "lang": "pt-BR",
        "description": "Estúdio do Projeto Canais: cria, aprova e publica os vídeos dos seus canais.",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#f5f5f7", "theme_color": "#f5f5f7",
        "icons": [{"src": url_for("static", filename=f"icone-{n}.png"), "sizes": f"{n}x{n}", "type": "image/png",
                   "purpose": "any"} for n in (192, 512)],
    }), 200, {"Content-Type": "application/manifest+json"}


@app.get("/sw.js")
def service_worker():
    resposta = send_file(Path(app.static_folder) / "sw.js", mimetype="text/javascript", max_age=0)
    resposta.headers["Cache-Control"] = "no-cache"  # o navegador confere o service worker novo a cada abertura
    return resposta


@app.get("/abertura")
def abertura():
    """Tela animada de quando o executável abre o Estúdio; confere o que já está de pé e entra no painel."""
    return render_template("abertura.html")


@app.get("/abertura/estado")
def abertura_estado():
    from ..app import n8n_ligando
    from .. import whatsapp
    n8n = "ligado" if _n8n_online() else "ligando" if n8n_ligando() else "desligado"
    return jsonify({"n8n": n8n, "nuvem": canal_nuvem.configurada(), "whatsapp": whatsapp.situacao()})


@app.post("/novidade/vista")
def novidade_vista():
    from .. import app as app_local
    app_local.marcar_novidade_vista()
    return redirect(request.referrer or url_for("inicio"))


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    from .. import app as app_local
    if request.method == "POST":
        f = request.form
        acao = f.get("acao", "salvar")
        if acao == "atalhos":
            try:
                for linha in app_local.atalhos(bool(f.get("area")), bool(f.get("menu")), bool(f.get("barra"))):
                    flash(linha, "ok")
            except Exception as erro:
                flash(f"Não consegui criar os atalhos: {erro}", "erro")
        elif acao == "atualizacao":
            try:
                horas = min(max(int(f.get("horas", 6)), 1), 168)
            except ValueError:
                horas = 6
            app_local.salvar({"atualizar_sozinho": bool(f.get("auto")), "verificar_a_cada_h": horas})
            flash("Preferências de atualização salvas.", "ok")
        elif acao == "modo_guiado":
            from ..contas import salvar_env
            ligado = bool(f.get("guiado"))
            salvar_env({"DARKOPS_MODO_GUIADO": "1" if ligado else "0"})
            flash("Modo guiado " + ("ligado: Fila, Novo vídeo e Histórico esperam a configuração terminar."
                                    if ligado else "desligado: todas as telas liberadas."), "ok")
        elif acao in ("verificar", "atualizar", "dependencias", "dependencias-aplicar"):
            perfis_ = listar()
            p = perfis_[0] if perfis_ else carregar(PADRAO).preparar()
            comandos = {"verificar": ["atualizar", "--verificar"], "atualizar": ["atualizar"],
                        "dependencias": ["atualizar-dependencias"], "dependencias-aplicar": ["atualizar-dependencias", "--aplicar"]}
            titulos = {"verificar": "Procurar atualização", "atualizar": "Atualizar o Projeto Canais",
                       "dependencias": "Verificar dependências", "dependencias-aplicar": "Atualizar dependências"}
            job = _iniciar_job(p, titulos[acao], [comandos[acao]])
            return redirect(url_for("acompanhar", pid=p.id, job=job, voltar=url_for("configuracoes")))
        return redirect(url_for("configuracoes"))
    from .. import __version__
    guiado = str(_env().get("DARKOPS_MODO_GUIADO") or os.getenv("DARKOPS_MODO_GUIADO", "1")).strip() != "0"
    return render_template("configuracoes.html", cfg=app_local.ler(), existem=app_local.estado_atalhos(), guiado=guiado,
                           versao=__version__, pastas=app_local._pastas())


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
    from ..aparencia import garantir
    if garantir(p):  # foto enviada pelo dono ou emblema do tema; a pulga é só do Pulga do Saber
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
                           tem_client=(config.RAIZ / "credenciais" / "client_secret.json").exists(),
                           nuvem=_status_nuvem(p), nuvem_repo=_env().get("NUVEM_REPO", ""),
                           passagem_repo=_env().get("NUVEM_VIDEOS_REPO", ""),
                           instagram_app=bool(_env().get("INSTAGRAM_APP_ID") and _env().get("INSTAGRAM_APP_SECRET")),
                           instagram_retorno=_instagram_retorno(), whatsapp=_status_whatsapp())


WHATSAPP_CAMPOS = [("WHATSAPP_TOKEN", True), ("WHATSAPP_NUMERO_ID", False), ("WHATSAPP_PARA", False),
                   ("WHATSAPP_APP_ID", False), ("WHATSAPP_APP_SECRET", True), ("WHATSAPP_CONTA_ID", False),
                   ("WHATSAPP_MODELO", False)]


def _status_whatsapp() -> dict:
    from .. import whatsapp
    estado, env = whatsapp.ler_estado(), _env()
    return {"situacao": whatsapp.situacao(), "configurado": whatsapp.configurado(),
            "comandos": whatsapp.recebe_comandos(), "janela": whatsapp.janela_aberta(),
            "guardados": len(estado.get("pendentes", [])), "erro": estado.get("tunel_erro", ""),
            "ligado": whatsapp.ligado(), "inscrito": estado.get("inscrito"), "inscrito_erro": estado.get("inscrito_erro", ""),
            "recebeu": bool(estado.get("ultima_mensagem")), "modelo": whatsapp._modelo(),
            "modelo_status": estado.get("modelo_status", ""), "modelo_erro": estado.get("modelo_erro", ""),
            "valores": {k: ("" if segredo else env.get(k, "")) for k, segredo in WHATSAPP_CAMPOS},
            "salvas": {k: bool(env.get(k)) for k, _ in WHATSAPP_CAMPOS},
            "canal_atual": (whatsapp._perfil_atual().id if whatsapp._perfil_atual() else "")}


@app.get("/whatsapp")
def whatsapp_pagina():
    """Um WhatsApp para todos os canais: conecta uma vez, vale também para os canais criados depois."""
    return render_template("whatsapp.html", whatsapp=_status_whatsapp())


@app.post("/whatsapp")
def whatsapp_salvar():
    """Salva os dados do WhatsApp (segredo vazio = mantém o salvo), testa mandando uma mensagem e, com o app
    completo, liga os comandos: workflow no n8n, túnel e webhook."""
    from .. import whatsapp
    if not whatsapp.ligado():
        return redirect(url_for("whatsapp_pagina"))
    voltar = url_for("whatsapp_pagina")
    novos = {}
    for chave, segredo in WHATSAPP_CAMPOS:
        valor = request.form.get(chave, "").strip()
        if chave == "WHATSAPP_PARA":
            valor = re.sub(r"\D", "", valor)
        if valor or not segredo:
            novos[chave] = valor
    _salvar_env({k: v for k, v in novos.items() if v})
    for chave, valor in novos.items():
        if valor:
            os.environ[chave] = valor
    if not whatsapp.configurado():
        flash("Faltam o token, o ID do número ou o seu número.", "erro")
        return redirect(voltar)
    try:
        numero = whatsapp.testar()
        flash(f"WhatsApp conectado pelo número {numero} para todos os canais: confira a mensagem no seu celular.", "ok")
    except (SystemExit, OSError, whatsapp.ErroMeta) as erro:
        flash(seguranca.ocultar(f"O WhatsApp recusou: {erro}"), "erro")
        return redirect(voltar)
    passos = []
    if whatsapp.recebe_comandos():
        passos.append(["whatsapp", "n8n"])
    if canal_nuvem.configurada():
        passos.append(["nuvem-segredos"])
    perfis = listar()
    if passos and perfis:  # a tela de acompanhar é de um canal; o trabalho vale para todos
        job = _iniciar_job(perfis[0], "Ligar os comandos do WhatsApp", passos)
        threading.Thread(target=_religar_whatsapp, daemon=True).start()
        return redirect(url_for("acompanhar", pid=perfis[0].id, job=job, voltar=voltar))
    if passos:
        threading.Thread(target=_religar_whatsapp, daemon=True).start()
    return redirect(voltar)


def _religar_whatsapp() -> None:
    """Depois de importar o workflow: reinicia o n8n se ele ainda não escuta o WhatsApp e refaz o túnel."""
    from .. import whatsapp
    from ..app import reiniciar_n8n
    from ..instalacao import webhook_whatsapp_ativo
    time.sleep(20)  # dá tempo da importação terminar
    if _n8n_online() and not webhook_whatsapp_ativo():
        reiniciar_n8n()
    whatsapp.ligar()


@app.post("/whatsapp/religar")
def whatsapp_religar():
    from .. import whatsapp
    if not whatsapp.ligado():
        return redirect(url_for("whatsapp_pagina"))
    whatsapp.ligar()
    flash("Ligando os comandos do WhatsApp: leva uns 20 segundos.", "ok")
    return redirect(url_for("whatsapp_pagina"))


@app.post("/p/<pid>/conexoes/chaves")
def salvar_chaves_conector(pid):
    _perfil(pid)
    permitidas = {k for k, _, _ in CHAVES} | {"ELEVENLABS_VOZ", "GOOGLE_TTS_VOZ", "GEMINI_TTS_VOZ", "GEMINI_TTS_ESTILO"}
    _salvar_conferindo({k: v.strip() for k, v in request.form.items() if k in permitidas and v.strip()})
    return redirect(url_for("conexoes", pid=pid) + "#" + request.form.get("ancora", ""))


@app.post("/p/<pid>/conexoes/n8n")
def ligar_n8n_agora(pid):
    from ..app import ligar_n8n
    _perfil(pid)
    estado = ligar_n8n()
    flash({"ligado": "O n8n já está ligado.",
           "ligando": "Ligando o n8n em segundo plano; ele leva de 1 a 3 minutos para ficar pronto.",
           "sem-n8n": "O n8n não está instalado neste PC. Rode: npm install -g n8n"}[estado],
          "erro" if estado == "sem-n8n" else "ok")
    return redirect(url_for("conexoes", pid=pid) + "#n8n")


@app.post("/p/<pid>/conexoes/youtube")
def conectar_youtube(pid):
    p = _perfil(pid).preparar()
    job = _iniciar_job(p, "Conectar YouTube", [["autorizar-youtube"]])
    flash(f"Abrimos o login do Google no navegador. Escolha o Gmail e, na tela seguinte (\"Escolha uma conta ou um "
          f"canal de marca\"), escolha o canal {p.dados.get('nome')}, não a conta pessoal. Se aparecer \"O Google não "
          "verificou este app\", é o seu próprio app ainda sem a verificação do Google: clique em Avançado e depois em "
          "\"Acessar (não seguro)\". Depois permita o acesso.", "ok")
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
    _nuvem_em_fundo(p, "segredos")  # token novo do YouTube ou do Instagram vale também na nuvem
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
        _nuvem_em_fundo(p, "sincronizar")  # a reserva na nuvem passa a ter (ou deixa de ter) este vídeo
    return redirect(request.referrer or url_for("fila", pid=pid))


def _nuvem_em_fundo(p, acao: str) -> None:
    if canal_nuvem.configurada():
        _iniciar_job(p, f"Nuvem: {acao}", [[f"nuvem-{acao}"]])


def _instagram_retorno() -> str:
    from ..contas import instagram_retorno
    return instagram_retorno()


def _status_nuvem(p) -> dict:
    try:
        return canal_nuvem.status(p)
    except (SystemExit, OSError) as erro:
        return {"configurada": True, "erro": str(erro)}


# ---------- contas por login: a pessoa só entra na conta, o resto o Estúdio faz (darkops/contas.py) ----------

@app.post("/p/<pid>/conectar/<servico>")
def conectar_conta(pid, servico):
    p = _perfil(pid)
    if servico not in ("github", "azure"):
        abort(404)
    from ..contas_guia import NOME_REPO
    nomes = [request.form.get("repo_fila", "").strip(), request.form.get("repo_passagem", "").strip()]
    if servico == "github" and any(nomes):  # nomes escolhidos no guia de contas
        if not all(NOME_REPO.fullmatch(n) for n in nomes) or nomes[0] == nomes[1]:
            flash("Confira os nomes dos repositórios: só letras, números, ponto, hífen e _, e diferentes entre si.", "erro")
            return redirect(url_for("contas_criar", pid=pid) + "#conta-github")
    extra = ["--fila", nomes[0], "--passagem", nomes[1]] if servico == "github" and all(nomes) else []
    comandos = {"github": [["conectar-github", *extra], ["nuvem-configurar"]], "azure": [["conectar-azure"]]}[servico]
    titulo = {"github": "Entrar com o GitHub e preparar a nuvem", "azure": "Entrar com a Microsoft e criar a chave da voz"}
    job = _iniciar_job(p, titulo[servico], comandos)
    flash("Abrimos a página de login no navegador. O código para colar lá aparece logo abaixo.", "ok")
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("conexoes", pid=pid) + "#" +
                            ("nuvem" if servico == "github" else "azure")))


@app.post("/p/<pid>/instagram/app")
def instagram_app(pid):
    """ID e chave secreta do app do Instagram (uma vez, todos os canais); em seguida já abre o login."""
    _perfil(pid)
    app_id = request.form.get("INSTAGRAM_APP_ID", "").strip()
    segredo = request.form.get("INSTAGRAM_APP_SECRET", "").strip()
    if not (app_id.isdigit() and re.fullmatch(r"[0-9a-f]{32}", segredo)):
        flash("Confira os dois campos: o ID do app tem só números e a chave secreta tem 32 letras e números.", "erro")
        return redirect(url_for("conexoes", pid=pid) + "#instagram")
    from ..contas import salvar_env
    salvar_env({"INSTAGRAM_APP_ID": app_id, "INSTAGRAM_APP_SECRET": segredo})
    return redirect(url_for("instagram_entrar", pid=pid), code=307)


@app.post("/p/<pid>/instagram/entrar")
def instagram_entrar(pid):
    _perfil(pid)
    from ..contas import instagram_url
    porta = int(request.host.rsplit(":", 1)[1]) if ":" in request.host else 80
    try:
        return redirect(instagram_url(pid, porta))
    except SystemExit as erro:
        flash(str(erro), "erro")
        return redirect(url_for("conexoes", pid=pid) + "#instagram")


@app.get("/instagram/retorno")
def instagram_volta():
    """A página https do site repassa o code da Meta para cá. Vem de outro site, então o cookie de sessão (Strict)
    não chega: o estado de uso único guardado no servidor é que diz qual canal pediu."""
    from ..contas import instagram_perfil_do_estado, instagram_trocar_codigo
    pid = instagram_perfil_do_estado(request.args.get("state", ""))
    if not pid:
        return render_template("instagram_retorno.html", ok=False, destino=url_for("inicio"),
                               texto="Este login expirou ou não foi pedido por este Estúdio. Clique de novo em Entrar com Instagram.")
    p = _perfil(pid)
    destino = url_for("conexoes", pid=pid) + "#instagram"
    if request.args.get("error"):
        return render_template("instagram_retorno.html", ok=False, destino=destino,
                               texto="O login no Instagram foi cancelado. Nada mudou.")
    try:
        token = instagram_trocar_codigo(request.args.get("code", ""))
    except (SystemExit, OSError, ValueError) as erro:
        return render_template("instagram_retorno.html", ok=False, destino=destino, texto=seguranca.ocultar(str(erro)))
    p.preparar()
    p.token_instagram.write_text(token, encoding="utf-8")
    ok, saida = _rodar_agora(pid, "conta-instagram", timeout=60)
    achado = re.search(r"token válido: @([A-Za-z0-9_.]+)", saida) if ok else None
    if canal_nuvem.configurada():
        _iniciar_job(p, "Atualizar as credenciais na nuvem", [["nuvem-segredos"]])
    return render_template("instagram_retorno.html", ok=True, destino=destino,
                           texto=f"Instagram conectado{(' em @' + achado.group(1)) if achado else ''}. "
                                 "O token vale 60 dias e se renova sozinho.")


@app.post("/p/<pid>/nuvem/salvar")
def nuvem_salvar(pid):
    """Guarda o repositório privado e o token do GitHub (só no .env deste PC) e prepara a nuvem."""
    p = _perfil(pid)
    repo = request.form.get("repo", "").strip().removeprefix("https://github.com/").strip("/")
    token = request.form.get("token", "").strip() or _env().get("NUVEM_TOKEN", "")
    antigos = {k: os.environ.get(k) for k in ("NUVEM_REPO", "NUVEM_TOKEN")}
    os.environ.update({"NUVEM_REPO": repo, "NUVEM_TOKEN": token})
    try:
        canal_nuvem.conferir_acesso()
    except SystemExit as erro:
        for k, v in antigos.items():  # volta como estava: o que falhou não fica valendo
            os.environ.pop(k, None) if v is None else os.environ.update({k: v})
        flash(seguranca.ocultar(str(erro)), "erro")
        return redirect(url_for("conexoes", pid=pid) + "#nuvem")
    _salvar_env({"NUVEM_REPO": repo, "NUVEM_TOKEN": token})
    job = _iniciar_job(p, "Preparar a nuvem", [["nuvem-configurar"]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("conexoes", pid=pid) + "#nuvem"))


@app.post("/p/<pid>/nuvem/passagem")
def nuvem_passagem(pid):
    """Repositório PÚBLICO de passagem: o Instagram só aceita o vídeo por um link público."""
    p = _perfil(pid)
    repo = request.form.get("repo", "").strip().removeprefix("https://github.com/").strip("/")
    antigo = os.environ.get("NUVEM_VIDEOS_REPO")
    os.environ["NUVEM_VIDEOS_REPO"] = repo
    try:
        canal_nuvem.conferir_passagem()
    except SystemExit as erro:
        os.environ.pop("NUVEM_VIDEOS_REPO", None) if antigo is None else os.environ.update({"NUVEM_VIDEOS_REPO": antigo})
        flash(seguranca.ocultar(str(erro)), "erro")
        return redirect(url_for("conexoes", pid=pid) + "#nuvem")
    _salvar_env({"NUVEM_VIDEOS_REPO": repo})
    job = _iniciar_job(p, "Ligar o Instagram na nuvem", [["nuvem-configurar"]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("conexoes", pid=pid) + "#nuvem"))


@app.post("/p/<pid>/nuvem/<acao>")
def nuvem_acao(pid, acao):
    p = _perfil(pid)
    if acao not in ("sincronizar", "testar", "configurar", "segredos", "instagram"):
        abort(404)
    titulos = {"sincronizar": "Sincronizar com a nuvem", "testar": "Testar a nuvem (simulação)",
               "instagram": "Testar o Instagram pelo link de passagem (não publica)",
               "configurar": "Preparar a nuvem", "segredos": "Atualizar as credenciais na nuvem"}
    job = _iniciar_job(p, titulos[acao], [[f"nuvem-{acao}"]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("conexoes", pid=pid) + "#nuvem"))


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
    from .. import carrossel as carrossel_mod
    slug_ = s["dados"].get("slug") or re.sub(r"^\d+-", "", Path(s["arquivo"]).stem)
    carrossel = {**carrossel_mod.ler(p, slug_), "imagens": [f.name for f in carrossel_mod.imagens(slug_)], "slug": slug_}
    return render_template("ver.html", p=p, d=p.dados, s=s, carrossel=carrossel,
                           conferencia=conferir.ler(p, s["video"]) if s.get("video") else {},
                           revisao=_revisao(p, s["dados"]), textos=_textos(p, s["arquivo"]))


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
    resultado = conferir.conferir(config.SAIDA / s["video"], s["dados"].get("duracao_alvo_s") or p.dados.get("duracao_s"))
    from ..descricao import ler as ler_textos
    extras = conferir.alcance(s["dados"], ler_textos(p, s["arquivo"]), p.dados)
    resultado["achados"] = [a for a in resultado["achados"] if a["nivel"] != "ok" or not extras] + extras
    conferir.salvar(resultado, p)
    return redirect(url_for("ver", pid=pid, nome=nome) + "#conferencia")


@app.post("/p/<pid>/fila/<nome>/revisar-visual")
def revisar_visual(pid, nome):
    """A IA olha os quadros do vídeo pronto (cerca de 1 min, num processo à parte)."""
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    s = _situacao(caminho)
    if not s.get("video"):
        flash("Gere a prévia antes da revisão visual.", "erro")
        return redirect(url_for("ver", pid=pid, nome=nome))
    subprocess.Popen([sys.executable, "-m", "darkops", "--perfil", p.id, "revisar-visual", str(caminho)],
                     cwd=config.RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    flash("A IA está olhando os quadros do vídeo. Recarregue a página em 1 ou 2 minutos.", "ok")
    return redirect(url_for("ver", pid=pid, nome=nome) + "#revisao-visual")


@app.post("/p/<pid>/fila/<nome>/carrossel/<acao>")
def carrossel_acao(pid, nome, acao):
    """Carrossel do Instagram: criar (cerca de 1 min, à parte), aprovar e publicar, ou desaprovar."""
    import requests
    from .. import carrossel as carrossel_mod
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    dados = _ler(caminho)
    slug_ = dados.get("slug") or re.sub(r"^\d+-", "", caminho.stem)
    volta = redirect(url_for("ver", pid=pid, nome=nome) + "#carrossel")
    if acao == "criar":
        subprocess.Popen([sys.executable, "-m", "darkops", "--perfil", p.id, "carrossel", str(caminho)],
                         cwd=config.RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        flash("A IA está escrevendo os slides. Recarregue a página em 1 ou 2 minutos.", "ok")
        return volta
    registro = carrossel_mod.ler(p, slug_)
    if not registro or acao not in ("publicar", "desaprovar"):
        abort(404)
    if acao == "desaprovar":
        registro["aprovado"] = False
        carrossel_mod._gravar(p, slug_, registro)
        return volta
    registro["aprovado"] = True  # o clique em "Aprovar e publicar" é a aprovação do dono
    carrossel_mod._gravar(p, slug_, registro)
    try:
        carrossel_mod.publicar(p, slug_)
        flash("Carrossel publicado no Instagram.", "ok")
    except (SystemExit, requests.RequestException) as erro:
        flash(seguranca.ocultar(f"Não publiquei: {erro}"), "erro")
    return volta


@app.get("/p/<pid>/carrossel/<slug_>/<arquivo>")
def carrossel_imagem(pid, slug_, arquivo):
    from .. import carrossel as carrossel_mod
    _perfil(pid)
    if not re.fullmatch(r"[\w-]+", slug_) or not re.fullmatch(r"\d{2}\.jpg", arquivo):
        abort(404)
    caminho = carrossel_mod.pasta(slug_) / arquivo
    if not caminho.is_file():
        abort(404)
    return send_file(caminho, mimetype="image/jpeg", max_age=0)


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


def _textos(p, nome: str) -> dict:
    from ..descricao import checar, ler
    t = ler(p, nome)
    return {**t, "avisos": checar(t["descricao"], t["tags"], t["hashtags"]) if t["descricao"] or t["tags"] else []}


def _revisao(p, r: dict) -> dict:
    """Resumo do que vai ser produzido, para conferir antes de gerar a prévia."""
    from ..leva import estimar
    from ..perfis import EDICOES
    d = {**p.dados, **{k: v for k, v in r.items() if k in ("estilo", "formato", "velocidade", "edicao", "layout")}}
    palavras = sum(len(c.get("texto", "").split()) for c in r.get("cenas", []))
    rapidez = 1 + int(str(d.get("velocidade", "+0%")).strip("+%") or 0) / 100
    duracao = round(palavras / (2.5 * rapidez))
    est = estimar({**d, "duracao_s": duracao, "cenas_reais": len(r.get("cenas", []))}, 1)
    return {"cenas": len(r.get("cenas", [])), "palavras": palavras, "duracao": duracao,
            "voz": r.get("voz") or d.get("voz"), "estilo": d.get("estilo") or "clipes reais",
            "formato": "Shorts/Reels 9:16" if d.get("formato", "vertical") == "vertical" else "16:9",
            "edicao": EDICOES.get(d.get("edicao", "pro"), "").split(":")[0], "fontes": len(r.get("fontes", [])),
            "notas": r.get("notas_roteiro") or [], "tempo": est["texto"].replace(" para 1 vídeo(s)", ""),
            "aviso": est["aviso"], "nasa": bool(d.get("acervo_nasa")), "alcance": _alcance(p, r)}


def _alcance(p, r: dict) -> list:
    from .. import conferir
    return conferir.alcance(r, perfil_dados=p.dados)


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
    """Grava um roteiro novo no fim da fila do perfil (sem aprovação) e devolve o caminho.
    O tipo, a duração e as plataformas do vídeo vêm do formulário (campos_video); sem eles, do perfil."""
    extra = {**campos_video(request.form, p.dados), **extra}
    numeros = [int(c.name[:3]) for c in fila_mod.roteiros(p) if c.name[:3].isdigit()]
    numero = max(numeros + [0]) + 1
    titulo = titulo.strip() or manchete
    s = slug(titulo)
    formato = extra.get("formato") or p.dados.get("formato", "vertical")
    roteiro = {
        "slug": s, "titulo": titulo, "manchete": manchete,
        "idioma": mercados.de(p.dados)["idioma"], "mercado": mercados.codigo(p.dados),
        "formato": formato, "velocidade": "+10%",
        "tipo_visual": "video", "fontes": [l.strip() for l in fontes.splitlines() if l.strip()],
        "cenas": cenas,
        "metadados": {("youtube_shorts" if formato == "vertical" else "youtube"): {"titulo": titulo},
                      "instagram": {"legenda": f"{manchete}. {mercados.texto(p.dados, 'voce_sabia')} "
                                                   f"{mercados.texto(p.dados, 'seguir_curto', arroba=p.dados['arroba'])}",
                                    "hashtags": mercados.texto(p.dados, "hashtags")}},
        **extra, "aprovado": False,
    }
    destino = p.fila / f"{numero:03d}-{s}.json"
    _gravar(destino, roteiro)
    _salvar_textos(p, destino.name, request.form)
    from ..descricao import ler as ler_textos
    t = ler_textos(p, destino.name)
    if "ia" in (t["descricao_modo"], t["tags_modo"]):  # a IA escreve em segundo plano enquanto você revisa
        _iniciar_job(p, f"Descrição e tags de {destino.name}", [["descricao", str(destino)]])
    return destino


def _salvar_textos(p, nome: str, f) -> None:
    from ..descricao import _limpar_hashtags, _limpar_tags, salvar
    if "descricao_modo" not in f:
        return
    dados = {"descricao_modo": f.get("descricao_modo") if f.get("descricao_modo") in ("ia", "manual") else "ia",
             "tags_modo": f.get("tags_modo") if f.get("tags_modo") in ("ia", "manual") else "ia"}
    if f.get("descricao", "").strip() or dados["descricao_modo"] == "manual":
        dados["descricao"] = f.get("descricao", "").strip()[:4900]
    if f.get("tags", "").strip() or f.get("hashtags", "").strip() or dados["tags_modo"] == "manual":
        dados["tags"] = _limpar_tags(f.get("tags", ""))
        dados["hashtags"] = _limpar_hashtags(f.get("hashtags", "").replace(",", " ").split())
    salvar(p, nome, dados)


@app.post("/p/<pid>/fila/<nome>/textos")
def textos_video(pid, nome):
    """Salva a descrição e as tags do vídeo ou pede à IA para escrever de novo."""
    p = _perfil(pid)
    caminho = _arquivo_fila(p, nome)
    _salvar_textos(p, caminho.name, request.form)
    if request.form.get("acao") == "refazer":
        job = _iniciar_job(p, f"Descrição e tags de {caminho.name}", [["descricao", str(caminho), "--refazer"]])
        return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("ver", pid=pid, nome=nome) + "#textos"))
    flash("Descrição e tags salvas.", "ok")
    return redirect(url_for("ver", pid=pid, nome=nome) + "#textos")


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


# ---------- estatísticas e análise da IA ----------

@app.get("/p/<pid>/estatisticas")
def estatisticas(pid):
    from .. import analise
    from .. import estatisticas as est
    p = _perfil(pid)
    dados = est.ler(p)
    return render_template("estatisticas.html", p=p, d=p.dados, dados=dados, totais=est.totais(dados),
                           sugestoes=analise.ler_sugestoes(p))


@app.get("/p/<pid>/estatisticas/<plataforma>/<modo>")
def estatisticas_tela(pid, plataforma, modo):
    """Tela cheia de Resultados: todos os vídeos ou a monetização de uma plataforma, com o Voltar."""
    from .. import estatisticas as est
    if plataforma not in ("youtube", "instagram") or modo not in ("videos", "monetizacao"):
        abort(404)
    p = _perfil(pid)
    dados = est.ler(p)
    totais = est.totais(dados)
    if plataforma not in totais:
        abort(404)
    return render_template("estatisticas.html", p=p, d=p.dados, dados=dados, totais=totais, modo=modo, so=plataforma,
                           sugestoes={})


@app.post("/p/<pid>/estatisticas/<acao>")
def estatisticas_acao(pid, acao):
    p = _perfil(pid)
    voltar = url_for("estatisticas", pid=pid)
    comandos = {"atualizar": ("Atualizar estatísticas", [["estatisticas"]]),
                "analisar": ("Análise da IA", [["estatisticas"], ["analisar"]]),
                "retencao": ("Liberar retenção do YouTube", [["autorizar-youtube", "--analytics"], ["estatisticas"]])}
    if acao not in comandos:
        abort(404)
    titulo, lista = comandos[acao]
    if acao == "retencao":
        flash("Abrimos o login do Google: escolha a conta do canal e permita também a leitura do YouTube Analytics.", "ok")
    job = _iniciar_job(p, titulo, lista)
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=voltar))


@app.get("/p/<pid>/comentarios")
def comentarios(pid):
    """Comentários dos vídeos: o que espera resposta (rascunho da IA para aprovar ou editar), o resto e as ideias."""
    from .. import comentarios as com
    p = _perfil(pid)
    filtro = request.args.get("ver", "esperando")
    if filtro not in ("esperando", "respondidos", "sem_resposta", "ignorados", "todos"):
        filtro = "esperando"
    dados = com.ler(p)
    return render_template("comentarios.html", p=p, d=p.dados, filtro=filtro, lista=com.listar(p, filtro)[:200],
                           resumo=com.resumo_geral(p), ideias=com.ideias(p), dados=dados,
                           pode_youtube=com.pode_responder_youtube(p), limite_auto=com.LIMITE_AUTO_DIA)


@app.post("/p/<pid>/comentarios/<acao>")
def comentarios_acao(pid, acao):
    p = _perfil(pid)
    voltar = url_for("comentarios", pid=pid)
    if acao == "auto":
        modo = request.form.get("modo")
        p.salvar({"comentarios_auto": "simples" if modo == "simples" else "nao"})
        flash("Modo automático ligado: só elogios e perguntas simples, até 20 por dia. O resto espera você."
              if modo == "simples" else "Modo automático desligado: toda resposta espera a sua aprovação.", "ok")
        return redirect(voltar)
    comandos = {"buscar": ("Buscar comentários", [["estatisticas"], ["comentarios"]]),
                "liberar": ("Liberar comentários do YouTube", [["autorizar-youtube", "--comentarios"], ["comentarios", "--sem-ia"]])}
    if acao not in comandos:
        abort(404)
    if acao == "liberar":
        flash("Abrimos o login do Google: escolha a conta do canal e permita gerenciar os comentários.", "ok")
    titulo, lista = comandos[acao]
    job = _iniciar_job(p, titulo, lista)
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=voltar))


@app.post("/p/<pid>/comentario/<cid>/<decisao>")
def decidir_comentario(pid, cid, decisao):
    from .. import comentarios as com
    p = _perfil(pid)
    voltar = url_for("comentarios", pid=pid, ver=request.form.get("ver", "esperando"))
    if decisao == "responder":
        try:
            c = com.responder(p, cid, request.form.get("texto", ""))
            flash(f"Respondido no {'YouTube' if c['plataforma'] == 'youtube' else 'Instagram'}.", "ok")
        except SystemExit as erro:
            flash(str(erro), "erro")
    elif decisao in ("ignorar", "reabrir"):
        if not com.decidir(p, cid, "ignorado" if decisao == "ignorar" else "pendente"):
            flash("Esse comentário já foi respondido ou não existe mais.", "erro")
    else:
        abort(404)
    return redirect(voltar)


@app.get("/p/<pid>/aprendizado")
def aprendizado(pid):
    """O que funcionou e o que não funcionou em cada ciclo de 14 vídeos, e o que mudou sozinho por causa disso."""
    from .. import aprendizado as apr
    p = _perfil(pid)
    return render_template("aprendizado.html", p=p, d=p.dados, prog=apr.progresso(p),
                           ciclos=list(reversed(apr.ler(p).get("ciclos", []))))


@app.post("/p/<pid>/aprendizado/<acao>")
def aprendizado_acao(pid, acao):
    from .. import aprendizado as apr
    p = _perfil(pid)
    if acao == "desfazer":
        n = apr.desfazer(p)
        flash(f"Pronto: {n} mudança(s) desfeita(s); o canal voltou ao que era antes da análise." if n
              else "Não há mudança para desfazer.", "ok" if n else "erro")
        return redirect(url_for("aprendizado", pid=pid))
    if acao != "analisar":
        abort(404)
    job = _iniciar_job(p, "Analisar o que funcionou", [["aprender", "--forcar"]])
    return redirect(url_for("acompanhar", pid=pid, job=job, voltar=url_for("aprendizado", pid=pid)))


@app.post("/p/<pid>/sugestao/<sid>/<decisao>")
def decidir_sugestao(pid, sid, decisao):
    from ..analise import decidir
    p = _perfil(pid)
    if decisao not in ("aprovar", "recusar"):
        abort(404)
    item = decidir(p, sid, decisao == "aprovar")
    if not item:
        flash("Essa sugestão já foi decidida ou não é mais válida.", "erro")
    elif item["estado"] == "aprovada":
        flash(f"Aprovada e aplicada: {item['titulo']}", "ok")
    else:
        flash(f"Recusada: {item['titulo']}", "ok")
    return redirect(url_for("estatisticas", pid=pid) + "#sugestoes")


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
    from .tarefas import codigo_login, resumo
    texto = Path(info["log"]).read_text(encoding="utf-8", errors="replace") if Path(info["log"]).exists() else ""
    texto = seguranca.ocultar(texto[-6000:])
    return jsonify({"estado": info["estado"], "log": texto, "codigo": codigo_login(texto),
                    "resumo": resumo(texto, info["estado"] == "concluido") if info["estado"] != "rodando" else "",
                    "segundos": int(info.get("fim", time.time()) - info["inicio"])})


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
    ambiente.exigir_local()  # o modo servidor está preparado em ambiente.py, mas bloqueado pelas regras de segurança
    porta = int(os.environ.get("PORT", porta))  # o preview do Claude Code pode escolher a porta
    url = f"http://127.0.0.1:{porta}"
    reinicio = os.environ.pop("DARKOPS_REINICIO", "") == "1"
    # no Windows dois servidores conseguem ocupar a mesma porta e responder misturado: não abre outro.
    # Num reinício pela atualização, espera o Estúdio antigo fechar (até 20 s).
    from ..app import ligar_n8n
    from .. import whatsapp
    whatsapp.ligar()  # comandos pelo WhatsApp: porteiro + túnel (em segundo plano; só se estiver configurado)
    ligar_n8n()  # a postagem das 12h e 19h depende do n8n; rápido (só confere e dispara), vale até com o Estúdio já aberto
    if canal_nuvem.configurada():  # traz o que a nuvem postou com o PC desligado e manda os aprovados novos
        def _sincronizar_nuvem():
            for p in listar():
                if p.dados.get("ativo"):
                    try:
                        canal_nuvem.sincronizar(p)
                    except (SystemExit, OSError) as erro:
                        print(seguranca.ocultar(f"nuvem: {erro}"))
        threading.Thread(target=_sincronizar_nuvem, daemon=True).start()
    for _ in range(40 if reinicio else 1):
        with socket.socket() as teste:
            livre = teste.connect_ex(("127.0.0.1", porta)) != 0
        if livre:
            break
        time.sleep(0.5)
    else:
        print(f"O Estúdio já está aberto em {url}")
        if abrir:
            webbrowser.open(url + "/abertura")
        return
    from werkzeug.serving import make_server
    servidor = make_server("127.0.0.1", porta, app, threaded=True)
    print(f"Estúdio em {url} (Ctrl+C para fechar)")
    if abrir and not reinicio:  # no reinício a aba aberta só recarrega, sem abrir outra
        # a porta já está escutando: o navegador abre na hora, sem esperar um tempo fixo
        threading.Thread(target=webbrowser.open, args=(url + "/abertura",), daemon=True).start()
    os.environ["PORT"] = str(porta)  # o Estúdio reaberto depois de uma atualização usa a mesma porta
    threading.Thread(target=_vigiar_atualizacao, daemon=True).start()
    threading.Thread(target=_vigiar_levas_adiadas, daemon=True).start()
    threading.Thread(target=_vigiar_palavra, daemon=True).start()
    servidor.serve_forever()


def _vigiar_palavra() -> None:
    """Quem comenta a palavra da chamada final (DARK) recebe o link do projeto em até ~15 min, sem esperar o ciclo
    de 3 horas dos comentários no n8n. Só coleta e manda o link fixo (palavra.py): nada de IA aqui."""
    from .. import comentarios, palavra
    time.sleep(90)  # deixa o Estúdio abrir antes
    while True:
        for p in listar():
            if not palavra.ligado(p) or not (p.token_youtube.exists() or p.token_instagram.exists()):
                continue
            try:
                palavra.responder(p, comentarios.coletar(p), avisar=lambda *_: None)
            except Exception as erro:  # noqa: BLE001 — sem internet ou token vencido: tenta de novo depois
                print(seguranca.ocultar(f"link da palavra-chave em {p.id}: {erro}"))
        time.sleep(15 * 60)


def _vigiar_levas_adiadas() -> None:
    """A produção espera a configuração do canal terminar: a cada 2 min, começa a leva guardada de quem já está pronto."""
    from .. import leva
    while True:
        for p in listar():
            try:
                if leva.retomar_adiada(p):
                    print(f"configuração de {p.dados.get('nome', p.id)} pronta: leva adiada iniciada")
            except (SystemExit, OSError, ValueError) as erro:
                print(seguranca.ocultar(f"leva adiada de {p.id}: {erro}"))
        time.sleep(120)


def _vigiar_atualizacao() -> None:
    """Procura versão nova de tempos em tempos (se ligado em Configurações) e, quando há atualização, reinicia
    o Estúdio com o código novo, mas só quando nenhuma tarefa (prévia, leva...) estiver rodando."""
    from .. import app as app_local
    from .. import whatsapp
    inicio, versao_conferida = time.time(), 0.0
    while True:
        time.sleep(5)
        if time.time() - versao_conferida > 60:  # versão nova (commit ou atualização) vira aviso no WhatsApp
            versao_conferida = time.time()
            try:
                whatsapp.avisar_versao()
            except Exception as erro:
                print(seguranca.ocultar(f"aviso de versão no WhatsApp falhou: {erro}"))
        cfg = app_local.ler()
        if cfg["atualizar_sozinho"] and time.time() - cfg["ultima_verificacao"] > cfg["verificar_a_cada_h"] * 3600:
            try:
                app_local.atualizar()
            except Exception as erro:
                print(f"atualização automática falhou: {erro}")
        sinal = app_local.SINAL_REINICIO
        ocupado = any(j["estado"] == "rodando" for j in JOBS.values())
        if sinal.exists() and sinal.stat().st_mtime > inicio - 1 and not ocupado:
            print("versão nova instalada: reiniciando o Estúdio")
            app_local.reiniciar_processo()
