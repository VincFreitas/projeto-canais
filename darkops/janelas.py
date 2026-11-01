"""Sem janelas de prompt piscando no Windows.

O Projeto Canais abre pelo pythonw (sem console). Nesse caso, cada programa de console que ele chama
(git, powershell, taskkill, ffmpeg, o próprio python das tarefas...) ganharia uma janela preta própria que
pisca na tela. `esconder()` faz todo subprocess desse processo nascer com CREATE_NO_WINDOW, a não ser que
quem chamou tenha pedido outra coisa (DETACHED_PROCESS ou CREATE_NEW_CONSOLE).

Só vale quando o processo não tem janela de console: rodando a CLI num terminal, a saída dos comandos
continua aparecendo nele.
"""
import os
import subprocess

_LIGADO = False


def sem_console() -> bool:
    if os.name != "nt":
        return False
    import ctypes
    return ctypes.windll.kernel32.GetConsoleWindow() == 0


def esconder() -> None:
    global _LIGADO
    if _LIGADO or not sem_console():
        return
    original = subprocess.Popen.__init__
    proprios = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE

    def iniciar(self, *args, **kwargs):
        flags = kwargs.get("creationflags", 0) or 0
        if not flags & proprios:
            kwargs["creationflags"] = flags | subprocess.CREATE_NO_WINDOW
        original(self, *args, **kwargs)

    subprocess.Popen.__init__ = iniciar
    _LIGADO = True
