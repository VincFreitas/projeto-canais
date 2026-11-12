"""Mercado do canal: a língua e a região do público para quem os vídeos são feitos.

O mercado decide a língua do roteiro, da narração, da descrição e das tags, a voz padrão, a língua declarada no
YouTube e o fuso dos horários de postagem (12:00 em Nova York não é 12:00 em Brasília).
As plataformas não deixam escolher o país do público pela API: o alcance numa região vem da língua do vídeo e dos
metadados, de referências que fazem sentido lá e de postar no horário de lá. É isso que o mercado acerta.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PADRAO = "pt-BR"

# chave: código BCP 47 do mercado. youtube: código aceito em defaultLanguage/defaultAudioLanguage.
MERCADOS = {
    "pt-BR": {"nome": "Português · Brasil", "idioma": "pt", "youtube": "pt-BR", "fuso": "America/Sao_Paulo",
              "cidade": "Brasília", "lingua": "português do Brasil", "publico": "público brasileiro",
              "unidades": "sistema métrico (km, kg, °C) e real (R$)",
              "vozes": ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural",
                        "pt-BR-MacerioMultilingualNeural"]},
    "pt-PT": {"nome": "Português · Portugal", "idioma": "pt", "youtube": "pt-PT", "fuso": "Europe/Lisbon",
              "cidade": "Lisboa", "lingua": "português europeu (de Portugal, não do Brasil)", "publico": "público de Portugal",
              "unidades": "sistema métrico (km, kg, °C) e euro (€)",
              "vozes": ["pt-PT-DuarteNeural", "pt-PT-RaquelNeural"]},
    "en-US": {"nome": "Inglês · Estados Unidos", "idioma": "en", "youtube": "en-US", "fuso": "America/New_York",
              "cidade": "Nova York", "lingua": "inglês americano", "publico": "público dos Estados Unidos",
              "unidades": "unidades americanas (milhas, libras, pés, °F) e dólar (US$)",
              "vozes": ["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural",
                        "en-US-AvaMultilingualNeural", "en-US-EmmaMultilingualNeural"]},
    "en-GB": {"nome": "Inglês · Reino Unido", "idioma": "en", "youtube": "en-GB", "fuso": "Europe/London",
              "cidade": "Londres", "lingua": "inglês britânico", "publico": "público do Reino Unido",
              "unidades": "sistema métrico, milhas nas estradas, °C e libra esterlina (£)",
              "vozes": ["en-GB-RyanNeural", "en-GB-SoniaNeural", "en-GB-ThomasNeural", "en-GB-LibbyNeural"]},
    "es-MX": {"nome": "Espanhol · México e América Latina", "idioma": "es", "youtube": "es-419",
              "fuso": "America/Mexico_City", "cidade": "Cidade do México", "lingua": "espanhol latino-americano neutro",
              "publico": "público do México e da América Latina",
              "unidades": "sistema métrico (km, kg, °C); dinheiro em dólar (US$) quando precisar de um valor",
              "vozes": ["es-MX-JorgeNeural", "es-MX-DaliaNeural"]},
    "es-US": {"nome": "Espanhol · hispânicos dos EUA", "idioma": "es", "youtube": "es-US", "fuso": "America/New_York",
              "cidade": "Nova York", "lingua": "espanhol latino-americano neutro",
              "publico": "público hispânico dos Estados Unidos",
              "unidades": "unidades americanas (milhas, libras, °F) e dólar (US$)",
              "vozes": ["es-US-AlonsoNeural", "es-US-PalomaNeural"]},
    "es-ES": {"nome": "Espanhol · Espanha", "idioma": "es", "youtube": "es-ES", "fuso": "Europe/Madrid",
              "cidade": "Madri", "lingua": "espanhol da Espanha", "publico": "público da Espanha",
              "unidades": "sistema métrico (km, kg, °C) e euro (€)",
              "vozes": ["es-ES-AlvaroNeural", "es-ES-ElviraNeural", "es-ES-XimenaNeural"]},
    "fr-FR": {"nome": "Francês · França", "idioma": "fr", "youtube": "fr", "fuso": "Europe/Paris",
              "cidade": "Paris", "lingua": "francês da França", "publico": "público da França",
              "unidades": "sistema métrico (km, kg, °C) e euro (€)",
              "vozes": ["fr-FR-HenriNeural", "fr-FR-DeniseNeural", "fr-FR-RemyMultilingualNeural"]},
    "de-DE": {"nome": "Alemão · Alemanha", "idioma": "de", "youtube": "de", "fuso": "Europe/Berlin",
              "cidade": "Berlim", "lingua": "alemão", "publico": "público da Alemanha",
              "unidades": "sistema métrico (km, kg, °C) e euro (€)",
              "vozes": ["de-DE-ConradNeural", "de-DE-KatjaNeural", "de-DE-FlorianMultilingualNeural"]},
    "it-IT": {"nome": "Italiano · Itália", "idioma": "it", "youtube": "it", "fuso": "Europe/Rome",
              "cidade": "Roma", "lingua": "italiano", "publico": "público da Itália",
              "unidades": "sistema métrico (km, kg, °C) e euro (€)",
              "vozes": ["it-IT-DiegoNeural", "it-IT-ElsaNeural", "it-IT-GiuseppeMultilingualNeural"]},
}
# perfis antigos só têm "idioma": cada língua cai no mercado mais comum dela
POR_IDIOMA = {"pt": "pt-BR", "en": "en-US", "es": "es-MX", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}

# frases fixas que vão para o público (descrição, legenda do Instagram, bio). {arroba}, {horarios}, {nicho}, {nome}
TEXTOS = {
    "pt": {"seguir": "Segue {arroba} para mais curiosidades.", "fontes": "Fontes:", "voce_sabia": "Você sabia?",
           "seguir_curto": "Segue a {arroba} para mais.", "hashtags": ["#curiosidades", "#vocesabia"],
           "todo_dia": "todo dia", "e": " e ", "bio_reels": "⏰ Reels novos às {horarios}",
           "bio_checadas": "Curiosidades rápidas e checadas", "gancho": "Vídeos curtos sobre {nicho}",
           "desc_canal": "O {nome} traz vídeos curtos sobre {nicho}. "
                         "Tudo com fonte checada: se é lenda, a gente avisa.",
           "desc_shorts": "⏰ Shorts novos todo dia, às {horarios}."},
    "en": {"seguir": "Follow {arroba} for more.", "fontes": "Sources:", "voce_sabia": "Did you know?",
           "seguir_curto": "Follow {arroba} for more.", "hashtags": ["#didyouknow", "#facts"],
           "todo_dia": "every day", "e": " and ", "bio_reels": "⏰ New Reels at {horarios}",
           "bio_checadas": "Quick, fact-checked curiosities", "gancho": "Short videos about {nicho}",
           "desc_canal": "{nome} makes short videos about {nicho}. "
                         "Every fact is checked: if it's a legend, we say so.",
           "desc_shorts": "⏰ New Shorts every day at {horarios}."},
    "es": {"seguir": "Sigue a {arroba} para más curiosidades.", "fontes": "Fuentes:", "voce_sabia": "¿Sabías que...?",
           "seguir_curto": "Sigue a {arroba} para más.", "hashtags": ["#curiosidades", "#sabiasque"],
           "todo_dia": "todos los días", "e": " y ", "bio_reels": "⏰ Reels nuevos a las {horarios}",
           "bio_checadas": "Curiosidades rápidas y verificadas", "gancho": "Videos cortos sobre {nicho}",
           "desc_canal": "{nome} trae videos cortos sobre {nicho}. "
                         "Todo con fuentes verificadas: si es leyenda, lo decimos.",
           "desc_shorts": "⏰ Shorts nuevos todos los días a las {horarios}."},
    "fr": {"seguir": "Abonne-toi à {arroba} pour plus de curiosités.", "fontes": "Sources :",
           "voce_sabia": "Le savais-tu ?", "seguir_curto": "Abonne-toi à {arroba}.",
           "hashtags": ["#lesaviezvous", "#culturegenerale"], "todo_dia": "tous les jours", "e": " et ",
           "bio_reels": "⏰ Nouveaux Reels à {horarios}", "bio_checadas": "Curiosités rapides et vérifiées",
           "gancho": "Vidéos courtes sur {nicho}",
           "desc_canal": "{nome} publie des vidéos courtes sur {nicho}. "
                         "Tout est vérifié : si c'est une légende, on le dit.",
           "desc_shorts": "⏰ Nouveaux Shorts tous les jours à {horarios}."},
    "de": {"seguir": "Folge {arroba} für mehr.", "fontes": "Quellen:", "voce_sabia": "Wusstest du?",
           "seguir_curto": "Folge {arroba} für mehr.", "hashtags": ["#wusstestdu", "#fakten"],
           "todo_dia": "jeden Tag", "e": " und ", "bio_reels": "⏰ Neue Reels um {horarios}",
           "bio_checadas": "Kurze, geprüfte Fakten", "gancho": "Kurze Videos über {nicho}",
           "desc_canal": "{nome} zeigt kurze Videos über {nicho}. "
                         "Alles mit geprüften Quellen: Ist es eine Legende, sagen wir es.",
           "desc_shorts": "⏰ Neue Shorts jeden Tag um {horarios}."},
    "it": {"seguir": "Segui {arroba} per altre curiosità.", "fontes": "Fonti:", "voce_sabia": "Lo sapevi?",
           "seguir_curto": "Segui {arroba} per altro.", "hashtags": ["#losapevi", "#curiosità"],
           "todo_dia": "ogni giorno", "e": " e ", "bio_reels": "⏰ Nuovi Reels alle {horarios}",
           "bio_checadas": "Curiosità rapide e verificate", "gancho": "Video brevi su {nicho}",
           "desc_canal": "{nome} pubblica video brevi su {nicho}. "
                         "Tutto con fonti verificate: se è una leggenda, lo diciamo.",
           "desc_shorts": "⏰ Nuovi Shorts ogni giorno alle {horarios}."},
}


def codigo(dados: dict) -> str:
    """O mercado do perfil (ou do roteiro). Sem "mercado", vem do "idioma" antigo."""
    escolhido = dados.get("mercado")
    if escolhido in MERCADOS:
        return escolhido
    return POR_IDIOMA.get(str(dados.get("idioma") or "pt")[:2], PADRAO)


def de(dados: dict) -> dict:
    return {"codigo": codigo(dados), **MERCADOS[codigo(dados)]}


def fuso(dados: dict) -> ZoneInfo:
    return ZoneInfo(MERCADOS[codigo(dados)]["fuso"])


def opcoes() -> dict:
    return {k: m["nome"] for k, m in MERCADOS.items()}


def voz_combina(cod: str, voz: str | None) -> bool:
    """A voz fala a língua com o sotaque do mercado (pt-BR-... para o Brasil, en-US-... para os EUA)."""
    return str(voz or "").lower().startswith(cod.lower() + "-")


def coerente(dados: dict) -> dict:
    """Mercado, idioma e voz que combinam entre si. Trocar o mercado troca a voz pela padrão da nova região."""
    cod = codigo(dados)
    m = MERCADOS[cod]
    voz = dados.get("voz")
    from .vozes import combina  # Thalita, Remy (multilíngue de fora), Charon do Gemini...: o catálogo decide
    return {"mercado": cod, "idioma": m["idioma"],
            "voz": voz if combina(cod, dados.get("motor_voz") or "auto", voz) else m["vozes"][0]}


def texto(dados: dict, chave: str, **campos) -> str | list:
    valor = TEXTOS.get(MERCADOS[codigo(dados)]["idioma"], TEXTOS["pt"])[chave]
    return valor.format(**campos) if isinstance(valor, str) else list(valor)


def horarios_legiveis(dados: dict) -> str:
    """'12h e 19h' / '12:00 and 19:00', no fuso do mercado."""
    horarios = dados.get("horarios") or []
    if MERCADOS[codigo(dados)]["idioma"] == "pt":
        horarios = [h.replace(":00", "h").replace(":", "h") for h in horarios]
    return str(texto(dados, "e")).join(horarios) or str(texto(dados, "todo_dia"))


def instrucao_roteiro(dados: dict) -> str:
    """O trecho do pedido de roteiro que fixa língua, região e referências."""
    m = de(dados)
    return (f"Público do canal: {m['publico']} (mercado {m['codigo']}). Escreva TUDO que o público vê ou ouve "
            f"(título, narração, textos na tela, legenda, descrição, tags e hashtags) em {m['lingua']}, com "
            f"expressões naturais de lá e nunca tradução literal. Use exemplos, marcas, lugares e comparações que "
            f"esse público reconhece, e {m['unidades']}. Grave \"idioma\": \"{m['idioma']}\" e "
            f"\"mercado\": \"{m['codigo']}\" no roteiro. As fontes podem ser em qualquer língua. ")


# ---------- horários de postagem no fuso do mercado ----------

def slot_na_hora(dados: dict, agora: datetime | None = None, janela_min: int = 30) -> str | None:
    """O horário de postagem que acabou de chegar (nos últimos `janela_min` minutos, no fuso do mercado), ou None.
    O gatilho do n8n roda a cada 30 minutos: cada horário cai em uma única rodada."""
    tz = fuso(dados)
    agora = (agora or datetime.now(tz)).astimezone(tz)
    for h in dados.get("horarios") or []:
        hh, mm = map(int, h.split(":"))
        for dia in (0, -1):  # 23:50 ainda vale à 00:10
            momento = agora.replace(hour=hh, minute=mm, second=0, microsecond=0) + timedelta(days=dia)
            if timedelta(0) <= agora - momento < timedelta(minutes=janela_min):
                return momento.strftime("%Y-%m-%d %H:%M")
    return None


def perto_de_postar(perfis_dados: list[dict], antes_min: int = 10, depois_min: int = 40,
                    agora: datetime | None = None) -> bool:
    """Algum canal ativo está a poucos minutos de um horário de postagem (no fuso de cada mercado)."""
    for d in perfis_dados:
        tz = fuso(d)
        local = (agora or datetime.now(tz)).astimezone(tz)
        for h in d.get("horarios") or []:
            hh, mm = map(int, h.split(":"))
            for dia in (-1, 0, 1):
                momento = local.replace(hour=hh, minute=mm, second=0, microsecond=0) + timedelta(days=dia)
                if -antes_min <= (local - momento).total_seconds() / 60 <= depois_min:
                    return True
    return False


def cron_utc(perfis_dados: list[dict], atraso_min: int = 20) -> str:
    """Linhas de cron (UTC) do GitHub Actions para a reserva da nuvem: `atraso_min` depois de cada horário, no
    fuso de cada mercado. Fusos com horário de verão ganham as duas horas UTC (a rodada fora de hora não acha
    horário na janela e não posta)."""
    pares = set()
    for d in perfis_dados:
        tz = fuso(d)
        for h in d.get("horarios") or []:
            hh, mm = map(int, h.split(":"))
            for mes in (1, 7):  # inverno e verão
                local = datetime(2026, mes, 15, hh, mm, tzinfo=tz) + timedelta(minutes=atraso_min)
                utc = local.astimezone(ZoneInfo("UTC"))
                pares.add((utc.minute, utc.hour))
    por_minuto: dict[int, set] = {}
    for minuto, hora in pares:
        por_minuto.setdefault(minuto, set()).add(hora)
    return "\n".join(f'    - cron: "{m} {",".join(str(h) for h in sorted(hs))} * * *"'
                     for m, hs in sorted(por_minuto.items()))
