# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Partes críticas da postagem: fila (ordem, aprovação, série), horários do PC e da nuvem e o cofre dos segredos.
Tudo numa pasta temporária: nenhum canal, token ou .env de verdade é tocado."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from darkops import cofre, fila, nuvem, perfis  # noqa: E402
from darkops.mercados import fuso  # noqa: E402


class ComPerfilTemporario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(perfis, "PERFIS", Path(self.tmp.name) / "perfis")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.p = perfis.Perfil("teste")
        self.p.salvar({"ativo": True, "horarios": ["12:00", "19:00"]})

    def roteiro(self, nome: str, **dados) -> Path:
        self.p.fila.mkdir(parents=True, exist_ok=True)
        caminho = self.p.fila / nome
        caminho.write_text(json.dumps({"slug": caminho.stem, **dados}), encoding="utf-8")
        return caminho


class Fila(ComPerfilTemporario):
    def test_so_sai_aprovado_e_na_ordem(self):
        self.roteiro("001-a.json")
        b = self.roteiro("002-b.json", aprovado=True)
        self.roteiro("003-c.json", aprovado=True)
        self.assertEqual(fila.proximo(self.p), b)
        self.assertEqual(fila.restantes(self.p), 2)

    def test_canal_pausado_nao_posta(self):
        self.roteiro("001-a.json", aprovado=True)
        self.p.salvar({"ativo": False})
        self.assertIsNone(fila.proximo(self.p))

    def test_parte_2_espera_a_parte_1(self):
        self.roteiro("001-parte2.json", aprovado=True, serie={"id": "s1", "parte": 2, "total": 2})
        parte1 = self.roteiro("002-parte1.json", serie={"id": "s1", "parte": 1, "total": 2})
        outro = self.roteiro("003-outro.json", aprovado=True)
        self.assertEqual(fila.proximo(self.p), outro)  # a parte 2 não passa na frente da 1 ainda não aprovada
        parte1.write_text(json.dumps({"slug": "parte1", "aprovado": True, "serie": {"id": "s1", "parte": 1}}),
                          encoding="utf-8")
        self.assertEqual(fila.proximo(self.p), parte1)

    def test_roteiro_quebrado_nao_trava(self):
        (self.p.fila).mkdir(parents=True, exist_ok=True)
        (self.p.fila / "001-quebrado.json").write_text("{ isto não é json", encoding="utf-8")
        bom = self.roteiro("002-bom.json", aprovado=True)
        self.assertEqual(fila.proximo(self.p), bom)

    def test_nome_seguro_para_o_comando(self):
        base = Path("C:/Área de Trabalho/canais/perfis/x/fila")
        self.assertTrue(fila.seguro_para_comando(base / "001-ok.json"))  # espaço e acento podem
        for ruim in ('001-a"&calc.json', "001-$(x).json", "001-a;b.json", "001-a%PATH%.json", "001-a!b.json",
                     "001-a|b.json", "001-ok.txt"):
            self.assertFalse(fila.seguro_para_comando(base / ruim), ruim)

    def test_registrar_falha_esconde_token(self):
        fila.registrar_falha("Publicar", "erro em https://x/?access_" + "token=SEGREDO123&a=1", self.p)
        texto = (self.p.controle / "falhas.log").read_text(encoding="utf-8")
        self.assertIn("[Publicar]", texto)
        self.assertNotIn("SEGREDO123", texto)

    def test_marcar_evita_post_duplicado(self):
        fila.marcar("video-a", "youtube", "abc123", self.p)
        self.assertEqual(fila.ja_publicado("video-a", "youtube", self.p), "abc123")
        self.assertIsNone(fila.ja_publicado("video-a", "instagram", self.p))


