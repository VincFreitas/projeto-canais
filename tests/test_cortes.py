# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Cortes de live: quem pode ser cortado, os sinais dos melhores momentos, a escolha e o layout (sem rede)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from darkops import cortes  # noqa: E402


class PerfilFalso:
    def __init__(self, dados=None):
        self.dados = dados or {}

    def salvar(self, novos):
        self.dados.update(novos)


class TestFontes(unittest.TestCase):
    def test_chaves_do_link(self):
        self.assertEqual(cortes.chaves_do_link("https://www.youtube.com/@PaulinhoLOKOoficial/streams"),
                         {"youtube:@paulinholokooficial"})
        self.assertEqual(cortes.chaves_do_link("https://www.twitch.tv/Gaules"), {"twitch:gaules"})
        self.assertEqual(cortes.chaves_do_link("https://www.twitch.tv/videos/123456"), set())
        self.assertEqual(cortes.chaves_do_link("https://kick.com/streamer-x"), {"kick:streamer-x"})
        self.assertEqual(cortes.chaves_do_link("https://exemplo.com/x"), set())

    def test_autorizacao_bate_pelo_canal_da_live(self):
        perfil = PerfilFalso()
        cortes.registrar_fonte(perfil, url="https://www.youtube.com/@Streamer", como="teste")
        info = {"plataforma": "youtube", "canal_url": "https://www.youtube.com/channel/UCabcdefghijklmnop",
                "arroba": "@Streamer", "canal_id": "UCabcdefghijklmnop"}
        self.assertIsNotNone(cortes.autorizado(perfil, info))
        outro = {**info, "arroba": "@Outro", "canal_id": "UCzzzzzzzzzzzzzz", "canal_url": ""}
        self.assertIsNone(cortes.autorizado(perfil, outro))

    def test_corte_sem_autorizacao_nao_aprova(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "001-corte.json"
            dados = {"tipo": "corte", "aprovado": False,
                     "corte": {"streamer": "Fulano", "canal_url": "https://www.twitch.tv/fulano", "autorizado": False}}
            caminho.write_text(json.dumps(dados), encoding="utf-8")
            perfil = PerfilFalso()
            self.assertIn("autorização", cortes.pode_aprovar(perfil, caminho, dados))
            cortes.registrar_fonte(perfil, url="https://www.twitch.tv/fulano")
            self.assertEqual(cortes.pode_aprovar(perfil, caminho, dados), "")
            self.assertTrue(json.loads(caminho.read_text(encoding="utf-8"))["corte"]["autorizado"])
            self.assertEqual(cortes.pode_aprovar(perfil, caminho, {"tipo": "roteiro"}), "")


class TestSinais(unittest.TestCase):
    def test_pico_de_volume_vira_candidato(self):
        duracao = 1200
        volume = [-30.0] * duracao
        for s in range(600, 606):
            volume[s] = -8.0  # grito
        notas = cortes.pontuar(duracao, volume, [], [])
        cands = cortes.candidatos(notas, duracao, 3)
        self.assertTrue(any(abs(c["pico"] - 602) <= 4 for c in cands), cands)
        principal = max(cands, key=lambda c: c["nota"])
        self.assertLess(principal["inicio"], principal["pico"])  # começa antes do lance
        self.assertGreater(principal["fim"], principal["pico"])

    def test_heatmap_puxa_o_trecho_mais_repetido(self):
        duracao = 1400
        heat = [{"start_time": s, "end_time": s + 70, "value": 1.0 if s == 700 else 0.05} for s in range(0, 1400, 70)]
        notas = cortes.pontuar(duracao, [-30.0] * duracao, heat, [])
        cands = cortes.candidatos(notas, duracao, 1)
        self.assertTrue(700 <= cands[0]["pico"] < 770)

    def test_candidatos_longe_uns_dos_outros(self):
        notas = [0.0] * 3000
        for s in (500, 520, 900, 1600):
            notas[s] = 5.0
        cands = cortes.candidatos(notas, 3000, 5)
        picos = [c["pico"] for c in cands]
        self.assertNotIn(520, picos)  # perto demais do 500
        self.assertTrue({500, 900, 1600} <= set(picos))

    def test_palavras_json3(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "fala.json3"
            arquivo.write_text(json.dumps({"events": [
                {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "olha"}, {"utf8": " isso", "tOffsetMs": 500}]},
                {"tStartMs": 3000, "dDurationMs": 1000, "segs": [{"utf8": "\n"}]},
                {"tStartMs": 3200, "dDurationMs": 800, "segs": [{"utf8": "caramba"}]}]}), encoding="utf-8")
            palavras = cortes.palavras_json3(arquivo)
        self.assertEqual([p["texto"] for p in palavras], ["olha", "isso", "caramba"])
        self.assertEqual(palavras[0]["inicio"], 1.0)
        self.assertLessEqual(palavras[0]["fim"], palavras[1]["inicio"])


