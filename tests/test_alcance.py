# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""O que derrubou o alcance do Enigma em 2026-11-15:
- a capa preta (o primeiro quadro vazio);
- o roteiro longo demais para a duração do canal;
- o horário perdido com o PC desligado."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from darkops import auditoria, conferir, leva, nuvem, prancha  # noqa: E402

ENIGMA = {"nicho": "misterios", "formato": "vertical", "duracao_s": 60, "velocidade": "+0%"}
PULGA = {"nicho": "como funciona", "formato": "vertical", "duracao_s": 90, "velocidade": "+0%"}


def _video(destino: Path, com_assunto: bool) -> Path:
    desenho = ",drawbox=x=20:y=60:w=70:h=40:color=white:t=fill" if com_assunto else ""
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=0x0B0F14:s=108x192:d=1:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    "-vf", "format=yuv420p" + desenho, "-shortest", "-c:v", "libx264", "-c:a", "aac", str(destino)],
                   check=True)
    return destino


class TestCapa(unittest.TestCase):
    def test_primeiro_quadro_vazio_e_erro(self):
        with tempfile.TemporaryDirectory() as pasta:
            vazio = conferir.conferir(_video(Path(pasta) / "vazio.mp4", False))
            cheio = conferir.conferir(_video(Path(pasta) / "cheio.mp4", True))
        capa = lambda r: [a for a in r["achados"] if "primeiro quadro" in a["texto"]]  # noqa: E731
        self.assertEqual(capa(vazio)[0]["nivel"], "erro")
        self.assertEqual(capa(cheio), [])

    def test_texto_da_capa(self):
        self.assertEqual(prancha.capa({"titulo": "Moai: como andaram sem roda #shorts"}, {}),
                         "Moai: como andaram sem roda")
        self.assertEqual(prancha.capa({"titulo": "x"}, {"capa": "Outro texto"}), "Outro texto")


class TestTamanho(unittest.TestCase):
    def _roteiro(self, palavras: int, **extra) -> dict:
        fala = " ".join(["palavra"] * (palavras - 1))
        return {"cenas": [{"texto": "Por que ninguém sabe?"}, {"texto": fala}], "fontes": ["x"], **extra}

    def test_fala_longa_para_o_canal_trava(self):
        erros = [p for p in auditoria.auditar(self._roteiro(310), ENIGMA) if p["parte"] == "tamanho"]
        self.assertEqual(erros[0]["nivel"], "erro")
        self.assertEqual([p for p in auditoria.auditar(self._roteiro(170), ENIGMA) if p["parte"] == "tamanho"], [])
        # o roteiro diz a duração pedida no Novo vídeo; corte de live não conta
        self.assertEqual([p for p in auditoria.auditar(self._roteiro(310, duracao_alvo_s=110), ENIGMA)
                          if p["parte"] == "tamanho"], [])
        self.assertEqual([p for p in auditoria.auditar(self._roteiro(310, tipo="corte"), ENIGMA)
                          if p["parte"] == "tamanho"], [])

    def test_explicativo_so_no_como_funciona(self):
        self.assertFalse(leva.explicativo(ENIGMA))
        self.assertTrue(leva.explicativo(PULGA))
        pedido = leva._formato_e_tamanho(ENIGMA)
        minimo, maximo = auditoria.palavras_alvo(60, "+0%")
        self.assertIn("não o explicativo", pedido)
        self.assertIn(f"de {minimo} a {maximo} palavras", pedido)
        self.assertNotIn("não o explicativo", leva._formato_e_tamanho(PULGA))
        self.assertGreater(auditoria.palavras_por_segundo("+15%"), auditoria.palavras_por_segundo("+0%"))


class PerfilFalso:
    def __init__(self, pasta: Path, horarios: list[str]):
        self.dados = {"horarios": horarios, "mercado": "pt-BR"}
        self.controle = pasta


class TestHorarioPerdido(unittest.TestCase):
    def test_pc_ligado_depois_ainda_posta_uma_vez(self):
        brasilia = datetime.now(nuvem.BRASILIA)
        duas_horas_antes = (brasilia - timedelta(hours=2)).strftime("%H:%M")
        with tempfile.TemporaryDirectory() as pasta:
            perfil = PerfilFalso(Path(pasta), [duas_horas_antes])
            slot = nuvem.slot_pendente(perfil)
            self.assertIsNotNone(slot)  # 2 h depois do horário ainda conta
            self.assertTrue(nuvem.reservar_slot(perfil))
            self.assertFalse(nuvem.reservar_slot(perfil))  # a rodada seguinte não posta de novo
            reserva = Path(pasta) / "slot-reservado.json"
            antiga = (datetime.now(timezone.utc) - timedelta(minutes=nuvem.RESERVA_MIN + 1)).isoformat()
            reserva.write_text(json.dumps({"slot": slot, "em": antiga}), encoding="utf-8")
            self.assertTrue(nuvem.reservar_slot(perfil))  # a postagem caiu: tenta de novo
            nuvem.registrar_slot(perfil, "x")
            self.assertIsNone(nuvem.slot_pendente(perfil))  # já postado


if __name__ == "__main__":
    unittest.main()