class Horarios(ComPerfilTemporario):
    def test_slot_dentro_e_fora_da_janela(self):
        br = fuso({"mercado": "pt-BR"})
        self.assertEqual(nuvem.slot_atual(["12:00", "19:00"], datetime(2026, 11, 15, 13, 0, tzinfo=br), br),
                         "2026-11-15 12:00")
        # a nuvem atrasou até 6,7 h em 2026-11: 6 h depois ainda vale, mais que isso não
        self.assertEqual(nuvem.slot_atual(["12:00"], datetime(2026, 11, 15, 18, 0, tzinfo=br), br), "2026-11-15 12:00")
        self.assertIsNone(nuvem.slot_atual(["12:00"], datetime(2026, 11, 15, 18, 1, tzinfo=br), br))
        # 1h da manhã: o horário da vez é o das 19h de ontem
        self.assertEqual(nuvem.slot_atual(["12:00", "19:00"], datetime(2026, 11, 16, 1, 0, tzinfo=br), br),
                         "2026-11-15 19:00")

    def _na_hora(self):
        agora = datetime.now(fuso(self.p.dados)) - timedelta(minutes=5)
        self.p.salvar({"horarios": [agora.strftime("%H:%M")]})

    def test_reserva_impede_duas_rodadas(self):
        self._na_hora()
        self.assertTrue(nuvem.reservar_slot(self.p))
        self.assertFalse(nuvem.reservar_slot(self.p))  # a rodada seguinte do n8n não posta de novo no mesmo horário

    def _publicado(self, nome="001-video-a.json"):
        """Roteiro na fila já publicado nas duas plataformas (IDs no estado), como no meio de uma rodada."""
        caminho = self.roteiro(nome, aprovado=True, formato="vertical")
        fila.marcar(caminho.stem, "youtube", "abc", self.p)
        fila.marcar(caminho.stem, "instagram", "123", self.p)
        return caminho

    def test_reserva_guarda_o_video(self):
        self._na_hora()
        self.assertEqual(nuvem.postando_agora(self.p), "")
        self.assertTrue(nuvem.reservar_slot(self.p, "video-a"))
        self.assertEqual(nuvem.postando_agora(self.p), "video-a")
        self.assertFalse(nuvem.reservar_slot(self.p, "video-b"))

    def test_sincronizar_nao_conclui_o_video_da_rodada_em_andamento(self):
        """Enigma, 2026-11-15: a rodada das 19h30 concluiu o vídeo que a das 19h ainda publicava, e o horário das
        19h ficou sem anotação. A sincronização deixa esse vídeo para o "Registrar publicação" da rodada dele."""
        self._na_hora()
        caminho = self._publicado()
        nuvem.reservar_slot(self.p, caminho.stem)
        with mock.patch.object(nuvem, "_ler", return_value=(None, None)), \
                mock.patch.object(nuvem, "_gravar", return_value=True), \
                mock.patch.object(nuvem, "na_nuvem", return_value=False):
            nuvem._sincronizar(self.p, enviar_videos=False)
            self.assertTrue(caminho.exists())
            # a rodada caiu antes de concluir: com a reserva vencida, a sincronização conclui e anota o horário
            reserva = self.p.controle / "slot-reservado.json"
            dados = json.loads(reserva.read_text(encoding="utf-8"))
            dados["em"] = (datetime.fromisoformat(dados["em"]) - timedelta(minutes=nuvem.RESERVA_MIN + 1)).isoformat()
            reserva.write_text(json.dumps(dados), encoding="utf-8")
            nuvem._sincronizar(self.p, enviar_videos=False)
        self.assertFalse(caminho.exists())
        self.assertTrue((self.p.publicados / caminho.name).exists())
        self.assertEqual(nuvem.slot_atendido(self.p), "pc")

    def test_fila_concluir_de_roteiro_ja_concluido_anota_o_horario(self):
        import argparse
        import contextlib
        import io
        import os
        from darkops import __main__ as cli
        self._na_hora()
        self.p.publicados.mkdir(parents=True, exist_ok=True)
        (self.p.publicados / "001-video-a.json").write_text(json.dumps({"slug": "video-a"}), encoding="utf-8")
        ambiente = {k: v for k, v in os.environ.items() if k != "DARKOPS_SIMULAR"}
        with mock.patch.dict(os.environ, {**ambiente, "DARKOPS_PERFIL": "teste"}, clear=True), \
                mock.patch.object(nuvem, "na_nuvem", return_value=False), \
                contextlib.redirect_stdout(io.StringIO()) as saida:
            cli.cmd_fila_concluir(argparse.Namespace(roteiro=str(self.p.fila / "001-video-a.json")))
        self.assertIn('"ja_concluido": true', saida.getvalue())
        self.assertEqual(nuvem.slot_atendido(self.p), "pc")

    def test_slot_atendido_pelo_pc(self):
        self._na_hora()
        self.assertIsNone(nuvem.slot_atendido(self.p))
        with mock.patch.object(nuvem, "na_nuvem", return_value=False):
            nuvem.registrar_slot(self.p, "video-a")
        self.assertEqual(nuvem.slot_atendido(self.p), "pc")
        self.assertIsNone(nuvem.slot_pendente(self.p))


class Cofre(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_env_cifra_so_os_segredos(self):
        with mock.patch.object(cofre, "_raiz", return_value=self.tmp), \
                mock.patch.object(cofre, "ligado", return_value=True):
            (self.tmp / ".env").write_text("# comentário\nDARKOPS_AVANCADO=0\n", encoding="utf-8")
            cofre.reescrever_env({"PEXELS_API_KEY": "valor-secreto", "DARKOPS_AVANCADO": "1"})
            texto = (self.tmp / ".env").read_text(encoding="utf-8")
            self.assertNotIn("valor-secreto", texto)
            self.assertIn("PEXELS_API_KEY=cofre:", texto)
            self.assertIn("DARKOPS_AVANCADO=1", texto)
            self.assertIn("# comentário", texto)
            lido = cofre.ler_env(self.tmp / ".env")
            self.assertEqual(lido["PEXELS_API_KEY"], "valor-secreto")
            with self.assertRaises(ValueError):
                cofre.reescrever_env({"X_TOKEN": "a\nOUTRA=1"})  # quebra de linha criaria outra variável

    def test_arquivo_de_segredo(self):
        arquivo = self.tmp / "credenciais" / "token.txt"
        with mock.patch.object(cofre, "ligado", return_value=True):
            cofre.gravar(arquivo, "token-de-teste")
        self.assertTrue(cofre.cifrado(arquivo.read_bytes()))
        self.assertEqual(cofre.ler(arquivo), "token-de-teste")

    def test_chave_nao_e_trocada_por_outra_partida(self):
        arquivo = self.tmp / "cofre.chave"
        self.assertTrue(cofre._gravar_privado(arquivo, b"primeira", so_se_novo=True))
        self.assertFalse(cofre._gravar_privado(arquivo, b"segunda", so_se_novo=True))
        self.assertEqual(arquivo.read_bytes(), b"primeira")
        self.assertEqual(list(self.tmp.glob("*.novo")), [])  # não sobra arquivo temporário
        cofre._gravar_privado(arquivo, b"troca normal")
        self.assertEqual(arquivo.read_bytes(), b"troca normal")


if __name__ == "__main__":
    unittest.main()
