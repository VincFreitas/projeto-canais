"""Animação das cenas pelo HyperFrames (HeyGen, Apache 2.0): HTML + GSAP renderizado em MP4, local e determinístico.

A cena-base continua sendo feita por render.cena (visual, movimento, card, palco, narrador), só que sem legenda.
Por cima dela o HyperFrames põe a camada rica, sincronizada com o tempo de cada palavra:
legenda que entra com desfoque e acende a palavra falada, título letra a letra na 1ª cena, palavra-herói com
clarão e tremor (número vira contador), carimbo, termo fixo no topo, etiquetas com pino, poeira, grão e luz.
O áudio da cena-base é devolvido no fim; a mixagem (música, efeitos, -14 LUFS) continua em render.juntar.

Instalação: dados/apps/hyperframes-teste (npm hyperframes + gsap, ffmpeg e ffprobe em bin/, Node em dados/apps/node).
Liga por canal com "animacao_motor": "hyperframes" no perfil (ou no roteiro). Se falhar, a produção volta ao antigo.
"""
import html
import json
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg

from . import config

PASTA = config.RAIZ / "dados" / "apps" / "hyperframes-teste"
NODE = config.RAIZ / "dados" / "apps" / "node"
VERSAO = 2  # sobe quando a camada muda, para refazer as cenas guardadas


def disponivel() -> bool:
    return all(p.exists() for p in (PASTA / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs",
                                    PASTA / "node_modules" / "gsap" / "dist" / "gsap.min.js",
                                    PASTA / "bin" / "ffprobe.exe", NODE / "node.exe"))


def _grupos(palavras: list[dict], maximo: int) -> list[list[dict]]:
    grupos, atual = [], []
    for p in palavras:
        atual.append(p)
        if len(atual) >= maximo or p["texto"][-1:] in ".,;:!?":
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    return grupos


def _limpo(texto: str) -> str:
    return html.escape(texto.strip(".,;:!?\"'«»“”").upper())


def _norm(texto: str) -> str:
    from .sincronia import _norm as norm
    return norm(texto)


