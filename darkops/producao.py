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
    """null = sem música; 'ambiente' (suspense), 'animada' (alegre) ou 'chiptune' (8 bits) = trilha sintetizada;
    'auto' = sorteia de assets/musica; ou um caminho."""
    escolha = roteiro.get("musica")
    if not escolha or escolha in ("ambiente", "animada", "chiptune"):
        return escolha or None
    if escolha.startswith("tema:"):  # faixa liberada em licencas.csv, da pasta do tema
        from .musica import escolher
        faixa, _ = escolher(escolha[5:].strip(), roteiro.get("slug", ""))
        return faixa
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
    from .perfis import carregar as carregar_perfil
    perfil = carregar_perfil()
    # o perfil dá o padrão do canal (nome, @, layout, voz, música); o roteiro pode sobrescrever
    padrao = {"layout": perfil.dados.get("layout"), "voz": perfil.dados.get("voz"),
              "musica": perfil.dados.get("musica"), "selo": perfil.dados.get("arroba"),
              "canal_nome": perfil.dados.get("nome")}
    roteiro = {**{k: v for k, v in padrao.items() if v}, **carregar(caminho)}
    formato = roteiro.get("formato", "longo")
    largura, altura = config.FORMATOS[formato]
    post = roteiro.get("layout") == "post"
    if post:  # cenas na janela; a moldura entra na junção
        largura, altura = config.JANELA_POST
    idioma = roteiro.get("idioma", "pt")
    motor = roteiro.get("motor_voz") or config.MOTOR_VOZ
    voz = roteiro.get("voz")
    velocidade = roteiro.get("velocidade", "+0%")
    usar_legenda = roteiro.get("legenda", True) if legenda is None else legenda
    slug = roteiro.get("slug") or caminho.stem
    estilo = roteiro.get("estilo")
    pixel = int(roteiro.get("pixel", 5)) if estilo == "pixel" else 0  # tamanho do pixel na tela

    obra = config.OBRA / slug / formato
    for sub in ("audio", "visuais", "cenas"):
        (obra / sub).mkdir(parents=True, exist_ok=True)

    usados: set = set()
    arquivos_cena, duracoes, visuais_usados = [], [], []
    efeitos: list[tuple[float, str]] = []  # (segundo no vídeo, som)
    total = len(roteiro["cenas"])
    for i, c in enumerate(roteiro["cenas"], 1):
        print(f"cena {i}/{total}")
        audio, palavras = narracao.narrar(c["texto"].strip(), motor, voz, velocidade, idioma,
                                          obra / "audio" / f"{i:02d}")
        pausa = float(c.get("pausa", PAUSA_PADRAO))
        visual = visuais.visual_da_cena(c, i, caminho.parent, obra / "visuais", largura, altura,
                                        roteiro.get("tipo_visual", "foto"), usados)
        dur_cena = render.duracao(audio) + pausa
        inicio_cena = sum(duracoes)
        if i > 1:
            efeitos.append((inicio_cena, "whoosh"))  # transição entre cenas
        card = None
        if c.get("animacao"):  # infográfico em card de vidro por cima do clipe, sincronizado com a fala
            from .animacoes import alvos_automaticos, eventos, gerar, posicao
            from .sincronia import momento
            alvos = c["animacao"].get("em") or alvos_automaticos(c["animacao"])
            gatilhos, depois = [], 0.0
            for alvo in alvos:  # cada elemento procura a sua palavra; sem achar, fica com o tempo padrão
                t = momento(palavras, alvo, depois)
                gatilhos.append(t)
                depois = t if t is not None else depois
            gatilhos = gatilhos if any(g is not None for g in gatilhos) else None
            card = (gerar(c["animacao"], dur_cena, largura, altura, obra / "visuais" / f"{i:02d}-animacao.mov",
                          gatilhos), *posicao(largura, altura))
            efeitos += [(inicio_cena + t, nome) for t, nome in eventos(c["animacao"], largura, altura,
                                                                      dur_cena, gatilhos)]
        narrador = None
        if roteiro.get("narrador"):  # pulga cartoon que fala junto com a voz, no canto esquerdo de baixo
            from .narrador import gerar as gerar_narrador
            lado = int(largura * (0.19 if altura < largura else 0.26))
            y = altura - lado - int(altura * (0.02 if altura < largura else 0.2))
            narrador = (gerar_narrador(audio, dur_cena, lado, obra / "visuais" / f"{i:02d}-narrador.mov",
                                       pixel),
                        int(largura * 0.01), y)
        destaque = None
        if c.get("destaque") and not c.get("animacao"):  # palavra-herói no segundo em que é falada
            from .sincronia import momento
            texto = c["destaque"]
            t = momento(palavras, c.get("destaque_em") or texto)
            if t is not None:
                destaque = (texto, t)
                efeitos.append((inicio_cena + t, "thud"))
        visuais_usados.append(visual)

        saida_cena = obra / "cenas" / f"cena{i:02d}.mp4"
        ass = None
        if usar_legenda:
            ass = obra / "cenas" / f"cena{i:02d}.ass"
            narracao.legenda_ass(palavras, largura, altura, dur_cena, ass,
                                 # no cartoon a legenda fica embaixo para não cobrir o personagem
                                 baixo=bool(c.get("animacao")) or estilo in ("cartoon", "pixel"),
                                 destaque=destaque, grande=post)
        # a cena só é refeita se áudio, visual ou legenda mudarem
        assinatura = {"render": render.VERSAO, "card": [str(card[0]), card[0].stat().st_mtime] if card else None,
                      "narrador": [str(narrador[0]), narrador[0].stat().st_mtime] if narrador else None, "audio": audio.name, "audio_mtime": audio.stat().st_mtime, "visual": str(visual),
                      "visual_mtime": visual.stat().st_mtime, "pausa": pausa, "pixel": pixel,
                      "legenda": hashlib.md5(ass.read_bytes()).hexdigest() if ass else None}
        marca = saida_cena.with_suffix(".json")
        if saida_cena.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
            duracoes.append(render.duracao(saida_cena))
        else:
            duracoes.append(render.cena(visual, audio, ass, saida_cena, largura, altura, i, pausa, card,
                                        narrador, pixel))
            marca.write_text(json.dumps(assinatura), encoding="utf-8")
        arquivos_cena.append(saida_cena)

    config.SAIDA.mkdir(parents=True, exist_ok=True)
    video = config.SAIDA / f"{slug}-{formato}.mp4"
    print("juntando cenas e mixando áudio")
    faixa = _musica(roteiro, caminho.parent)
    from .sincronia import trilha_efeitos
    sfx = trilha_efeitos(efeitos, sum(duracoes), obra / "cenas" / "efeitos.wav") \
        if roteiro.get("efeitos", True) else None
    render.juntar(arquivos_cena, faixa, video, float(roteiro.get("volume_musica", 0.12)),
                  selo=roteiro.get("selo"), efeitos=sfx,
                  mascote=roteiro.get("mascote", True),
                  post={"manchete": roteiro.get("manchete") or roteiro.get("titulo", slug),
                        "nome": roteiro.get("canal_nome", perfil.dados.get("nome")),
                        "arroba": roteiro.get("selo", perfil.dados.get("arroba")),
                        "avatar": perfil.avatar} if post else None)
    from .musica import _liberadas, salvar_credito
    licenca = _liberadas().get(faixa.relative_to(config.MUSICA).as_posix(), {})         if isinstance(faixa, Path) and faixa.is_relative_to(config.MUSICA) else {}
    salvar_credito(video, faixa or "sem música", licenca)

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
