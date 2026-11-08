"""Ponte para o ambiente separado dados/apps/voz-local (Kokoro e faster-whisper, sem tocar no .venv).

Roda com o Python daquele ambiente. Lê um pedido JSON da entrada padrão e escreve uma linha JSON na saída:
- {"acao": "falar", "frases": [...], "voz": "pf_dora", "lingua": "pt-br", "velocidade": 1.1, "modelos": "...",
   "pasta": "..."} grava frase-<i>.wav (16 bits, mono) e devolve {"taxa": 24000}
- {"acao": "ouvir", "audio": "...", "idioma": "pt", "modelo": "small", "modelos": "..."} devolve
  {"texto": "...", "segmentos": [{"inicio", "fim", "texto"}]}
Este arquivo não importa nada do darkops: só a biblioteca padrão e o que está no ambiente."""
import json
import sys
import wave
from pathlib import Path


def falar(p: dict) -> dict:
    import numpy as np
    from kokoro_onnx import Kokoro
    modelos = Path(p["modelos"])
    kokoro = Kokoro(str(modelos / "kokoro-v1.0.onnx"), str(modelos / "voices-v1.0.bin"))
    taxa = 24000
    for i, frase in enumerate(p["frases"]):
        amostras, taxa = kokoro.create(frase, voice=p["voz"], speed=float(p.get("velocidade", 1.0)),
                                       lang=p.get("lingua", "pt-br"))
        with wave.open(str(Path(p["pasta"]) / f"frase-{i}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(taxa)
            w.writeframes((np.clip(amostras, -1, 1) * 32767).astype(np.int16).tobytes())
    return {"taxa": taxa}


def ouvir(p: dict) -> dict:
    from faster_whisper import WhisperModel
    modelo = WhisperModel(p.get("modelo", "small"), device="cpu", compute_type="int8",
                          download_root=str(Path(p["modelos"]) / "whisper"))
    segmentos, _ = modelo.transcribe(p["audio"], language=p.get("idioma") or None, vad_filter=True)
    lista = [{"inicio": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip()} for s in segmentos]
    return {"texto": " ".join(s["texto"] for s in lista), "segmentos": lista}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pedido = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    print(json.dumps({"falar": falar, "ouvir": ouvir}[pedido["acao"]](pedido), ensure_ascii=False))
