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
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = ChatterboxMultilingualTTS.from_pretrained(device=dispositivo)
    pasta = Path(pedido["pasta"])
    extra = {"audio_prompt_path": pedido["voz"]} if pedido.get("voz") else {}
    for i, frase in enumerate(pedido["frases"]):
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
