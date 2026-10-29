"""Montagem com ffmpeg: uma cena por arquivo (cacheável), depois concatenação e mixagem final."""
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from .visuais import EXT_VIDEO

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
ZOOM = 0.12  # quanto a imagem aproxima/afasta ao longo da cena
TRANSICAO = 0.15  # segundos de entrada (do preto) em cada cena, marca o corte sem dessincronizar o áudio
VERSAO = 4  # mude para refazer as cenas em cache quando o visual do render mudar


def rodar(args: list[str], cwd: Path | None = None) -> None:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou:\n{proc.stderr[-2000:]}")


def duracao(arquivo: Path) -> float:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(arquivo)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    achado = re.search(r"Duration: (\d+):(\d+):([\d.]+)", proc.stderr)
    if not achado:
        raise RuntimeError(f"não consegui ler a duração de {arquivo}")
    h, m, s = achado.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


MOVIMENTOS = {"aproxima": 0, "afasta": 1, "panoramica_direita": 2, "panoramica_esquerda": 3}


def _movimento(indice: int, quadros: int, escolhido: str | None = None) -> str:
    """Alterna aproximar, afastar e panorâmica para as cenas não parecerem iguais; o editor de cenas
    pode fixar um deles (escolhido)."""
    tipo = MOVIMENTOS.get(escolhido, indice % 4)
    if tipo == 0:
        z, x = f"1+{ZOOM}*on/{quadros}", "(iw-iw/zoom)/2"
    elif tipo == 1:
        z, x = f"{1 + ZOOM}-{ZOOM}*on/{quadros}", "(iw-iw/zoom)/2"
    elif tipo == 2:
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*on/{quadros}"
    else:
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*(1-on/{quadros})"
    return f"zoompan=z='{z}':x='{x}':y='(ih-ih/zoom)/2':d={quadros}"


