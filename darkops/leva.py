"""Levas de vídeos: criar vários de uma vez e reabastecer a fila quando ela ficar curta.

  python -m darkops leva [--quantidade N]      escreve N roteiros com o Claude Code e gera a prévia de cada um
  python -m darkops leva --se-faltar [--fundo] só cria se o perfil pedir reabastecimento e a fila tiver
                                               leva_minimo vídeos ou menos (o n8n chama depois de cada post)

Os roteiros são escritos pelo Claude Code do próprio PC (/escrever-roteiro, com pesquisa e fontes), no nicho,
formato e duração do perfil. Tudo entra na fila sem aprovação: nada vai ao ar antes de você aprovar.
Tudo roda no seu PC, então ele precisa ficar ligado até a leva terminar.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import config

MINUTOS_ROTEIRO = (2, 5)    # Claude pesquisando os fatos e escrevendo, por roteiro
MINUTOS_DESENHO = (2, 5)    # gerador local, por cena desenhada
MINUTOS_CLIPES = (0.5, 1.5)  # busca e download dos clipes de um vídeo
LIMITE_LEVA = 14


def _cenas(dados: dict) -> int:
    """Quantas cenas um vídeo do perfil costuma ter: a duração dividida pelo tempo de cada cena
    (ou o número real, quando o roteiro já existe)."""
    if dados.get("cenas_reais"):
        return int(dados["cenas_reais"])
    return max(math.ceil(dados.get("duracao_s", 60) / max(dados.get("ritmo_corte_s", 4), 6)), 3)


def estimar(dados: dict, quantidade: int) -> dict:
    """Minutos por vídeo e no total (faixa), e o aviso sobre deixar o PC ligado."""
    from .visuais import ESTILOS_IA
    desenhado = dados.get("estilo") in ESTILOS_IA
    render = max(dados.get("duracao_s", 60) / 60, 0.5)  # cerca de 1 min de render por minuto de vídeo
    if desenhado:
        visuais = tuple(_cenas(dados) * m for m in MINUTOS_DESENHO)
    else:
        visuais = MINUTOS_CLIPES
    por_video = tuple(round(r + v + render, 1) for r, v in zip(MINUTOS_ROTEIRO, visuais))
    total = tuple(round(m * quantidade) for m in por_video)
    if desenhado:
        aviso = (f"Cada vídeo tem cerca de {_cenas(dados)} cenas desenhadas no seu PC, que é a parte mais lenta. "
                 "Deixe o computador ligado, na tomada e sem suspender até a leva terminar; "
                 "se ele desligar, a leva para e continua de onde parou na próxima vez.")
    else:
        aviso = ("Os roteiros, a narração e a montagem rodam no seu PC (os clipes vêm da internet). "
                 "Deixe o computador ligado e sem suspender até a leva terminar.")
    return {"por_video": por_video, "total": total, "desenhado": desenhado, "aviso": aviso,
            "texto": f"cerca de {_tempo(total[0])} a {_tempo(total[1])} para {quantidade} vídeo(s)"}


def _tempo(minutos: float) -> str:
    if minutos < 60:
        return f"{round(minutos)} min"
    horas, resto = divmod(round(minutos), 60)
    return f"{horas} h" + (f" {resto} min" if resto else "")


def _claude() -> str | None:
    # o .exe vem antes do .cmd: um .cmd passa pelo cmd.exe, que interpreta & | ^ nos argumentos (BatBadBut)
    return next((str(c) for c in (Path.home() / ".local" / "bin" / "claude.exe",) if c.exists()), None) \
        or shutil.which("claude") \
        or next((str(c) for c in (Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",) if c.exists()), None)


def rodar_claude(pedido: str, ferramentas: tuple[str, ...] = (), timeout: int = 300) -> subprocess.CompletedProcess:
    """Roda o Claude Code sem interação. O pedido vai pela entrada padrão (nunca como argumento: textos vindos da
    internet ou do roteiro não viram comando no cmd.exe). Só as ferramentas listadas são permitidas; o resto é
    negado sozinho no modo -p, sem aceitar edições em qualquer pasta."""
    claude = _claude()
    if not claude:
        raise SystemExit("Claude Code não encontrado: instale em claude.com/claude-code")
    args = [claude, "-p"] + (["--allowedTools", *ferramentas] if ferramentas else [])
    return subprocess.run(args, input=pedido, cwd=config.RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def _escrever_roteiro(perfil, tema: str = "") -> Path | None:
    """Pede ao Claude Code um roteiro novo para o perfil e devolve o arquivo criado na fila.
    Com `tema`, o vídeo é sobre ele (pedido do Novo vídeo); sem, o Claude escolhe um tema forte."""
    from .perfis import resumo_persona
    d = perfil.dados
    persona = resumo_persona(d)
    antes = set(perfil.fila.glob("*.json"))
    existentes = sorted(p.stem for p in [*antes, *perfil.publicados.glob("*.json")])
    pedido = (
        f"Use a skill /escrever-roteiro para escrever UM roteiro novo para o perfil {perfil.id} "
        f"(canal {d['nome']}, nicho: {d.get('nicho') or 'curiosidades'}, formato {d.get('formato', 'vertical')}, "
        f"cerca de {d.get('duracao_s', 60)} segundos). "
        + (f"O tema do vídeo, pedido pelo dono do canal, é: {tema[:200]}. Encontre um ângulo que ainda não exista "
           if tema else "Escolha sozinho um tema forte que ainda não exista ")
        + f"no canal (já existem: {', '.join(existentes[-40:]) or 'nenhum'}). Pesquise os fatos e guarde as fontes. "
        + (f"Personalidade do canal (siga à risca): {persona} " if persona else "")
        + f"Nível de edição do canal: {d.get('edicao', 'pro')}. "
        f"Salve o roteiro em perfis/{perfil.id}/fila/NNN-slug.json (NNN = próximo número da fila), "
        "com \"aprovado\": false, e, se a skill pedir o palco, também o módulo cenas/<slug>.py; nesse caso, teste "
        f"com: .venv\\Scripts\\python.exe -m darkops palco-testar perfis/{perfil.id}/fila/<arquivo>.json "
        "antes de terminar. Não produza o vídeo, não publique nada e não faça commit."
    )
    # o Claude lê páginas da internet: só pode gravar na fila do perfil e em cenas/, e só roda o teste do palco
    fila = f"perfis/{perfil.id}/fila"
    proc = rodar_claude(pedido, (
        "Read", "Glob", "Grep", "WebSearch", "WebFetch", "Skill",
        f"Write({fila}/**)", f"Edit({fila}/**)", "Write(cenas/**)", "Edit(cenas/**)",
        "Bash(.venv/Scripts/python.exe -m darkops palco-testar:*)",
        r"Bash(.venv\Scripts\python.exe -m darkops palco-testar:*)"), timeout=30 * 60)
    novos = sorted(set(perfil.fila.glob("*.json")) - antes)
    if not novos:
        print(f"  o Claude não criou roteiro: {(proc.stdout + proc.stderr).strip()[-400:]}")
        return None
    roteiro = novos[0]
    dados = json.loads(roteiro.read_text(encoding="utf-8"))
    if dados.get("palco") and not (config.RAIZ / dados["palco"]).exists():
        # sem o módulo da cena programada, o vídeo sai com a cena viva (desenho por IA) em vez de quebrar
        print(f"  {dados['palco']} não foi criado; o vídeo usa a cena viva")
        dados.pop("palco")
        roteiro.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return roteiro


def _produzir(perfil, roteiro: Path) -> bool:
    proc = subprocess.run([sys.executable, "-m", "darkops", "--perfil", perfil.id, "fila-produzir", str(roteiro)],
                          cwd=config.RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return proc.returncode == 0


def _vivo(pid: int) -> bool:
    if os.name == "nt":
        saida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                               errors="replace").stdout
        return str(pid) in saida
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def criar(perfil, quantidade: int, tema: str = "") -> list[Path]:
    """Escreve e produz uma leva. Uma trava impede duas levas ao mesmo tempo no mesmo perfil; se o PC desligou
    no meio, a próxima leva primeiro termina as prévias dos roteiros que ficaram sem vídeo."""
    trava = perfil.controle / "leva.trava"
    pendentes_arq = perfil.controle / "leva-pendentes.json"
    perfil.controle.mkdir(parents=True, exist_ok=True)
    if trava.exists():
        pid = int(trava.read_text(encoding="utf-8").strip() or 0)
        if pid and _vivo(pid):
            print("já existe uma leva rodando neste perfil")
            return []
        trava.unlink(missing_ok=True)  # sobra de uma leva interrompida (PC desligado, por exemplo)
    trava.write_text(str(os.getpid()), encoding="utf-8")
    pendentes = [perfil.fila / n for n in json.loads(pendentes_arq.read_text(encoding="utf-8"))]         if pendentes_arq.exists() else []
    pendentes = [r for r in pendentes if r.exists()]

    def anotar():
        pendentes_arq.write_text(json.dumps([r.name for r in pendentes], ensure_ascii=False), encoding="utf-8")

    feitos = []
    try:
        for n in range(1, quantidade + 1):
            if pendentes:
                roteiro = pendentes[0]
                print(f"vídeo {n}/{quantidade}: retomando a prévia de {roteiro.name}", flush=True)
            else:
                print(f"vídeo {n}/{quantidade}: escrevendo o roteiro", flush=True)
                roteiro = _escrever_roteiro(perfil, tema)
                if not roteiro:
                    continue
                pendentes.append(roteiro)
                anotar()
                from .descricao import gerar as gerar_textos
                gerar_textos(perfil, roteiro)  # descrição e tags pela IA, para a revisão já mostrar
                print(f"  roteiro {roteiro.name}; gerando a prévia", flush=True)
            if _produzir(perfil, roteiro):
                feitos.append(roteiro)
            pendentes.remove(roteiro)
            anotar()
    finally:
        trava.unlink(missing_ok=True)
        if not pendentes:
            pendentes_arq.unlink(missing_ok=True)
    registro = perfil.controle / "levas.log"
    with registro.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"quando": time.strftime("%Y-%m-%d %H:%M"), "pedidos": quantidade,
                            "feitos": [p.name for p in feitos]}, ensure_ascii=False) + "\n")
    print(f"leva pronta: {len(feitos)} de {quantidade} vídeo(s) na fila esperando aprovação")
    return feitos


def precisa_reabastecer(perfil) -> bool:
    d = perfil.dados
    return bool(d.get("leva_reabastecer")) and len(list(perfil.fila.glob("*.json"))) <= int(d.get("leva_minimo", 3))


def em_segundo_plano(perfil, quantidade: int) -> None:
    """Dispara a leva num processo separado e volta na hora (o n8n não fica esperando horas)."""
    log = (perfil.controle / "leva-ultima.log").open("w", encoding="utf-8")
    sinais = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen([sys.executable, "-m", "darkops", "--perfil", perfil.id, "leva", "--quantidade", str(quantidade)],
                     cwd=config.RAIZ, stdout=log, stderr=subprocess.STDOUT, creationflags=sinais,
                     env={**os.environ, "PYTHONIOENCODING": "utf-8"})
