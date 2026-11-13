# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Gera o mesmo trecho em cada motor de voz disponível, para ouvir lado a lado.

  python -m darkops comparar-vozes [--texto "..."]   grava saida/vozes-teste/<motor>.wav|mp3 e um resumo

Motor sem chave ou sem instalação é pulado com o motivo. Nada vai para a fila nem para o canal.
"""
import json
import shutil
import time

import requests

from . import config, narracao
from .seguranca import ocultar

TEXTO = ("Em 1901, mergulhadores encontraram no fundo do mar Egeu um bloco de bronze corroído. "
         "Ninguém imaginava que, dentro dele, havia engrenagens capazes de prever eclipses. "
         "Mais de dois mil anos depois, a máquina de Anticítera ainda guarda um segredo.")


def comparar(texto: str = TEXTO) -> list[dict]:
    pasta = config.RAIZ / "saida" / "vozes-teste"
    shutil.rmtree(pasta, ignore_errors=True)
    pasta.mkdir(parents=True)
    resultados = []
    for motor in ("azure", "edge", "piper", "chirp", "gemini", "chatterbox", "elevenlabs"):
        inicio = time.time()
        try:
            audio, _ = narracao.MOTORES[motor](texto, narracao.voz_padrao(motor, "pt"), "+0%", pasta / motor)
            resultados.append({"motor": motor, "arquivo": str(audio.relative_to(config.RAIZ)),
                               "segundos_para_gerar": round(time.time() - inicio, 1)})
        except (SystemExit, ConnectionError, requests.RequestException, KeyError, OSError) as erro:
            resultados.append({"motor": motor, "pulado": ocultar(str(erro))[:300]})
        for sobra in pasta.glob(f"{motor}.*"):  # marcas de tempo e arquivo vazio de motor que falhou
            if sobra.suffix == ".json" or sobra.stat().st_size == 0:
                sobra.unlink()
    (pasta / "resumo.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultados
