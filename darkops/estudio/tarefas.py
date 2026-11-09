"""Como a tela de tarefa fala com a pessoa: tempo estimado, se a página pode ser fechada e o resultado em
uma frase. O log continua guardado em controle/jobs/ e aparece só em "Ver detalhes técnicos"."""
from __future__ import annotations

import re

from .. import seguranca

# animação de carregamento no máximo por este tempo nas tarefas longas; depois vira o cartão do tempo estimado
ANIMACAO_MAX_S = 30
LONGA_MIN = 3  # tarefa com estimativa acima disso (em minutos) é "longa"

FECHAR_SIM = ("Pode fechar esta página: a tarefa continua rodando no Estúdio. "
              "Só não feche o Estúdio nem desligue o computador até terminar.")
FECHAR_LOGIN = ("Deixe esta página aberta até terminar o login: o código para colar aparece aqui. "
                "Depois do login, pode fechar.")
FECHAR_GOOGLE = ("Termine o login na janela do navegador que abrimos. Esta página pode ficar fechada, "
                 "mas não feche o Estúdio.")

# (minutos mínimos, máximos, mensagem de pronto) pelo primeiro comando da tarefa
_TIPOS = {
    "fila-produzir": (2, 6, "A prévia está pronta para assistir e aprovar."),
    "publicar-youtube": (1, 4, "O vídeo foi enviado."),
    "publicar-instagram": (1, 4, "O vídeo foi enviado."),
    "descricao": (0.5, 2, "Descrição e tags prontas."),
    "ajustar-canal": (1, 4, "A proposta de ajuste está pronta: confira e aprove nos Ajustes do canal."),
    "referencia": (2, 8, "A análise das referências terminou."),
    "aprender": (2, 6, "A análise do que funcionou terminou: veja em Resultados."),
    "analisar": (2, 6, "A análise da IA terminou: veja em Resultados."),
    "estatisticas": (0.5, 3, "Números atualizados."),
    "identidade": (2, 6, "A identidade visual está pronta para você aprovar."),
    "autorizar-youtube": (1, 5, "YouTube conectado."),
    "conectar-github": (2, 6, "GitHub conectado e nuvem preparada."),
    "conectar-azure": (2, 6, "Conta da Microsoft conectada e chave da voz criada."),
    "atualizar": (0.5, 3, "Atualização conferida."),
    "atualizar-dependencias": (1, 6, "Dependências conferidas."),
    "demanda": (1, 4, "A pesquisa de assuntos terminou."),
    "outliers": (1, 5, "A pesquisa de assuntos terminou."),
}


def _tempo(minutos: float) -> str:
    if minutos < 1:
        return f"{round(minutos * 60)} s"
    if minutos < 60:
        return f"{round(minutos)} min"
    horas, resto = divmod(round(minutos), 60)
    return f"{horas} h" + (f" {resto} min" if resto else "")


def descrever(dados: dict, comandos: list[list[str]]) -> dict:
    """Estimativa (segundos), se é longa, se pode fechar a página e a frase de pronto."""
    primeiro = comandos[0][0] if comandos and comandos[0] else ""
    fechar, aviso = True, FECHAR_SIM
    if primeiro == "leva":
        from ..leva import estimar
        args = comandos[0]
        try:
            quantidade = int(args[args.index("--quantidade") + 1])
        except (ValueError, IndexError):
            quantidade = 1
        faixa = estimar(dados, quantidade)["total"]
        minimo, maximo = faixa[0], faixa[1]
        pronto = "Os vídeos aparecem em Início para você assistir e aprovar."
    elif primeiro == "fila-produzir" and any(c and c[0].startswith("publicar") for c in comandos):
        minimo, maximo, pronto = 3, 10, "O vídeo foi publicado nas plataformas do canal."
    elif primeiro.startswith("nuvem"):
        minimo, maximo, pronto = 0.5, 3, "Nuvem atualizada."
    else:
        minimo, maximo, pronto = _TIPOS.get(primeiro, (0.5, 3, "Tudo certo."))
        if primeiro == "fila-produzir":
            from ..leva import estimar
            minimo, maximo = estimar(dados, 1)["por_video"]
    if primeiro in ("conectar-github", "conectar-azure"):
        fechar, aviso = False, FECHAR_LOGIN
    elif primeiro == "autorizar-youtube":
        aviso = FECHAR_GOOGLE
    texto = _tempo(maximo) if minimo == maximo else f"{_tempo(minimo)} a {_tempo(maximo)}"
    return {"estimativa_min_s": int(minimo * 60), "estimativa_max_s": int(maximo * 60),
            "estimativa": f"cerca de {texto}", "longa": maximo > LONGA_MIN, "fechar": fechar,
            "aviso_fechar": aviso, "pronto": pronto, "animacao_max_s": ANIMACAO_MAX_S}


_CODIGO = (re.compile(r"one-time code:\s*([A-Z0-9]{4}-[A-Z0-9]{4})"),
           re.compile(r"enter the code\s+([A-Z0-9]{8,12})\b"))
_RUIDO = re.compile(r"^(\$ darkops|Traceback|\s+File |\s+\^|During handling)")


def codigo_login(log: str) -> str:
    """Código de 8 letras do login por dispositivo (GitHub ou Microsoft) para mostrar grande na tela."""
    for padrao in _CODIGO:
        achado = padrao.findall(log)
        if achado:
            return achado[-1]
    return ""


def resumo(log: str, sucesso: bool = False) -> str:
    """Última frase útil do log, curta e sem segredos, para o resultado em uma linha. No sucesso, só se parecer
    uma frase (nada de tabela, caminho de arquivo ou lista técnica)."""
    for linha in reversed(log.splitlines()):
        linha = linha.strip()
        if not linha or _RUIDO.match(linha) or len(linha) < 4:
            continue
        linha = re.sub(r"^(SystemExit|RuntimeError|ValueError|Exception|Erro|erro):\s*", "", linha)
        linha = seguranca.ocultar(linha)
        if sucesso and (re.search(r"\s{3,}|[A-Za-z]:\\|/\w+/|^[\[{(]", linha) or " " not in linha):
            return ""
        return linha if len(linha) <= 220 else linha[:217].rstrip() + "…"
    return ""