def _html(base: str, palavras: list[dict], dur: float, W: int, H: int, indice: int, *, cor: str, fonte: str,
          semente: str, etiqueta: str | None, titulo: list[str], destaque, termo, selo, rotulos, maximo: int,
          baixo: bool, pixel: int, entrada: bool) -> str:
    vertical = H > W
    escala = W / 1080 if vertical else H / 1080
    tam_leg = int((90 if vertical else 64) * escala)
    topo_leg = int(H * (0.74 if baixo else 0.64)) if vertical else int(H * 0.8)
    anim, corpo = [], []
    chaves_termo = {_norm(t) for t in (termo[0].split() if termo else [])}

    # legenda: grupos de até N palavras; a falada acende na cor do canal, as do termo ficam acesas
    grupos = _grupos(palavras, maximo)
    for i, g in enumerate(grupos):
        ini = g[0]["inicio"]
        fim = grupos[i + 1][0]["inicio"] if i + 1 < len(grupos) else dur
        spans = []
        for j, p in enumerate(g):
            fixa = _norm(p["texto"]) in chaves_termo
            spans.append(f'<span class="p" id="g{i}p{j}"{" style=\"color:var(--acento)\"" if fixa else ""}>'
                         f'{_limpo(p["texto"])}</span>')
            anim.append(f'tl.to("#g{i}p{j}",{{color:"{cor}",scale:1.12,duration:.07,ease:"power2.out"}},{p["inicio"]:.3f});')
            if not fixa:
                anim.append(f'tl.to("#g{i}p{j}",{{color:"#ffffff",scale:1,duration:.14}},{p["fim"]:.3f});')
        corpo.append(f'<div class="grupo clip" id="g{i}" data-start="{ini:.3f}" data-duration="{max(fim - ini, .05):.3f}">'
                     f'{" ".join(spans)}</div>')
        lado = -1 if i % 2 else 1
        anim.append(f'tl.fromTo("#g{i}",{{opacity:0,y:{int(50 * escala)},rotation:{3 * lado},scale:.8,filter:"blur(8px)"}},'
                    f'{{opacity:1,y:0,rotation:0,scale:1,filter:"blur(0px)",duration:.2,ease:"back.out(2.2)"}},{ini:.3f});')

    # ambiente: poeira com semente fixa (o mesmo vídeo sai igual a cada render), grão e luz
    rng = random.Random(f"{semente}-{indice}")
    for k in range(28):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(2, 6) * escala
        forma = "border-radius:0" if pixel else "border-radius:50%"
        corpo.append(f'<i class="po" id="d{k}" style="left:{x:.0f}px;top:{y:.0f}px;width:{r:.1f}px;height:{r:.1f}px;'
                     f'{forma};opacity:{rng.uniform(.2, .7):.2f}"></i>')
        anim.append(f'tl.to("#d{k}",{{x:{rng.uniform(-60, 60):.0f},y:{rng.uniform(-220, -50):.0f},duration:{dur:.3f},ease:"none"}},0);')
    if not pixel:
        anim.append(f'for(let f=0;f<{int(dur * 15)};f++)tl.set("#grao",{{x:((f*37)%13-6)*12,y:((f*53)%11-5)*12}},f/15);')
    anim.append(f'tl.fromTo("#base",{{scale:1}},{{scale:1.04,duration:{dur:.3f},ease:"none"}},0);')
    if entrada:
        anim.append('tl.fromTo("#cortina",{opacity:1},{opacity:0,duration:.28,ease:"power2.out"},0);')
    anim.append(f'tl.fromTo("#vazamento",{{opacity:{.85 if indice == 1 else .35}}},{{opacity:0,duration:{1.1 if indice == 1 else .6},ease:"power2.out"}},0);')

    # cabeçalho: etiqueta em toda cena (dossiê) e título letra a letra na 1ª
    if etiqueta:
        corpo.append(f'<div id="etiqueta"><span>{html.escape(etiqueta.upper())}</span></div>')
        anim.append('tl.fromTo("#etiqueta",{opacity:0,y:-12},{opacity:.9,y:0,duration:.5,ease:"power3.out"},.05);')
    for n, linha in enumerate(titulo[:2]):
        letras = "".join(f'<span class="l">{html.escape(c) if c != " " else "&nbsp;"}</span>' for c in linha.upper())
        ultima = n == len(titulo[:2]) - 1 and len(titulo[:2]) > 1
        corpo.append(f'<div class="titulo{" acento" if ultima else ""}" id="t{n}" style="top:{int(H * (.085 + n * .05))}px">{letras}</div>')
        anim.append(f'tl.fromTo("#t{n} .l",{{opacity:0,y:{int(70 * escala)},rotationX:-90}},'
                    f'{{opacity:1,y:0,rotationX:0,duration:.35,stagger:.03,ease:"back.out(2)"}},{.1 + n * .35:.2f});')

    impacto = None
    if destaque:  # palavra-herói: número vira contador; texto entra batendo
        texto, t = destaque
        numero = re.search(r"\d+(?:[.,]\d+)?", texto)
        corpo.append(f'<div id="heroi" class="clip" data-start="{max(t - .1, 0):.3f}" data-duration="{max(dur - t + .1, .1):.3f}">'
                     + (f'{html.escape(texto[:numero.start()].upper())}<span id="num">0</span>{html.escape(texto[numero.end():].upper())}'
                        if numero else html.escape(texto.upper())) + "</div>")
        anim.append(f'tl.fromTo("#heroi",{{opacity:0,scale:2.4}},{{opacity:1,scale:1,duration:.25,ease:"power4.in"}},{max(t - .1, 0):.3f});')
        if numero:
            alvo = float(numero.group().replace(".", "").replace(",", "."))
            casas = 0 if alvo.is_integer() else 1
            anim.append(f'const nh={{v:0}};tl.to(nh,{{v:{alvo},duration:.6,ease:"power2.out",onUpdate:()=>{{'
                        f'document.querySelector("#num").textContent=nh.v.toLocaleString("pt-BR",{{minimumFractionDigits:{casas},'
                        f'maximumFractionDigits:{casas}}});}}}},{max(t - .1, 0):.3f});')
        impacto = t + .15
    if selo:  # carimbo vermelho (problema) ou verde (solução)
        texto, tipo, t = selo
        corpo.append(f'<div id="selo" class="clip {"bom" if tipo == "bom" else "ruim"}" data-start="{t:.3f}" '
                     f'data-duration="{min(1.6, max(dur - t, .1)):.3f}">{html.escape(texto.upper())}</div>')
        anim.append(f'tl.fromTo("#selo",{{opacity:0,scale:1.8,rotation:{4 if tipo == "bom" else -6}}},'
                    f'{{opacity:1,scale:1,duration:.14,ease:"power4.in"}},{t:.3f});')
        impacto = impacto or t + .14
    if impacto is not None:  # clarão e tremor de câmera quadro a quadro
        anim.append(f'tl.fromTo("#flash",{{opacity:0}},{{opacity:.5,duration:.05}},{impacto:.3f});')
        anim.append(f'tl.to("#flash",{{opacity:0,duration:.5}},{impacto + .05:.3f});')
        for n, (dx, dy, rot) in enumerate([(18, -12, 1.2), (-14, 10, -1), (10, -6, .6), (-6, 4, -.4), (3, -2, .2), (0, 0, 0)]):
            anim.append(f'tl.to("#camera",{{x:{dx * escala:.1f},y:{dy * escala:.1f},rotation:{rot},duration:.033,ease:"none"}},'
                        f'{impacto + n * .033:.3f});')
    if termo:  # nome técnico fixo no topo até o fim da cena
        texto, t = termo
        corpo.append(f'<div id="termo" class="clip" data-start="{t:.3f}" data-duration="{max(dur - t, .1):.3f}">'
                     f'{html.escape(texto.upper())}</div>')
        anim.append(f'tl.fromTo("#termo",{{opacity:0,scale:.4,y:-30}},{{opacity:1,scale:1,y:0,duration:.3,ease:"back.out(2.5)"}},{t:.3f});')
    for k, (texto, x, y, t) in enumerate(rotulos or []):  # etiquetas com pino, cada uma na sua palavra
        corpo.append(f'<div class="rotulo clip" id="r{k}" data-start="{t:.3f}" data-duration="{max(dur - t, .1):.3f}" '
                     f'style="left:{int(W * x)}px;top:{int(H * y)}px"><i></i><b>{html.escape(texto.upper())}</b></div>')
        anim.append(f'tl.fromTo("#r{k}",{{opacity:0,scale:.3}},{{opacity:1,scale:1,duration:.28,ease:"back.out(3)"}},{t:.3f});')

    grao = "" if pixel else ('<div id="grao" class="clip" data-start="0" data-duration="{d}"></div>').format(d=f"{dur:.3f}")
    return f"""<!doctype html>
<html lang="pt-BR" data-resolution="{"portrait" if vertical else "landscape"}">
<head>
<meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<script src="gsap.min.js"></script>
<style>
  @font-face {{ font-family: '{fonte}'; src: local('{fonte}'); }}
  @font-face {{ font-family: 'Consolas'; src: local('Consolas'); }}
  :root {{ --acento: {cor}; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; font-family: '{fonte}', sans-serif; }}
  #camera {{ position: absolute; inset: 0; }}
  #base {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
  #veu {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,.55) 100%); }}
  .po {{ position: absolute; background: rgba(243,230,200,.85); box-shadow: 0 0 {6 * escala:.0f}px rgba(243,230,200,.5); }}
  #grao {{ position: absolute; inset: -50%; opacity: .11; mix-blend-mode: overlay;
          background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }}
  #vazamento {{ position: absolute; inset: -20%; opacity: 0; mix-blend-mode: screen;
               background: radial-gradient(ellipse 45% 60% at 15% 30%, rgba(255,190,120,.7), transparent 60%); }}
  #cortina, #flash {{ position: absolute; inset: 0; opacity: 0; }}
  #cortina {{ background: #000; }} #flash {{ background: #fff; }}
  .grupo {{ position: absolute; left: {int(W * .05)}px; right: {int(W * .05)}px; top: {topo_leg}px; text-align: center;
           font-size: {tam_leg}px; line-height: 1.05; color: #fff; text-shadow: 0 0 2px #000, 0 {6 * escala:.0f}px {18 * escala:.0f}px rgba(0,0,0,.95); }}
  .p {{ display: inline-block; margin: 0 .12em; }}
  .l {{ display: inline-block; }}
  #etiqueta {{ position: absolute; top: {int(H * .055)}px; left: 0; right: 0; text-align: center; font: 600 {int(28 * escala)}px Consolas, monospace;
              letter-spacing: {int(8 * escala)}px; color: #e6dccf; text-shadow: 0 2px 8px #000; }}
  #etiqueta span {{ background: rgba(0,0,0,.55); padding: {int(6 * escala)}px {int(16 * escala)}px; }}
  .titulo {{ position: absolute; left: {int(W * .04)}px; right: {int(W * .04)}px; text-align: center; color: #fff; font-size: {int(84 * escala)}px;
            line-height: 1.02; text-shadow: 0 {6 * escala:.0f}px {24 * escala:.0f}px rgba(0,0,0,.85); }}
  .titulo.acento {{ color: var(--acento); }}
  #heroi {{ position: absolute; left: 0; right: 0; top: {int(H * (.36 if vertical else .3))}px; text-align: center; color: var(--acento);
           font-size: {int(150 * escala)}px; line-height: 1; text-shadow: 0 0 {40 * escala:.0f}px rgba(0,0,0,.6), 0 {8 * escala:.0f}px {20 * escala:.0f}px #000;
           font-variant-numeric: tabular-nums; }}
  #selo {{ position: absolute; left: 50%; top: {int(H * .22)}px; transform: translateX(-50%); padding: {int(14 * escala)}px {int(34 * escala)}px;
          color: #fff; font-size: {int(72 * escala)}px; border: {int(8 * escala)}px solid #fff; white-space: nowrap; }}
  #selo.ruim {{ background: #E63C3C; }} #selo.bom {{ background: #3CC850; }}
  #termo {{ position: absolute; left: 0; right: 0; top: {int(H * .12)}px; text-align: center; color: var(--acento); font-size: {int(68 * escala)}px;
           text-shadow: 0 0 3px #000, 0 {6 * escala:.0f}px {16 * escala:.0f}px #000; }}
  .rotulo {{ position: absolute; display: flex; align-items: center; gap: {int(12 * escala)}px; transform-origin: left center; }}
  .rotulo i {{ width: {int(22 * escala)}px; height: {int(22 * escala)}px; border-radius: 50%; background: var(--acento); box-shadow: 0 0 {20 * escala:.0f}px var(--acento); }}
  .rotulo b {{ background: rgba(5,7,10,.8); border-left: {int(5 * escala)}px solid var(--acento); color: #fff; font-size: {int(34 * escala)}px;
              padding: {int(8 * escala)}px {int(16 * escala)}px; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="{W}" data-height="{H}">
  <div id="camera">
    <video id="base" class="clip" src="{base}" data-start="0" data-duration="{dur:.3f}" muted playsinline></video>
    <div id="veu"></div>
    {chr(10).join("    " + c for c in corpo)}
  </div>
  <div id="vazamento" class="clip" data-start="0" data-duration="{dur:.3f}"></div>
  {grao}
  <div id="flash" class="clip" data-start="0" data-duration="{dur:.3f}"></div>
  <div id="cortina" class="clip" data-start="0" data-duration="{dur:.3f}"></div>
</div>
<script>
  const tl = gsap.timeline({{ paused: true }});
  {chr(10).join("  " + a for a in anim)}
  window.__timelines["main"] = tl;
  tl.seek(0);
</script>
</body>
</html>
"""


