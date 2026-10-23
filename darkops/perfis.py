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
}

# onde o canal existe; só YouTube e Instagram têm postagem automática, as outras ficam como referência
PLATAFORMAS = [("youtube", "YouTube"), ("instagram", "Instagram"), ("facebook", "Facebook"),
               ("tiktok", "TikTok"), ("kwai", "Kwai")]
FORMATOS = {"vertical": "Shorts / Reels (vertical 9:16)", "longo": "Vídeo convencional do YouTube (16:9)"}
# duração alvo de cada vídeo, em segundos, por formato
DURACOES = {"vertical": [15, 30, 45, 60, 90, 180], "longo": [180, 300, 480, 600, 900, 1200, 1800]}


def rotulo_duracao(segundos: int) -> str:
    return f"{segundos}s" if segundos < 120 else f"{segundos // 60} min"


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
    return {**{k: bool(form.get(k)) for k, _ in PLATAFORMAS},
            "outra_plataforma": form.get("outra_plataforma", "").strip(), "formato": formato,
            "duracao_s": duracao, "video_exemplo": exemplo if re.match(r"^https?://\S+$", exemplo) else ""}


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
