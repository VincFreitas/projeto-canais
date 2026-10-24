"""Roteiro JSON -> vídeo pronto + thumbnail + metadados por plataforma."""
import hashlib
import json
import random
from pathlib import Path

from . import config, narracao, render, visuais
from .perfis import TAMANHOS_LEGENDA

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
    if roteiro.get("creditos_imagens"):
        partes += ["## Créditos das imagens (colar na descrição)",
                   "\n".join(roteiro["creditos_imagens"]) + "\nA NASA não endossa este vídeo.", ""]
    if roteiro.get("estilo") in visuais.ESTILOS_SINTETICOS or roteiro.get("sintetico"):
        partes += ["## ATENÇÃO: conteúdo sintético",
                   "Este vídeo tem imagens realistas feitas por IA. No upload, marque 'conteúdo alterado ou sintético' "
                   "no YouTube Studio e o selo de IA no Instagram.", ""]
    partes += ["## Antes de publicar",
               "- Assista inteiro: a entrega cumpre o que o título e a thumbnail prometem?",
               "- Se houver imagem ou vídeo realista gerado por IA, marque 'conteúdo alterado ou sintético' no YouTube Studio.",
               "- Confirme a licença de todas as imagens, clipes e músicas."]
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")


def _aplicar_edicao(roteiro: dict) -> None:
    """Nível de edição do canal: 'simples' tira os elementos da tela (cards, palavra-herói, termo e etiquetas);
    'leve' deixa a palavra-herói e só os 2 primeiros cards; 'pro' (padrão) usa tudo que o roteiro trouxer."""
    edicao = roteiro.get("edicao", "pro")
    if edicao == "pro":
        return
    cards = 0
    for c in roteiro["cenas"]:
        if edicao == "simples":
            for campo in ("animacao", "destaque", "termo", "rotulos"):
                c.pop(campo, None)
        elif c.get("animacao"):
            cards += 1
            if cards > 2:
                c.pop("animacao")


def _tipo_da_cena(roteiro: dict, indice: int) -> str:
    """'misto' alterna clipe e foto na proporção pedida (proporcao_video = % de cenas com clipe),
    sempre igual para o mesmo roteiro, para o cache das cenas continuar valendo."""
    tipo = roteiro.get("tipo_visual", "foto")
    if tipo != "misto":
        return tipo
    proporcao = int(roteiro.get("proporcao_video", 50))
    # espalha os clipes: a cena vira clipe quando a conta acumulada passa de mais um inteiro
    return "video" if (indice * proporcao) // 100 > ((indice - 1) * proporcao) // 100 else "foto"


