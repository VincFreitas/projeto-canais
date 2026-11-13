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
        texto = ocultar('ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 {"access_token": "abc"} ya29.' + "a" * 30)
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

    def test_skills_tem_cabecalho(self):
        for skill in (RAIZ / ".claude" / "skills").glob("*/SKILL.md"):
            texto = skill.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith("---\nname: "), skill)
            self.assertIn("\ndescription: ", texto.split("---")[1], skill)


if __name__ == "__main__":
    unittest.main()
