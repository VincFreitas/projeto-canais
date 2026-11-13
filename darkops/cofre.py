# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Cofre: os segredos ficam cifrados no disco (decisão do dono em 2026-11-12: criptografar só os segredos; código e
documentos continuam abertos para qualquer pessoa e qualquer IA ler).

O que é cifrado:
- tokens dos canais (perfis/<id>/credenciais/token_youtube.json e token_instagram.txt);
- o app do Google (credenciais/client_secret.json) e qualquer outro arquivo em credenciais/;
- no .env, só os valores de nomes com KEY, TOKEN, SECRET, SENHA, PASSWORD ou VERIFICAR (o resto, como
  DARKOPS_MODO_GUIADO, continua legível). O valor vira `cofre:<base64>`.

Cifra: XSalsa20-Poly1305 (SecretBox do PyNaCl, que o projeto já usa para os Secrets do GitHub), com uma chave de 32
bytes por usuário do sistema:
- Windows: a chave fica em dados/cofre.chave protegida pelo DPAPI (só abre no mesmo usuário do mesmo PC);
- macOS e Linux: no chaveiro do sistema (Keychain, Secret Service) pelo pacote keyring; sem chaveiro (servidor sem
  tela), num arquivo só do dono em ~/.config/projeto-canais (Linux) ou ~/Library/Application Support (macOS), fora
  da pasta do projeto.
Copiar a pasta do projeto para outro PC não leva os segredos legíveis: lá é só conectar as contas de novo.

