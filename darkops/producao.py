"""Roteiro JSON -> vídeo pronto + thumbnail + metadados por plataforma."""
import hashlib
import json
import random
from pathlib import Path

from . import config, narracao, render, visuais

PAUSA_PADRAO = 0.35
LIMITE_VERTICAL_S = 180  # Shorts aceita até 3 min; TikTok e Reels rendem melhor bem abaixo disso


def carregar(caminho: Path) -> dict:
    roteiro = json.loads(caminho.read_text(encoding="utf-8"))
    erros = []
    if roteiro.get("formato", "longo") not in config.FORMATOS:
        erros.append(f"formato deve ser um de {list(config.FORMATOS)}")
    cenas = roteiro.get("cenas") or []
    if not cenas:
        erros.append("roteiro sem cenas")
    for i, c in enumerate(cenas, 1):
        if not (c.get("texto") or "").strip():
            erros.append(f"cena {i} sem texto")
    if erros:
        raise SystemExit(f"Roteiro inválido ({caminho.name}):\n- " + "\n- ".join(erros))
    return roteiro


def _musica(roteiro: dict, pasta_roteiro: Path) -> Path | str | None:
    """null = sem música; 'ambiente' = trilha sintetizada; 'auto' = sorteia de assets/musica; ou um caminho."""
    escolha = roteiro.get("musica")
    if not escolha or escolha == "ambiente":
        return escolha or None
    if escolha == "auto":
        opcoes = sorted(p for p in config.MUSICA.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"})
        if not opcoes:
            print("  assets/musica está vazia; usando trilha ambiente sintetizada")
            return "ambiente"
        return random.choice(opcoes)
    caminho = Path(escolha)
    if not caminho.is_absolute():
        caminho = config.RAIZ / caminho if (config.RAIZ / caminho).exists() else pasta_roteiro / caminho
    if not caminho.exists():
        raise SystemExit(f"Música não encontrada: {caminho}")
    return caminho


def _capitulos(roteiro: dict, duracoes: list[float]) -> list[str]:
    """Capítulos do YouTube: precisam começar em 00:00, ter 3+ itens e 10 s+ cada."""
    linhas, t = [], 0.0
    for c, d in zip(roteiro["cenas"], duracoes):
        if c.get("capitulo"):
            linhas.append((t, c["capitulo"]))
        t += d
    if len(linhas) < 3 or linhas[0][0] > 0.5:
        return []
    return [f"{int(s // 60):02d}:{int(s % 60):02d} {nome}" for s, nome in linhas]


def _metadados(roteiro: dict, duracoes: list[float], destino: Path) -> None:
    meta = roteiro.get("metadados") or {}
    total = sum(duracoes)
    partes = [f"# {roteiro.get('titulo', destino.stem)}", "",
              f"Duração: {int(total // 60)}min{int(total % 60):02d}s · formato {roteiro.get('formato', 'longo')}", ""]
    capitulos = _capitulos(roteiro, duracoes)
    for plataforma, dados in meta.items():
        partes.append(f"## {plataforma}")
        for chave, valor in dados.items():
            if isinstance(valor, list):
                valor = (" ".join(valor) if chave == "hashtags" else ", ".join(valor))
            partes.append(f"**{chave}:**\n\n{valor}\n")
        if plataforma == "youtube" and capitulos:
            partes.append("**capítulos (colar na descrição):**\n\n" + "\n".join(capitulos) + "\n")
    partes += ["## Antes de publicar",
               "- Assista inteiro: a entrega cumpre o que o título e a thumbnail prometem?",
               "- Se houver imagem ou vídeo realista gerado por IA, marque 'conteúdo alterado ou sintético' no YouTube Studio.",
               "- Confirme a licença de todas as imagens, clipes e músicas."]
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")


def produzir(caminho: Path, legenda: bool | None = None) -> Path:
    caminho = caminho.resolve()
    roteiro = carregar(caminho)
    formato = roteiro.get("formato", "longo")
    largura, altura = config.FORMATOS[formato]
    idioma = roteiro.get("idioma", "pt")
    motor = roteiro.get("motor_voz") or config.MOTOR_VOZ
    voz = roteiro.get("voz")
    velocidade = roteiro.get("velocidade", "+0%")
    usar_legenda = roteiro.get("legenda", True) if legenda is None else legenda
    slug = roteiro.get("slug") or caminho.stem

    obra = config.OBRA / slug / formato
    for sub in ("audio", "visuais", "cenas"):
        (obra / sub).mkdir(parents=True, exist_ok=True)

    usados: set = set()
    arquivos_cena, duracoes, visuais_usados = [], [], []
    total = len(roteiro["cenas"])
    for i, c in enumerate(roteiro["cenas"], 1):
        print(f"cena {i}/{total}")
        audio, palavras = narracao.narrar(c["texto"].strip(), motor, voz, velocidade, idioma,
                                          obra / "audio" / f"{i:02d}")
        visual = visuais.visual_da_cena(c, i, caminho.parent, obra / "visuais", largura, altura,
                                        roteiro.get("tipo_visual", "foto"), usados)
        visuais_usados.append(visual)
        pausa = float(c.get("pausa", PAUSA_PADRAO))

        saida_cena = obra / "cenas" / f"cena{i:02d}.mp4"
        ass = None
        if usar_legenda:
            ass = obra / "cenas" / f"cena{i:02d}.ass"
            narracao.legenda_ass(palavras, largura, altura, render.duracao(audio) + pausa, ass)
        # a cena só é refeita se áudio, visual ou legenda mudarem
        assinatura = {"audio": audio.name, "audio_mtime": audio.stat().st_mtime, "visual": str(visual),
                      "visual_mtime": visual.stat().st_mtime, "pausa": pausa,
                      "legenda": hashlib.md5(ass.read_bytes()).hexdigest() if ass else None}
        marca = saida_cena.with_suffix(".json")
        if saida_cena.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
            duracoes.append(render.duracao(saida_cena))
        else:
            duracoes.append(render.cena(visual, audio, ass, saida_cena, largura, altura, i, pausa))
            marca.write_text(json.dumps(assinatura), encoding="utf-8")
        arquivos_cena.append(saida_cena)

    config.SAIDA.mkdir(parents=True, exist_ok=True)
    video = config.SAIDA / f"{slug}-{formato}.mp4"
    print("juntando cenas e mixando áudio")
    render.juntar(arquivos_cena, _musica(roteiro, caminho.parent), video,
                  float(roteiro.get("volume_musica", 0.12)))

    if sum(duracoes) > LIMITE_VERTICAL_S and formato == "vertical":
        print(f"  aviso: vertical com {sum(duracoes):.0f}s passa de {LIMITE_VERTICAL_S}s; encurte para Shorts/Reels")

    if formato == "longo":
        thumb = roteiro.get("thumbnail") or {}
        imagem = None
        if thumb.get("arquivo"):
            imagem = (caminho.parent / thumb["arquivo"]).resolve()
        else:
            imagem = next((v for v in visuais_usados if v.suffix.lower() in visuais.EXT_IMAGEM), None)
        texto = thumb.get("texto") or roteiro.get("titulo", slug)
        visuais.thumbnail(imagem, texto, config.SAIDA / f"{slug}-thumb.jpg")

    _metadados(roteiro, duracoes, config.SAIDA / f"{slug}-{formato}-metadados.md")
    print(f"pronto: {video} ({sum(duracoes):.0f}s)")
    return video