def cena(visual: Path, audio: Path, legenda: Path | None, saida: Path,
         largura: int, altura: int, indice: int, pausa: float,
         card: tuple[Path, int, int] | None = None, narrador: tuple[Path, int, int] | None = None,
         pixel: int = 0, movimento: str | None = None, transicao: bool = True) -> float:
    """Renderiza uma cena com a duração da narração + pausa. Devolve a duração.

    card = (vídeo com transparência, x, y): infográfico por cima do clipe, que fica desfocado e
    um pouco mais escuro para o card se destacar. pixel = tamanho do pixel no estilo pixel art: a imagem
    é ampliada sem suavizar e anda em degraus de pixel, como num jogo antigo."""
    dur = duracao(audio) + pausa
    quadros = max(int(dur * FPS), 1)
    legendas = f",ass={legenda.name}" if legenda else ""  # caminho relativo evita escapar 'C:' no filtro
    if visual.suffix.lower() in EXT_VIDEO:
        entrada = ["-stream_loop", "-1", "-i", str(visual)]
        video = (f"[0:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
                 f"crop={largura}:{altura},fps={FPS},setsar=1")
        if pixel:
            video += (f",scale={largura // pixel}:{altura // pixel}:flags=area,"
                      f"scale={largura // pixel * pixel}:{altura // pixel * pixel}:flags=neighbor,"
                      f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2")
    elif pixel:
        entrada = ["-loop", "1", "-i", str(visual)]
        folga = pixel * 16  # margem para a panorâmica
        x = f"floor({folga}*t/{dur:.3f}/{pixel})*{pixel}"
        if indice % 2 == 0:
            x = f"{folga}-{x}"
        grade_w, grade_h = -(-(largura + folga) // pixel), -(-(altura + folga) // pixel)
        video = (f"[0:v]scale={grade_w}:{grade_h}:force_original_aspect_ratio=increase:flags=area,"
                 f"scale=iw*{pixel}:ih*{pixel}:flags=neighbor,crop={largura}:{altura}:x='{x}':y='floor((ih-{altura})/2/{pixel})*{pixel}',"
                 f"fps={FPS},setsar=1")
    else:
        entrada = ["-i", str(visual)]
        # ampliar antes do zoompan tira o tremido causado pelo arredondamento de pixels
        video = (f"[0:v]scale={largura * 2}:{altura * 2}:force_original_aspect_ratio=increase,"
                 f"crop={largura * 2}:{altura * 2},{_movimento(indice, quadros, movimento)}:s={largura}x{altura}:fps={FPS},"
                 f"setsar=1")
    # a cena viva (cinema.py) já traz a própria transição de entrada
    entrada_suave = f",fade=t=in:st=0:d={TRANSICAO}" if transicao else ""
    extra = []
    if card:
        arquivo, x, y = card
        extra = ["-i", str(arquivo)]
        if pixel:  # sem desfoque (borraria os pixels); o card também vira pixel art
            video += (f",eq=brightness=-0.12[base];[2:v]format=rgba,scale=iw/{pixel}:ih/{pixel}:flags=area,"
                      "lutrgb=r='floor(val/40)*40':g='floor(val/40)*40':b='floor(val/40)*40',"  # poucas cores
                      f"scale=iw*{pixel}:ih*{pixel}:flags=neighbor[card];")
        else:
            video += ",boxblur=7:1,eq=brightness=-0.07[base];[2:v]format=rgba[card];"
        video += f"[base][card]overlay=x={x}:y={y}:eof_action=pass:format=auto"
    if narrador:  # a pulga que fala, num canto da cena
        arquivo_n, xn, yn = narrador
        indice = 2 + (1 if card else 0)
        extra += ["-i", str(arquivo_n)]
        video += (f"[pre];[{indice}:v]format=rgba[nar];"
                  f"[pre][nar]overlay=x={xn}:y={yn}:eof_action=pass:format=auto")
    filtro = f"{video}{entrada_suave}{legendas},format=yuv420p[v];[1:a]aresample=48000,apad[a]"
    rodar([*entrada, "-i", str(audio), *extra, "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
           "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-r", str(FPS),
           "-pix_fmt", "yuv420p", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "192k", "-ac", "2", saida.name], cwd=saida.parent)
    return dur


def ambiente(duracao_s: float, destino: Path) -> Path:
    """Trilha de suspense sintetizada (ruído grave + drones): livre de direitos, sem download."""
    filtro = ("anoisesrc=color=brown:amplitude=0.5,lowpass=f=300,volume=0.6[n];"
              "sine=f=55,volume=0.35,tremolo=f=0.15:d=0.6[a];"
              "sine=f=82.41,volume=0.2,tremolo=f=0.11:d=0.7[b];"
              "sine=f=116.54,volume=0.08,tremolo=f=0.1:d=0.9[c];"
              "[n][a][b][c]amix=inputs=4:normalize=0,aecho=0.8:0.7:900:0.4,"
              "highpass=f=35,alimiter=limit=0.8[out]")
    rodar(["-filter_complex", filtro, "-map", "[out]", "-t", f"{duracao_s:.2f}", "-ar", "48000", "-ac", "2",
           str(destino)])
    return destino


def animada(duracao_s: float, destino: Path, semente: str = "", chip: bool = False) -> Path:
    """Trilha alegre sintetizada (bumbo, palmas, chimbal, baixo e arpejo em I-V-vi-IV): livre de direitos.

    A semente (slug do vídeo) varia tom e andamento, para os vídeos não soarem todos iguais.
    chip = baixo e arpejo em onda quadrada, som de videogame 8 bits (para o estilo pixel).
    """
    import wave
    import zlib

    import numpy as np

    taxa = 48000
    rng = np.random.default_rng(zlib.crc32(semente.encode("utf-8")))
    bpm = float(rng.choice([104, 108, 112, 116]))
    tom = int(rng.integers(-3, 4))                    # semitons a partir de Dó
    batida = 60 / bpm
    n = int((duracao_s + 1) * taxa)
    t = np.arange(n) / taxa
    esq, dir_ = np.zeros(n), np.zeros(n)

    def osc(fase):  # fase em ciclos; senoide ou quadrada (chiptune)
        return np.sign(np.sin(2 * np.pi * fase)) * 0.5 if chip else np.sin(2 * np.pi * fase)

    def nota(semitom: int) -> float:                  # 0 = Dó4
        return 261.63 * 2 ** ((semitom + tom) / 12)

    def soar(inicio: float, duracao: float, onda, ganho: float, pan: float = 0.0) -> None:
        i0, i1 = int(inicio * taxa), min(int((inicio + duracao) * taxa), n)
        if i0 >= n:
            return
        trecho = onda(t[: i1 - i0]) * ganho
        esq[i0:i1] += trecho * (1 - pan)
        dir_[i0:i1] += trecho * (1 + pan)

    # acordes de 1 compasso cada: C, G, Am, F (fundamental + terça + quinta)
    acordes = [(0, 4, 7), (7, 11, 14), (9, 12, 16), (5, 9, 12)]
    compasso = 4 * batida
    for c in range(int(duracao_s / compasso) + 1):
        base = c * compasso
        raiz, terca, quinta = acordes[c % 4]
        for b in range(4):
            tb = base + b * batida
            if b in (0, 2):   # bumbo: senoide que desce de 120 para 45 Hz
                soar(tb, 0.25, lambda x: np.sin(2 * np.pi * (45 * x + 75 * (1 - np.exp(-x * 30)) / 30))
                     * np.exp(-x * 14), 0.55)
            else:             # palma: ruído curto filtrado
                soar(tb, 0.12, lambda x: rng.standard_normal(len(x)) * np.exp(-x * 40), 0.12)
            for meio in (0, 0.5):  # chimbal em colcheias
                soar(tb + meio * batida, 0.04, lambda x: np.diff(rng.standard_normal(len(x) + 1)) * np.exp(-x * 120),
                     0.05, 0.4)
            for meio in (0, 0.5):  # baixo em colcheias
                f = nota(raiz - 24)
                soar(tb + meio * batida, batida * 0.45, lambda x, f=f: (osc(f * x)
                     + 0.3 * osc(2 * f * x)) * np.exp(-x * 6), 0.22)
            for k, grau in enumerate((raiz, terca, quinta, terca + 12)):  # arpejo em semicolcheias
                f = nota(grau + 12)
                soar(tb + k * batida / 4, batida / 2, lambda x, f=f: (osc(f * x)
                     + 0.25 * osc(3 * f * x)) * np.exp(-x * 9), 0.07, -0.3 if k % 2 else 0.3)

    mix = np.stack([esq, dir_], axis=1)[: int(duracao_s * taxa)]
    mix = mix / (np.abs(mix).max() or 1) * 0.8
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    return destino


def _selo(texto: str, largura: int, destino: Path) -> Path:
    """Etiqueta '@canal' em pílula translúcida, para o topo dos verticais."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        fonte = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", int(largura * 0.038))
    except OSError:
        fonte = ImageFont.load_default()
    caixa = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto, font=fonte)
    w, h = caixa[2] - caixa[0] + 60, caixa[3] - caixa[1] + 34
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=(0, 0, 0, 120))
    d.text((30, 17 - caixa[1]), texto, font=fonte, fill=(255, 255, 255, 235))
    img.save(destino)
    return destino


def _mascote(largura: int, destino: Path) -> Path:
    """A pulga do canal em pixel art (corpo marrom, olhos grandes, óculos, antenas e patas)."""
    from PIL import Image
    desenho = [
        "....a......a....",
        ".....a....a.....",
        "......a..a......",
        "....MMMMMMMM....",
        "...MMMMMMMMMM...",
        "..MOOOOMMOOOOM..",
        "..MOWPOMMOWPOM..",
        "..MOPPOOOOPPOM..",
        "..MOOOOMMOOOOM..",
        "..MMMMMMMMMMMM..",
        "..MMMMSSSSMMMM..",
        "...MMMMMMMMMM...",
        "....MMMMMMMM....",
        "...p.p....p.p...",
        "..p..p....p..p..",
        ".pp..pp..pp..pp.",
    ]
    cores = {"M": (150, 82, 40, 255), "O": (30, 30, 30, 255), "W": (255, 255, 255, 255),
             "P": (20, 20, 20, 255), "S": (240, 120, 120, 255), "a": (110, 60, 30, 255), "p": (110, 60, 30, 255)}
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, linha in enumerate(desenho):
        for x, ch in enumerate(linha):
            if ch in cores:
                img.putpixel((x, y), cores[ch])
    lado = int(largura * 0.12)
    img.resize((lado, lado), Image.NEAREST).save(destino)
    return destino


def _moldura_post(manchete: str, nome: str, arroba: str, destino: Path, avatar: Path | None = None,
                  pixel: int = 0) -> Path:
    """Fundo branco 1080x1920 com avatar (a pulga num círculo amarelo), nome, @ e a manchete."""
    from PIL import Image, ImageDraw, ImageFont

    from .config import JANELA_POST, TOPO_JANELA_POST

    def fonte(arquivo, tamanho):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{arquivo}", tamanho)
        except OSError:
            return ImageFont.load_default()

    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    # avatar: círculo amarelo com borda, a pulga em pixel art no meio
    lado, ax, ay = 180, 100, 215
    d.ellipse([ax - 8, ay - 8, ax + lado + 8, ay + lado + 8], fill=(255, 196, 0))
    d.ellipse([ax, ay, ax + lado, ay + lado], fill=(255, 222, 70), outline=(230, 150, 0), width=6)
    if avatar:  # foto do perfil recortada em círculo
        from PIL import ImageOps
        foto = ImageOps.fit(Image.open(avatar).convert("RGB"), (lado, lado))
        mascara = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(mascara).ellipse([0, 0, lado - 1, lado - 1], fill=255)
        img.paste(foto, (ax, ay), mascara)
    else:  # a mesma pulga cartoon que narra os vídeos
        from .narrador import _desenhar, _pixelar
        pulga = _desenhar(0.4, 0.15, int(lado * 0.92))
        if pixel:
            pulga = _pixelar(pulga, max(pixel - 1, 2))
        img.paste(pulga, (ax + (lado - pulga.width) // 2, ay + (lado - pulga.height) // 2 + 4), pulga)
    # nome e @
    tx = ax + lado + 36
    d.text((tx, ay + 32), nome, font=fonte("segoeuib.ttf", 64), fill=(17, 17, 17))
    d.text((tx, ay + 112), arroba, font=fonte("segoeui.ttf", 46), fill=(140, 140, 140))
    # manchete: centralizada, até 3 linhas, encolhe se precisar
    topo_texto, base_texto = ay + lado + 40, TOPO_JANELA_POST - 30
    def quebrar(limite, f):
        linhas, atual = [], ""
        for palavra in manchete.split():
            teste = f"{atual} {palavra}".strip()
            if d.textlength(teste, font=f) <= limite or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        return linhas + [atual]

    for tamanho in range(68, 34, -4):
        f = fonte("segoeui.ttf", tamanho)
        linhas = quebrar(w - 100, f)
        # linhas equilibradas: a menor largura que mantém o mesmo número de linhas (sem palavra sozinha)
        limite = w - 100
        while limite > 200 and len(quebrar(limite - 10, f)) == len(linhas):
            limite -= 10
        linhas = quebrar(limite, f)
        altura_linha = int(tamanho * 1.28)
        if len(linhas) <= 3 and len(linhas) * altura_linha <= base_texto - topo_texto:
            break
    y = topo_texto + (base_texto - topo_texto - len(linhas) * altura_linha) // 2
    for linha in linhas:
        d.text(((w - d.textlength(linha, font=f)) / 2, y), linha, font=f, fill=(17, 17, 17))
        y += altura_linha
    # sombra leve embaixo da janela do vídeo
    jw, jh = JANELA_POST
    d.rectangle([0, TOPO_JANELA_POST + jh, w, TOPO_JANELA_POST + jh + 3], fill=(235, 235, 235))
    img.save(destino)
    return destino


def juntar(cenas: list[Path], musica: Path | str | None, saida: Path, volume_musica: float = 0.12,
           selo: str | None = None, efeitos: Path | None = None, mascote: bool = False,
           post: dict | None = None) -> None:
    """Concatena as cenas, põe a barra de progresso e o selo do canal (só no vertical) e normaliza o
    volume para -14 LUFS (padrão das plataformas)."""
    pasta = cenas[0].parent
    lista = pasta / "lista.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in cenas), encoding="utf-8")
    junta = pasta / "junta.mp4"
    rodar(["-f", "concat", "-safe", "0", "-i", lista.name, "-c", "copy", junta.name], cwd=pasta)

    total = duracao(junta)
    if musica == "ambiente":
        musica = ambiente(total, pasta / "ambiente.wav")
    elif musica in ("animada", "chiptune"):
        musica = animada(total, pasta / f"{musica}.wav", saida.stem, chip=musica == "chiptune")
    normalizar = "loudnorm=I=-14:TP=-1.5:LRA=11"
    entradas = ["-i", str(junta)]
    fontes, partes = ["[0:a]"], []
    if musica:
        fim = max(total - 3, 0)
        entradas += ["-stream_loop", "-1", "-i", str(musica)]
        partes.append(f"[1:a]volume={volume_musica},afade=t=in:d=2,afade=t=out:st={fim:.2f}:d=3[m]")
        fontes.append("[m]")
    if efeitos:
        entradas += ["-i", str(efeitos)]
        partes.append(f"[{len(fontes)}:a]volume=1.0[fx]")
        fontes.append("[fx]")
    if len(fontes) > 1:
        partes.append(f"{''.join(fontes)}amix=inputs={len(fontes)}:duration=first:dropout_transition=0:"
                      f"normalize=0,{normalizar}[a]")
    else:
        partes.append(f"[0:a]{normalizar}[a]")
    audio = ";".join(partes)

    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(junta)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    larg, alt = map(int, re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", proc.stderr).groups())
    if post:  # moldura branca de post; a janela do vídeo fica no meio, com a barra de progresso embaixo
        from .config import TOPO_JANELA_POST
        entradas += ["-loop", "1", "-i", str(_moldura_post(post["manchete"], post["nome"], post["arroba"],
                                                          pasta / "moldura.png", post.get("avatar"),
                                                          post.get("pixel", 0)))]
        indice = len([e for e in entradas if e == "-i"]) - 1
        barra = 8
        video = (f"[{indice}:v]format=yuv420p,setsar=1[fundo];"
                 f"[fundo][0:v]overlay=x=0:y={TOPO_JANELA_POST}:shortest=1[comvideo];"
                 f"color=c=0xFFD400:s={larg}x{barra}:r={FPS}:d={total:.3f}[barra];"
                 f"[comvideo][barra]overlay=x='-W+W*t/{total:.3f}':y={TOPO_JANELA_POST + alt - barra}:"
                 f"eval=frame[v]")
        mapa_video = "[v]"
        codec = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "12M", "-bufsize", "24M",
                 "-pix_fmt", "yuv420p", "-r", str(FPS)]
        filtro = f"{video};{audio}"
    elif alt > larg:  # vertical: barra amarela que enche até o fim + selo do canal no topo
        barra = max(int(alt * 0.006), 6)
        video = (f"color=c=0xFFD400:s={larg}x{barra}:r={FPS}:d={total:.3f}[barra];"
                 f"[0:v][barra]overlay=x='-W+W*t/{total:.3f}':y=H-h:eval=frame[vb]")
        atual = "vb"
        if selo:
            entradas += ["-i", str(_selo(selo, larg, pasta / "selo.png"))]
            indice = len([e for e in entradas if e == "-i"]) - 1
            video += f";[{atual}][{indice}:v]overlay=x=(W-w)/2:y=H*0.055[vs]"
            atual = "vs"
        if mascote:  # pulga em pixel art no canto, pulando de leve
            entradas += ["-i", str(_mascote(larg, pasta / "mascote.png"))]
            indice = len([e for e in entradas if e == "-i"]) - 1
            video += (f";[{atual}][{indice}:v]overlay=x=W*0.05:"
                      f"y='H*0.835-abs(sin(t*2.6))*{int(alt * 0.012)}':eval=frame[vm]")
            atual = "vm"
        video += f";[{atual}]null[v]"
        mapa_video, codec = "[v]", ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p"]
        filtro = f"{video};{audio}"
    else:
        mapa_video, codec, filtro = "0:v", ["-c:v", "copy"], audio
    saida.parent.mkdir(parents=True, exist_ok=True)
    rodar([*entradas, "-filter_complex", filtro, "-map", mapa_video, "-map", "[a]", *codec,
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(saida)])
