# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Fontes em qualquer sistema. O código desenha com as fontes do Windows (C:/Windows/Fonts/arialbd.ttf, segoeui.ttf,
consola.ttf...). No macOS e no Linux esses arquivos não existem: aqui cada uma vira a equivalente do sistema (Arial
do macOS, DejaVu ou Liberation no Linux) e, sem nenhuma, a fonte padrão do Pillow no tamanho pedido.

`instalar()` (chamado pelo config) troca o ImageFont.truetype por uma versão que faz essa tradução só quando o
arquivo pedido não existe. No Windows nada muda."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_FORTE = ["Arial Black.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf",
          "FreeSansBold.ttf", "Ubuntu-B.ttf"]
_NORMAL = ["Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf", "FreeSans.ttf",
           "Ubuntu-R.ttf"]
_MONO = ["Menlo.ttc", "Courier New.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", "NotoSansMono-Regular.ttf"]
_MONO_FORTE = ["Courier New Bold.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"] + _MONO
_SERIFA = ["Georgia Bold.ttf", "Times New Roman Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]
EQUIVALENTES = {
    "ariblk.ttf": _FORTE, "arialbd.ttf": ["Arial Bold.ttf"] + _FORTE, "seguibl.ttf": _FORTE, "segoeuib.ttf": _FORTE,
    "impact.ttf": ["Impact.ttf"] + _FORTE, "verdanab.ttf": ["Verdana Bold.ttf"] + _FORTE,
    "bahnschrift.ttf": _FORTE, "arial.ttf": _NORMAL, "segoeui.ttf": _NORMAL, "verdana.ttf": ["Verdana.ttf"] + _NORMAL,
    "consola.ttf": _MONO, "consolab.ttf": _MONO_FORTE, "georgiab.ttf": _SERIFA, "timesbd.ttf": _SERIFA,
    "comic.ttf": _NORMAL, "comicbd.ttf": _FORTE,
}
PASTAS = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts"), Path("/Library/Fonts"),
          Path.home() / "Library" / "Fonts", Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
          Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts"]


@lru_cache(maxsize=1)
def _no_sistema() -> dict[str, str]:
    achadas = {}
    for pasta in PASTAS:
        if pasta.is_dir():
            for arquivo in pasta.rglob("*"):
                if arquivo.suffix.lower() in (".ttf", ".ttc", ".otf"):
                    achadas.setdefault(arquivo.name.lower(), str(arquivo))
    return achadas


def resolver(pedida) -> str | None:
    """O caminho de uma fonte que existe neste sistema para o arquivo pedido (ou None)."""
    if not isinstance(pedida, (str, os.PathLike)):
        return None
    caminho = Path(pedida)
    if caminho.exists():
        return str(caminho)
    sistema = _no_sistema()
    nome = caminho.name.lower()
    for candidato in [caminho.name] + EQUIVALENTES.get(nome, _FORTE if "bd" in nome or "bl" in nome else _NORMAL):
        if candidato.lower() in sistema:
            return sistema[candidato.lower()]
    return None


def instalar() -> None:
    if os.name == "nt":
        return
    try:
        from PIL import ImageFont
    except ImportError:
        return
    if getattr(ImageFont.truetype, "_projeto_canais", False):
        return
    original = ImageFont.truetype

    def truetype(font=None, size=10, *args, **kwargs):
        try:
            return original(font, size, *args, **kwargs)
        except OSError:
            achada = resolver(font)
            if achada:
                return original(achada, size, *args, **kwargs)
            return ImageFont.load_default(size)  # fonte padrão do Pillow, no tamanho pedido

    truetype._projeto_canais = True  # type: ignore[attr-defined]
    ImageFont.truetype = truetype
