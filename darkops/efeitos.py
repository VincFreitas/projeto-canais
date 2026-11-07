"""Banco de efeitos sonoros reais de licença CC0, para o som não ser igual em todo vídeo.

  python -m darkops efeitos-baixar [--por-tipo 6]   busca no Openverse (sem chave) e grava em assets/efeitos/<tipo>/

Só entra som CC0 (domínio público, sem crédito obrigatório) e todo arquivo fica registrado em
assets/efeitos/licencas.csv (arquivo;licenca;credito;fonte), como a música. A mixagem sorteia, por vídeo, uma
variação de cada tipo entre os sons do banco e o sintetizado de sincronia.py.
"""
import csv
import subprocess

import imageio_ffmpeg
import requests

from . import config
from .seguranca import ocultar

PASTA = config.RAIZ / "assets" / "efeitos"
LICENCAS = PASTA / "licencas.csv"
API = "https://api.openverse.org/v1/audio/"
# tipo -> (buscas, duração máxima em segundos depois do corte)
TIPOS = {
    "whoosh": (["whoosh", "swoosh transition"], 1.0),
    "pop": (["pop click", "bubble pop"], 0.4),
    "ding": (["ding bell notification", "chime"], 1.5),
    "thud": (["thud", "low hit"], 0.9),
    "riser": (["riser", "rising whoosh tension"], 2.5),
    "impacto": (["cinematic impact boom", "braam hit"], 2.0),
}


def registrados(todos: bool = False) -> dict[str, dict]:
    """caminho relativo (tipo/arquivo.wav) -> {licenca, credito, fonte}. Só o que está no CSV como cc0 vale;
    todos=True inclui as linhas "recusado" (som que não serviu e não deve ser baixado de novo)."""
    if not LICENCAS.exists():
        return {}
    with LICENCAS.open(encoding="utf-8") as f:
        return {l["arquivo"]: l for l in csv.DictReader(f, delimiter=";") if todos or l.get("licenca") == "cc0"}


def do_tipo(tipo: str) -> list:
    banco = registrados()
    return sorted(PASTA / a for a in banco if a.startswith(f"{tipo}/") and (PASTA / a).is_file())


def _converter(url: str, destino, maximo: float, final: bool = False) -> bool:
    """Baixa, corta no máximo do tipo e grava WAV 48 kHz mono. Começo do som com fade no fim; com final=True
    (riser), os últimos segundos com fade na entrada, porque o clímax fica no fim."""
    bruto = requests.get(url, timeout=60, headers={"User-Agent": "projeto-canais"})
    bruto.raise_for_status()
    temporario = destino.with_suffix(".baixado")
    temporario.write_bytes(bruto.content)
    corte = (["-sseof", f"-{maximo:.2f}", "-i", str(temporario)], "afade=t=in:d=0.3") if final else \
        (["-i", str(temporario), "-t", f"{maximo:.2f}"],
         f"silenceremove=start_periods=1:start_threshold=-50dB,afade=t=out:st={max(maximo - 0.15, 0):.2f}:d=0.15")
    try:
        proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                               *corte[0], "-af", corte[1], "-ac", "1", "-ar", "48000", str(destino)],
                              capture_output=True)
        return proc.returncode == 0 and destino.exists()
    finally:
        temporario.unlink(missing_ok=True)


def baixar(por_tipo: int = 6) -> dict[str, int]:
    PASTA.mkdir(parents=True, exist_ok=True)
    banco = registrados(todos=True)
    contagem = {}
    for tipo, (buscas, maximo) in TIPOS.items():
        (PASTA / tipo).mkdir(exist_ok=True)
        tem = len([a for a in banco if a.startswith(f"{tipo}/") and banco[a].get("licenca") == "cc0"])
        for busca in buscas:
            if tem >= por_tipo:
                break
            try:
                # só Freesound: as outras fontes do Openverse trazem gravação de pronúncia e música
                r = requests.get(API, params={"q": busca, "license": "cc0", "source": "freesound", "page_size": 20},
                                 headers={"User-Agent": "projeto-canais"}, timeout=60)
                r.raise_for_status()
                resultados = r.json().get("results", [])
            except (requests.RequestException, ValueError) as erro:
                print(ocultar(f"  busca '{busca}' falhou: {erro}"))
                continue
            for item in resultados:
                if tem >= por_tipo:
                    break
                if item.get("license") != "cc0" or not item.get("url") or (item.get("duration") or 0) > 8000:
                    continue  # confere a licença de novo e pula gravação longa (trilha, ambiente)
                nome = f"{tipo}/{item['source']}-{item['id'][:8]}.wav"
                if nome in banco:
                    continue
                try:
                    if not _converter(item["url"], PASTA / nome, maximo, final=tipo == "riser"):
                        continue
                except (requests.RequestException, OSError) as erro:
                    print(ocultar(f"  {tipo}: {erro}"))
                    continue
                autor = item.get("creator") or "autor desconhecido"
                linha = {"arquivo": nome, "licenca": "cc0",
                         "credito": f"{item.get('title', '').strip()[:80]}, de {autor} (CC0)",
                         "fonte": item.get("foreign_landing_url") or item["url"]}
                _registrar(linha)  # um a um: uma queda da internet no meio não perde o que já baixou
                banco[nome] = linha
                tem += 1
        contagem[tipo] = tem
    return contagem


def _registrar(linha: dict) -> None:
    novo = not LICENCAS.exists()
    with LICENCAS.open("a", encoding="utf-8", newline="") as f:
        escrita = csv.DictWriter(f, fieldnames=["arquivo", "licenca", "credito", "fonte"], delimiter=";")
        if novo:
            escrita.writeheader()
        escrita.writerow(linha)
