"""Leva o que está em Ajustes do canal (nome, nicho, descrição e público) para as contas conectadas.

- YouTube, pela API oficial (channels.update, parte brandingSettings): descrição do canal, palavras-chave, idioma e
  país. O nome e o @ não mudam pela API (o YouTube devolve channelTitleUpdateForbidden): só no YouTube Studio.
  Precisa do escopo youtube.force-ssl, o mesmo de "Liberar comentários".
- Instagram: a API com login do Instagram não muda bio, nome nem foto. A bio nova fica pronta para copiar em
  Ajustes, ou a skill /identidade-visual aplica pelo navegador com o dono logado.

Os textos são os da identidade (identidade.textos_padrao, a partir dos Ajustes) e também vão para
perfis/<id>/marca/textos.json, para a aba "Foto, capa e bio" mostrar e aplicar o mesmo texto."""
from __future__ import annotations

import json
import re

from . import identidade, mercados
from .seguranca import ocultar

MAX_PALAVRAS = 500  # limite das palavras-chave do canal no YouTube


def _arquivo(p):
    return p.controle / "contas-atualizadas.json"


def _ler(p) -> dict:
    try:
        return json.loads(_arquivo(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar(p, **mudancas) -> None:
    p.controle.mkdir(parents=True, exist_ok=True)
    _arquivo(p).write_text(json.dumps({**_ler(p), **mudancas}, ensure_ascii=False, indent=2), encoding="utf-8")


def arrobas(p) -> dict:
    """Lê o @ de verdade de cada conta conectada (pode ser diferente do @ do vídeo) e guarda no perfil, para a bio
    do Instagram citar o @ do YouTube e a descrição do YouTube citar o do Instagram sem errar."""
    achados = {}
    if p.token_youtube.exists():
        try:
            from .comentarios import _youtube
            yt, _ = _youtube(p)
            itens = yt.channels().list(part="snippet", mine=True).execute().get("items") or []
            if itens and itens[0]["snippet"].get("customUrl"):
                achados["arroba_youtube"] = "@" + itens[0]["snippet"]["customUrl"].lstrip("@")
        except Exception:  # sem rede ou token vencido: fica o @ que já estava
            pass
    if p.token_instagram.exists():
        try:
            import requests
            from .comentarios import _token_instagram
            r = requests.get("https://graph.instagram.com/v21.0/me", timeout=30,
                             params={"fields": "username", "access_token": _token_instagram(p)}).json()
            if r.get("username"):
                achados["arroba_instagram"] = "@" + r["username"]
        except Exception:
            pass
    if achados and any(p.dados.get(k) != v for k, v in achados.items()):
        p.salvar(achados)
    return achados


def textos(p) -> dict:
    """A descrição do YouTube e a bio do Instagram feitas a partir dos Ajustes de agora (com o @ real de cada conta)."""
    arrobas(p)
    return identidade.textos_padrao(p)


def palavras_chave(d: dict) -> str:
    """Palavras-chave do canal: o nome e o nicho por extenso, separados por espaço (com aspas se tiverem espaço)."""
    termos = [d.get("nome", ""), *re.split(r",\s*|\s+(?:e|and|y|et|und)\s+", identidade.nicho_legivel(d))]
    vistos, saida = set(), []
    for t in (x.strip() for x in termos):
        if t and t.casefold() not in vistos:
            vistos.add(t.casefold())
            saida.append(f'"{t}"' if " " in t else t)
    texto = ""
    for t in saida:
        if len(texto) + len(t) + 1 > MAX_PALAVRAS:
            break
        texto = f"{texto} {t}".strip()
    return texto


def youtube(p, t: dict) -> dict:
    """Atualiza a descrição, as palavras-chave, o idioma e o país do canal. O título fica como está."""
    from .comentarios import _youtube, pode_responder_youtube
    if not pode_responder_youtube(p):
        _gravar(p, youtube_sem_permissao=True)
        return {"ok": False, "texto": "YouTube: falta liberar a edição do canal (botão no alto de Ajustes). "
                                      "Nada foi mudado lá."}
    try:
        yt, _ = _youtube(p)
        canais = yt.channels().list(part="brandingSettings", mine=True).execute().get("items") or []
        if not canais:
            return {"ok": False, "texto": "YouTube: a conta conectada não tem canal."}
        canal = canais[0]
        # a API apaga o que não for mandado de volta: parte do que o canal já tem e muda só estes campos
        marca = canal.get("brandingSettings") or {}
        info = dict(marca.get("channel") or {})
        info.update({"description": t["descricao_youtube"][:1000], "keywords": palavras_chave(p.dados),
                     "defaultLanguage": mercados.de(p.dados)["youtube"],
                     "country": mercados.codigo(p.dados).split("-")[-1].upper()})
        yt.channels().update(part="brandingSettings",
                             body={"id": canal["id"], "brandingSettings": {**marca, "channel": info}}).execute()
    except Exception as erro:  # rede, token vencido ou recusa da API: o Ajustes já foi salvo, só avisa
        return {"ok": False, "texto": f"YouTube: não consegui atualizar o canal ({ocultar(str(erro))[:160]})."}
    _gravar(p, youtube_sem_permissao=False, youtube=t["descricao_youtube"])
    return {"ok": True, "texto": "YouTube: descrição, palavras-chave, idioma e país do canal atualizados."}


def instagram(p, t: dict) -> dict:
    if _ler(p).get("instagram_colada") == t["bio_instagram"]:
        return {"ok": True, "texto": "Instagram: a bio já está em dia."}
    _gravar(p, instagram_bio=t["bio_instagram"])
    return {"ok": True, "texto": "Instagram: a Meta não deixa app mudar a bio; ela está pronta para copiar no alto "
                                 "de Ajustes."}


def _guardar_na_identidade(p, t: dict) -> None:
    """A aba "Foto, capa e bio" passa a mostrar os mesmos textos (as artes não mudam)."""
    arquivo = identidade.pasta(p) / "textos.json"
    if arquivo.exists():
        atual = json.loads(arquivo.read_text(encoding="utf-8"))
        atual.update({"bio_instagram": t["bio_instagram"], "descricao_youtube": t["descricao_youtube"]})
        arquivo.write_text(json.dumps(atual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def atualizar(p) -> list[dict]:
    """Leva os Ajustes para cada conta conectada e devolve uma frase por conta."""
    t = textos(p)
    _guardar_na_identidade(p, t)
    resultados = []
    if p.dados.get("youtube", True) and p.token_youtube.exists():
        resultados.append(youtube(p, t))
    if p.dados.get("instagram", True) and p.token_instagram.exists():
        resultados.append(instagram(p, t))
    return resultados


def instagram_feito(p) -> None:
    estado = _ler(p)
    _gravar(p, instagram_colada=estado.get("instagram_bio", ""), instagram_bio="")


def situacao(p) -> dict:
    """O que a tela de Ajustes mostra: contas conectadas, falta de permissão no YouTube e bio a colar."""
    from .comentarios import pode_responder_youtube
    estado = _ler(p)
    yt = bool(p.dados.get("youtube", True) and p.token_youtube.exists())
    ig = bool(p.dados.get("instagram", True) and p.token_instagram.exists())
    return {"youtube": yt, "instagram": ig,
            # some sozinho depois que o dono libera (o token novo já tem a permissão)
            "youtube_sem_permissao": yt and bool(estado.get("youtube_sem_permissao")) and not pode_responder_youtube(p),
            "instagram_bio": estado.get("instagram_bio", "") if ig else ""}
