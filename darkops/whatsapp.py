"""WhatsApp do dono do canal: avisos da produção e da postagem, e comandos para mandar no canal pelo celular.

Usa só a API oficial da Meta (WhatsApp Cloud API) e só conversa com UM número: o do dono (WHATSAPP_PARA).

Avisos (saem do PC e da nuvem): vídeo postado, falha, fila acabando, vídeo novo pronto para aprovar (o próprio
vídeo, com os botões Aprovar e Recusar) e um resumo do dia. A Meta só deixa mandar texto livre até 24 h depois da
última mensagem do dono; fora dessa janela o aviso usa o modelo aprovado (WHATSAPP_MODELO, opcional) ou fica
guardado e é entregue na próxima vez que o dono escrever.

Comandos (só com o PC ligado): a Meta manda cada mensagem para um túnel da Cloudflare (endereço público
temporário) que chega a um porteiro local (127.0.0.1:5680). O porteiro confere a assinatura da Meta
(X-Hub-Signature-256 com o segredo do app), guarda a mensagem em dados/whatsapp/entrada/ e avisa o n8n, que roda
`python -m darkops whatsapp-receber`. O túnel só leva a esse porteiro: o n8n e o Estúdio continuam fechados em
127.0.0.1. Se o n8n estiver desligado, o porteiro processa direto para o comando não se perder.

Variáveis no .env (nunca no código nem no chat):
  WHATSAPP_TOKEN        token permanente (usuário do sistema) com whatsapp_business_messaging
  WHATSAPP_NUMERO_ID    "Phone number ID" do número que envia
  WHATSAPP_PARA         número do dono, com DDI e DDD (ex.: 5511999998888)
  WHATSAPP_APP_ID       ID do app da Meta           } só para receber comandos
  WHATSAPP_APP_SECRET   chave secreta do app        }
  WHATSAPP_VERIFICAR    gerado sozinho (verificação do webhook)
  WHATSAPP_MODELO       nome de um modelo aprovado com 1 variável no corpo (opcional)
"""
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config
from .seguranca import ocultar

GRAPH = "https://graph.facebook.com/v21.0"
PASTA = config.RAIZ / "dados" / "whatsapp"
ESTADO = PASTA / "estado.json"
ENTRADA = PASTA / "entrada"
PORTA_PORTEIRO = 5680
CAMINHO_WEBHOOK = "/webhook/whatsapp"            # o que a Meta chama (no túnel)
N8N_WEBHOOK = "http://127.0.0.1:5678/webhook/whatsapp-canais"
ID_WORKFLOW = "whatsappcanais1"
JANELA_S = 24 * 3600 - 15 * 60                  # janela de atendimento da Meta, com folga
LIMITE_VIDEO = 16 * 1024 * 1024                 # vídeo no WhatsApp: até 16 MB


# ---------- configuração e estado ----------

def _env(nome: str) -> str:
    return os.getenv(nome, "").strip()


def configurado() -> bool:
    return bool(_env("WHATSAPP_TOKEN") and _env("WHATSAPP_NUMERO_ID") and _numero(_env("WHATSAPP_PARA")))


def recebe_comandos() -> bool:
    return configurado() and bool(_env("WHATSAPP_APP_ID") and _env("WHATSAPP_APP_SECRET"))


