# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Atualizações autônomas (volta do que quebra) e vitrine (números do canal no README e no site), sem rede nem git:
python -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

README = """## Feito com o Projeto Canais

| Números reais (11 de novembro de 2026, pelas APIs oficiais) | YouTube | Instagram |
|---|---|---|
| Vídeos publicados | 20 | 19 |
| Visualizações | 15.112 | 6.795 |
| Curtidas | 453 | 132 |
| Inscritos e seguidores | 43 | 6 |
| Vídeo mais visto | 1.365 visualizações | 1.274 visualizações |

O canal nasceu em 20 de outubro de 2026, então tinha três semanas nessa contagem. São números de um canal novo.
"""
SITE = """<div class="surge"><b>39</b><span>vídeos no YouTube e no Instagram</span></div>
<div class="surge"><b>21.907</b><span>visualizações em três semanas</span></div>
<p class="lead">Números reais de 11 de novembro de 2026, pelas APIs oficiais. Canal novo.</p>"""


def _plataforma(videos, seguidores, views, curtidas):
    return {"conta": {"videos": videos, "seguidores": seguidores},
            "videos": [{"visualizacoes": v, "curtidas": curtidas, "publicado": "2026-10-21T15:00:00Z"} for v in views]}


class Vitrine(unittest.TestCase):
    def setUp(self):
        from darkops import vitrine
        self.v = vitrine
        dados = {"plataformas": {"youtube": _plataforma(21, 1047, [10000, 7425], 289),
                                 "instagram": _plataforma(21, 7, [5000, 2126], 70)}}
        self.n = vitrine.numeros(dados, date(2026, 12, 1))
        self.n["nasceu"] = vitrine.nascimento(README)

    def test_readme(self):
        novo = self.v.readme(README, self.n)
        self.assertIn("| Números reais (1 de dezembro de 2026, pelas APIs oficiais) | YouTube | Instagram |", novo)
        self.assertIn("| Visualizações | 17.425 | 7.126 |", novo)
        self.assertIn("| Inscritos e seguidores | 1.047 | 7 |", novo)
        self.assertIn("| Vídeo mais visto | 10.000 visualizações | 5.000 visualizações |", novo)
        self.assertIn("O canal nasceu em 20 de outubro de 2026, então tinha seis semanas nessa contagem.", novo)
        self.assertEqual(self.v.readme(novo, self.n), novo)  # rodar de novo não muda nada

    def test_site(self):
        novo = self.v.site(SITE, self.n)
        self.assertIn("<b>42</b><span>vídeos no YouTube e no Instagram</span>", novo)
        self.assertIn("<b>24.551</b><span>visualizações em seis semanas</span>", novo)
        self.assertIn("Números reais de 1 de dezembro de 2026, pelas APIs oficiais.", novo)

    def test_formato_mudou_avisa(self):
        with self.assertRaises(ValueError):
            self.v.readme(README.replace("| Curtidas |", "| Likes |"), self.n)

    def test_idade(self):
        nasceu = date(2026, 1, 1)
        casos = {1: "um dia", 13: "13 dias", 14: "duas semanas", 62: "oito semanas", 63: "dois meses",
                 800: "dois anos"}
        for dias, esperado in casos.items():
            self.assertEqual(self.v.idade(nasceu, date.fromordinal(nasceu.toordinal() + dias)), esperado)


class AtualizacaoComVolta(unittest.TestCase):
    """Sobe o grupo; se quebrar, volta e tenta um por um; o que quebra fica recusado."""

    def setUp(self):
        from darkops import terceiros
        self.t = terceiros
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(terceiros, "RECUSADAS", Path(self.tmp.name) / "recusadas.json")
        patch.start()
        self.addCleanup(patch.stop)

    def _itens(self):
        return [{"id": f"py:{n}", "nome": n, "atual": "1.0", "nova": "2.0"} for n in ("bom", "ruim", "outro")]

    def _rodar(self, itens, quebra):
        instalados = {i["nome"]: "1.0" for i in itens}

        def subir(lote):
            instalados.update({i["nome"]: "2.0" for i in lote})
            return ""

        def voltar(lote):
            instalados.update({i["nome"]: "1.0" for i in lote})

        def conferir():
            return ["teste x"] if any(instalados[n] == "2.0" for n in quebra) else []

        self.t._em_grupo(itens, subir, voltar, conferir)
        return instalados

    def test_tudo_passa(self):
        itens = self._itens()
        instalados = self._rodar(itens, quebra=())
        self.assertEqual(set(instalados.values()), {"2.0"})
        self.assertTrue(all(i.get("atualizado") for i in itens))
        self.assertEqual(self.t.recusadas(), {})

    def test_um_quebra_e_volta(self):
        itens = self._itens()
        instalados = self._rodar(itens, quebra=("ruim",))
        self.assertEqual(instalados, {"bom": "2.0", "ruim": "1.0", "outro": "2.0"})
        ruim = next(i for i in itens if i["nome"] == "ruim")
        self.assertTrue(ruim.get("desfeito"))
        self.assertEqual(self.t.recusadas()["py:ruim"]["versao"], "2.0")

    def test_recusada_pula_no_automatico(self):
        self._rodar(self._itens(), quebra=("ruim",))
        itens = [{**i, "aplicavel": True, "tipo": "Python"} for i in self._itens()]
        with mock.patch.object(self.t, "ocupado", return_value="produzir"):
            tocados = self.t.aplicar(itens, automatico=True)
        self.assertNotIn("py:ruim", [i["id"] for i in tocados])
        self.assertTrue(all(i["resultado"].startswith("fica para depois") for i in tocados))

    def test_falha_antiga_nao_culpa_a_versao_nova(self):
        itens = self._itens()[:1]
        self.t._em_grupo(itens, lambda lote: "", lambda lote: None, lambda: ["já falhava"])
        self.assertTrue(itens[0].get("atualizado"))


if __name__ == "__main__":
    unittest.main()
