# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Projeto Canais: pesquisa, produção e postagem de canais dark. Autor: Vinicius Freitas."""
__version__ = "0.68.4"

from .sistema import esconder_janelas as _esconder_janelas

_esconder_janelas()  # no pythonw (Estúdio, rotinas), node/ffmpeg/powershell não abrem janela de terminal
