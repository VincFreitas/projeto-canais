# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Ajuda de instalação: gera o workflow do n8n para esta pasta e confere o que falta configurar.

  python -m darkops diagnostico           lista o que está pronto e o que falta, com o próximo passo
  python -m darkops n8n-workflow          gera n8n/workflow.json com a pasta e o Python deste PC
  python -m darkops n8n-workflow --importar   e importa no n8n (precisa do n8n instalado)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config
from .apps import env_node, node_exe

MODELO = config.RAIZ / "n8n" / "workflow.modelo.json"
GERADO = config.RAIZ / "n8n" / "workflow.json"


def _n8n_virtual() -> Path | None:
    """n8n instalado pelo terminal de dentro do app Claude (pacote MSIX): o Windows desvia o AppData/Roaming desse
    terminal para a pasta do pacote, e fora do Claude (atalho, Explorer, n8n agendado) o npm global parece vazio."""
    pacotes = Path(os.environ.get("LOCALAPPDATA", ""), "Packages")
    if not pacotes.exists():
        return None
    return next((c for c in pacotes.glob("Claude_*/LocalCache/Roaming/npm/n8n.cmd") if c.exists()), None)


def _n8n_cmd() -> str | None:
    from .apps import N8N_CMD
    if N8N_CMD.exists():  # o do projeto (instalar-apps) vem primeiro: é o que todo processo enxerga
        return str(N8N_CMD)
    achado = shutil.which("n8n")
    if achado:
        return achado
    candidato = Path(os.environ.get("APPDATA", ""), "npm", "n8n.cmd")
    if candidato.exists():
        return str(candidato)
    virtual = _n8n_virtual()
    return str(virtual) if virtual else None


def n8n_so_no_claude() -> bool:
    """O n8n só existe na pasta virtual do app Claude: funciona, mas some se o Claude for desinstalado."""
    from .apps import N8N_CMD
    if N8N_CMD.exists():
        return False
    real = Path(os.environ.get("APPDATA", ""), "npm", "n8n.cmd")
    # dentro do terminal do Claude o caminho "real" também existe, mas aponta (resolve) para a pasta do pacote
    instalado_de_verdade = real.exists() and "Packages" not in str(real.resolve())
    return bool(_n8n_virtual()) and not instalado_de_verdade


def _preencher(texto: str, windows: bool | None = None) -> str:
    """Troca __PASTA__ e __PYTHON__ do modelo do workflow pelos caminhos deste PC, no formato do shell do n8n."""
    python = Path(sys.executable)
    if os.name == "nt" if windows is None else windows:
        # os comandos do workflow rodam no cmd.exe; no JSON a barra invertida vai escapada
        texto = texto.replace("__PASTA__", str(config.RAIZ).replace("\\", "\\\\"))
        return texto.replace("__PYTHON__", str(python).replace("\\", "\\\\"))
    # macOS e Linux: /bin/sh, sem o /d do cmd.exe; caminho entre aspas simples (aceita espaço)
    aspas = lambda p: json.dumps("'" + str(p).replace("'", "'\\''") + "'")[1:-1]  # noqa: E731
    texto = texto.replace("cd /d __PASTA__", "cd " + aspas(config.RAIZ)).replace("__PASTA__", aspas(config.RAIZ))
    return texto.replace("__PYTHON__", aspas(python))


