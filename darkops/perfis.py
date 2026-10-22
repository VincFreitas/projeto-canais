"""Perfis: cada canal (contas do YouTube e do Instagram, estilo, fila e histórico) numa pasta própria.

perfis/<id>/perfil.json        nome, @, nicho, estilo dos vídeos, se a postagem está ativa
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
}


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
