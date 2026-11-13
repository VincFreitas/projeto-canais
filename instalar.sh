#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
#
# Instalação no macOS e no Linux (o instalar.ps1 faz o mesmo no Windows). Rode de novo para atualizar o yt-dlp.
#   ./instalar.sh            instala tudo (Python do projeto, pacotes, voz offline, Node, n8n, Claude Code, Chromium)
#   ./instalar.sh --sem-apps só a parte Python
# Precisa de: Python 3.11 ou mais novo, curl e git. Nada é instalado no sistema: tudo fica nesta pasta (dados/apps).
set -euo pipefail
cd "$(dirname "$0")"

falhou() { echo "ERRO: $1" >&2; exit 1; }

PY=""
for c in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  case "$(uname -s)" in
    Darwin) falhou "Python 3.11+ não encontrado. Instale pelo python.org (instalador para macOS) ou: brew install python@3.13" ;;
    *)      falhou "Python 3.11+ não encontrado. Instale com o gerenciador do sistema (ex.: sudo apt install python3 python3-venv)" ;;
  esac
fi

if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv || falhou "não consegui criar o .venv (no Debian/Ubuntu: sudo apt install python3-venv)"
fi
VPY=.venv/bin/python
"$VPY" -m pip install -q --upgrade pip
"$VPY" -m pip install -q --upgrade -r requirements.txt || falhou "pip não instalou os pacotes de requirements.txt"

if [ ! -f assets/vozes/pt_BR-faber-medium.onnx ]; then
  mkdir -p assets/vozes
  "$VPY" -c "from pathlib import Path; from piper.download_voices import download_voice; download_voice('pt_BR-faber-medium', Path('assets/vozes'))" \
    || falhou "não consegui baixar a voz offline (Piper); confira a internet e rode de novo"
fi
[ -f .env ] || cp .env.example .env
chmod 600 .env 2>/dev/null || true
chmod +x dark.sh 2>/dev/null || true

if [ "${1:-}" != "--sem-apps" ]; then
  "$VPY" -m darkops instalar-apps || echo "Algum programa não instalou; veja a mensagem acima e rode de novo."
fi
"$VPY" -m darkops mcp-configurar || true
"$VPY" -m darkops atalhos --area-de-trabalho --menu-iniciar || true
"$VPY" -m darkops diagnostico
echo
echo "Pronto. Abra o Estúdio com: ./dark.sh estudio"
