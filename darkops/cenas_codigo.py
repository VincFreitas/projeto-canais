# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Cenas desenhadas por código para a edição dossiê: mapa, diagrama, escala e ficha do caso.

Servem de fundo da cena no lugar da imagem de IA: renderizam em segundos e variam o visual do vídeo. A imagem de IA
fica para as 3 ou 4 cenas de impacto (abertura, momento-chave, final). Campo "codigo" da cena:

  {"tipo": "mapa", "centro": [-14.7, -75.1], "raio_km": 400, "titulo": "Peru",
   "pontos": [{"lat": -14.7, "lon": -75.1, "rotulo": "Nazca"}], "rota": [[-12.05, -77.04], [-14.7, -75.1]]}
      contorno dos países (Natural Earth, domínio público), câmera que se aproxima, marcador que pulsa, rota que se
      desenha. Coordenadas reais do caso (confira na fonte).
  {"tipo": "diagrama", "titulo": "Grade de escala", "tracos": [[[0.2, 0.7], [0.5, 0.3], [0.8, 0.7]]],
   "rotulos": [{"texto": "estaca", "x": 0.2, "y": 0.7}], "grade": true}
      traços que se desenham em sequência (x e y de 0 a 1 dentro da área do desenho), com etiquetas.
  {"tipo": "escala", "unidade": "m", "itens": [{"rotulo": "Pessoa", "valor": 1.7}, {"rotulo": "Condor", "valor": 134}]}
      barras que crescem na mesma escala, com uma pessoa de referência.
  {"tipo": "ficha", "titulo": "Ficha do caso", "campos": [["Local", "Nazca, Peru"], ["Época", "500 a.C. a 500 d.C."]]}
      resumo do caso em campos (fatos com fonte; nunca imita documento oficial).

A legenda e os painéis (animacao) entram por cima no render, como numa cena com imagem.
"""
import json
import math
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .render import FFMPEG, FPS

VERSAO = 4
_F = "C:/Windows/Fonts/"
MONO = _F + "consola.ttf"
MONO_FORTE = _F + "consolab.ttf"
FORTE = _F + "ariblk.ttf"
TEXTO = _F + "segoeuib.ttf"
FUNDO_TOPO, FUNDO_BASE = (14, 20, 36), (6, 9, 18)
LINHA = (120, 150, 190)
CINZA = (150, 160, 176)
BRANCO = (236, 242, 250)
ALERTA = (255, 84, 84)
MAPA_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
            "ne_50m_admin_0_countries.geojson")
MAPA = config.RAIZ / "dados" / "cache" / "mapa" / "ne_50m_admin_0_countries.geojson"


def _fonte(caminho: str, tamanho: float):
    try:
        return ImageFont.truetype(caminho, max(int(tamanho), 8))
    except OSError:
        return ImageFont.load_default()


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _cor(valor, padrao):
    if isinstance(valor, str) and valor.startswith("#") and len(valor) == 7:
        return tuple(int(valor[i:i + 2], 16) for i in (1, 3, 5))
    return padrao


def _numero(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fundo(w: int, h: int, grade: bool = True) -> Image.Image:
    """Azul-noite com gradiente, grade fina e vinheta: a mesa de trabalho do dossiê."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(FUNDO_TOPO, FUNDO_BASE)))
    if grade:
        passo = w // 12
        for x in range(0, w, passo):
            d.line([(x, 0), (x, h)], fill=(22, 30, 50))
        for y in range(0, h, passo):
            d.line([(0, y), (w, y)], fill=(22, 30, 50))
    return img


def _titulo(d: ImageDraw.ImageDraw, w: int, h: int, texto: str, destaque, alfa: float = 1.0) -> None:
    if texto and alfa > 0.01:
        d.text((w * 0.075, h * 0.175), str(texto).upper(), font=_fonte(FORTE, h * 0.024),
               fill=destaque + (int(255 * alfa),))


# ---------- mapa ----------

def _paises() -> list[list[list[tuple[float, float]]]]:
    """Polígonos dos países (lon, lat). Baixa o arquivo da Natural Earth uma vez para dados/cache."""
    if not MAPA.exists():
        MAPA.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(MAPA_URL, timeout=60) as r:
            MAPA.write_bytes(r.read())
    dados = json.loads(MAPA.read_text(encoding="utf-8"))
    saida = []
    for f in dados["features"]:
        g = f["geometry"]
        partes = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        saida.append([[(float(x), float(y)) for x, y in anel] for poli in partes for anel in poli[:1]])
    return saida