def cena(base: Path, palavras: list[dict], dur: float, largura: int, altura: int, indice: int, saida: Path, *,
         cor: str = "#FFE500", fonte: str = "Arial Black", semente: str = "", etiqueta: str | None = None,
         titulo: list[str] | None = None, destaque=None, termo=None, selo=None, rotulos=None, maximo: int = 3,
         baixo: bool = False, pixel: int = 0, entrada: bool = True) -> float:
    """Põe a camada animada sobre a cena-base (mp4 com a narração) e grava em saida. Devolve a duração."""
    from .render import duracao
    pasta = saida.parent / f"hf-{saida.stem}"
    shutil.rmtree(pasta, ignore_errors=True)
    pasta.mkdir(parents=True)
    shutil.copy(PASTA / "node_modules" / "gsap" / "dist" / "gsap.min.js", pasta / "gsap.min.js")
    shutil.copy(base, pasta / "base.mp4")
    (pasta / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}), encoding="utf-8")
    (pasta / "index.html").write_text(
        _html("base.mp4", palavras, dur, largura, altura, indice, cor=cor, fonte=fonte, semente=semente,
              etiqueta=etiqueta, titulo=titulo or [], destaque=destaque, termo=termo, selo=selo, rotulos=rotulos,
              maximo=maximo, baixo=baixo, pixel=pixel, entrada=entrada), encoding="utf-8")
    mudo = pasta / "mudo.mp4"
    env = {**os.environ, "PATH": f"{PASTA / 'bin'};{NODE};{os.environ.get('PATH', '')}", "DO_NOT_TRACK": "1",
           "HYPERFRAMES_SKIP_SKILLS": "1"}
    proc = subprocess.run([str(NODE / "node.exe"), str(PASTA / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"),
                           "render", str(pasta), "-o", str(mudo), "--quality", "looks"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=1800,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if proc.returncode != 0 or not mudo.exists():
        raise RuntimeError(f"HyperFrames falhou na cena {indice}: {(proc.stderr or proc.stdout)[-400:]}")
    # devolve o som da cena-base e reencoda em H.264 (o ffmpeg do projeto tem libx264)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(mudo),
                    "-i", str(base), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-color_range", "tv", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-ac", "2", "-t", f"{dur:.3f}", str(saida)], check=True)  # mesmos parâmetros de render.cena
    shutil.rmtree(pasta, ignore_errors=True)
    return duracao(saida)
