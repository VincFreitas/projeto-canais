# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Testes rápidos que rodam em Windows, macOS e Linux (CI em .github/workflows/testes.yml):
python -m unittest discover -s tests -v"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "darkops", *args], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300,
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})


class Basico(unittest.TestCase):
    def test_cli_abre(self):
        r = cli("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("integridade", r.stdout)
        from darkops import __version__
        self.assertIn(__version__, cli("--version").stdout)

    def test_ocultar(self):
        from darkops.seguranca import ocultar
        # montado em pedaços: um token de mentira inteiro no código faria a rotina de integridade acusar chave vazada
        texto = ocultar("ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + ' {"access_token": "abc"} ya29.' + "a" * 30)
        self.assertNotIn("ghp_ABC", texto)
        self.assertNotIn('"abc"', texto)
        self.assertNotIn("ya29.aaaa", texto)

    def test_cofre_ida_e_volta(self):
        from darkops import cofre
        dados = '{"token": "teste"}'.encode()
        self.assertEqual(cofre.decifrar(cofre.cifrar(dados)), dados)
        self.assertEqual(cofre.decifrar(b"em claro"), b"em claro")  # arquivo de antes do cofre continua legivel

    def test_roteiro_nao_sai_do_projeto(self):
        from darkops.producao import caminhos_inseguros
        erros = caminhos_inseguros({"slug": "a/../b", "palco": "../x.py", "cenas": [{"arquivo": "/etc/passwd"}]},
                                   RAIZ / "perfis" / "x" / "fila" / "1.json")
        self.assertEqual(len(erros), 3)
        self.assertEqual(caminhos_inseguros({"slug": "ok-1", "cenas": []}, RAIZ / "roteiros" / "a.json"), [])

    def test_workflow_n8n_nos_dois_shells(self):
        from darkops import instalacao
        modelo = instalacao.MODELO.read_text(encoding="utf-8")
        for windows in (True, False):
            texto = instalacao._preencher(modelo, windows=windows)
            dados = json.loads(texto)
            comandos = [n["parameters"]["command"] for n in dados["nodes"] if "command" in n.get("parameters", {})]
            self.assertTrue(comandos)
            self.assertEqual(any("cd /d" in c for c in comandos), windows)

    def test_mcp(self):
        from darkops.mcp_servidor import tratar
        inicio = tratar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(inicio["protocolVersion"], "2025-06-18")
        nomes = {f["name"] for f in tratar({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]}
        self.assertIn("diagnostico", nomes)
        self.assertNotIn("publicar", nomes)  # publicar continua sendo o clique do dono
        self.assertIsNone(tratar({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_fontes_do_windows_em_qualquer_sistema(self):
        from darkops import config  # noqa: F401 (instala a tradução de fontes)
        from PIL import ImageFont
        self.assertIsNotNone(ImageFont.truetype("C:/Windows/Fonts/ariblk.ttf", 40))

    def test_estudio_protegido(self):
        from darkops.estudio import app
        c = app.test_client()
        local = {"Host": "127.0.0.1:8765"}
        for url in ("/saude", "/configuracoes", "/progresso", "/sobre"):
            self.assertIn(c.get(url, headers=local).status_code, (200, 302), url)
        self.assertEqual(c.get("/", headers={"Host": "exemplo.invalid"}).status_code, 403)
        self.assertEqual(c.post("/configuracoes", headers=local, data={"acao": "x"}).status_code, 403)

    def test_estudio_modo_escuro(self):
        """Tema claro, escuro e automático: o tema.js vem antes do CSS (sem piscar branco), o seletor tem as três
        opções e o texto passa no contraste WCAG AA (4,5:1) nos dois temas."""
        import re
        from darkops.estudio import app
        html = app.test_client().get("/sobre", headers={"Host": "127.0.0.1:8765"}).get_data(as_text=True)
        cabeca = html.split("</head>")[0]
        self.assertLess(cabeca.find("tema.js"), cabeca.find("estudio.css"))
        etiqueta = re.search(r"<script[^>]*tema\.js[^>]*>", cabeca)
        self.assertIsNotNone(etiqueta)
        self.assertNotIn("defer", etiqueta.group(0) if etiqueta else "")
        self.assertEqual(sorted(re.findall(r'data-escolher-tema="(\w+)"', html)), ["auto", "claro", "escuro"])
        css = (RAIZ / "darkops" / "estudio" / "static" / "estudio.css").read_text(encoding="utf-8")

        def variaveis(seletor):
            bloco = css.split(seletor + " {", 1)[1].split("}", 1)[0]
            return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\b", bloco))

        def contraste(a, b):
            def lum(cor):
                canais = [int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
                r, g, b_ = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
                return 0.2126 * r + 0.7152 * g + 0.0722 * b_
            claro, escuro = sorted((lum(a), lum(b)), reverse=True)
            return (claro + 0.05) / (escuro + 0.05)

        claro = variaveis(":root")
        escuro = {**claro, **variaveis(':root[data-tema="escuro"]')}
        self.assertEqual(escuro["amarelo"], "#ffc400")  # a cor da logo não muda no escuro
        pares = [("texto", "fundo"), ("texto", "cartao"), ("texto", "elevado"), ("texto", "escolhido"), ("texto", "neutro"),
                 ("suave", "fundo"), ("suave", "cartao"), ("suave", "cartao-suave"), ("suave", "neutro"), ("suave", "elevado"),
                 ("ok-texto", "ok-fundo"), ("erro-texto", "erro-fundo"), ("alerta-texto", "alerta-fundo"),
                 ("info-texto", "info-fundo"), ("verde-texto", "cartao"), ("vermelho", "cartao"), ("azul", "cartao")]
        for nome, tema in (("claro", claro), ("escuro", escuro)):
            for texto, fundo in pares:
                self.assertGreaterEqual(contraste(tema[texto], tema[fundo]), 4.5, f"{nome}: --{texto} sobre --{fundo}")

    def test_skills_tem_cabecalho(self):
        for skill in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"):
            texto = skill.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith("---\nname: "), skill)
            self.assertIn("\ndescription: ", texto.split("---")[1], skill)


class SemJanela(unittest.TestCase):
    """No pythonw (Estúdio, rotinas), node, ffmpeg e powershell abriam uma janela de terminal cada (2026-11-17)."""

    def test_filho_sai_sem_janela(self):
        from darkops.sistema import _com_janela_escondida
        sem_janela = 0x08000000
        self.assertEqual(_com_janela_escondida((["node"],), {}), {"creationflags": sem_janela})
        self.assertEqual(_com_janela_escondida((["x"],), {"creationflags": 0x200})["creationflags"], 0x200 | sem_janela)
        for proprio in (0x10, 0x08, sem_janela):  # novo console, processo solto ou já sem janela: a chamada decidiu
            self.assertEqual(_com_janela_escondida((["x"],), {"creationflags": proprio}), {"creationflags": proprio})
        self.assertEqual(_com_janela_escondida(tuple(range(14)), {}), {})  # creationflags pela posição

    def test_com_terminal_nada_muda(self):
        """No terminal (dark.ps1, testes) os filhos usam o mesmo console: a saída não pode sumir num console escondido."""
        if os.name == "nt":
            import ctypes
            if not ctypes.windll.kernel32.GetConsoleCP():
                self.skipTest("estes testes rodam sem console")
        r = subprocess.run([sys.executable, "-c", "import darkops, subprocess; print(hasattr(subprocess.Popen, '_sem_janela'))"],
                           cwd=RAIZ, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.stdout.strip(), "False", r.stderr)


if __name__ == "__main__":
    unittest.main()