class _Mapa:
    def __init__(self, w, h, c, dur, destaque):
        self.w, self.h, self.c, self.dur, self.destaque = w, h, c, dur, destaque
        self.lat0, self.lon0 = (float(v) for v in c.get("centro") or [0, 0])
        self.raio = float(c.get("raio_km", 500))
        # base desenhada uma vez, 2,5x maior que o quadro final: a câmera se aproxima recortando
        self.fator = 2.5
        self.base = self._desenhar_base()

    def _proj(self, lat, lon, km_por_px):
        x = (lon - self.lon0) * 111.32 * math.cos(math.radians(self.lat0)) / km_por_px
        y = -(lat - self.lat0) * 110.57 / km_por_px
        return x, y

    def _desenhar_base(self) -> Image.Image:
        bw, bh = int(self.w * self.fator), int(self.h * self.fator)
        img = _fundo(bw, bh, grade=False)
        d = ImageDraw.Draw(img, "RGBA")
        km_por_px = self.raio / (self.w * 0.45)  # no recorte final, o raio ocupa 45% da largura
        self.km_por_px_base = km_por_px
        cx, cy = bw / 2, bh / 2
        for pais in _paises():
            for anel in pais:
                pts = [self._proj(lat, lon, km_por_px) for lon, lat in anel]
                if all(abs(x) > bw or abs(y) > bh for x, y in pts):
                    continue
                d.polygon([(cx + x, cy + y) for x, y in pts], fill=(26, 36, 58), outline=(70, 96, 140))
        passo = max(int(bw / 14), 40)
        for x in range(0, bw, passo):
            d.line([(x, 0), (x, bh)], fill=(255, 255, 255, 10))
        for y in range(0, bh, passo):
            d.line([(0, y), (bw, y)], fill=(255, 255, 255, 10))
        return img

    def quadro(self, t: float) -> Image.Image:
        w, h, c = self.w, self.h, self.c
        p = _suave(t / max(self.dur * 0.75, 0.8))
        zoom = 1 - (1 - 1 / self.fator) * p  # fração da base visível: da base inteira até o recorte final
        cw, ch = self.base.width * zoom, self.base.height * zoom
        # o centro sobe para 40% da altura no fim: embaixo ficam os painéis e a legenda
        sobe = 0.1 * p
        x0, y0 = (self.base.width - cw) / 2, (self.base.height - ch) / 2 + ch * sobe
        quadro = self.base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h), Image.Resampling.BILINEAR)
        d = ImageDraw.Draw(quadro, "RGBA")
        escala = self.base.width / cw  # px da base viram px do quadro
        km_por_px = self.km_por_px_base / escala

        def tela(lat, lon):
            x, y = self._proj(lat, lon, km_por_px)
            return w / 2 + x, h * (0.5 - sobe) + y

        rota = c.get("rota") or []
        if len(rota) > 1:
            pts = [tela(float(a), float(b)) for a, b in rota]
            andar = _suave((t - 0.4) / max(self.dur * 0.6, 0.6))
            total = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)) * andar
            feito = [pts[0]]
            for k in range(len(pts) - 1):
                seg = math.dist(pts[k], pts[k + 1])
                if total <= 0:
                    break
                f = min(total / seg, 1) if seg else 1
                feito.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f))
                total -= seg
            if len(feito) > 1:
                d.line(feito, fill=self.destaque + (255,), width=max(int(w * 0.007), 4), joint="curve")
        for k, ponto in enumerate(c.get("pontos") or []):
            x, y = tela(float(ponto["lat"]), float(ponto["lon"]))
            entra = _suave((t - 0.3 - 0.3 * k) / 0.3)
            if entra <= 0.01:
                continue
            onda = (t * 0.9 + k * 0.3) % 1
            r = w * 0.012
            d.ellipse([x - r * (1 + 3 * onda), y - r * (1 + 3 * onda), x + r * (1 + 3 * onda), y + r * (1 + 3 * onda)],
                      outline=ALERTA + (int(200 * (1 - onda) * entra),), width=3)
            d.ellipse([x - r, y - r, x + r, y + r], fill=ALERTA + (int(255 * entra),), outline=(255, 255, 255, 230),
                      width=3)
            if ponto.get("rotulo"):
                d.text((x + r * 2, y - r * 1.4), str(ponto["rotulo"]).upper(), font=_fonte(FORTE, h * 0.022),
                       fill=BRANCO + (int(255 * entra),))
        _titulo(d, w, h, c.get("titulo", ""), self.destaque, _suave(t / 0.4))
        return quadro


