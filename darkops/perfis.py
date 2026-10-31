"""Perfis: cada canal (contas do YouTube e do Instagram, estilo, fila e histórico) numa pasta própria.

perfis/<id>/perfil.json        nome, @, nicho, plataformas, formato e duração, estilo, se a postagem está ativa
perfis/<id>/credenciais/       token_youtube.json e token_instagram.txt (fora do Git)
perfis/<id>/fila/*.json        roteiros esperando; só os com "aprovado": true vão ao ar
perfis/<id>/publicados/*.json  roteiros já publicados
perfis/<id>/controle/          estado.json (IDs publicados), testes.csv, falhas.log, jobs/
perfis/<id>/avatar.png         foto do perfil na moldura do layout post (opcional)

O perfil da execução vem de --perfil na CLI (variável DARKOPS_PERFIL); o padrão é o Pulga do Saber.
As chaves de serviços (Azure, Pixabay...) e o app OAuth do Google são compartilhados no .env.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import config

PERFIS = config.RAIZ / "perfis"
PADRAO = "pulga-do-saber"
ID_VALIDO = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")

MODELO = {
    "nome": "Novo canal",
    "arroba": "@novocanal",
    "nicho": "curiosidades",
    "descricao": "",
    "idioma": "pt",
    "layout": "post",
    "voz": "pt-BR-AntonioNeural",
    "musica": "animada",
    "horarios": ["12:00", "19:00"],
    "ativo": False,
    "youtube": True,
    "instagram": True,
    "privacidade_youtube": "public",
    "facebook": False,
    "tiktok": False,
    "kwai": False,
    "outra_plataforma": "",
    "formato": "vertical",
    "duracao_s": 60,
    "video_exemplo": "",
    "leva_quantidade": 7,       # vídeos criados de uma vez
    "leva_reabastecer": False,  # criar outra leva sozinho quando a fila ficar curta
    "leva_minimo": 3,           # ... quando sobrarem esta quantidade de vídeos ou menos
    # padrão dos vídeos (o roteiro pode sobrescrever cada um)
    "motor_voz": "auto",
    "tipo_visual": "video",
    "proporcao_video": 50,
    "ritmo_corte_s": 4,
    "velocidade": "+0%",
    "legenda": True,
    "legenda_tamanho": "media",
    "legenda_cor": "#FFE500",
    "legenda_fonte": "Arial Black",
    "tema_cards": "padrao",
    "edicao": "pro",            # quantos elementos na tela: simples, leve ou pro (pro = tudo que o roteiro trouxer)
    "acervo_nasa": False,       # usar o acervo de imagens da NASA (domínio público, com crédito)
    # personalidade do canal: o /escrever-roteiro e a leva seguem isso em todo roteiro
    "persona_narrador": "",
    "persona_tom": "",
    "persona_publico": "",
    "persona_abertura": "",
    "persona_linguagem": "",
    "persona_titulos": "",
}

EDICOES = {"simples": "Simples: só imagem, narração e legenda",
           "leve": "Leve: palavra-herói e até 2 cards com dados por vídeo",
           "pro": "Pro: card ou etiqueta em toda cena com número, data ou comparação"}
PERSONA = [("persona_narrador", "Quem narra", "Ex.: uma pulga curiosa e animada que fala com o público como amigo"),
           ("persona_tom", "Tom", "Ex.: divertido e espantado, sem exagero"),
           ("persona_publico", "Público", "Ex.: adolescentes e adultos curiosos, 13 a 35 anos"),
           ("persona_abertura", "Como os vídeos começam", "Ex.: com uma pergunta ou um fato que parece impossível"),
           ("persona_linguagem", "Linguagem", "Ex.: português do dia a dia, frases curtas, sem gíria pesada"),
           ("persona_titulos", "Títulos e capa", "Ex.: título curto com número; capa com 2 a 4 palavras em amarelo")]


def resumo_persona(dados: dict) -> str:
    """A personalidade do canal em texto corrido, para pedir roteiros ao Claude."""
    texto = " ".join(f"{rotulo}: {dados[chave].strip()}." for chave, rotulo, _ in PERSONA if dados.get(chave, "").strip())
    if dados.get("diretrizes"):  # orientações aprovadas na análise das estatísticas
        texto += " Diretrizes do canal (aprovadas pelo dono): " + "; ".join(x.rstrip(". ") for x in dados["diretrizes"]) + "."
    return texto.strip()

MOTORES_VOZ = {"auto": "Automático (Azure, depois Edge e Piper; grátis)", "azure": "Azure Speech (grátis até 500 mil caracteres)",
               "elevenlabs": "ElevenLabs (pago; precisa da chave)"}
TIPOS_VISUAL = {"foto": "Só imagens", "video": "Só vídeos (foto quando faltar clipe)", "misto": "Imagens e vídeos"}
RITMOS = [2, 3, 4, 6, 8]
TAMANHOS_LEGENDA = {"pequena": 0.8, "media": 1.0, "grande": 1.25}
TEMAS_CARDS = {"padrao": "Vidro escuro (padrão)", "arquivo_frio": "Arquivo frio", "jornal_antigo": "Jornal antigo",
               "moderno_limpo": "Moderno limpo"}
FONTES_LEGENDA = ["Arial Black", "Impact", "Segoe UI Black", "Bahnschrift", "Verdana", "Comic Sans MS"]


def campos_padrao(form) -> dict:
    """Lê do formulário o padrão dos vídeos (voz, visual, ritmo e legenda), validando cada valor."""
    def numero(chave: str, padrao: int, minimo: int, maximo: int) -> int:
        try:
            return min(max(int(form.get(chave, padrao)), minimo), maximo)
        except ValueError:
            return padrao
    cor = form.get("legenda_cor", "")
    return {"motor_voz": form.get("motor_voz") if form.get("motor_voz") in MOTORES_VOZ else "auto",
            "tipo_visual": form.get("tipo_visual") if form.get("tipo_visual") in TIPOS_VISUAL else "video",
            "proporcao_video": numero("proporcao_video", 50, 0, 100),
            "ritmo_corte_s": numero("ritmo_corte_s", 4, 1, 15),
            "legenda": bool(form.get("legenda")),
            "legenda_tamanho": form.get("legenda_tamanho") if form.get("legenda_tamanho") in TAMANHOS_LEGENDA else "media",
            "legenda_cor": cor.upper() if re.match(r"^#[0-9a-fA-F]{6}$", cor) else "#FFE500",
            "legenda_fonte": form.get("legenda_fonte") if form.get("legenda_fonte") in FONTES_LEGENDA else "Arial Black",
            "tema_cards": form.get("tema_cards") if form.get("tema_cards") in TEMAS_CARDS else "padrao",
            "edicao": form.get("edicao") if form.get("edicao") in EDICOES else "pro",
            "acervo_nasa": bool(form.get("acervo_nasa")),
            **{chave: form.get(chave, "").strip()[:300] for chave, _, _ in PERSONA}}

# onde o canal existe; só YouTube e Instagram têm postagem automática, as outras ficam como referência
PLATAFORMAS = [("youtube", "YouTube"), ("instagram", "Instagram"), ("facebook", "Facebook"),
               ("tiktok", "TikTok"), ("kwai", "Kwai")]
FORMATOS = {"vertical": "Shorts / Reels (vertical 9:16)", "longo": "Vídeo convencional do YouTube (16:9)"}
# duração alvo de cada vídeo, em segundos, por formato
DURACOES = {"vertical": [15, 30, 45, 60, 90, 180], "longo": [180, 300, 480, 600, 900, 1200, 1800]}


def rotulo_duracao(segundos: int) -> str:
    return f"{segundos}s" if segundos < 120 else f"{segundos // 60} min"


def campos_video(form, dados: dict) -> dict:
    """Tipo, duração e plataformas de UM vídeo (Novo vídeo); o que faltar vem do perfil.
    O Reels só aceita vídeo vertical: num vídeo longo o Instagram sai da lista."""
    formato = form.get("formato") if form.get("formato") in FORMATOS else dados.get("formato", "vertical")
    try:
        duracao = int(form.get("duracao_s", ""))
    except ValueError:
        duracao = 0
    if duracao not in DURACOES[formato]:
        duracao = dados.get("duracao_s") if dados.get("duracao_s") in DURACOES[formato] else DURACOES[formato][3]
    # o formulário manda "plataformas_enviadas" junto com as caixas; sem ele (CLI, leva), valem as do perfil
    origem = (lambda k: form.get(f"video_{k}")) if form.get("plataformas_enviadas") else dados.get
    escolhidas = [k for k, _ in PLATAFORMAS if origem(k)]
    if formato == "longo":
        escolhidas = [k for k in escolhidas if k != "instagram"]
    return {"formato": formato, "duracao_alvo_s": duracao, "plataformas": escolhidas}


def nomes_plataformas(dados: dict) -> str:
    nomes = [nome for chave, nome in PLATAFORMAS if dados.get(chave)]
    return ", ".join(nomes + ([dados["outra_plataforma"]] if dados.get("outra_plataforma") else []))


def campos_canal(form) -> dict:
    """Lê do formulário as plataformas, o formato, a duração e o vídeo de exemplo do canal."""
    formato = form.get("formato") if form.get("formato") in FORMATOS else "vertical"
    try:
        duracao = int(form.get("duracao_s", ""))
    except ValueError:
        duracao = 0
    if duracao not in DURACOES[formato]:
        duracao = 60 if formato == "vertical" else 600
    exemplo = form.get("video_exemplo", "").strip()

    def inteiro(chave: str, padrao: int, minimo: int, maximo: int) -> int:
        try:
            return min(max(int(form.get(chave, padrao)), minimo), maximo)
        except ValueError:
            return padrao
    return {**{k: bool(form.get(k)) for k, _ in PLATAFORMAS},
            "outra_plataforma": form.get("outra_plataforma", "").strip(), "formato": formato,
            "duracao_s": duracao, "video_exemplo": exemplo if re.match(r"^https?://\S+$", exemplo) else "",
            "leva_quantidade": inteiro("leva_quantidade", 7, 1, 14), "leva_reabastecer": bool(form.get("leva_reabastecer")),
            "leva_minimo": inteiro("leva_minimo", 3, 0, 13)}


def atual() -> str:
    return os.getenv("DARKOPS_PERFIL", PADRAO)


@dataclass
class Perfil:
    id: str

    @property
    def pasta(self) -> Path:
        return PERFIS / self.id

    @property
    def arquivo(self) -> Path:
        return self.pasta / "perfil.json"

    @property
    def dados(self) -> dict:
        salvo = json.loads(self.arquivo.read_text(encoding="utf-8")) if self.arquivo.exists() else {}
        return {**MODELO, **salvo}

    def salvar(self, novos: dict) -> None:
        dados = {**self.dados, **novos}
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # pastas e arquivos
    @property
    def fila(self) -> Path:
        return self.pasta / "fila"

    @property
    def publicados(self) -> Path:
        return self.pasta / "publicados"

    @property
    def controle(self) -> Path:
        return self.pasta / "controle"

    @property
    def credenciais(self) -> Path:
        return self.pasta / "credenciais"

    @property
    def token_youtube(self) -> Path:
        return self.credenciais / "token_youtube.json"

    @property
    def token_instagram(self) -> Path:
        return self.credenciais / "token_instagram.txt"

    @property
    def avatar(self) -> Path | None:
        caminho = self.pasta / "avatar.png"
        return caminho if caminho.exists() else None

    def preparar(self) -> "Perfil":
        for pasta in (self.fila, self.publicados, self.controle, self.credenciais):
            pasta.mkdir(parents=True, exist_ok=True)
        return self


def carregar(perfil_id: str | None = None) -> Perfil:
    perfil_id = perfil_id or atual()
    if not ID_VALIDO.match(perfil_id):
        raise SystemExit(f"id de perfil inválido: {perfil_id!r} (use letras minúsculas, números e hífen)")
    return Perfil(perfil_id)


def listar() -> list[Perfil]:
    if not PERFIS.exists():
        return []
    return [Perfil(p.name) for p in sorted(PERFIS.iterdir()) if (p / "perfil.json").exists()]


def criar(perfil_id: str, dados: dict) -> Perfil:
    perfil = carregar(perfil_id)
    if perfil.arquivo.exists():
        raise SystemExit(f"o perfil {perfil_id} já existe")
    perfil.preparar().salvar(dados)
    return perfil


def slug(texto: str) -> str:
    import unicodedata
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:40] or "canal"


# ---------- sugestões de nome para o canal novo ----------

_PRONTOS = {
    "misterios": ["Arquivo Oculto", "Enigma Diário", "O Inexplicado", "Mapa do Mistério", "Caso Sem Fim"],
    "terror": ["Arquivo do Terror", "Relatos da Meia-Noite", "Casa Fria", "Lenda Viva", "Sussurro Sombrio"],
    "curiosidades": ["Pulga do Saber", "Fato Rápido", "Você Sabia Hoje", "Mente Curiosa", "Minuto Curioso"],
    "animais": ["Bicho Raro", "Planeta Selvagem", "Zoo de Bolso", "Fera Curiosa", "Mundo Animal Já"],
    "geopolitica": ["Mapa do Poder", "Xadrez Global", "Por Trás do Mapa", "Fronteira Explicada", "Mundo em 1 Minuto"],
}


def sugerir_nomes(nicho: str, formato: str = "vertical") -> dict:
    """Cinco nomes com @ e bio. A IA (Claude Code, sem ferramentas) cria a partir do assunto; sem ela, prontos."""
    import subprocess
    from .leva import rodar_claude
    assunto = re.sub(r"[^\w\s,.-]", "", nicho)[:80] or "curiosidades"
    pedido = (f"Sugira 5 nomes originais em português para um canal dark (vídeos sem rosto) sobre: {assunto}. "
              f"Formato: {'vídeos curtos verticais (Shorts/Reels)' if formato == 'vertical' else 'vídeos longos do YouTube'}. "
              "Cada nome: curto (até 3 palavras), fácil de lembrar e de buscar, sem marcas registradas. "
              "Responda SÓ um JSON, sem texto em volta: "
              '[{"nome": "...", "arroba": "@...", "bio": "uma frase de até 120 caracteres"}]')
    try:
        proc = rodar_claude(pedido, timeout=120)
        achado = re.search(r"\[.*\]", proc.stdout, re.S)
        lista = json.loads(achado.group(0)) if achado else []
        nomes = [{"nome": str(s["nome"])[:60], "bio": str(s.get("bio", ""))[:200],
                  "arroba": "@" + re.sub(r"[^a-z0-9_.]", "", str(s.get("arroba") or s["nome"]).lower())[:30]}
                 for s in lista if isinstance(s, dict) and s.get("nome")][:5]
        if nomes:
            return {"ia": True, "nomes": nomes}
    except (SystemExit, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        pass
    chave = next((k for k in _PRONTOS if k in assunto.lower()), "curiosidades")
    return {"ia": False, "nomes": [{"nome": n, "arroba": "@" + re.sub(r"[^a-z0-9]", "", n.lower()
                                    .translate(str.maketrans("áâãàéêíóôõúç", "aaaaeeiooouc"))), "bio": ""}
                                   for n in _PRONTOS[chave]]}
