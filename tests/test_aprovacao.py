# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Aprovação automática: só entra na postagem o vídeo que passa em todas as conferências."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import imageio_ffmpeg  # noqa: E402

from darkops import aprovacao, config  # noqa: E402


class PerfilFalso:
    def __init__(self, pasta: Path, dados: dict):
        self.id = "teste"
        self.pasta = pasta
        self.dados = dados
        self.controle = pasta / "controle"
        self.fila = pasta / "fila"
        self.fila.mkdir(parents=True, exist_ok=True)

    def salvar(self, novos):
        self.dados.update(novos)


class TestAprovacao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.saida_antiga = config.SAIDA
        config.SAIDA = base / "saida"
        config.SAIDA.mkdir()
        self.nuvem = aprovacao._nuvem
        aprovacao._nuvem = lambda perfil: None  # o teste nunca mexe na nuvem de verdade
        self.perfil = PerfilFalso(base / "perfil", {
            "aprovacao_automatica": True,
            "cortes_fontes": [{"chaves": ["twitch:fulano"], "autorizado_em": "2026-11-13", "como": "teste"}]})
        self.roteiro = self.perfil.fila / "001-corte-x.json"
        self._roteiro(autorizado=True, canal="https://www.twitch.tv/fulano")
        video = config.SAIDA / "corte-x-vertical.mp4"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=s=1080x1920:d=2:r=30", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                        "-shortest", "-pix_fmt", "yuv420p", str(video)], check=True)
        os.utime(video, (time.time() + 5, time.time() + 5))  # prévia mais nova que o roteiro

    def tearDown(self):
        config.SAIDA = self.saida_antiga
        aprovacao._nuvem = self.nuvem
        self.tmp.cleanup()

    def _roteiro(self, autorizado: bool, canal: str):
        self.roteiro.write_text(json.dumps({
            "slug": "corte-x", "tipo": "corte", "formato": "vertical", "aprovado": False, "cenas": [{"texto": "oi"}],
            "corte": {"streamer": "Fulano", "canal_url": canal, "autorizado": autorizado}}), encoding="utf-8")

    def _visual(self, nota: float, erro: bool = False):
        pasta = self.perfil.controle / "conferencias"
        pasta.mkdir(parents=True, exist_ok=True)
        achados = [{"nivel": "erro", "texto": "legenda cortada"}] if erro else []
        arquivo = pasta / "corte-x-vertical.json"
        arquivo.write_text(json.dumps({"video": "corte-x-vertical.mp4", "visual": {"nota": nota, "achados": achados}}),
                           encoding="utf-8")
        os.utime(arquivo, (time.time() + 10, time.time() + 10))

    def _aprovado(self) -> bool:
        return json.loads(self.roteiro.read_text(encoding="utf-8"))["aprovado"]

    def test_passa_em_tudo(self):
        self._visual(8)
        self.assertTrue(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))
        self.assertTrue(self._aprovado())

    def test_nota_baixa_espera_o_dono(self):
        self._visual(5)
        self.assertFalse(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))
        self.assertFalse(self._aprovado())
        motivos = json.loads(self.roteiro.read_text(encoding="utf-8"))["aprovacao_automatica"]["motivos"]
        self.assertTrue(any("nota" in m for m in motivos))

    def test_erro_visual_espera(self):
        self._visual(9, erro=True)
        self.assertFalse(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))

    def test_sem_revisao_visual_espera(self):
        self.assertFalse(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))

    def test_corte_sem_autorizacao_espera(self):
        self._roteiro(autorizado=False, canal="https://www.twitch.tv/outro")
        os.utime(config.SAIDA / "corte-x-vertical.mp4", (time.time() + 20, time.time() + 20))
        self._visual(9)
        self.assertFalse(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))
        self.assertFalse(self._aprovado())

    def test_desligada_nao_faz_nada(self):
        self.perfil.dados["aprovacao_automatica"] = False
        self._visual(9)
        self.assertIsNone(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))
        self.assertFalse(self._aprovado())

    def test_previa_desatualizada_espera(self):
        os.utime(config.SAIDA / "corte-x-vertical.mp4", (time.time() - 100, time.time() - 100))
        self._visual(9)
        self.assertFalse(aprovacao.aprovar_sozinho(self.perfil, self.roteiro, revisar=False))


if __name__ == "__main__":
    unittest.main()