def gerar_workflow(importar: bool = False) -> Path:
    texto = _preencher(MODELO.read_text(encoding="utf-8"))
    json.loads(texto)  # confere se continua JSON válido
    GERADO.write_text(texto, encoding="utf-8")
    print(f"workflow gerado: {GERADO}")
    if importar:
        n8n = _n8n_cmd()
        if not n8n:
            raise SystemExit("n8n não encontrado. Instale com: npm install -g n8n")
        env = {**env_node(), "N8N_DIAGNOSTICS_ENABLED": "false",
               "NODES_EXCLUDE": '["n8n-nodes-base.localFileTrigger"]'}
        # importar deixa o workflow desligado: publica em seguida, senão nada posta e ninguém percebe
        for args in (["import:workflow", f"--input={GERADO}"], ["publish:workflow", f"--id={ID_POSTAGEM}"]):
            proc = subprocess.run([n8n, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            if proc.returncode != 0:
                raise SystemExit(f"falha no n8n ({args[0]}): {(proc.stdout + proc.stderr).strip()[-300:]}")
        print("importado e ligado no n8n" + _reiniciar_se_aberto())
    return GERADO


def _reiniciar_se_aberto() -> str:
    """O n8n aberto só passa a seguir um workflow publicado pela linha de comando depois de reiniciar."""
    from .app import n8n_ligado, reiniciar_n8n
    if not n8n_ligado():
        return " (vale quando o n8n abrir)"
    if reiniciar_n8n() == "perto-do-horario":
        return "; perto das 12h/19h o n8n não reinicia: reabra o Estúdio depois do horário para valer"
    return "; o n8n está reiniciando para valer (1 a 3 min)"


ID_POSTAGEM = "516k0cfwhvZqU0cp"  # o "id" de n8n/workflow.modelo.json


def workflow_ativo(wid: str) -> bool | None:
    """O workflow está ligado no n8n deste PC? None = n8n ainda sem banco (nunca abriu)."""
    import sqlite3
    pasta = Path(os.environ.get("N8N_USER_FOLDER") or Path.home()) / ".n8n" / "database.sqlite"
    if not pasta.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{pasta}?mode=ro", uri=True, timeout=2)
        try:
            linha = con.execute("select active from workflow_entity where id = ?", (wid,)).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return bool(linha and linha[0])


MODELO_WHATSAPP = config.RAIZ / "n8n" / "whatsapp.modelo.json"
GERADO_WHATSAPP = config.RAIZ / "n8n" / "whatsapp.json"


def webhook_whatsapp_ativo() -> bool:
    """O n8n já escuta o webhook do WhatsApp? (um teste vazio que o whatsapp-receber ignora)"""
    import urllib.request
    from .whatsapp import N8N_WEBHOOK
    req = urllib.request.Request(N8N_WEBHOOK, data=b'{"arquivo": "verificar"}',
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status < 300
    except OSError:
        return False


def gerar_workflow_whatsapp(importar: bool = False) -> Path:
    """Workflow que recebe os comandos do WhatsApp e manda o resumo das 21h. Importa e publica no n8n."""
    texto = _preencher(MODELO_WHATSAPP.read_text(encoding="utf-8"))
    json.loads(texto)
    GERADO_WHATSAPP.write_text(texto, encoding="utf-8")
    print(f"workflow gerado: {GERADO_WHATSAPP}")
    if importar:
        n8n = _n8n_cmd()
        if not n8n:
            raise SystemExit("n8n não encontrado. Instale com: npm install -g n8n")
        env = {**env_node(), "N8N_DIAGNOSTICS_ENABLED": "false", "NODES_EXCLUDE": '["n8n-nodes-base.localFileTrigger"]'}
        for args in (["import:workflow", f"--input={GERADO_WHATSAPP}"], ["publish:workflow", "--id=whatsappcanais1"]):
            proc = subprocess.run([n8n, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            if proc.returncode != 0:
                raise SystemExit(f"falha no n8n ({args[0]}): {(proc.stdout + proc.stderr).strip()[-300:]}")
        print("importado e publicado no n8n" + ("" if webhook_whatsapp_ativo() else
              "; o n8n aberto passa a escutar o WhatsApp quando reiniciar"))
    return GERADO_WHATSAPP


def diagnostico() -> list[tuple[str, bool, str]]:
    """(item, pronto?, o que fazer) para cada peça do projeto."""
    from .leva import _claude
    from .perfis import listar
    env = {}
    arquivo_env = config.RAIZ / ".env"
    if arquivo_env.exists():
        for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                env[k.strip()] = v.strip()
    perfis = listar()
    itens = [
        ("Python e dependências", True, ""),
        ("Arquivo .env", arquivo_env.exists(), "copie .env.example para .env (o instalador faz isso)"),
        ("Voz offline (Piper)", any((config.RAIZ / "assets" / "vozes").glob("*.onnx")),
         "rode: powershell -ExecutionPolicy Bypass -File instalar.ps1"),
        ("Voz Azure (recomendado)", bool(env.get("AZURE_SPEECH_KEY")),
         "crie um recurso Speech F0 no portal.azure.com e cole a chave no Estúdio (Conexões)"),
        ("Imagens (Pixabay ou Pexels)", bool(env.get("PIXABAY_API_KEY") or env.get("PEXELS_API_KEY")),
         "pegue a chave grátis em pixabay.com/api/docs e cole no Estúdio"),
        ("App OAuth do Google (YouTube)", (config.RAIZ / "credenciais" / "client_secret.json").exists(),
         "Google Cloud: ative a YouTube Data API v3, crie um cliente OAuth 'App para computador' e baixe o JSON "
         "(o Estúdio pega sozinho da pasta Downloads, ou rode pegar-app-google)"),
        ("Desenho local em pixel art (sd.cpp)", (config.MODELOS / "sd" / ("sd-cli.exe" if os.name == "nt" else "sd-cli")).exists()
         and (config.MODELOS / "z_image_turbo-Q4_K.gguf").exists(),
         "opcional: veja 'Estilo pixel art' em docs/roteiro.md; sem ele as cenas usam Pexels/Pixabay"),
        ("Pelo menos um perfil", bool(perfis), "crie no Estúdio: python -m darkops estudio"),
    ]
    for p in perfis:
        itens.append((f"YouTube do perfil {p.id}", p.token_youtube.exists() or not p.dados.get("youtube", True),
                      "Estúdio > Conexões > Conectar YouTube"))
        itens.append((f"Instagram do perfil {p.id}", p.token_instagram.exists() or not p.dados.get("instagram", True),
                      "Estúdio > Conexões > colar o token do app da Meta"))
        ident = p.dados.get("identidade") or {}
        faltam = [n for n in ("youtube", "instagram") if p.dados.get(n, True) and n not in ident.get("aplicada", {})]
        itens.append((f"Identidade visual do perfil {p.id}", bool(ident.get("aprovada")) and not faltam,
                      "opcional: Estúdio > Identidade para aprovar, depois /identidade-visual no Claude"))
    itens += [
        ("Node.js", bool(node_exe()), "python -m darkops instalar-apps"),
        ("n8n", bool(_n8n_cmd()), "python -m darkops instalar-apps (instala o Node.js e o n8n na pasta do projeto)"),
        ("n8n instalado fora do app Claude", not n8n_so_no_claude(),
         "o n8n foi instalado pelo terminal do app Claude e só existe na pasta dele (some se o Claude for desinstalado). "
         "Rode: python -m darkops instalar-apps (instala na pasta do projeto, visível para todo o Windows)"),
        ("Postagem automática ligada no n8n", bool(workflow_ativo(ID_POSTAGEM)),
         "python -m darkops n8n-workflow --importar (importa, liga e reinicia o n8n)"),
        ("Claude Code (escreve os roteiros)", bool(_claude()),
         "necessário: python -m darkops instalar-apps (instalador oficial) e depois o login, rodando: claude"),
    ]
    return itens
