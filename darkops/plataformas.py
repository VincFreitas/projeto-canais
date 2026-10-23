"""Progresso da configuração de cada plataforma: o que já está pronto e o próximo passo.

  python -m darkops progresso     mostra a base comum e cada plataforma, com as etapas feitas e as que faltam

O Estúdio usa o mesmo cálculo no formulário de perfil (alerta das plataformas) e na tela Progresso.
Só o YouTube e o Instagram têm postagem automática; Facebook, TikTok e Kwai ficam como postagem manual.
"""
from dataclasses import dataclass, field

from . import config

PRONTA, FALTA, MANUAL = "pronta", "falta", "manual"


@dataclass
class Etapa:
    nome: str
    feita: bool
    como: str = ""
    link: str = ""


@dataclass
class Plataforma:
    id: str
    nome: str
    automatica: bool
    etapas: list[Etapa] = field(default_factory=list)

    @property
    def feitas(self) -> int:
        return sum(e.feita for e in self.etapas)

    @property
    def situacao(self) -> str:
        if not self.automatica:
            return MANUAL
        return PRONTA if self.etapas and self.feitas == len(self.etapas) else FALTA

    @property
    def proximo(self) -> Etapa | None:
        return next((e for e in self.etapas if not e.feita), None)

    @property
    def percentual(self) -> int:
        return round(100 * self.feitas / len(self.etapas)) if self.etapas else 0


def _youtube(perfis_alvo) -> Plataforma:
    app = (config.RAIZ / "credenciais" / "client_secret.json").exists()
    etapas = [Etapa("App OAuth do Google", app,
                    "Vale para todos os perfis. Google Cloud: ative a YouTube Data API v3, crie um cliente OAuth 'App para computador' e salve "
                    "o JSON em credenciais/client_secret.json (passo a passo: /configurar)",
                    "https://console.cloud.google.com/apis/library/youtube.googleapis.com")]
    etapas += [Etapa(f"Canal conectado: {p.dados['nome']}", p.token_youtube.exists(),
                     "Estúdio > Conexões > Conectar YouTube e escolher a conta do canal") for p in perfis_alvo]
    return Plataforma("youtube", "YouTube", True, etapas)


def _instagram(perfis_alvo, todos) -> Plataforma:
    # o app da Meta não deixa rastro local; um token salvo em qualquer perfil mostra que ele já existe
    app = any(p.token_instagram.exists() for p in todos)
    etapas = [Etapa("Conta Profissional e app da Meta", app,
                    "Conta do Instagram Profissional (Criador) ligada a uma Página do Facebook; em "
                    "developers.facebook.com crie o app e gere o token (passo a passo: /configurar)",
                    "https://developers.facebook.com/apps/")]
    etapas += [Etapa(f"Token salvo: {p.dados['nome']}", p.token_instagram.exists(),
                     "Estúdio > Conexões > colar o token gerado no app da Meta (dura 60 dias)") for p in perfis_alvo]
    return Plataforma("instagram", "Instagram", True, etapas)


def _manual(pid: str, nome: str, link: str) -> Plataforma:
    return Plataforma(pid, nome, False, [
        Etapa("Postagem automática (ainda não existe)", False, f"Ainda não disponível no {nome}; o projeto não posta lá sozinho.", link),
        Etapa("Postar à mão", True, "Os vídeos ficam em saida/<slug>-vertical.mp4; envie pelo app ou pelo site."),
    ])


def calcular(perfil=None, novo: bool = False) -> list[Plataforma]:
    """Uma Plataforma por rede. Com perfil, as etapas por canal olham só ele; sem, todos os que marcaram a rede.
    novo=True (perfil ainda não criado) deixa só as etapas da instalação, que dizem se a rede pode ser escolhida."""
    from .perfis import listar
    todos = listar()

    def alvo(chave: str) -> list:
        if novo:
            return []
        return [perfil] if perfil else [p for p in todos if p.dados.get(chave)]

    return [
        _youtube(alvo("youtube")),
        _instagram(alvo("instagram"), todos),
        _manual("facebook", "Facebook", "https://developers.facebook.com/docs/video-api/guides/reels-publishing"),
        _manual("tiktok", "TikTok", "https://developers.tiktok.com/products/content-posting-api/"),
        _manual("kwai", "Kwai", "https://www.kwai.com/"),
    ]


def base() -> list[Etapa]:
    """Peças comuns a todas as plataformas (voz, imagens, perfil e n8n), tiradas do diagnóstico."""
    from .instalacao import diagnostico
    por_plataforma = ("YouTube do perfil", "Instagram do perfil", "App OAuth do Google")
    return [Etapa(item, pronto, fazer) for item, pronto, fazer in diagnostico() if not item.startswith(por_plataforma)]