def produzir(caminho: Path, legenda: bool | None = None) -> Path:
    caminho = caminho.resolve()
    from .perfis import carregar as carregar_perfil
    perfil = carregar_perfil()
    # o perfil dá o padrão do canal (nome, @, layout, voz, música); o roteiro pode sobrescrever
    padrao = {"layout": perfil.dados.get("layout"), "voz": perfil.dados.get("voz"),
              "musica": perfil.dados.get("musica"), "selo": perfil.dados.get("arroba"),
              "canal_nome": perfil.dados.get("nome"), "estilo": perfil.dados.get("estilo"),
              "narrador": perfil.dados.get("narrador"), "pixel": perfil.dados.get("pixel"),
              "motor_voz": perfil.dados.get("motor_voz") if perfil.dados.get("motor_voz") != "auto" else None,
              "tipo_visual": perfil.dados.get("tipo_visual"), "proporcao_video": perfil.dados.get("proporcao_video"),
              "legenda_fonte": perfil.dados.get("legenda_fonte"), "legenda_tamanho": perfil.dados.get("legenda_tamanho"),
              "legenda_cor": perfil.dados.get("legenda_cor"), "velocidade": perfil.dados.get("velocidade"),
              "tema_cards": perfil.dados.get("tema_cards"), "edicao": perfil.dados.get("edicao")}
    roteiro = {**{k: v for k, v in padrao.items() if v}, **carregar(caminho)}
    _aplicar_edicao(roteiro)
    visuais.ACERVO_NASA = bool(roteiro.get("acervo_nasa", perfil.dados.get("acervo_nasa")))
    visuais.CREDITOS.clear()
    if "legenda" not in roteiro and perfil.arquivo.exists():
        roteiro["legenda"] = perfil.dados.get("legenda", True)
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
    palavra = roteiro.get("legenda_modo") == "palavra"  # formato explicativo: uma palavra por vez

    obra = config.OBRA / slug / formato
    for sub in ("audio", "visuais", "cenas"):
        (obra / sub).mkdir(parents=True, exist_ok=True)

    usados: set = set()
    arquivos_cena, duracoes, visuais_usados = [], [], []
    efeitos: list[tuple[float, str]] = []  # (segundo no vídeo, som)
    total = len(roteiro["cenas"])
    for i, c in enumerate(roteiro["cenas"], 1):
        print(f"cena {i}/{total}")
        if c.get("audio"):  # narração pronta: o trecho do áudio enviado, com o tempo das palavras já medido
            audio = (caminho.parent / c["audio"]).resolve()
            if not audio.exists():
                raise SystemExit(f"Cena {i}: áudio não encontrado: {audio}")
            palavras = c.get("palavras") or []
        else:
            audio, palavras = narracao.narrar(c["texto"].strip(), motor, voz, velocidade, idioma,
                                              obra / "audio" / f"{i:02d}")
        pausa = float(c.get("pausa", PAUSA_PADRAO))
        visual, depois_img = None, None
        # palco: a cena é programada em código (cenas/<slug>.py), sem desenho de IA nem busca de mídia
        palco = (config.RAIZ / roteiro["palco"]) if roteiro.get("palco") and pixel and not post else None
        if palco is None and estilo in visuais.ESTILOS_IA and c.get("ilustracao") and not c.get("arquivo"):
            visual = visuais.ilustracao_local(c["ilustracao"], roteiro.get("personagem", ""), i, obra / "visuais",
                                              largura, altura, estilo, slug, pixel)
            if visual is not None and c.get("ilustracao_depois"):  # o mesmo objeto depois da mudança
                depois_img = visuais.ilustracao_local(c["ilustracao_depois"], roteiro.get("personagem", ""), i,
                                                      obra / "visuais", largura, altura, estilo, slug, pixel)
        # cena viva: câmera, partículas e etiquetas presas ao objeto (pixel art em tela cheia)
        viva = (visual is not None and pixel and not post and roteiro.get("cena_viva", True)
                and visual.suffix.lower() in visuais.EXT_IMAGEM)
        if visual is None and palco is None:
            visual = visuais.visual_da_cena(c, i, caminho.parent, obra / "visuais", largura, altura,
                                            _tipo_da_cena(roteiro, i), usados)
        dur_cena = render.duracao(audio) + pausa
        inicio_cena = sum(duracoes)
        if i > 1:
            efeitos.append((inicio_cena, "whoosh"))  # transição entre cenas
        card = None
        if c.get("animacao"):  # infográfico em card de vidro por cima do clipe, sincronizado com a fala
            from .animacoes import alvos_automaticos, eventos, gerar, posicao
            from .sincronia import momento
            tema = roteiro.get("tema_cards")
            if tema and tema != "padrao" and "tema" not in c["animacao"]:  # tema de edição do canal
                c["animacao"] = {**c["animacao"], "tema": tema}
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
            # com a legenda de uma palavra, o meio de baixo fica livre e a pulga desce para o canto
            margem = 0.02 if altura < largura else 0.04 if palavra else 0.2
            y = altura - lado - int(altura * margem)
            narrador = (gerar_narrador(audio, dur_cena, lado, obra / "visuais" / f"{i:02d}-narrador.mov",
                                       pixel, c.get("expressao", "normal")),
                        int(largura * 0.01), y)
        destaque = None
        if c.get("destaque") and not c.get("animacao"):  # palavra-herói no segundo em que é falada
            from .sincronia import momento
            texto = c["destaque"]
            t = momento(palavras, c.get("destaque_em") or texto)
            if t is not None:
                destaque = (texto, t)
                efeitos.append((inicio_cena + t, "thud"))
        termo, rotulos, rotulos_vivos = None, [], []
        if c.get("termo"):  # "Esse é o tungstênio": o nome técnico fica no topo até o fim da cena
            from .sincronia import momento
            t = momento(palavras, c.get("termo_em") or c["termo"])
            termo = (c["termo"], t if t is not None else 0.2)
            efeitos.append((inicio_cena + termo[1], "thud"))
        for r in c.get("rotulos", []):  # etiquetas presas ao objeto, cada uma na sua palavra
            from .sincronia import momento
            t = momento(palavras, r.get("em") or r["texto"])
            rotulos.append((r["texto"], float(r.get("x", 0.5)), float(r.get("y", 0.4)), t if t is not None else 0.3))
            rotulos_vivos.append((*rotulos[-1], r.get("alvo")))
            efeitos.append((inicio_cena + rotulos[-1][3], "pop"))
        visuais_usados.append(visual)
        if viva:
            from .cinema import gerar as gerar_cena_viva
            from .sincronia import momento
            t_depois = None
            if depois_img is not None:
                t_depois = momento(palavras, c.get("depois_em") or "") if c.get("depois_em") else None
                t_depois = t_depois if t_depois is not None else dur_cena * 0.5
                efeitos.append((inicio_cena + t_depois, "whoosh"))
            impactos = [t for t in (termo[1] if termo else None, destaque[1] if destaque else None) if t is not None]
            visual = gerar_cena_viva(visual, depois_img, t_depois, dur_cena, largura, altura, pixel, i, c, palavras,
                                     rotulos_vivos, impactos, obra / "visuais" / f"{i:02d}-viva.mp4")
            rotulos = []  # as etiquetas agora andam com a câmera, dentro da cena viva
        elif palco is not None:
            from .palco import gerar as gerar_palco
            if c.get("nova_peca"):
                from .sincronia import momento
                t = momento(palavras, c.get("nova_em") or c["nova_peca"])
                efeitos.append((inicio_cena + (t if t is not None else 0.4), "pop"))
            impactos = [t for t in (termo[1] if termo else None, destaque[1] if destaque else None) if t is not None]
            visual = gerar_palco(palco, roteiro["cenas"], i, dur_cena, palavras, largura, altura, pixel, inicio_cena,
                                 impactos, obra / "visuais" / f"{i:02d}-palco.mp4")
            rotulos = []  # o palco desenha as etiquetas presas às peças
            viva = True  # o palco traz a própria transição

        saida_cena = obra / "cenas" / f"cena{i:02d}.mp4"
        ass = None
        if usar_legenda:
            ass = obra / "cenas" / f"cena{i:02d}.ass"
            narracao.legenda_ass(palavras, largura, altura, dur_cena, ass,
                                 # no cartoon a legenda fica embaixo para não cobrir o personagem
                                 baixo=bool(c.get("animacao")) or estilo in ("cartoon", "pixel"),
                                 destaque=destaque, grande=post,
                                 fonte=roteiro.get("legenda_fonte", "Arial Black"),
                                 escala=TAMANHOS_LEGENDA.get(roteiro.get("legenda_tamanho", "media"), 1.0),
                                 cor=roteiro.get("legenda_cor", "#FFE500"),
                                 palavra=palavra, termo=termo, rotulos=rotulos)
        # a cena só é refeita se áudio, visual ou legenda mudarem
        assinatura = {"render": render.VERSAO, "card": [str(card[0]), card[0].stat().st_mtime] if card else None,
                      "narrador": [str(narrador[0]), narrador[0].stat().st_mtime] if narrador else None, "audio": audio.name, "audio_mtime": audio.stat().st_mtime, "visual": str(visual),
                      "visual_mtime": visual.stat().st_mtime, "pausa": pausa, "pixel": pixel,
                      "movimento": c.get("movimento"),
                      "legenda": hashlib.md5(ass.read_bytes()).hexdigest() if ass else None}
        marca = saida_cena.with_suffix(".json")
        if saida_cena.exists() and marca.exists() and json.loads(marca.read_text(encoding="utf-8")) == assinatura:
            duracoes.append(render.duracao(saida_cena))
        else:
            duracoes.append(render.cena(visual, audio, ass, saida_cena, largura, altura, i, pausa, card,
                                        narrador, pixel, c.get("movimento"), transicao=not viva))
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
                  # no palco, o nome do canal já vai na barra de peças, no lugar do selo
                  selo=None if roteiro.get("palco") else roteiro.get("selo"), efeitos=sfx,
                  # a pulga narradora já faz o papel do mascote do canto
                  mascote=roteiro.get("mascote", not roteiro.get("narrador")),
                  post={"manchete": roteiro.get("manchete") or roteiro.get("titulo", slug),
                        "nome": roteiro.get("canal_nome", perfil.dados.get("nome")),
                        "arroba": roteiro.get("selo", perfil.dados.get("arroba")),
                        "avatar": perfil.avatar, "pixel": pixel} if post else None)
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

    roteiro["creditos_imagens"] = sorted(visuais.CREDITOS)
    _metadados(roteiro, duracoes, config.SAIDA / f"{slug}-{formato}-metadados.md")
    print(f"pronto: {video} ({sum(duracoes):.0f}s)")
    return video
