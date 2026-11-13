# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
r"""Renderiza a animação da capa do README (docs/capa/capa.html) quadro a quadro e gera docs/img/capa.gif.

Uso, na raiz do projeto (precisa do Playwright com Chromium e do `npm install` em web/, como o palco 3D):
    .\.venv\Scripts\python.exe docs\capa\render.py
A timeline do GSAP fica pausada e é avançada quadro a quadro: os quadros saem iguais toda vez.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

PASTA = Path(__file__).resolve().parent
SAIDA = PASTA.parent / "img" / "capa.gif"
FPS = 15

with tempfile.TemporaryDirectory() as tmp:
    quadros = Path(tmp)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1600, "height": 500})
        pagina.goto((PASTA / "capa.html").as_uri())
        pagina.wait_for_function("window.DUR > 0")
        total = int(pagina.evaluate("window.DUR") * FPS) + 1
        for i in range(total):
            pagina.evaluate(f"window.tl.seek({i / FPS:.4f}, false); 0")  # o "; 0" evita devolver a timeline
            pagina.screenshot(path=str(quadros / f"{i:04d}.png"))
        navegador.close()
    filtro = ("scale=1200:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
              "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
                    "-i", str(quadros / "%04d.png"), "-vf", filtro, "-loop", "0", str(SAIDA)], check=True)
print(f"pronto: {SAIDA} ({total} quadros)")
