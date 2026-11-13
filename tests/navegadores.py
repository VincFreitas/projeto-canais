# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Abre as telas do Estúdio no Chromium, no Firefox e no WebKit (o motor do Safari) e confere: sem erro de script e
sem rolagem lateral em 320, 375, 768 e 1920 px. Motor que não estiver instalado é pulado.

    python -m playwright install chromium firefox webkit   (no Linux: --with-deps)
    python tests/navegadores.py"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TELAS = ["/", "/abertura", "/progresso", "/saude", "/configuracoes", "/sobre", "/perfis"]
LARGURAS = [320, 375, 768, 1920]


def main() -> int:
    from playwright.sync_api import Error, sync_playwright
    from werkzeug.serving import make_server

    from darkops.estudio import app
    servidor = make_server("127.0.0.1", 0, app, threaded=True)
    porta = servidor.server_port
    import os
    os.environ["PORT"] = str(porta)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    falhas, testados = [], []
    with sync_playwright() as p:
        for nome in ("chromium", "firefox", "webkit"):
            try:
                nav = getattr(p, nome).launch()
            except Error as erro:
                print(f"{nome}: não instalado, pulado ({str(erro).splitlines()[0][:80]})")
                continue
            testados.append(nome)
            for largura in LARGURAS:
                pg = nav.new_page(viewport={"width": largura, "height": 900})
                erros = []
                pg.on("pageerror", lambda e, lista=erros: lista.append(str(e)))
                for tela in TELAS:
                    resposta = pg.goto(f"http://127.0.0.1:{porta}{tela}", wait_until="load")
                    if resposta and resposta.status >= 500:
                        falhas.append(f"{nome} {largura}px {tela}: HTTP {resposta.status}")
                    lateral = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    if lateral > 1:
                        falhas.append(f"{nome} {largura}px {tela}: rolagem lateral de {lateral}px")
                falhas += [f"{nome} {largura}px: erro de script: {e[:160]}" for e in erros]
                pg.close()
            nav.close()
    servidor.shutdown()
    print(f"motores testados: {', '.join(testados) or 'nenhum'}")
    print("\n".join(falhas) or "tudo certo")
    return 1 if falhas or not testados else 0


if __name__ == "__main__":
    sys.exit(main())
