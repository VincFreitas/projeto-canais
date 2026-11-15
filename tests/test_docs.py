# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""A documentação acompanha o código: todo comando da CLI está em docs/cli.md (e nada que não existe), todo
argumento tem ajuda e os docs novos estão ligados ao README."""
import argparse
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

OCULTOS = {"estrela"}  # comando escondido de propósito (easter egg): fica fora da doc


def _comandos() -> dict[str, argparse.ArgumentParser]:
    from darkops.__main__ import criar_parser
    sub = next(a for a in criar_parser()._actions if isinstance(a, argparse._SubParsersAction))
    return {nome: p for nome, p in sub.choices.items() if nome not in OCULTOS}


class Docs(unittest.TestCase):
    def test_todo_comando_documentado(self):
        texto = (RAIZ / "docs" / "cli.md").read_text(encoding="utf-8")
        documentados = set(re.findall(r"^### `([\w-]+)`", texto, re.M))
        comandos = set(_comandos())
        self.assertEqual(sorted(comandos - documentados), [], "comando sem doc em docs/cli.md")
        self.assertEqual(sorted(documentados - comandos), [], "docs/cli.md fala de comando que não existe")

    def test_todo_argumento_tem_ajuda(self):
        sem_ajuda = [f"{nome} {a.option_strings or a.dest}" for nome, p in _comandos().items() for a in p._actions
                     if not isinstance(a, argparse._HelpAction) and not a.help]
        self.assertEqual(sem_ajuda, [])

    def test_docs_ligados(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        for doc in ("arquitetura.md", "desenvolvimento.md", "cli.md", "seguranca.md"):
            self.assertTrue((RAIZ / "docs" / doc).exists(), doc)
            self.assertIn(f"docs/{doc}", readme, f"README sem link para docs/{doc}")


if __name__ == "__main__":
    unittest.main()
