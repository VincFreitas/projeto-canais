# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Excluir um canal: apaga tudo dele no app e corta o acesso do app às contas que ele conectou.

Decisão do dono em 2026-11-08: o YouTube e o Instagram não deixam um app apagar o canal ou a conta pela API (só o
dono faz isso no site deles). Então "Excluir canal":
- revoga o token do YouTube no Google (o app perde o acesso na hora);
- apaga o token do Instagram daqui (a Instagram Login não tem revogação pela API: o dono remove o app em
  "Apps e sites" do Instagram, link no aviso);
- tira o canal da nuvem (arquivos e vídeos no repositório de fila, o Secret com as credenciais e a agenda);
- apaga a pasta do canal (perfil, fila, publicados, controle, credenciais) e os vídeos gerados só para ele em saida/.
Os vídeos já publicados continuam no ar; o aviso traz os links oficiais para apagar o canal e a conta."""
import json
import shutil
from pathlib import Path

import requests

from . import cofre, config
from .seguranca import ocultar

LINKS = {
    "youtube_excluir": "https://www.youtube.com/account_advanced",
    "google_acessos": "https://myaccount.google.com/connections",
    "instagram_acessos": "https://www.instagram.com/accounts/manage_access/",
    "instagram_excluir": "https://accountscenter.instagram.com/personal_info/account_ownership_and_control/",
}


def _slugs(perfil) -> set[str]:
    slugs = set()
    for pasta in (perfil.pasta / "fila", perfil.pasta / "publicados"):
        for arquivo in pasta.glob("*.json") if pasta.exists() else []:
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                dados = {}
            slugs.add(dados.get("slug") or arquivo.stem)
    return {s for s in slugs if s}


def _arquivos_saida(perfil) -> list[Path]:
    """Vídeos, thumbnails e carrosséis em saida/ que são só deste canal (slug que nenhum outro canal usa)."""
    from .perfis import listar
    outros = set()
    for p in listar():
        if p.id != perfil.id:
            outros |= _slugs(p)
    achados = []
    for slug in _slugs(perfil) - outros:
        achados += [a for a in config.SAIDA.glob(f"{slug}*")
                    if a.name == slug or a.name.startswith((f"{slug}-", f"{slug}."))]
    return achados


def plano(perfil) -> dict:
    """O que a exclusão vai fazer, para o aviso antes de confirmar."""
    from . import nuvem
    contar = lambda pasta: len(list(pasta.glob("*.json"))) if pasta.exists() else 0  # noqa: E731
    return {"nome": perfil.dados.get("nome") or perfil.id, "youtube": perfil.token_youtube.exists(),
            "instagram": perfil.token_instagram.exists(), "nuvem": nuvem.configurada(),
            "na_fila": contar(perfil.pasta / "fila"), "publicados": contar(perfil.pasta / "publicados"),
            "arquivos_saida": len(_arquivos_saida(perfil)), "links": LINKS}


def _revogar_youtube(perfil) -> str:
    if not perfil.token_youtube.exists():
        return "YouTube: não estava conectado"
    dados = json.loads(cofre.ler(perfil.token_youtube))
    token = dados.get("refresh_token") or dados.get("token")
    if not token:
        return "YouTube: token sem chave para revogar (apagado daqui)"
    # o token vai no corpo do POST, nunca na URL; revogar o refresh_token derruba também os de acesso
    r = requests.post("https://oauth2.googleapis.com/revoke", data={"token": token}, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code == 200:
        return "YouTube: acesso do app revogado no Google"
    if r.status_code == 400:
        return "YouTube: o acesso já estava revogado"
    return f"YouTube: o Google respondeu {r.status_code}; remova o app em {LINKS['google_acessos']}"


def _tirar_da_nuvem(perfil) -> str:
    from . import nuvem
    from .perfis import listar
    if not nuvem.configurada():
        return "Nuvem: não estava ligada"
    nuvem.remover_perfil(perfil.id)
    nuvem.atualizar_agenda([p for p in listar() if p.id != perfil.id and p.dados.get("ativo")])
    return "Nuvem: arquivos, vídeos e credenciais do canal apagados do repositório de fila"


def excluir(perfil) -> list[str]:
    """Faz a exclusão e devolve o que aconteceu em cada parte. Falha numa conta não impede o resto."""
    from .perfis import PERFIS
    pasta = perfil.pasta.resolve()
    if pasta.parent != PERFIS.resolve() or not (pasta / "perfil.json").exists():
        raise SystemExit("canal não encontrado")
    resultado = []
    for passo in (_revogar_youtube, _tirar_da_nuvem):
        try:
            resultado.append(passo(perfil))
        except (SystemExit, OSError, ValueError, KeyError, requests.RequestException) as erro:
            resultado.append(f"{passo.__name__.strip('_').replace('_', ' ')}: falhou ({ocultar(str(erro))[:160]})")
    if perfil.token_instagram.exists():
        resultado.append("Instagram: token apagado daqui; para cortar o acesso também no Instagram, remova o app "
                         "em Apps e sites")
    apagados = 0
    for arquivo in _arquivos_saida(perfil):
        try:
            shutil.rmtree(arquivo) if arquivo.is_dir() else arquivo.unlink()
            apagados += 1
        except OSError:
            pass
    shutil.rmtree(pasta)
    resultado.append(f"App: canal apagado ({apagados} arquivo(s) de vídeo, thumbnail ou carrossel em saida/)")
    return resultado
