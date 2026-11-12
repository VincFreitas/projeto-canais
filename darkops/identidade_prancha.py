"""Identidade das contas no estilo da Prancha de Campo (canal com "motor_cena": "prancha").

A foto, a marca d'água e a capa do YouTube ficam com a mesma cara dos vídeos: traço verde-água sobre grafite, papel
técnico quadriculado e a peça do canal desenhada em linha (as peças SVG de web/prancha/pecas/), com as fontes que já
vêm no Windows. Cada arte é um SVG único e pequeno (foto.svg, marca.svg, capa.svg em perfis/<id>/marca/):
o Chromium do projeto acerta o tamanho dos textos, grava o SVG final e fotografa o PNG. Como o SVG tem poucos KB, a
skill /identidade-visual o leva inteiro para a página logada e desenha o PNG lá dentro (sem colar dezenas de blocos)."""
from __future__ import annotations

import math
import re
from pathlib import Path

from . import config

PECAS = config.RAIZ / "web" / "prancha" / "pecas"
FUNDO, BORDA, HALO, LINHA = "#0B0F14", "#05070A", "#12202A", "#5CF2E0"
TEXTO, OSSO, AMBAR = "#F4F1EA", "#B7B3A8", "#F2B33D"


def _peca(nome: str) -> tuple[list[float], str]:
    """(viewBox, desenho) de uma peça SVG da Prancha, sem comentários nem atributos de dados."""
    texto = (PECAS / f"{nome}.svg").read_text(encoding="utf-8")
    caixa = re.search(r'viewBox="([^"]+)"', texto)
    miolo = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", texto, flags=re.S)
    miolo = re.sub(r"<!--.*?-->|\s+data-[a-z-]+=\"[^\"]*\"", "", miolo, flags=re.S)
    return [float(x) for x in (caixa.group(1) if caixa else "0 0 500 1000").split()], " ".join(miolo.split())


def _estilo(traco: float, tracejado: float) -> str:
    return (f".l{{fill:none;stroke:{LINHA};stroke-width:{traco:.1f};stroke-linecap:round;stroke-linejoin:round}}"
            f".d{{fill:none;stroke:{LINHA};stroke-width:{tracejado:.1f};stroke-linecap:round;stroke-linejoin:round;"
            "opacity:.7}.m{fill:rgba(92,242,224,.10);stroke:none}.sombra{fill:rgba(5,7,10,.55);stroke:none}")


def _papel(largura: int, altura: int, grade: int) -> str:
    """Fundo grafite com a grade do papel técnico, o halo e a vinheta (tudo em SVG)."""
    fino = grade / 5
    return (f'<defs><pattern id="gf" width="{fino}" height="{fino}" patternUnits="userSpaceOnUse">'
            f'<path d="M{fino} 0H0V{fino}" fill="none" stroke="{LINHA}" stroke-opacity=".045" stroke-width="1"/></pattern>'
            f'<pattern id="gg" width="{grade}" height="{grade}" patternUnits="userSpaceOnUse">'
            f'<path d="M{grade} 0H0V{grade}" fill="none" stroke="{LINHA}" stroke-opacity=".09" stroke-width="2"/></pattern>'
            f'<radialGradient id="halo"><stop offset="0" stop-color="{HALO}"/><stop offset=".45" stop-color="{HALO}" '
            f'stop-opacity=".5"/><stop offset="1" stop-color="{HALO}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="vinheta"><stop offset=".55" stop-color="{BORDA}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{BORDA}"/></radialGradient></defs>'
            f'<rect width="{largura}" height="{altura}" fill="{FUNDO}"/>'
            f'<rect width="{largura}" height="{altura}" fill="url(#gf)"/><rect width="{largura}" height="{altura}" fill="url(#gg)"/>'
            f'<ellipse cx="{largura / 2}" cy="{altura / 2}" rx="{largura * .6}" ry="{altura * .6}" fill="url(#halo)"/>')


def _vinheta(largura: int, altura: int) -> str:
    return f'<ellipse cx="{largura / 2}" cy="{altura / 2}" rx="{largura * .85}" ry="{altura * .75}" fill="url(#vinheta)"/>'