class TestEscolha(unittest.TestCase):
    def setUp(self):
        palavras = [{"texto": f"p{i}", "inicio": 100 + i * 0.5, "fim": 100 + i * 0.5 + 0.4} for i in range(150)]
        self.cands = [{"id": 1, "pico": 150, "inicio": 100, "fim": 175, "nota": 3.0, "palavras": palavras}]

    def test_validar_corte_bom(self):
        c = cortes.validar({"candidato": 1, "inicio": 110, "fim": 150, "titulo": "Fuga absurda",
                            "gancho": "olha o que o Fulano fez", "texto_tela": "FUGA", "hashtags": ["gta6"],
                            "nota": 8}, self.cands)
        self.assertIsNotNone(c)
        self.assertGreaterEqual(c["fim"] - c["inicio"], cortes.DURACAO_MIN - 2)
        self.assertEqual(c["hashtags"], ["#gta6"])
        self.assertTrue(c["palavras"])

    def test_validar_recusa_curto_ou_candidato_errado(self):
        self.assertIsNone(cortes.validar({"candidato": 1, "inicio": 110, "fim": 118, "titulo": "x"}, self.cands))
        self.assertIsNone(cortes.validar({"candidato": 9, "inicio": 110, "fim": 150, "titulo": "x"}, self.cands))
        self.assertIsNone(cortes.validar({"candidato": 1, "inicio": "a", "fim": 150, "titulo": "x"}, self.cands))

    def test_validar_corta_o_que_passa_do_shorts(self):
        c = cortes.validar({"candidato": 1, "inicio": 100, "fim": 175, "titulo": "Longo"}, self.cands)
        self.assertLessEqual(c["fim"] - c["inicio"], cortes.DURACAO_MAX)

    def test_reserva_sem_ia(self):
        r = cortes.reserva({"canal": "Fulano"}, self.cands, 2)
        self.assertEqual(len(r), 1)
        self.assertIn("Fulano", r[0]["titulo"])


class TestLayout(unittest.TestCase):
    def test_caixa_da_camera(self):
        self.assertEqual(cortes.caixa_valida([0.7, 0.05, 0.28, 0.3]), [0.7, 0.05, 0.28, 0.3])
        self.assertIsNone(cortes.caixa_valida([0, 0, 1, 1]))       # tela toda: não é câmera sobreposta
        self.assertIsNone(cortes.caixa_valida([0.9, 0.9, 0.02, 0.02]))
        self.assertIsNone(cortes.caixa_valida(None))

    def test_filtros(self):
        com = cortes.filtro_video(1920, 1080, [0.72, 0.05, 0.26, 0.3])
        self.assertIn("vstack", com)
        self.assertIn(f"scale={cortes.LARGURA}:{cortes.TOPO_CAMERA}", com)
        sem = cortes.filtro_video(1920, 1080, None)
        self.assertIn("boxblur", sem)
        self.assertTrue(com.endswith("[v]") and sem.endswith("[v]"))

    def test_suavizar(self):
        self.assertEqual(cortes.suavizar("Plano concluído, caralho!"), "Plano concluído, c******!")
        self.assertEqual(cortes.suavizar("disputa no computador"), "disputa no computador")

    def test_legenda_ass(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "c.ass"
            palavras = [{"texto": "olha", "inicio": 0.2, "fim": 0.5}, {"texto": "isso", "inicio": 0.6, "fim": 0.9}]
            cortes.legenda(palavras, "fuga absurda", "LIVE DE @FULANO", 2.0, 30.0, True, destino)
            texto = destino.read_text(encoding="utf-8")
        self.assertIn("FUGA ABSURDA", texto)
        self.assertIn("LIVE DE @FULANO", texto)
        self.assertIn("\\kf", texto)


class TestCanalDeCortes(unittest.TestCase):
    def test_canal(self):
        self.assertTrue(cortes.canal_de_cortes({"nicho": "cortes-de-lives"}))
        self.assertTrue(cortes.canal_de_cortes({"tipo_canal": "cortes"}))
        self.assertFalse(cortes.canal_de_cortes({"nicho": "curiosidades"}))
        padrao = cortes.padrao_canal()
        self.assertEqual(padrao["corte_gancho"], "texto")  # sem narração: a voz é a da live
        self.assertTrue(padrao["corte_realce"] and padrao["cortes_vigiar"])

    def test_reacoes(self):
        volume = [-30.0] * 300
        volume[120], volume[121], volume[140] = -8.0, -9.0, -10.0
        self.assertEqual(cortes.reacoes(volume, 100, 150), [20, 40])
        self.assertEqual(cortes.reacoes([-30.0] * 300, 100, 150), [])  # sem estouro, sem zoom

    def test_filtro_realce(self):
        sem = cortes.filtro_realce(40, [], True)
        self.assertIn("cas=", sem)
        self.assertNotIn("concat", sem)
        com = cortes.filtro_realce(40, [10.0, 25.0], True)
        self.assertIn("concat=n=5", com)
        self.assertEqual(com.count("setsar=1"), 5)
        self.assertTrue(com.endswith("[vr]"))


class TestLinkDeLive(unittest.TestCase):
    def test_link(self):
        from darkops.estudio import link_de_live
        self.assertEqual(link_de_live("https://www.youtube.com/watch?v=_W-ujkRXa_Q&t=30s&list=x"),
                         "https://www.youtube.com/watch?v=_W-ujkRXa_Q")
        self.assertEqual(link_de_live("https://www.twitch.tv/videos/2345678?filter=archives"),
                         "https://www.twitch.tv/videos/2345678")
        self.assertEqual(link_de_live("https://evil.com/twitch.tv/x"), "")
        self.assertEqual(link_de_live("javascript:alert(1)"), "")
        self.assertNotIn(";", link_de_live("https://www.twitch.tv/x;rm -rf"))  # o resto do link é descartado
        self.assertEqual(link_de_live("https://www.twitch.tv/x y"), "")


if __name__ == "__main__":
    unittest.main()
