import subprocess, sys, time
from pathlib import Path

M = Path(r"C:\Users\Vinic\canais-dark\modelos")
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
ESTILO = ("16-bit pixel art, retro SNES video game style, crisp visible square pixels, limited color palette, "
          "no anti-aliasing, dithering in the water, side view game scene. The same cute friendly purple "
          "octopus character with big round eyes, deep blue ocean palette. No text, no letters, no watermark. ")
CENAS = [
    "Scene: the purple octopus floating in a deep blue ocean, three small glowing red cartoon hearts floating above its head, tiny bubbles rising, soft light rays from the surface, simple coral silhouettes at the bottom. Subject centered, calm uncluttered background.",
    "Scene: a simple cartoon cutaway diagram of the purple octopus showing its insides: two small hearts next to its gills on each side and one bigger heart in the center, glowing lines showing blood flowing from the central heart to the tentacles. Clean, educational, centered.",
    "Scene: big glossy cartoon drops of bright blue blood floating in the water next to the purple octopus, small shiny copper-colored round particles sparkling inside the drops. Sense of discovery, centered.",
    "Scene: the purple octopus looking a bit tired, catching small oxygen bubbles with its tentacles, while its three little red hearts beat hard together like a team, small motion marks around the hearts. Funny, cute, centered.",
    "Scene: the purple octopus swimming fast with jet propulsion, water jet trail behind it, speed lines, its biggest heart in the center pausing with a tiny sleepy face while the two small hearts keep beating. Funny, dynamic, centered.",
]
for i, cena in enumerate(CENAS, 1):
    t = time.time()
    r = subprocess.run([str(M / "sd" / "sd-cli.exe"), "--diffusion-model", str(M / "z_image_turbo-Q4_K.gguf"),
                        "--vae", str(M / "ae.safetensors"), "--llm", str(M / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"),
                        "-p", ESTILO + cena, "--cfg-scale", "1.0", "--steps", "8", "--offload-to-cpu",
                        "--flash-attn", "off,diffusion=on", "--vae-tiling", "-W", "1024", "-H", "768", "--seed", "42", "-o", str(OUT / f"cena{i}.png")],
                       capture_output=True, text=True, errors="replace")
    print(f"cena {i}: {'ok' if r.returncode == 0 else 'falhou'} em {time.time() - t:.0f}s", flush=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:]); break