def svg_foto(peca: str, fundo: bool = True) -> str:
    """Emblema 800x800: anel de transferidor com marcas e a peça no meio, traço grosso para ler pequeno.
    Sem `fundo`, os cantos ficam transparentes (marca d'água)."""
    (x0, y0, w, h), miolo = _peca(peca)
    escala = 560 / h
    dx, dy = 400 - (x0 + w / 2) * escala, 410 - (y0 + h / 2) * escala
    chao = dy + (y0 + h * .955) * escala
    marcas = "".join(
        f'<line x1="{400 + 352 * math.cos(math.radians(g)):.1f}" y1="{400 + 352 * math.sin(math.radians(g)):.1f}" '
        f'x2="{400 + (334 if g % 30 else 312) * math.cos(math.radians(g)):.1f}" '
        f'y2="{400 + (334 if g % 30 else 312) * math.sin(math.radians(g)):.1f}"/>' for g in range(0, 360, 10))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">'
            + (_papel(800, 800, 80) if fundo else
               f'<defs><radialGradient id="halo"><stop offset="0" stop-color="{HALO}"/>'
               f'<stop offset="1" stop-color="{FUNDO}"/></radialGradient></defs>')
            + f'<defs><clipPath id="dentro"><circle cx="400" cy="400" r="350"/></clipPath>'
            f'<style>{_estilo(11 / escala, 6 / escala)}</style></defs>'
            f'<circle cx="400" cy="400" r="372" fill="{FUNDO if not fundo else "none"}"/>'
            f'<circle cx="400" cy="400" r="350" fill="{"url(#halo)" if not fundo else "rgba(11,15,20,.55)"}"/>'
            f'<g clip-path="url(#dentro)"><g transform="translate({dx:.1f} {dy:.1f}) scale({escala:.4f})">{miolo}</g>'
            f'<line x1="60" y1="{chao:.1f}" x2="740" y2="{chao:.1f}" stroke="{LINHA}" stroke-width="4" opacity=".55"/></g>'
            f'<circle cx="400" cy="400" r="372" fill="none" stroke="{LINHA}" stroke-width="12"/>'
            f'<circle cx="400" cy="400" r="352" fill="none" stroke="{LINHA}" stroke-width="3" opacity=".6"/>'
            f'<g stroke="{LINHA}" stroke-width="4" opacity=".75">{marcas}</g>'
            f'<circle cx="400" cy="28" r="10" fill="{AMBAR}"/>'
            + (_vinheta(800, 800) if fundo else "") + "</svg>")


def _escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def svg_capa(peca: str, titulo: str, subtitulo: str, rotulo: str, medida: str) -> str:
    """Capa 2560x1440. Tudo o que importa fica na área que aparece em todo aparelho (1546x423 no centro).
    Os textos levam data-caber: o Chromium encolhe cada um até caber, antes de gravar o SVG final."""
    (x0, y0, w, h), miolo = _peca(peca)
    sx, sy, sw = 507, 508, 1546
    escala = 400 / h
    px, py = sx + 40 - x0 * escala, sy + 12 - y0 * escala
    base, topo = py + (y0 + h * .97) * escala, py + (y0 + h * .05) * escala
    cota = px + (x0 + w) * escala + 18
    tx = int(cota + 180)  # a medida ("9,8 m") fica entre a cota e o título
    largura = sx + sw - tx - 20
    centro = (px + w * escala / 2, (topo + base) / 2)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="2560" height="1440" viewBox="0 0 2560 1440">'
            + _papel(2560, 1440, 120)
            + f'<defs><style>{_estilo(6 / escala, 3.5 / escala)}</style></defs>'
            # fora da área segura (só na TV e no computador largo): círculo de construção e chão, bem apagados
            f'<circle cx="{centro[0]:.0f}" cy="{centro[1]:.0f}" r="420" fill="none" stroke="{LINHA}" stroke-width="2" '
            f'stroke-dasharray="10 14" opacity=".22"/>'
            f'<line x1="0" y1="{base:.0f}" x2="2560" y2="{base:.0f}" stroke="{LINHA}" stroke-width="2" opacity=".25"/>'
            f'<g transform="translate({px:.1f} {py:.1f}) scale({escala:.4f})">{miolo}</g>'
            f'<g stroke="{AMBAR}" stroke-width="3"><line x1="{cota:.0f}" y1="{topo:.0f}" x2="{cota:.0f}" y2="{base:.0f}"/>'
            f'<line x1="{cota - 14:.0f}" y1="{topo:.0f}" x2="{cota + 14:.0f}" y2="{topo:.0f}"/>'
            f'<line x1="{cota - 14:.0f}" y1="{base:.0f}" x2="{cota + 14:.0f}" y2="{base:.0f}"/></g>'
            + (f'<text x="{cota + 22:.0f}" y="{centro[1] + 12:.0f}" fill="{AMBAR}" font-family="Consolas" '
               f'font-size="34">{_escapar(medida)}</text>' if medida else "")
            + f'<text data-caber="{largura}" x="{tx}" y="{sy + 66}" fill="{OSSO}" font-family="Consolas" font-size="30" '
            f'letter-spacing="5">{_escapar(rotulo)}</text>'
            f'<text data-caber="{largura}" x="{tx - 6}" y="{sy + 250}" fill="{TEXTO}" font-family="Bahnschrift" '
            f'font-weight="700" font-size="168" letter-spacing="6">{_escapar(titulo)}</text>'
            f'<rect x="{tx}" y="{sy + 286}" width="{largura}" height="5" fill="{LINHA}"/>'
            f'<text data-caber="{largura}" x="{tx}" y="{sy + 356}" fill="{LINHA}" font-family="Consolas" font-size="40" '
            f'letter-spacing="2">{_escapar(subtitulo)}</text>'
            + _vinheta(2560, 1440) + "</svg>")


