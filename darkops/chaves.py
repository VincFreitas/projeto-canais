"""Confere uma chave de serviço na hora em que ela é colada, antes de salvar no .env.

Cada teste é uma chamada pequena e gratuita à API do serviço. Respostas:
  (True, texto)  chave aceita
  (False, texto) o serviço recusou a chave (não salva)
  (None, texto)  não deu para testar agora (sem internet, serviço fora): salva e avisa
"""
import urllib.error
import urllib.parse
import urllib.request

from .seguranca import ocultar

RECUSADA = {400, 401, 403}


def _pedir(url: str, cabecalhos: dict | None = None, metodo: str = "GET") -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "projeto-canais", **(cabecalhos or {})}, method=metodo,
                                 data=b"" if metodo == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status
    except urllib.error.HTTPError as erro:
        return erro.code


def _teste(nome: str, valor: str, env: dict) -> tuple[str, int]:
    if nome == "AZURE_SPEECH_KEY":
        regiao = (env.get("AZURE_SPEECH_REGION") or "brazilsouth").strip()
        return (f"Azure Speech ({regiao})",
                _pedir(f"https://{urllib.parse.quote(regiao)}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
                       {"Ocp-Apim-Subscription-Key": valor}, "POST"))
    if nome == "PIXABAY_API_KEY":
        return "Pixabay", _pedir("https://pixabay.com/api/?" + urllib.parse.urlencode({"key": valor, "q": "sky", "per_page": 3}))
    if nome == "PEXELS_API_KEY":
        return "Pexels", _pedir("https://api.pexels.com/v1/search?query=sky&per_page=1", {"Authorization": valor})
    if nome == "ELEVENLABS_API_KEY":
        return "ElevenLabs", _pedir("https://api.elevenlabs.io/v1/user", {"xi-api-key": valor})
    return "", 0


def validar(nome: str, valor: str, env: dict) -> tuple[bool | None, str]:
    try:
        servico, status = _teste(nome, valor, env)
    except OSError as erro:
        return None, ocultar(f"não deu para testar a chave agora ({type(erro).__name__}); ela foi salva assim mesmo")
    if not servico:
        return None, ""
    if status == 200:
        return True, f"{servico}: chave conferida e salva"
    if status in RECUSADA:
        dica = " Confira também a região do recurso no portal do Azure." if nome == "AZURE_SPEECH_KEY" else ""
        return False, f"{servico} recusou a chave (código {status}); ela não foi salva.{dica}"
    return None, f"{servico} não respondeu agora (código {status}); a chave foi salva assim mesmo"