# ---------- diagrama ----------

class _Diagrama:
    def __init__(self, w, h, c, dur, destaque):
        self.w, self.h, self.c, self.dur, self.destaque = w, h, c, dur, destaque
        self.base = _fundo(w, h, grade=bool(c.get("grade", True)))
        # área do desenho: abaixo do título e acima da legenda
        self.area = (w * 0.08, h * 0.25, w * 0.92, h * 0.62)
        self.tracos = [[self._ponto(p) for p in tr] for tr in c.get("tracos") or [] if len(tr) > 1]
        self.comprimentos = [sum(math.dist(tr[k], tr[k + 1]) for k in range(len(tr) - 1)) for tr in self.tracos]

    def _ponto(self, p):
        x0, y0, x1, y1 = self.area
        return x0 + (x1 - x0) * float(p[0]), y0 + (y1 - y0) * float(p[1])

    def quadro(self, t: float) -> Image.Image:
        w, h, c = self.w, self.h, self.c
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        _titulo(d, w, h, c.get("titulo", ""), self.destaque, _suave(t / 0.4))
        total = sum(self.comprimentos) or 1
        feito = total * _suave((t - 0.3) / max(self.dur * 0.7, 0.8))
        for tr, comp in zip(self.tracos, self.comprimentos):
            if feito <= 0:
                break
            resto, pts = min(feito, comp), [tr[0]]
            for k in range(len(tr) - 1):
                seg = math.dist(tr[k], tr[k + 1])
                if resto <= 0:
                    break
                f = min(resto / seg, 1) if seg else 1
                pts.append((tr[k][0] + (tr[k + 1][0] - tr[k][0]) * f, tr[k][1] + (tr[k + 1][1] - tr[k][1]) * f))
                resto -= seg
            d.line(pts, fill=self.destaque + (255,), width=max(int(w * 0.006), 4), joint="curve")
            ponta = pts[-1]
            if feito < comp:
                d.ellipse([ponta[0] - 9, ponta[1] - 9, ponta[0] + 9, ponta[1] + 9], fill=(255, 255, 255, 230))
            feito -= comp
        n = max(len(c.get("rotulos") or []), 1)
        for k, r in enumerate(c.get("rotulos") or []):
            entra = _suave((t - 0.5 - (self.dur * 0.6) * k / n) / 0.3)
            if entra <= 0.01:
                continue
            x, y = self._ponto((r.get("x", 0.5), r.get("y", 0.5)))
            fonte = _fonte(MONO_FORTE, h * 0.014)
            texto = str(r["texto"]).upper()
            lw = d.textlength(texto, font=fonte)
            d.rounded_rectangle([x - lw / 2 - 14, y - h * 0.04, x + lw / 2 + 14, y - h * 0.018], radius=8,
                                fill=(12, 16, 30, int(220 * entra)), outline=self.destaque + (int(200 * entra),), width=2)
            d.text((x, y - h * 0.029), texto, font=fonte, fill=BRANCO + (int(255 * entra),), anchor="mm")
            d.line([(x, y - h * 0.018), (x, y)], fill=self.destaque + (int(200 * entra),), width=2)
        return img


# ---------- escala ----------

class _Escala:
    def __init__(self, w, h, c, dur, destaque):
        self.w, self.h, self.c, self.dur, self.destaque = w, h, c, dur, destaque
        self.base = _fundo(w, h)
        self.itens = (c.get("itens") or [])[:4]

    def quadro(self, t: float) -> Image.Image:
        w, h, c = self.w, self.h, self.c
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        _titulo(d, w, h, c.get("titulo", ""), self.destaque, _suave(t / 0.4))
        chao, teto = h * 0.62, h * 0.27
        d.line([(w * 0.05, chao), (w * 0.95, chao)], fill=LINHA, width=3)
        maior = max((float(i["valor"]) for i in self.itens), default=1) or 1
        n = max(len(self.itens), 1)
        larg = w * 0.8 / n
        for k, item in enumerate(self.itens):
            cresce = _suave((t - 0.3 - 0.35 * k) / 0.8)
            if cresce <= 0.01:
                continue
            valor = float(item["valor"])
            alt = max((chao - teto) * valor / maior * cresce, 4)
            x0 = w * 0.1 + k * larg + larg * 0.15
            x1 = x0 + larg * 0.7
            cor = self.destaque if k == len(self.itens) - 1 else (200, 210, 225)
            d.rectangle([x0, chao - alt, x1, chao], fill=cor + (90,), outline=cor + (255,), width=3)
            casas = 1 if valor < 10 and valor != int(valor) else 0
            d.text(((x0 + x1) / 2, chao - alt - h * 0.012), f"{_numero(valor * cresce, casas)} {c.get('unidade', '')}",
                   font=_fonte(MONO_FORTE, h * 0.022), fill=BRANCO, anchor="md")
            d.text(((x0 + x1) / 2, chao + h * 0.025), str(item.get("rotulo", "")).upper(),
                   font=_fonte(MONO, h * 0.015), fill=CINZA, anchor="mm")
            if valor / maior < 0.05:  # o pequeno vira um ponto com seta, para ainda dar para ver
                cx = (x0 + x1) / 2
                d.polygon([(cx - 14, chao - alt - h * 0.06), (cx + 14, chao - alt - h * 0.06), (cx, chao - alt - h * 0.04)],
                          fill=ALERTA)
        return img


