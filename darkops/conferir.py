"""Conferência automática do vídeo pronto, antes de aprovar.

  python -m darkops conferir saida/<slug>-vertical.mp4

Procura o que costuma passar despercebido: tela preta, silêncio no meio, volume baixo ou estourado,
duração fora do padrão do canal ou acima do limite do Shorts, e resolução errada para o formato.
Não substitui assistir: é uma segunda olhada que aponta o segundo exato de cada problema.
"""
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from . import config

LIMITE_SHORTS_S = 180


def _ffmpeg(video: Path, *filtros: str) -> str:
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video), *filtros,
                           "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    return proc.stderr


def _minuto(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def conferir(video: Path, duracao_alvo: float | None = None) -> dict:
    if not video.exists():
        raise SystemExit(f"vídeo não encontrado: {video}")
    info = _ffmpeg(video)
    total = sum(float(x) * m for x, m in zip(re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups(), (3600, 60, 1)))
    largura, altura = map(int, re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", info).groups())
    achados = []

    def anotar(nivel: str, texto: str, t: float | None = None):
        achados.append({"nivel": nivel, "texto": texto, "t": round(t, 1) if t is not None else None})

    pretas = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", _ffmpeg(video, "-vf", "blackdetect=d=0.4:pic_th=0.97", "-an"))
    for ini, fim in pretas:
        ini, fim = float(ini), float(fim)
        if ini > 0.3 and fim < total - 0.3:  # o fade do começo e do fim não conta
            anotar("erro", f"tela preta de {fim - ini:.1f} s em {_minuto(ini)}", ini)

    audio = _ffmpeg(video, "-af", "silencedetect=noise=-45dB:d=1.2,volumedetect", "-vn")
    for ini, fim in zip(re.findall(r"silence_start: ([\d.]+)", audio), re.findall(r"silence_end: ([\d.]+)", audio)):
        ini, fim = float(ini), float(fim)
        if fim < total - 0.5:
            anotar("aviso", f"silêncio de {fim - ini:.1f} s em {_minuto(ini)} (narração cortada?)", ini)
    media = re.search(r"mean_volume: (-?[\d.]+) dB", audio)
    pico = re.search(r"max_volume: (-?[\d.]+) dB", audio)
    if media and float(media.group(1)) < -28:
        anotar("aviso", f"volume médio baixo ({media.group(1)} dB); o ideal fica entre -20 e -14 dB")
    if pico and float(pico.group(1)) >= -0.1:
        anotar("aviso", "o áudio bate no máximo (pode estourar no celular)")
    if not media:
        anotar("erro", "o vídeo não tem áudio")

    vertical = altura > largura
    if vertical and (largura, altura) != config.FORMATOS["vertical"]:
        anotar("aviso", f"resolução {largura}x{altura}; o vertical do projeto é 1080x1920")
    if vertical and total > LIMITE_SHORTS_S:
        anotar("erro", f"{total:.0f} s passa do limite do Shorts ({LIMITE_SHORTS_S} s)")
    if duracao_alvo and abs(total - duracao_alvo) > max(duracao_alvo * 0.4, 10):
        anotar("aviso", f"duração {total:.0f} s, longe do padrão do canal ({duracao_alvo:.0f} s)")
    if not achados:
        anotar("ok", "nenhum problema encontrado")
    return {"video": video.name, "duracao_s": round(total, 1), "resolucao": f"{largura}x{altura}", "achados": achados}


def salvar(resultado: dict, perfil) -> Path:
    destino = perfil.controle / "conferencias" / (Path(resultado["video"]).stem + ".json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def ler(perfil, video: str) -> dict:
    destino = perfil.controle / "conferencias" / (Path(video).stem + ".json")
    return json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}


SAUDACOES = ("olá", "ola", "oi pessoal", "fala galera", "bem-vindo", "bem vindo", "neste vídeo", "nesse vídeo",
             "hoje eu vou", "hoje vamos")
CHAMADAS = ("comenta", "comente", "manda", "mande", "compartilh", "envia", "marca alguém", "marque alguém", "salva")


def alcance(roteiro: dict, textos: dict | None = None) -> list[dict]:
    """Regras de alcance de docs/viralizacao.md aplicadas ao roteiro, ao título e ao texto da publicação."""
    import re as _re
    achados = []
    cenas = roteiro.get("cenas") or []
    falas = " ".join(c.get("texto", "") for c in cenas)
    primeira = _re.split(r"(?<=[.!?…])\s+", (cenas[0].get("texto", "") if cenas else "").strip())[0]
    if len(primeira.split()) > 16:
        segundos = round(len(primeira.split()) / 2.6)
        achados.append({"nivel": "aviso", "texto": f"a 1ª frase leva ~{segundos} s ({len(primeira.split())} palavras); "
                                                   "garanta que as 4 ou 5 primeiras palavras já prendam (o gancho decide em 1 a 2 s)"})
    if primeira.lower().startswith(SAUDACOES):
        achados.append({"nivel": "aviso", "texto": "o vídeo abre com saudação ou apresentação; comece direto no assunto"})
    titulo = roteiro.get("titulo") or roteiro.get("manchete") or ""
    from collections import Counter
    from .descricao import GENERICAS
    from .entrada import _conteudo
    # o começo do título (o que o feed mostra) precisa ter ao menos uma palavra de conteúdo dita no vídeo
    ditas = {w[:-1] for w in _conteudo(falas) if w not in GENERICAS}  # sem a última letra: singular e plural
    no_inicio = [w for w in _conteudo(titulo[:40]) if w not in GENERICAS]
    if no_inicio and not any(w[:-1] in ditas for w in no_inicio):
        principais = [p for p, _ in Counter(w for w in _conteudo(falas) if w not in GENERICAS).most_common(3)]
        achados.append({"nivel": "aviso", "texto": f"o começo do título não tem nenhuma palavra dita no vídeo; use o assunto (ex.: {', '.join(principais)})"})
    if len(titulo) > 100:
        achados.append({"nivel": "erro", "texto": "o título passa de 100 caracteres (limite do YouTube)"})
    final = (cenas[-1].get("texto", "") if cenas else "").lower()
    if not any(c in final for c in CHAMADAS):
        achados.append({"nivel": "aviso", "texto": "a última cena não convida a comentar ou mandar para alguém (envios contam muito no Reels)"})
    if textos:
        from .descricao import checar
        achados += [{"nivel": "aviso", "texto": a} for a in checar(textos.get("descricao", ""), textos.get("tags", []),
                                                                 textos.get("hashtags", []))]
    return achados
