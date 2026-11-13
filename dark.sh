#!/usr/bin/env sh
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
# Atalho da linha de comando no macOS e no Linux (o mesmo que o dark.ps1 faz no Windows):  ./dark.sh <comando>
cd "$(dirname "$0")" || exit 1
exec ./.venv/bin/python -m darkops "$@"