# ---------- ficha ----------

class _Ficha:
    def __init__(self, w, h, c, dur, destaque):
        self.w, self.h, self.c, self.dur, self.destaque = w, h, c, dur, destaque
        self.base = _fundo(w, h)
        self.campos = (c.get("campos") or [])[:6]

    def quadro(self, t: float) -> Image.Image:
        w, h, c = self.w, self.h, self.c
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        x0, x1, y = w * 0.075, w * 0.925, h * 0.22
        entra = _suave(t / 0.4)
        d.rounded_rectangle([x0, y, x1, y + h * (0.08 + 0.065 * len(self.campos))], radius=16,
                            fill=(16, 22, 40, int(235 * entra)), outline=(255, 255, 255, int(50 * entra)), width=2)
        d.rectangle([x0, y, x1, y + h * 0.05], fill=self.destaque + (int(40 * entra),))
        d.text((x0 + w * 0.04, y + h * 0.025), str(c.get("titulo", "ficha do caso")).upper(),
               font=_fonte(MONO_FORTE, h * 0.018), fill=self.destaque + (int(255 * entra),), anchor="lm")
        yy = y + h * 0.08
        for k, campo in enumerate(self.campos):
            rotulo, valor = (campo + ["", ""])[:2] if isinstance(campo, list) else (campo.get("rotulo", ""), campo.get("valor", ""))
            aparece = _suave((t - 0.4 - k * min(0.5, self.dur * 0.6 / max(len(self.campos), 1))) / 0.3)
            if aparece > 0.01:
                d.text((x0 + w * 0.04, yy), str(rotulo).upper(), font=_fonte(MONO, h * 0.0135),
                       fill=CINZA + (int(255 * aparece),))
                d.text((x0 + w * 0.04, yy + h * 0.02), str(valor), font=_fonte(TEXTO, h * 0.024),
                       fill=BRANCO + (int(255 * aparece),))
                d.line([(x0 + w * 0.04, yy + h * 0.055), (x1 - w * 0.04, yy + h * 0.055)], fill=(255, 255, 255, 22))
            yy += h * 0.065
        return img


TIPOS = {"mapa": _Mapa, "diagrama": _Diagrama, "escala": _Escala, "ficha": _Ficha}


def gerar(codigo: dict, duracao: float, largura: int, altura: int, destino: Path, destaque: str = "#5CF2E0") -> Path:
    """Grava a cena de código como .mp4 do tamanho da tela. Reaproveita se nada mudou."""
    tipo = codigo.get("tipo")
    if tipo not in TIPOS:
        raise SystemExit(f"cena de código '{tipo}' não existe. Opções: {', '.join(TIPOS)}")
    destino = destino.with_suffix(".mp4")
    assinatura = {"codigo": codigo, "duracao": round(duracao, 2), "tamanho": [largura, altura], "versao": VERSAO,
                  "destaque": destaque}
    marca = destino.with_suffix(".json")
    if destino.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
        return destino
    cena = TIPOS[tipo](largura, altura, codigo, duracao, _cor(destaque, (92, 242, 224)))
    proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{largura}x{altura}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(destino)],
                            stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for q in range(max(int(duracao * FPS), 1)):
            proc.stdin.write(cena.quadro(q / FPS).convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao gravar a cena de código {destino.name}")
    marca.write_text(json.dumps(assinatura, ensure_ascii=False), encoding="utf-8")
    return destino