_AJUSTAR = """async () => {
  await document.fonts.ready;
  for (const t of document.querySelectorAll('text[data-caber]')) {
    let tam = +t.getAttribute('font-size');
    while (t.getComputedTextLength() > +t.dataset.caber && tam > 10) { tam -= 1; t.setAttribute('font-size', tam); }
    t.removeAttribute('data-caber');
  }
  return document.querySelector('svg').outerHTML;
}"""


def _desenhar(artes: list[tuple[str, int, int, Path, bool]]) -> None:
    """Abre cada SVG no Chromium do projeto, acerta os textos, grava o SVG final e o PNG."""
    from . import palco_web  # noqa: F401  (aponta o Playwright para o Chromium do projeto)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        try:
            for svg, largura, altura, destino, transparente in artes:
                pagina = navegador.new_page(viewport={"width": largura, "height": altura})
                pagina.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
                final = pagina.evaluate(_AJUSTAR)
                destino.with_suffix(".svg").write_text(final, encoding="utf-8")
                pagina.locator("svg").screenshot(path=str(destino), omit_background=transparente)
                pagina.close()
        finally:
            navegador.close()


def gerar(p, tx: dict, pasta: Path, peca: str = "") -> None:
    """Grava foto-perfil, marca-dagua (150, cantos transparentes) e capa-youtube (2560x1440), em SVG e PNG."""
    from PIL import Image
    peca = peca or p.dados.get("peca_marca") or "moai-perfil"
    frente = peca.replace("-perfil", "-frente")
    frente = frente if (PECAS / f"{frente}.svg").exists() else peca
    achado = re.search(r"altura_m:([\d.]+)", (PECAS / f"{peca}.svg").read_text(encoding="utf-8"))
    medida = f"{achado.group(1).replace('.', ',')} m" if achado else ""
    rotulo = tx.get("rotulo_capa") or "ARQUIVO DE CAMPO · CASOS REAIS"
    _desenhar([
        (svg_foto(frente), 800, 800, pasta / "foto-perfil.png", False),
        (svg_foto(frente, fundo=False), 800, 800, pasta / "marca-dagua.png", True),
        (svg_capa(peca, tx["titulo_capa"], tx["subtitulo_capa"].upper(), rotulo, medida), 2560, 1440,
         pasta / "capa-youtube.png", False),
    ])
    marca = Image.open(pasta / "marca-dagua.png").convert("RGBA").resize((150, 150), Image.Resampling.LANCZOS)
    marca.save(pasta / "marca-dagua.png")
    (pasta / "marca-dagua.svg").write_text(  # o SVG da marca desenha em 150x150
        (pasta / "marca-dagua.svg").read_text(encoding="utf-8").replace('width="800" height="800"',
                                                                         'width="150" height="150"', 1),
        encoding="utf-8")
    for nome in ("foto-perfil", "marca-dagua", "capa-youtube"):  # versões leves para conferir à mão, se preciso
        transparente = nome == "marca-dagua"
        Image.open(pasta / f"{nome}.png").convert("RGBA" if transparente else "RGB") \
            .quantize(64, method=Image.Quantize.FASTOCTREE if transparente else Image.Quantize.MEDIANCUT) \
            .save(pasta / f"{nome}-pequena.png", optimize=True)