No GitHub Actions (nuvem) os arquivos são gravados em claro: a máquina é descartada no fim e os valores vêm dos
Secrets do GitHub. Ler sempre aceita arquivo em claro (o que veio antes do cofre); `proteger()` cifra o que falta."""
from __future__ import annotations

import base64
import os
import re
import stat
from pathlib import Path

from . import sistema

MAGICO = b"PCCOFRE1\n"
PREFIXO = "cofre:"
SERVICO, CONTA = "projeto-canais", "cofre"
SEGREDO_ENV = re.compile(r"KEY|TOKEN|SECRET|SENHA|PASSWORD|VERIFICAR", re.I)
_chave_cache: bytes | None = None


class CofreFechado(RuntimeError):
    """A chave deste usuário não abre o segredo (pasta copiada de outro PC ou chave apagada)."""


def _raiz() -> Path:
    from . import config
    return config.RAIZ


def ligado() -> bool:
    return not sistema.nuvem_ci() and os.environ.get("DARKOPS_COFRE", "1") != "0"


# ---------- a chave ----------

def _dpapi(dados: bytes, proteger: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def blob(b: bytes):
        buf = ctypes.create_string_buffer(b, len(b))
        return Blob(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    entrada, _b1 = blob(dados)
    entropia, _b2 = blob(b"projeto-canais-cofre")
    saida = Blob()
    funcao = crypt32.CryptProtectData if proteger else crypt32.CryptUnprotectData
    funcao.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                       ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    funcao.restype = wintypes.BOOL
    if not funcao(ctypes.byref(entrada), None, ctypes.byref(entropia), None, None, 0x1, ctypes.byref(saida)):
        raise CofreFechado("o Windows não abriu a chave do cofre (outro usuário ou outro PC)")
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        kernel32.LocalFree(saida.pbData)


def _arquivo_chave() -> Path:
    return _raiz() / "dados" / "cofre.chave" if sistema.WINDOWS else sistema.pasta_usuario() / "cofre.chave"


def _gravar_privado(arquivo: Path, dados: bytes) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temp = arquivo.with_name(arquivo.name + ".novo")
    if not sistema.WINDOWS:  # nasce só do dono, antes de ter conteúdo
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
    else:
        temp.write_bytes(dados)
    os.replace(temp, arquivo)


def _ler_chave() -> bytes | None:
    if sistema.WINDOWS:
        arquivo = _arquivo_chave()
        return _dpapi(arquivo.read_bytes(), proteger=False) if arquivo.exists() else None
    try:
        import keyring
        valor = keyring.get_password(SERVICO, CONTA)
        if valor:
            return base64.b64decode(valor)
    except Exception:  # noqa: BLE001 — sem chaveiro (servidor sem tela): vai para o arquivo
        pass
    arquivo = _arquivo_chave()
    return base64.b64decode(arquivo.read_text().strip()) if arquivo.exists() else None


def _criar_chave() -> bytes:
    from nacl.secret import SecretBox
    from nacl.utils import random
    chave = random(SecretBox.KEY_SIZE)
    if sistema.WINDOWS:
        _gravar_privado(_arquivo_chave(), _dpapi(chave, proteger=True))
        return chave
    try:
        import keyring
        keyring.set_password(SERVICO, CONTA, base64.b64encode(chave).decode())
        if keyring.get_password(SERVICO, CONTA):
            return chave
    except Exception:  # noqa: BLE001
        pass
    _gravar_privado(_arquivo_chave(), base64.b64encode(chave))
    return chave


def _chave(criar: bool = True) -> bytes | None:
    global _chave_cache
    if _chave_cache is None:
        _chave_cache = _ler_chave() or (_criar_chave() if criar else None)
    return _chave_cache


# ---------- cifrar e decifrar ----------

def cifrar(dados: bytes) -> bytes:
    from nacl.secret import SecretBox
    return MAGICO + base64.b64encode(SecretBox(_chave()).encrypt(dados)) + b"\n"


def cifrado(dados: bytes) -> bool:
    return dados.startswith(MAGICO)


def decifrar(dados: bytes) -> bytes:
    if not cifrado(dados):
        return dados  # arquivo de antes do cofre (ou da nuvem): em claro
    from nacl.exceptions import CryptoError
    from nacl.secret import SecretBox
    chave = _chave(criar=False)
    if not chave:
        raise CofreFechado("a chave do cofre sumiu deste PC: conecte a conta de novo")
    try:
        return SecretBox(chave).decrypt(base64.b64decode(dados[len(MAGICO):].strip()))
    except (CryptoError, ValueError) as erro:
        raise CofreFechado("a chave deste PC não abre este segredo: conecte a conta de novo") from erro


def ler(arquivo: Path) -> str:
    """Conteúdo de um arquivo de segredo, cifrado ou não."""
    return decifrar(Path(arquivo).read_bytes()).decode("utf-8-sig")


def gravar(arquivo: Path, texto: str) -> None:
    """Grava um segredo cifrado (em claro só na nuvem), sem nunca deixar meio arquivo no disco."""
    dados = texto.encode("utf-8")
    _gravar_privado(Path(arquivo), cifrar(dados) if ligado() else dados)


# ---------- .env ----------

def segredo_env(nome: str) -> bool:
    return bool(SEGREDO_ENV.search(nome)) and not nome.startswith("DARKOPS_")


def valor_env(nome: str, valor: str) -> str:
    """O valor como vai para o .env: cifrado se o nome é de segredo."""
    if not valor or not ligado() or not segredo_env(nome) or valor.startswith(PREFIXO):
        return valor
    from nacl.secret import SecretBox
    return PREFIXO + base64.urlsafe_b64encode(SecretBox(_chave()).encrypt(valor.encode())).decode()


def abrir_env(valor: str | None) -> str | None:
    if not valor or not valor.startswith(PREFIXO):
        return valor
    from nacl.secret import SecretBox
    chave = _chave(criar=False)
    if not chave:
        raise CofreFechado("a chave do cofre sumiu deste PC")
    return SecretBox(chave).decrypt(base64.urlsafe_b64decode(valor[len(PREFIXO):])).decode()


def carregar_env() -> list[str]:
    """Depois do load_dotenv: troca no ambiente do processo cada `cofre:...` pelo valor. Devolve os que não abriram
    (ficam fora do ambiente, e a tela de Chaves mostra como faltando)."""
    falhas = []
    for nome, valor in list(os.environ.items()):
        if valor.startswith(PREFIXO):
            try:
                os.environ[nome] = abrir_env(valor) or ""
            except Exception:  # noqa: BLE001 — nunca derruba o app por uma chave; ela só fica faltando
                del os.environ[nome]
                falhas.append(nome)
    return falhas


def ler_env(arquivo: Path | None = None) -> dict[str, str]:
    """O .env como dicionário, com os segredos já abertos (o que não abrir fica vazio)."""
    from dotenv import dotenv_values
    arquivo = arquivo or _raiz() / ".env"
    if not arquivo.exists():
        return {}
    saida = {}
    for nome, valor in dotenv_values(arquivo).items():
        try:
            saida[nome] = abrir_env(valor) or ""
        except Exception:  # noqa: BLE001
            saida[nome] = ""
    return saida


# ---------- conferir e proteger ----------

def arquivos_de_segredo() -> list[Path]:
    raiz = _raiz()
    achados = list((raiz / "credenciais").glob("*")) + list((raiz / "perfis").glob("*/credenciais/*"))
    return [a for a in achados if a.is_file() and not a.name.endswith((".novo", ".bak"))]


def _env_em_claro() -> list[str]:
    from dotenv import dotenv_values
    arquivo = _raiz() / ".env"
    if not arquivo.exists():
        return []
    return [n for n, v in dotenv_values(arquivo).items() if v and segredo_env(n) and not v.startswith(PREFIXO)]


def em_claro() -> list[str]:
    """Segredos ainda sem cifra (arquivos e nomes do .env). Na nuvem nada é cobrado."""
    if not ligado():
        return []
    raiz = _raiz()
    saida = [str(a.relative_to(raiz)) for a in arquivos_de_segredo() if not cifrado(a.read_bytes()[:len(MAGICO)])]
    return saida + [f".env:{n}" for n in _env_em_claro()]


def proteger() -> list[str]:
    """Cifra tudo o que está em claro e deixa os arquivos legíveis só pelo dono. Confere cada um lendo de volta."""
    if not ligado():
        return []
    feitos = []
    for arquivo in arquivos_de_segredo():
        bruto = arquivo.read_bytes()
        if not cifrado(bruto):
            texto, antes = bruto.decode("utf-8-sig"), arquivo.stat()
            gravar(arquivo, texto)
            if ler(arquivo) != texto:  # nunca perde um token: se não voltar igual, desfaz
                arquivo.write_bytes(bruto)
                raise CofreFechado(f"o cofre não conferiu {arquivo.name}; nada foi mudado nele")
            # a data do arquivo marca a idade do token do Instagram (renova aos 40 dias): cifrar não pode zerar
            os.utime(arquivo, (antes.st_atime, antes.st_mtime))
            feitos.append(str(arquivo.relative_to(_raiz())))
        elif not sistema.WINDOWS:
            os.chmod(arquivo, stat.S_IRUSR | stat.S_IWUSR)
    nomes = _env_em_claro()
    if nomes:
        from dotenv import dotenv_values
        valores = dotenv_values(_raiz() / ".env")
        reescrever_env({n: valores[n] or "" for n in nomes})
        feitos += [f".env:{n}" for n in nomes]
    return feitos


def reescrever_env(novos: dict[str, str]) -> None:
    """Troca (ou acrescenta) linhas do .env, cifrando os segredos. Recusa quebra de linha no nome ou no valor."""
    for nome, valor in novos.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome) or "\n" in valor or "\r" in valor:
            raise ValueError(f"valor inválido para {nome!r}")
    arquivo = _raiz() / ".env"
    linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
    vistos = set()
    for i, linha in enumerate(linhas):  # nome repetido no .env: todas as linhas dele mudam
        nome = linha.split("=", 1)[0].strip()
        if "=" in linha and not linha.lstrip().startswith("#") and nome in novos:
            linhas[i] = f"{nome}={valor_env(nome, novos[nome])}"
            vistos.add(nome)
    linhas += [f"{n}={valor_env(n, v)}" for n, v in novos.items() if n not in vistos]
    _gravar_privado(arquivo, ("\n".join(linhas) + "\n").encode("utf-8"))
