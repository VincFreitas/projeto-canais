# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Ponte para o Chatterbox Multilingual, que roda no ambiente separado dados/apps/vozes (torch não entra no .venv).

Lê da entrada padrão {"frases": [...], "idioma": "pt", "voz": "<wav de referência ou vazio>", "pasta": "..."}
e grava frase-0.wav, frase-1.wav... na pasta. Imprime {"taxa": <Hz>} no fim. Não importa nada do darkops.
"""
import json
import sys
import wave
from pathlib import Path


def main() -> None:
    pedido = json.loads(sys.stdin.read())
    import torch
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    if pedido.get("codigo"):  # ajuste fino em pt-BR: código próprio (V3 do demo oficial), mesma interface
        sys.path.insert(0, pedido["codigo"])
        from chatterbox.tts import ChatterboxTTS
        modelo = ChatterboxTTS.from_pretrained(dispositivo)
        # ritmo mais solto e um pouco mais de expressão: o que soou melhor nos testes de 2026-11-03
        extra = {"cfg_weight": 0.3, "exaggeration": 0.5}
    else:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        modelo = ChatterboxMultilingualTTS.from_pretrained(device=dispositivo)
        extra = {}
    pasta = Path(pedido["pasta"])
    if pedido.get("voz"):
        extra["audio_prompt_path"] = pedido["voz"]
    for i, frase in enumerate(pedido["frases"]):
        torch.manual_seed(1)  # o mesmo texto sai igual a cada vez
        onda = modelo.generate(frase, language_id=pedido.get("idioma", "pt"), **extra)
        amostras = (onda.squeeze().clamp(-1, 1) * 32767).to(torch.int16).cpu().numpy().tobytes()
        with wave.open(str(pasta / f"frase-{i}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(modelo.sr)
            w.writeframes(amostras)
    print(json.dumps({"taxa": modelo.sr, "dispositivo": dispositivo}))


if __name__ == "__main__":
    main()
