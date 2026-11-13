# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Vitrine: os números reais do canal de teste do autor no README ("Feito com o Projeto Canais") e no site (#feito),
atualizados no GitHub ao ligar o PC e uma vez por dia (pedido do dono em 2026-11-13).

Só roda no PC do autor: precisa do perfil da Pulga do Saber (perfis/ fica fora do Git) com as contas conectadas e de
um clone do repositório com permissão de envio. Os números vêm das APIs oficiais (estatisticas.coletar).

O commit é montado direto sobre o origin/main, sem tocar na pasta de trabalho (onde pode haver trabalho em andamento):
lê o README e o site do origin/main, troca só os números, a data e a idade do canal, grava um commit novo com esses dois
arquivos e envia. Nada muda: nada é enviado. Se a pasta local estava igual ao origin/main, ela avança junto."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import config, sistema
from .aparencia import PULGA
from .repositorio import avancar_local
from .repositorio import git as _git
from .seguranca import ocultar

ARQUIVOS = ("README.md", "site/index.html")
RAMO = "main"
BRASILIA = ZoneInfo("America/Sao_Paulo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
_EXTENSO = {1: ("um", "uma"), 2: ("dois", "duas"), 3: ("três",) * 2, 4: ("quatro",) * 2, 5: ("cinco",) * 2,
            6: ("seis",) * 2, 7: ("sete",) * 2, 8: ("oito",) * 2, 9: ("nove",) * 2, 10: ("dez",) * 2,
            11: ("onze",) * 2, 12: ("doze",) * 2}




def _perfil():
    from .perfis import Perfil
    pasta = config.RAIZ / "perfis" / PULGA
    if not (pasta / "perfil.json").exists():
        return None
    p = Perfil(PULGA)
    return p if p.token_youtube.exists() or p.token_instagram.exists() else None


def disponivel() -> bool:
    """PC do autor: tem a Pulga conectada e um clone do git com o origin no GitHub."""
    if not (config.RAIZ / ".git").exists() or not _perfil():
        return False
    origem = _git("remote", "get-url", "origin").stdout.strip()
    return "github.com" in origem


def ao_ligar() -> bool:
    """O PC ligou depois da última vez que a vitrine rodou (o Estúdio abre no logon)?"""
    from .rotinas import estado
    if not disponivel():
        return False
    ligado = sistema.ligado_desde()
    return bool(ligado) and ligado > estado("vitrine").get("quando_ts", 0)


# ---------- números ----------

def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _data_extenso(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _quantos(n: int, singular: str, plural: str, feminino: bool) -> str:
    palavra = _EXTENSO.get(n, (str(n),) * 2)[1 if feminino else 0]
    return f"{palavra} {singular if n == 1 else plural}"


def idade(nasceu: date, hoje: date) -> str:
    """"três semanas", "dez dias", "dois meses"..."""
    dias = (hoje - nasceu).days
    if dias < 14:
        return _quantos(max(dias, 1), "dia", "dias", False)
    if dias < 63:
        return _quantos(dias // 7, "semana", "semanas", True)
    if dias < 730:
        return _quantos(dias // 30, "mês", "meses", False)
    return _quantos(dias // 365, "ano", "anos", False)


def _publicado(texto: str) -> date | None:
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (quando.astimezone(BRASILIA) if quando.tzinfo else quando).date()


def nascimento(texto_readme: str) -> date | None:
    """A data em que o canal nasceu, como o README já diz ("O canal nasceu em 20 de outubro de 2026")."""
    achado = re.search(r"O canal nasceu em (\d{1,2}) de (\w+) de (\d{4})", texto_readme)
    if not achado or achado.group(2) not in MESES:
        return None
    return date(int(achado.group(3)), MESES.index(achado.group(2)) + 1, int(achado.group(1)))


def numeros(dados: dict, hoje: date) -> dict:
    """Do estatisticas.json para o que a vitrine mostra, por plataforma."""
    saida, datas = {}, []
    for nome in ("youtube", "instagram"):
        p = (dados.get("plataformas") or {}).get(nome)
        if not p or not p.get("videos"):
            return {}
        videos = p["videos"]
        datas += [d for d in (_publicado(v.get("publicado")) for v in videos) if d]
        saida[nome] = {"videos": p["conta"].get("videos") or len(videos),
                       "visualizacoes": sum(v.get("visualizacoes") or 0 for v in videos),
                       "curtidas": sum(v.get("curtidas") or 0 for v in videos),
                       "seguidores": p["conta"].get("seguidores") or 0,
                       "mais_visto": max((v.get("visualizacoes") or 0) for v in videos)}
    saida["hoje"] = hoje
    saida["nasceu"] = min(datas) if datas else hoje
    return saida


# ---------- textos ----------

def _linha(texto: str, rotulo: str, yt: str, ig: str) -> str:
    padrao = re.compile(rf"^\| {re.escape(rotulo)} \|[^\n]*\|[^\n]*\|$", re.M)
    if not padrao.search(texto):
        raise ValueError(f"linha '{rotulo}' sumiu do README")
    return padrao.sub(f"| {rotulo} | {yt} | {ig} |", texto, count=1)


def readme(texto: str, n: dict) -> str:
    yt, ig = n["youtube"], n["instagram"]
    texto, trocas = re.subn(r"\| Números reais \([^)]*\) \|",
                            f"| Números reais ({_data_extenso(n['hoje'])}, pelas APIs oficiais) |", texto, count=1)
    if not trocas:
        raise ValueError("cabeçalho da tabela de números sumiu do README")
    texto = _linha(texto, "Vídeos publicados", str(yt["videos"]), str(ig["videos"]))
    texto = _linha(texto, "Visualizações", _milhar(yt["visualizacoes"]), _milhar(ig["visualizacoes"]))
    texto = _linha(texto, "Curtidas", _milhar(yt["curtidas"]), _milhar(ig["curtidas"]))
    texto = _linha(texto, "Inscritos e seguidores", _milhar(yt["seguidores"]), _milhar(ig["seguidores"]))
    texto = _linha(texto, "Vídeo mais visto", f"{_milhar(yt['mais_visto'])} visualizações",
                   f"{_milhar(ig['mais_visto'])} visualizações")
    return re.sub(r"O canal nasceu em [^,]+, então tinha [^.]+ nessa contagem\.",
                  f"O canal nasceu em {_data_extenso(n['nasceu'])}, então tinha {idade(n['nasceu'], n['hoje'])} "
                  "nessa contagem.", texto, count=1)


def site(texto: str, n: dict) -> str:
    yt, ig = n["youtube"], n["instagram"]
    texto, a = re.subn(r"<b>[\d.]+</b><span>vídeos no YouTube e no Instagram</span>",
                       f"<b>{_milhar(yt['videos'] + ig['videos'])}</b><span>vídeos no YouTube e no Instagram</span>",
                       texto, count=1)
    texto, b = re.subn(r"<b>[\d.]+</b><span>visualizações em [^<]+</span>",
                       f"<b>{_milhar(yt['visualizacoes'] + ig['visualizacoes'])}</b><span>visualizações em "
                       f"{idade(n['nasceu'], n['hoje'])}</span>", texto, count=1)
    texto, c = re.subn(r"Números reais de [^,]+, pelas APIs oficiais\.",
                       f"Números reais de {_data_extenso(n['hoje'])}, pelas APIs oficiais.", texto, count=1)
    if not (a and b and c):
        raise ValueError("os números do site (#feito) mudaram de formato")
    return texto


# ---------- envio ----------

def _commit(base: str, novos: dict[str, str], mensagem: str) -> str:
    """Commit com os arquivos novos sobre `base`, por um índice temporário (a pasta de trabalho não muda)."""
    with tempfile.TemporaryDirectory(prefix="vitrine-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
        _git("read-tree", base, env=env).check_returncode()
        for caminho, texto in novos.items():
            # em bytes: no Windows, o modo texto trocaria cada quebra de linha por CRLF dentro do repositório
            blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=config.RAIZ, capture_output=True,
                                  input=texto.encode("utf-8"), timeout=60, **sistema.sem_janela()).stdout.decode().strip()
            _git("update-index", "--cacheinfo", f"100644,{blob},{caminho}", env=env).check_returncode()
        arvore = _git("write-tree", env=env).stdout.strip()
    return _git("commit-tree", arvore, "-p", base, "-m", mensagem).stdout.strip()


def atualizar() -> dict:
    """Coleta os números, troca no README e no site do origin/main e envia. Devolve o resultado da rotina."""
    from . import estatisticas
    perfil = _perfil()
    if not perfil or not disponivel():
        return {"situacao": "ok", "texto": "Só roda no PC do autor (canal de teste conectado).", "itens": []}
    hoje = datetime.now(BRASILIA).date()
    n = numeros(estatisticas.coletar(perfil), hoje)
    if not n:
        return {"situacao": "aviso", "texto": "As APIs não devolveram os números do YouTube e do Instagram agora; "
                                               "tento de novo mais tarde.", "itens": [], "tentar_em_h": 2}
    envio = None
    for _ in range(2):  # se alguém enviou no meio, busca de novo e refaz
        busca = _git("fetch", "--quiet", "origin", RAMO)
        if busca.returncode != 0:
            return {"situacao": "aviso", "texto": f"Sem acesso ao GitHub agora: {ocultar(busca.stderr.strip())[-200:]}",
                    "itens": [], "tentar_em_h": 2}
        base = _git("rev-parse", f"origin/{RAMO}").stdout.strip()
        atuais = {c: _git("show", f"{base}:{c}").stdout for c in ARQUIVOS}
        n["nasceu"] = nascimento(atuais["README.md"]) or n["nasceu"]  # a data do README vale (criação do canal)
        novos = {"README.md": readme(atuais["README.md"], n), "site/index.html": site(atuais["site/index.html"], n)}
        novos = {c: t for c, t in novos.items() if t != atuais[c]}
        if not novos:
            return {"situacao": "ok", "texto": "Os números no GitHub já estão em dia.", "itens": []}
        commit = _commit(base, novos, f"Números da Pulga do Saber em {hoje:%d/%m/%Y}")
        envio = _git("push", "origin", f"{commit}:refs/heads/{RAMO}")
        if envio.returncode == 0:
            avancar_local(base, commit)
            yt, ig = n["youtube"], n["instagram"]
            return {"situacao": "ok", "itens": [],
                    "texto": f"README e site atualizados no GitHub: {_milhar(yt['visualizacoes'])} visualizações no "
                             f"YouTube e {_milhar(ig['visualizacoes'])} no Instagram ({hoje:%d/%m/%Y})."}
    erro = ocultar(envio.stderr.strip())[-200:] if envio else "?"
    return {"situacao": "aviso", "texto": f"O GitHub recusou o envio: {erro}",
            "itens": [], "tentar_em_h": 2}

