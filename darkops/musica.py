"""Escolha da trilha de cada vídeo e crédito de licença.

Só entram faixas listadas em assets/musica/licencas.csv (arquivo;licenca;credito), com
licença livre conferida pelo usuário. Assim um MP3 com direitos autorais na pasta nunca
vai para um vídeo publicado (Content ID e strike no canal).
"""
import csv
import json
import random
from pathlib import Path

from . import config

LICENCAS = config.MUSICA / "licencas.csv"
EXT_AUDIO = {".mp3", ".wav", ".m4a", ".ogg"}
LIVRES = {"cc0", "cc-by", "pixabay", "youtube-audio-library", "propria"}


def _liberadas() -> dict[str, dict]:
    """caminho relativo (com /) -> {licenca, credito}."""
    if not LICENCAS.exists():
        return {}
    with LICENCAS.open(encoding="utf-8-sig", newline="") as f:
        linhas = csv.DictReader(f, delimiter=";")
        return {l["arquivo"].strip().replace("\\", "/"): {"licenca": l["licenca"].strip().lower(),
                                                          "credito": (l.get("credito") or "").strip()}
                for l in linhas if l.get("arquivo") and (l.get("licenca") or "").strip().lower() in LIVRES}


def escolher(tema: str, semente: str) -> tuple[Path | str, dict]:
    """Faixa liberada da pasta do tema (ou de qualquer pasta); sem nenhuma, a trilha 'animada'."""
    liberadas = _liberadas()
    def candidatas(pasta: Path) -> list[Path]:
        if not pasta.is_dir():
            return []
        return sorted(p for p in pasta.rglob("*") if p.suffix.lower() in EXT_AUDIO
                      and p.relative_to(config.MUSICA).as_posix() in liberadas)
    opcoes = candidatas(config.MUSICA / tema) if tema else []
    if not opcoes:
        if tema:
            print(f"  sem faixa liberada em assets/musica/{tema}; usando trilha animada sintetizada")
        return "animada", {}
    escolhida = random.Random(semente).choice(opcoes)
    return escolhida, liberadas[escolhida.relative_to(config.MUSICA).as_posix()]


def salvar_credito(video: Path, faixa: Path | str, licenca: dict) -> None:
    """Grava ao lado do vídeo qual faixa entrou, para a publicação pôr o crédito."""
    dados = {"faixa": faixa.name if isinstance(faixa, Path) else str(faixa), **licenca}
    video.with_name(video.stem + "-musica.json").write_text(json.dumps(dados, ensure_ascii=False),
                                                           encoding="utf-8")


def credito(video: Path) -> str:
    """Texto de crédito para descrição ou legenda ('' quando a faixa não exige)."""
    arquivo = video.with_name(video.stem + "-musica.json")
    if not arquivo.exists():
        return ""
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    if dados.get("licenca") != "cc-by" or not dados.get("credito"):
        return ""
    return f"Música: {dados['credito']}"
