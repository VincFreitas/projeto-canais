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

MODELO = config.RAIZ / "n8n" / "workflow.modelo.json"
GERADO = config.RAIZ / "n8n" / "workflow.json"


def _n8n_cmd() -> str | None:
    achado = shutil.which("n8n")
    if achado:
        return achado
    candidato = Path(os.environ.get("APPDATA", ""), "npm", "n8n.cmd")
    return str(candidato) if candidato.exists() else None


def gerar_workflow(importar: bool = False) -> Path:
    texto = MODELO.read_text(encoding="utf-8")
    python = Path(sys.executable)
    # os comandos do workflow rodam no cmd.exe; no JSON a barra invertida vai escapada
    texto = texto.replace("__PASTA__", str(config.RAIZ).replace("\\", "\\\\"))
    texto = texto.replace("__PYTHON__", str(python).replace("\\", "\\\\"))
    json.loads(texto)  # confere se continua JSON válido
    GERADO.write_text(texto, encoding="utf-8")
    print(f"workflow gerado: {GERADO}")
    if importar:
        n8n = _n8n_cmd()
        if not n8n:
            raise SystemExit("n8n não encontrado. Instale com: npm install -g n8n")
        env = {**os.environ, "N8N_DIAGNOSTICS_ENABLED": "false",
               "NODES_EXCLUDE": '["n8n-nodes-base.localFileTrigger"]'}
        proc = subprocess.run([n8n, "import:workflow", f"--input={GERADO}"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)
        print((proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout + proc.stderr).strip() else "")
        if proc.returncode != 0:
            raise SystemExit("falha ao importar no n8n")
        print("Importado. Abra http://localhost:5678 e ative o workflow (chave no canto superior direito).")
    return GERADO


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
    texto = MODELO_WHATSAPP.read_text(encoding="utf-8")
    texto = texto.replace("__PASTA__", str(config.RAIZ).replace("\\", "\\\\"))
    texto = texto.replace("__PYTHON__", str(Path(sys.executable)).replace("\\", "\\\\"))
    json.loads(texto)
    GERADO_WHATSAPP.write_text(texto, encoding="utf-8")
    print(f"workflow gerado: {GERADO_WHATSAPP}")
    if importar:
        n8n = _n8n_cmd()
        if not n8n:
            raise SystemExit("n8n não encontrado. Instale com: npm install -g n8n")
        env = {**os.environ, "N8N_DIAGNOSTICS_ENABLED": "false", "NODES_EXCLUDE": '["n8n-nodes-base.localFileTrigger"]'}
        for args in (["import:workflow", f"--input={GERADO_WHATSAPP}"], ["publish:workflow", "--id=whatsappcanais1"]):
            proc = subprocess.run([n8n, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            if proc.returncode != 0:
                raise SystemExit(f"falha no n8n ({args[0]}): {(proc.stdout + proc.stderr).strip()[-300:]}")
        print("importado e publicado no n8n" + ("" if webhook_whatsapp_ativo() else
              "; o n8n aberto passa a escutar o WhatsApp quando reiniciar"))
    return GERADO_WHATSAPP


def diagnostico() -> list[tuple[str, bool, str]]:
    """(item, pronto?, o que fazer) para cada peça do projeto."""
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
         "Google Cloud: ative a YouTube Data API v3, crie um cliente OAuth 'App para computador' e salve o JSON "
         "em credenciais/client_secret.json"),
        ("Desenho local em pixel art (sd.cpp)", (config.MODELOS / "sd" / "sd-cli.exe").exists()
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
        ("Node.js", bool(shutil.which("node")), "instale o Node.js LTS em nodejs.org"),
        ("n8n", bool(_n8n_cmd()), "npm install -g n8n"),
        ("Workflow do n8n gerado", GERADO.exists(), "python -m darkops n8n-workflow --importar"),
        ("Claude Code (para escrever roteiros)", bool(shutil.which("claude")), "opcional: claude.com/claude-code"),
    ]
    return itens