def _numero(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def mesmo_numero(a: str, b: str) -> bool:
    """O WhatsApp às vezes manda celular do Brasil sem o 9 da frente (55 11 9xxxx-xxxx vira 55 11 xxxx-xxxx)."""
    a, b = _numero(a), _numero(b)

    def sem_nove(n: str) -> str:
        return n[:4] + n[5:] if n.startswith("55") and len(n) == 13 and n[4] == "9" else n
    return bool(a) and sem_nove(a) == sem_nove(b)


def ler_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_estado(**novos) -> dict:
    PASTA.mkdir(parents=True, exist_ok=True)
    estado = {**ler_estado(), **novos}
    temp = ESTADO.with_suffix(".tmp")
    temp.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(ESTADO)
    return estado


def janela_aberta() -> bool:
    return time.time() - ler_estado().get("ultima_mensagem", 0) < JANELA_S


def situacao() -> str:
    """Para a abertura e o painel: desligado, ligando (túnel subindo) ou ligado."""
    if not configurado():
        return "desligado"
    if not recebe_comandos():
        return "ligado"
    return "ligado" if ler_estado().get("tunel_ok") else "ligando"


def verificador() -> str:
    """Senha da verificação do webhook (não é segredo da Meta; só confirma que o webhook é nosso)."""
    valor = _env("WHATSAPP_VERIFICAR")
    if not valor:
        valor = secrets.token_urlsafe(24)
        from .estudio import _salvar_env
        _salvar_env({"WHATSAPP_VERIFICAR": valor})
        os.environ["WHATSAPP_VERIFICAR"] = valor
    return valor


# ---------- API da Meta ----------

def _pedir(metodo: str, caminho: str, dados: dict | None = None, corpo: bytes | None = None, tipo: str = "",
           token: str | None = None) -> dict:
    url = caminho if caminho.startswith("http") else f"{GRAPH}{caminho}"
    if dados is not None:
        corpo, tipo = json.dumps(dados).encode(), "application/json"
    cab = {"Authorization": f"Bearer {token or _env('WHATSAPP_TOKEN')}"}
    if corpo is not None:
        cab["Content-Type"] = tipo
    req = urllib.request.Request(url, data=corpo, headers=cab, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as erro:
        try:
            info = json.loads(erro.read()).get("error", {})
        except ValueError:
            info = {}
        raise ErroMeta(info.get("code"), ocultar(f"Meta respondeu {erro.code}: {info.get('message', '')}"
                                                  f" {info.get('error_data', {}).get('details', '')}".strip()))


class ErroMeta(Exception):
    def __init__(self, codigo, texto):
        super().__init__(texto)
        self.codigo = codigo


def _destino() -> str:
    """Responde no formato que a Meta usou para o dono (wa_id); antes da primeira mensagem, o número do .env."""
    return ler_estado().get("wa_id") or _numero(_env("WHATSAPP_PARA"))


def _mandar(mensagem: dict) -> None:
    _pedir("POST", f"/{_env('WHATSAPP_NUMERO_ID')}/messages",
           {"messaging_product": "whatsapp", "recipient_type": "individual", "to": _destino(), **mensagem})


def _subir_midia(arquivo: Path) -> str:
    """Envia o arquivo para a Meta (multipart) e devolve o id da mídia."""
    limite = f"----canais{uuid.uuid4().hex}"
    tipo = mimetypes.guess_type(arquivo.name)[0] or "application/octet-stream"
    partes = [f"--{limite}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode(),
              f"--{limite}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\n{tipo}\r\n".encode(),
              f"--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{arquivo.name}\"\r\n"
              f"Content-Type: {tipo}\r\n\r\n".encode(), arquivo.read_bytes(), f"\r\n--{limite}--\r\n".encode()]
    return _pedir("POST", f"/{_env('WHATSAPP_NUMERO_ID')}/media", corpo=b"".join(partes),
                  tipo=f"multipart/form-data; boundary={limite}")["id"]


def _guardar(texto: str) -> None:
    pendentes = ler_estado().get("pendentes", [])[-19:]
    _gravar_estado(pendentes=pendentes + [{"quando": time.strftime("%d/%m %H:%M"), "texto": texto[:900]}])


def enviar(texto: str, botoes: list[tuple[str, str]] | None = None, video: Path | None = None) -> bool:
    """Manda um aviso ao dono. Nunca derruba quem chamou: qualquer erro vira linha no log.
    botoes: até 3 (id, rótulo). video: o próprio vídeo junto (se couber no limite do WhatsApp)."""
    if not configurado():
        return False
    from . import nuvem
    if nuvem.simulando():
        print(f"[simulação] WhatsApp: {texto.splitlines()[0][:120]}")
        return False
    texto = texto[:1000]
    try:
        if not janela_aberta() and not nuvem.na_nuvem():  # a nuvem não sabe da janela: tenta e trata o erro
            return _fora_da_janela(texto)
        midia = _subir_midia(video) if video and video.exists() and video.stat().st_size <= LIMITE_VIDEO else None
        if botoes:
            interativo = {"type": "button", "body": {"text": texto},
                          "action": {"buttons": [{"type": "reply", "reply": {"id": i[:200], "title": r[:20]}}
                                                 for i, r in botoes[:3]]}}
            if midia:
                interativo["header"] = {"type": "video", "video": {"id": midia}}
            _mandar({"type": "interactive", "interactive": interativo})
        elif midia:
            _mandar({"type": "video", "video": {"id": midia, "caption": texto}})
        else:
            _mandar({"type": "text", "text": {"body": texto, "preview_url": True}})
        return True
    except ErroMeta as erro:
        if erro.codigo == 131047:  # passou da janela de 24 h
            return _fora_da_janela(texto)
        print(ocultar(f"WhatsApp: {erro}"))
    except (OSError, KeyError, ValueError) as erro:
        print(ocultar(f"WhatsApp: {erro}"))
    return False


def _fora_da_janela(texto: str) -> bool:
    modelo = _env("WHATSAPP_MODELO")
    if modelo:
        try:
            _mandar({"type": "template", "template": {
                "name": modelo, "language": {"code": _env("WHATSAPP_MODELO_IDIOMA") or "pt_BR"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": " ".join(texto.split())[:900]}]}]}})
            return True
        except (ErroMeta, OSError) as erro:
            print(ocultar(f"WhatsApp (modelo): {erro}"))
    from . import nuvem
    if nuvem.na_nuvem():
        print("WhatsApp: fora da janela de 24 h e sem modelo aprovado; aviso não enviado pela nuvem")
        return False
    _guardar(texto)  # entregue quando o dono escrever de novo
    return False


# ---------- avisos ----------

def _titulo(roteiro: dict, caminho: Path) -> str:
    return roteiro.get("titulo") or (roteiro.get("youtube") or {}).get("titulo") or caminho.stem


def postado(perfil, roteiro: dict, caminho: Path, ids: dict, por: str = "PC") -> None:
    from .fila import restantes, url
    linhas = [f"✅ *{perfil.dados['nome']}* postou: {_titulo(roteiro, caminho)}"]
    for plataforma, midia in ids.items():
        linhas.append(f"• {plataforma.capitalize()}: {url(plataforma, midia, perfil)}")
    sobra = restantes(perfil)
    linhas.append(f"Postado pelo {por}. Na fila: {sobra} aprovado(s).")
    enviar("\n".join(linhas))
    if sobra <= 2:
        fila_curta(perfil, sobra)


def falhou(perfil, etapa: str, mensagem: str) -> None:
    enviar(f"⚠️ *{perfil.dados['nome']}*: falha em {etapa}.\n{ocultar(mensagem)[:500]}\n"
           "A fila continua. Detalhes no Estúdio, em Resultados.")


def fila_curta(perfil, sobra: int) -> None:
    enviar(f"📉 *{perfil.dados['nome']}*: só {sobra} vídeo(s) aprovado(s) na fila. "
           "Responda *criar 3* para fazer mais, ou *aprovar* para ver os que esperam.", botoes=[
               (f"criar|{perfil.id}|3", "Criar 3 vídeos"), (f"lista|{perfil.id}", "Ver para aprovar")])


def pronto_para_aprovar(perfil, caminho: Path) -> None:
    """Manda o vídeo novo com os botões de aprovar e recusar."""
    try:
        roteiro = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    video = _video(roteiro, caminho)
    enviar(f"🎬 *{perfil.dados['nome']}*: vídeo novo pronto.\n*{_titulo(roteiro, caminho)}*\n"
           "Assista e escolha. Aprovado, ele entra na postagem automática.",
           botoes=[(f"aprovar|{perfil.id}|{caminho.name}", "Aprovar"), (f"recusar|{perfil.id}|{caminho.name}", "Recusar")],
           video=video)


def resumo_do_dia() -> None:
    enviar("🌙 Resumo do dia\n" + _status())


# ---------- comandos ----------

AJUDA = ("Comandos do Projeto Canais:\n"
         "• *status*: como está cada canal\n"
         "• *fila*: o que vai ao ar e o que espera aprovação\n"
         "• *aprovar*: manda o próximo vídeo para você aprovar (*aprovar todos* aprova os prontos)\n"
         "• *criar 3*: cria 3 vídeos novos  ·  *criar sobre <tema>*: um vídeo sobre o tema\n"
         "• *pausar* / *retomar*: para ou volta a postagem (*pausar todos* / *retomar todos*: todos os canais)\n"
         "• *ajustar <pedido>*: a IA propõe uma mudança no canal (você aprova antes)\n"
         "• *canal <nome>*: escolhe o canal dos próximos comandos")


def _simples(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _perfis():
    from .perfis import listar
    return listar()


def _perfil_atual():
    from .perfis import carregar
    perfis = _perfis()
    escolhido = ler_estado().get("perfil")
    if escolhido and any(p.id == escolhido for p in perfis):
        return carregar(escolhido)
    ativos = [p for p in perfis if p.dados.get("ativo")]
    return (ativos or perfis or [None])[0]


def _video(roteiro: dict, caminho: Path) -> Path:
    return config.SAIDA / f"{roteiro.get('slug') or caminho.stem}-{roteiro.get('formato', 'vertical')}.mp4"


def _pendentes(perfil) -> list[Path]:
    """Roteiros com prévia pronta (vídeo mais novo que o roteiro) e ainda sem aprovação."""
    from .fila import roteiros
    saida = []
    for caminho in roteiros(perfil):
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        video = _video(dados, caminho)
        if not dados.get("aprovado") and video.exists() and video.stat().st_mtime >= caminho.stat().st_mtime - 1:
            saida.append(caminho)
    return saida


def _status() -> str:
    from .fila import restantes
    linhas = []
    for p in _perfis():
        d = p.dados
        horarios = " e ".join(d.get("horarios", ["12:00", "19:00"]))
        linhas.append(f"*{d['nome']}* ({'no ar' if d.get('ativo') else 'pausado'})\n"
                      f"  aprovados na fila: {restantes(p)} · esperando você: {len(_pendentes(p))}\n"
                      f"  posta às {horarios}" + (f" · leva criando vídeos" if (p.controle / 'leva.trava').exists() else ""))
    return "\n".join(linhas) or "Nenhum canal criado ainda."


def _fila(perfil) -> str:
    from .fila import aprovado, roteiros
    linhas = [f"*{perfil.dados['nome']}*"]
    aprovados = [r for r in roteiros(perfil) if aprovado(r)]
    linhas.append(f"Vão ao ar ({len(aprovados)}):")
    linhas += [f"  {i}. {_titulo(json.loads(r.read_text(encoding='utf-8')), r)}" for i, r in enumerate(aprovados[:6], 1)]
    pend = _pendentes(perfil)
    linhas.append(f"Esperando sua aprovação ({len(pend)}):")
    linhas += [f"  {i}. {_titulo(json.loads(r.read_text(encoding='utf-8')), r)}" for i, r in enumerate(pend[:6], 1)]
    if pend:
        linhas.append("Responda *aprovar* para ver o próximo.")
    return "\n".join(linhas)


def _decidir_video(perfil, nome: str, aprovar: bool) -> str:
    """Aprovar: só com prévia pronta (a mesma regra do Estúdio). Recusar: sai da fila para recusados/ (nada apagado)."""
    caminho = perfil.fila / Path(nome).name
    if not caminho.exists() or caminho.suffix != ".json":
        return "Esse vídeo não está mais na fila."
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if aprovar:
        if caminho not in _pendentes(perfil) and not dados.get("aprovado"):
            return "A prévia desse vídeo não está pronta. Gere a prévia no Estúdio antes de aprovar."
        video = _video(dados, caminho)
        dados["aprovado"] = True
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        if video.exists():
            os.utime(video)  # a prévia continua em dia
        _sincronizar_nuvem(perfil)
        return f"✅ Aprovado: {_titulo(dados, caminho)}. Entra na postagem automática."
    destino = perfil.pasta / "recusados"
    destino.mkdir(parents=True, exist_ok=True)
    shutil.move(str(caminho), destino / caminho.name)
    return f"🗑️ Recusado: {_titulo(dados, caminho)}. Saiu da fila (fica guardado em recusados/)."


def _sincronizar_nuvem(perfil) -> None:
    from . import nuvem
    if nuvem.configurada():
        subprocess.Popen([sys.executable, "-m", "darkops", "--perfil", perfil.id, "nuvem-sincronizar"], cwd=config.RAIZ,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _criar(perfil, quantidade: int, tema: str) -> str:
    from . import leva
    if (perfil.controle / "leva.trava").exists():
        return "Já tem uma leva criando vídeos neste canal. Aviso quando cada um ficar pronto."
    quantidade = max(1, min(quantidade, leva.LIMITE_LEVA))
    leva.em_segundo_plano(perfil, quantidade, tema)
    est = leva.estimar(perfil.dados, quantidade)
    return (f"🛠️ Criando {quantidade} vídeo(s)" + (f" sobre *{tema}*" if tema else "") +
            f" para {perfil.dados['nome']} ({est['texto']}). Mando cada um aqui quando ficar pronto.")


def processar(texto: str) -> str | None:
    """Um comando do dono vira uma resposta. Botões chegam como 'acao|perfil|arquivo'."""
    from .perfis import carregar
    if "|" in texto:
        acao, *resto = texto.split("|")
        try:
            perfil = carregar(resto[0])
        except SystemExit:
            return "Canal não encontrado."
        if acao in ("aprovar", "recusar") and len(resto) > 1:
            resposta = _decidir_video(perfil, resto[1], acao == "aprovar")
            proximo = _pendentes(perfil)
            if proximo:
                pronto_para_aprovar(perfil, proximo[0])
            return resposta
        if acao == "criar":
            return _criar(perfil, int(resto[1]) if len(resto) > 1 and resto[1].isdigit() else 3, "")
        if acao == "lista":
            pend = _pendentes(perfil)
            if pend:
                pronto_para_aprovar(perfil, pend[0])
                return None
            return "Nenhum vídeo esperando aprovação."
        if acao == "ajuste":
            from . import canal_ia
            n = canal_ia.decidir(perfil, resto[1] == "sim" if len(resto) > 1 else False)
            return f"✅ Ajuste aplicado ({n} campo(s))." if n else "Ajuste descartado."
        return None

    original = texto.strip()
    t = _simples(original)
    perfil = _perfil_atual()
    if not perfil and not t.startswith(("ajuda", "menu")):
        return "Nenhum canal criado ainda. Crie o primeiro no Estúdio."
    if t in ("", "oi", "ola", "menu", "ajuda", "comandos", "?"):
        return AJUDA
    if t.startswith("status"):
        return _status()
    if t.startswith("fila"):
        return _fila(perfil)
    if t.startswith("canal"):
        nome = _simples(original[5:])
        achado = next((p for p in _perfis() if nome and (nome in _simples(p.dados["nome"]) or nome in p.id)), None)
        if not achado:
            return "Canais: " + ", ".join(p.dados["nome"] for p in _perfis())
        _gravar_estado(perfil=achado.id)
        return f"Ok, os próximos comandos valem para *{achado.dados['nome']}*."
    if t.startswith(("pausar todos", "parar todos", "retomar todos", "ligar todos")):
        ativo = t.startswith(("retomar", "ligar"))
        for p in _perfis():
            p.salvar({"ativo": ativo})
        return ("▶️ Todos os canais no ar: " if ativo else "⏸️ Todos os canais pausados: ") + \
            ", ".join(p.dados["nome"] for p in _perfis())
    if len(_perfis()) > 1 and not ler_estado().get("perfil"):
        _gravar_estado(perfil=perfil.id)  # com vários canais, diz uma vez em qual os comandos valem
        enviar(f"ℹ️ Você tem {len(_perfis())} canais; os comandos valem para *{perfil.dados['nome']}*. "
               "Para trocar: *canal <nome>*.")
    if t.startswith("aprovar todos"):
        respostas = [_decidir_video(perfil, r.name, True) for r in _pendentes(perfil)]
        return "\n".join(respostas) or "Nenhum vídeo pronto esperando aprovação."
    if t.startswith("aprovar"):
        pend = _pendentes(perfil)
        if not pend:
            return "Nenhum vídeo pronto esperando aprovação."
        pronto_para_aprovar(perfil, pend[0])
        return None
    if t.startswith("criar"):
        resto = original[5:].strip()
        achado = re.match(r"(\d+)?\s*(?:videos?|vídeos?)?\s*(?:sobre\s+(.+))?$", resto, re.I)
        quantidade = int(achado.group(1)) if achado and achado.group(1) else (1 if achado and achado.group(2) else 3)
        tema = (achado.group(2) or "").strip() if achado else resto
        return _criar(perfil, quantidade, tema[:200])
    if t.startswith(("pausar", "parar")):
        perfil.salvar({"ativo": False})
        return f"⏸️ {perfil.dados['nome']} pausado. Nada vai ao ar até você mandar *retomar*."
    if t.startswith(("retomar", "ligar", "voltar")):
        perfil.salvar({"ativo": True})
        return f"▶️ {perfil.dados['nome']} no ar de novo."
    if t.startswith("ajustar"):
        pedido = original[7:].strip()
        if not pedido:
            return "Diga o que mudar. Ex.: *ajustar vídeos mais curtos e com mais humor*"
        enviar("⏳ Pensando no ajuste (cerca de 1 minuto)…")
        from . import canal_ia
        try:
            proposta = canal_ia.propor(perfil, pedido)
        except SystemExit as erro:
            return str(erro)
        if not proposta["mudancas"]:
            canal_ia.decidir(perfil, False)
            return f"A IA não achou o que mudar: {proposta['resumo']}"
        linhas = [f"Proposta para {perfil.dados['nome']}: {proposta['resumo']}"]
        linhas += [f"• {m['campo']}: {m['antes']} → {m['depois']}" for m in proposta["mudancas"]]
        enviar("\n".join(linhas)[:1000], botoes=[(f"ajuste|{perfil.id}|sim", "Aplicar"), (f"ajuste|{perfil.id}|nao", "Descartar")])
        return None
    return "Não entendi. " + AJUDA


# ---------- entrada (webhook) ----------

def assinatura_valida(corpo: bytes, assinatura: str) -> bool:
    segredo = _env("WHATSAPP_APP_SECRET").encode()
    esperado = "sha256=" + hmac.new(segredo, corpo, hashlib.sha256).hexdigest()
    return bool(segredo) and hmac.compare_digest(esperado, assinatura or "")


def receber(arquivo: Path) -> int:
    """Processa uma entrega do webhook (já com a assinatura conferida pelo porteiro). Devolve quantas mensagens
    do dono foram tratadas; mensagens de outros números são ignoradas."""
    try:
        evento = json.loads(arquivo.read_text(encoding="utf-8"))
    finally:
        arquivo.unlink(missing_ok=True)
    tratadas = 0
    for entrada in evento.get("entry", []):
        for mudanca in entrada.get("changes", []):
            valor = mudanca.get("value", {})
            for msg in valor.get("messages", []):
                if not mesmo_numero(msg.get("from", ""), _env("WHATSAPP_PARA")):
                    continue
                estado = ler_estado()
                vistos = estado.get("vistos", [])
                if msg.get("id") in vistos:  # a Meta reentrega quando demora: não repete o comando
                    continue
                _gravar_estado(vistos=(vistos + [msg.get("id")])[-50:], ultima_mensagem=time.time(), wa_id=msg["from"])
                pendentes = ler_estado().get("pendentes", [])
                if pendentes:
                    _gravar_estado(pendentes=[])
                    enviar("📬 Avisos enquanto você estava fora:\n" +
                           "\n".join(f"[{p['quando']}] {p['texto']}" for p in pendentes)[:990])
                texto = (msg.get("text", {}).get("body")
                         or msg.get("interactive", {}).get("button_reply", {}).get("id")
                         or msg.get("button", {}).get("payload") or msg.get("button", {}).get("text") or "")
                try:
                    resposta = processar(texto)
                except Exception as erro:  # um comando quebrado responde o erro em vez de sumir
                    resposta = ocultar(f"Não consegui: {erro}")
                if resposta:
                    enviar(resposta)
                tratadas += 1
    return tratadas


class _Porteiro(BaseHTTPRequestHandler):
    """Única porta aberta para a internet (pelo túnel): só o caminho do webhook, só da Meta."""
    server_version = "canais"

    def log_message(self, format, *args):  # noqa: A002 (nome da classe base)
        pass

    def _responder(self, codigo: int, texto: str = "") -> None:
        corpo = texto.encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(url.query))
        if url.path == CAMINHO_WEBHOOK and q.get("hub.mode") == "subscribe" \
                and hmac.compare_digest(q.get("hub.verify_token", ""), _env("WHATSAPP_VERIFICAR")):
            return self._responder(200, re.sub(r"[^\w-]", "", q.get("hub.challenge", ""))[:100])
        self._responder(404)

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != CAMINHO_WEBHOOK:
            return self._responder(404)
        tamanho = int(self.headers.get("Content-Length") or 0)
        if not 0 < tamanho <= 1_000_000:
            return self._responder(413)
        corpo = self.rfile.read(tamanho)
        if not assinatura_valida(corpo, self.headers.get("X-Hub-Signature-256", "")):
            return self._responder(403)
        ENTRADA.mkdir(parents=True, exist_ok=True)
        nome = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
        (ENTRADA / nome).write_bytes(corpo)
        self._responder(200, "ok")  # a Meta quer resposta rápida; o resto segue em segundo plano
        threading.Thread(target=_entregar, args=(nome,), daemon=True).start()


def _entregar(nome: str) -> None:
    """Avisa o n8n (que roda o whatsapp-receber); com o n8n fora do ar, processa aqui mesmo."""
    try:
        req = urllib.request.Request(N8N_WEBHOOK, data=json.dumps({"arquivo": nome}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status < 300:
                return
    except OSError:
        pass
    subprocess.run([sys.executable, "-m", "darkops", "whatsapp-receber", "--arquivo", nome], cwd=config.RAIZ,
                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ---------- túnel e registro do webhook ----------

CLOUDFLARED = config.RAIZ / "dados" / "bin" / "cloudflared.exe"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def instalar_cloudflared() -> str:
    """Baixa o cloudflared oficial (releases da Cloudflare no GitHub) e só aceita se a assinatura digital do
    Windows for válida e da Cloudflare."""
    CLOUDFLARED.parent.mkdir(parents=True, exist_ok=True)
    temp = CLOUDFLARED.with_suffix(".baixando")
    with urllib.request.urlopen(CLOUDFLARED_URL, timeout=300) as r, temp.open("wb") as f:
        shutil.copyfileobj(r, f)
    assinatura = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 f"$s = Get-AuthenticodeSignature -LiteralPath '{temp}'; "
                                 "\"$($s.Status)|$($s.SignerCertificate.Subject)\""],
                                capture_output=True, text=True).stdout.strip()
    if not assinatura.startswith("Valid|") or "Cloudflare" not in assinatura:
        temp.unlink(missing_ok=True)
        raise SystemExit(f"o cloudflared baixado não tem a assinatura da Cloudflare ({assinatura[:80]}); descartado")
    temp.replace(CLOUDFLARED)
    return str(CLOUDFLARED)


def _cloudflared() -> str | None:
    for caminho in (str(CLOUDFLARED), shutil.which("cloudflared"), r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
                    r"C:\Program Files\cloudflared\cloudflared.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe")):
        if caminho and Path(caminho).exists():
            return caminho
    return None


def _parar_tunel_antigo() -> None:
    pid = ler_estado().get("tunel_pid")
    if pid and os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)


def ligar() -> None:
    """Chamado pelo Estúdio ao abrir: porteiro + túnel + webhook na Meta. Roda em segundo plano."""
    if not recebe_comandos():
        return
    threading.Thread(target=_ligar, daemon=True).start()


_PORTEIRO: ThreadingHTTPServer | None = None


def _ligar() -> None:
    global _PORTEIRO
    _gravar_estado(tunel_ok=False, tunel_erro="")
    verificador()
    if _PORTEIRO is None:  # ligar de novo (troca de configuração) reaproveita o porteiro e refaz só o túnel
        try:
            _PORTEIRO = ThreadingHTTPServer(("127.0.0.1", PORTA_PORTEIRO), _Porteiro)
        except OSError:
            _gravar_estado(tunel_erro="a porta 5680 já está em uso (outro Estúdio aberto?)")
            return
        threading.Thread(target=_PORTEIRO.serve_forever, daemon=True).start()
    exe = _cloudflared()
    if not exe and os.name == "nt":
        try:
            exe = instalar_cloudflared()
        except (SystemExit, OSError) as erro:
            _gravar_estado(tunel_erro=ocultar(f"não consegui instalar o túnel: {erro}")[:300])
            return
    if not exe:
        _gravar_estado(tunel_erro="falta o cloudflared (o túnel da Cloudflare)")
        return
    _parar_tunel_antigo()
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORTA_PORTEIRO}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    _gravar_estado(tunel_pid=proc.pid)
    endereco = None
    inicio = time.time()
    for linha in proc.stderr:
        achado = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linha)
        if achado:
            endereco = achado.group(0)
            break
        if time.time() - inicio > 60:
            break
    if not endereco:
        _gravar_estado(tunel_erro="o túnel da Cloudflare não respondeu; tente de novo em Ajustes")
        return
    threading.Thread(target=lambda: [None for _ in proc.stderr], daemon=True).start()  # esvazia o log do túnel
    time.sleep(4)  # o endereço novo leva uns segundos para valer na internet
    try:
        registrar_webhook(endereco + CAMINHO_WEBHOOK)
        _gravar_estado(tunel=endereco, tunel_ok=True, tunel_erro="")
        print("WhatsApp: comandos ligados")
    except (ErroMeta, OSError) as erro:
        _gravar_estado(tunel_erro=ocultar(str(erro))[:300])
        print(ocultar(f"WhatsApp: não consegui registrar o webhook: {erro}"))


def _token_app() -> str:
    return f"{_env('WHATSAPP_APP_ID')}|{_env('WHATSAPP_APP_SECRET')}"


def registrar_webhook(url: str) -> None:
    """Aponta o webhook do app para o túnel (a Meta confere na hora com um GET) e inscreve o app na conta do
    WhatsApp Business, para as mensagens chegarem."""
    corpo = urllib.parse.urlencode({"object": "whatsapp_business_account", "callback_url": url,
                                    "verify_token": verificador(), "fields": "messages"}).encode()
    for tentativa in range(3):
        try:
            _pedir("POST", f"/{_env('WHATSAPP_APP_ID')}/subscriptions", corpo=corpo,
                   tipo="application/x-www-form-urlencoded", token=_token_app())
            break
        except ErroMeta:
            if tentativa == 2:
                raise
            time.sleep(6)
    for waba in contas_business():
        _pedir("POST", f"/{waba}/subscribed_apps")


def contas_business() -> list[str]:
    """IDs das contas do WhatsApp Business que o token alcança (pelo debug_token do próprio app)."""
    q = urllib.parse.urlencode({"input_token": _env("WHATSAPP_TOKEN")})
    dados = _pedir("GET", f"/debug_token?{q}", token=_token_app()).get("data", {})
    ids = []
    for escopo in dados.get("granular_scopes", []):
        if escopo.get("scope") in ("whatsapp_business_management", "whatsapp_business_messaging"):
            ids += [i for i in escopo.get("target_ids", []) if i not in ids]
    return ids


def testar() -> str:
    """Confere o token e o número e manda uma mensagem de teste."""
    if not configurado():
        raise SystemExit("faltam WHATSAPP_TOKEN, WHATSAPP_NUMERO_ID ou WHATSAPP_PARA no .env")
    numero = _pedir("GET", f"/{_env('WHATSAPP_NUMERO_ID')}?fields=display_phone_number,verified_name")
    try:
        _mandar({"type": "text", "text": {"body": "✦ Projeto Canais conectado. Responda *oi* para ver os comandos."}})
    except ErroMeta as erro:
        if erro.codigo != 131047:
            raise SystemExit(str(erro))
        # fora da janela: o modelo hello_world existe em toda conta e abre a conversa
        _mandar({"type": "template", "template": {"name": "hello_world", "language": {"code": "en_US"}}})
    return f"{numero.get('verified_name', '')} ({numero.get('display_phone_number', '')})"
