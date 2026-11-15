# SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
# Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
"""Travas de segurança do Estúdio e do código (revisão de 2026-11-15): volta e links só seguros, cabeçalhos,
segredos escondidos, links colados só da internet e o Claude Code sem acesso aos segredos."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

LOCAL = {"Host": "127.0.0.1:8765"}


class Estudio(unittest.TestCase):
    def setUp(self):
        from darkops.estudio import app
        self.app = app
        self.c = app.test_client()

    def test_cabecalhos(self):
        r = self.c.get("/sobre", headers=LOCAL)
        h = r.headers
        self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(h["Cross-Origin-Opener-Policy"], "same-origin")
        self.assertIn("microphone=(self)", h["Permissions-Policy"])
        csp = h["Content-Security-Policy"]
        for trecho in ("default-src 'self'", "frame-ancestors 'none'", "base-uri 'none'", "script-src-attr 'none'",
                       "object-src 'none'"):
            self.assertIn(trecho, csp)

    def test_csp_sem_script_dentro_do_html(self):
        """Script só com o nonce da página: nada de 'unsafe-inline', e todo <script> da tela leva o nonce certo."""
        import re
        paginas = ["/sobre", "/saude", "/configuracoes", "/progresso", "/perfis", "/abertura"]
        from darkops.perfis import listar
        perfis = listar()
        if perfis:
            pid = perfis[0].id
            paginas += [f"/p/{pid}/configurar", f"/p/{pid}/conexoes", f"/p/{pid}/novo", f"/p/{pid}/estatisticas"]
        nonces = set()
        for url in paginas:
            r = self.c.get(url, headers=LOCAL)
            if r.status_code != 200:
                continue
            script_src = next(p for p in r.headers["Content-Security-Policy"].split(";") if "script-src " in p)
            self.assertNotIn("unsafe-inline", script_src, url)
            nonce = re.search(r"'nonce-([\w-]+)'", script_src).group(1)
            nonces.add(nonce)
            html = r.get_data(as_text=True)
            for etiqueta in re.findall(r"<script\b[^>]*>", html):
                self.assertIn(f'nonce="{nonce}"', etiqueta, f"{url}: {etiqueta}")
        self.assertGreater(len(nonces), 1)  # um nonce novo por página

    def test_templates_sem_javascript_no_html(self):
        """onclick=, onchange=... e javascript: não rodam com a CSP: o comportamento vai por data-* (static/estudio.js),
        e toda função chamada por data-ao-* existe num <script> das telas."""
        import re
        pasta = RAIZ / "darkops" / "estudio" / "templates"
        todos = "\n".join(a.read_text(encoding="utf-8") for a in pasta.glob("*.html"))
        for arquivo in pasta.glob("*.html"):
            texto = arquivo.read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"\son[a-z]+\s*=", texto), [], arquivo.name)
            self.assertNotIn("javascript:", texto.lower(), arquivo.name)
        for nome in set(re.findall(r'data-ao-(?:clicar|mudar|mudar-form|digitar-form)="(\w+)"', todos)):
            self.assertRegex(todos, rf"function {nome}\(", f"função {nome} não existe nas telas")

    def test_so_local(self):
        self.assertEqual(self.c.get("/sobre", headers={"Host": "127.0.0.1.exemplo.invalid"}).status_code, 403)
        self.assertEqual(self.c.get("/sobre", headers={"Host": "localhost.exemplo.invalid:8765"}).status_code, 403)
        self.assertEqual(self.c.get("/sobre", headers=LOCAL, environ_base={"REMOTE_ADDR": "192.168.0.10"}).status_code,
                         403)
        for origem in ("https://exemplo.invalid", "null", "http://127.0.0.1.exemplo.invalid", "http://localhost@x.invalid"):
            r = self.c.post("/novidade/vista", headers={**LOCAL, "Origin": origem})
            self.assertEqual(r.status_code, 403, origem)

    def test_volta_segura(self):
        from darkops.estudio import volta_segura
        for ruim in ("javascript:alert(1)", "https://exemplo.invalid/x", "//exemplo.invalid", "/\\exemplo.invalid",
                     " /\texemplo", "data:text/html,oi", "http://127.0.0.1.exemplo.invalid/", ""):
            self.assertEqual(volta_segura(ruim, "/padrao"), "/padrao", repr(ruim))
        self.assertEqual(volta_segura("/p/x/fila#a", "/padrao"), "/p/x/fila#a")
        with mock.patch.dict(os.environ, {"PORT": "8765"}):
            self.assertEqual(volta_segura("http://127.0.0.1:8765/p/x?y=1", "/padrao"), "/p/x?y=1")
            self.assertEqual(volta_segura("http://127.0.0.1:5678/", "/padrao"), "/padrao")  # o n8n não é o Estúdio

    def test_link_seguro(self):
        modelo = self.app.jinja_env.from_string('<a href="{{ u|link }}">')
        for ruim in ("javascript:alert(1)", " JavaScript:alert(1)", "java\tscript:x", "vbscript:x", "data:text/html,x",
                     "//exemplo.invalid", "\x01javascript:x"):
            self.assertEqual(modelo.render(u=ruim), '<a href="#">', repr(ruim))
        self.assertEqual(modelo.render(u="https://pt.wikipedia.org/wiki/A?b=1&c=2"),
                         '<a href="https://pt.wikipedia.org/wiki/A?b=1&amp;c=2">')
        self.assertEqual(modelo.render(u="/p/x/conexoes"), '<a href="/p/x/conexoes">')

    def test_tarefa_nao_volta_para_fora(self):
        from darkops.perfis import listar
        perfis = listar()
        if not perfis:
            self.skipTest("sem canal neste PC")
        r = self.c.get(f"/p/{perfis[0].id}/tarefa/naoexiste", query_string={"voltar": "javascript:alert(1)"},
                       headers=LOCAL)
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertNotIn("javascript:alert", html)
        self.assertIn(f'href="/p/{perfis[0].id}"', html)

    def test_todo_href_de_dado_passa_pelo_filtro(self):
        """Um href com valor que não sai de url_for precisa do |link (ou ser constante do app)."""
        import re
        constantes = ("autoria.", "e.links.")
        for arquivo in (RAIZ / "darkops" / "estudio" / "templates").glob("*.html"):
            for achado in re.finditer(r'href="\{\{([^}]*)\}\}', arquivo.read_text(encoding="utf-8")):
                expr = achado.group(1).strip()
                if "url_for" in expr or expr.startswith(constantes):
                    continue
                self.assertTrue(expr.endswith("|link"), f"{arquivo.name}: href sem |link: {expr}")


class Segredos(unittest.TestCase):
    def test_ocultar_mais_formatos(self):
        from darkops.seguranca import ocultar
        # montados em pedaços: um segredo de mentira inteiro no código faria a integridade acusar chave vazada
        casos = {
            "https://graph.facebook.com/x?fb_exchange_" + "token=AB12cd&client_id=1": "AB12cd",
            "erro: {'access_" + "token': 'segredo123'}": "segredo123",
            '{"pass' + 'word": "minha-senha"}': "minha-senha",
            "xi-api-" + "key: abcdef123456": "abcdef123456",
            "chave sk_" + "a1b2c3d4e5f6a7b8c9d0e1f2": "a1b2c3d4e5f6",
            "?senha=batata&x=1": "batata",
        }
        for texto, segredo in casos.items():
            self.assertNotIn(segredo, ocultar(texto), texto)
        self.assertIn("tokens=12", ocultar("tokens=12 custo=0.1"))  # contagem de tokens não é segredo

    def test_link_publico(self):
        from darkops.seguranca import link_publico
        for ruim in ("http://127.0.0.1:5678/webhook", "http://localhost:8765", "http://[::1]/", "http://192.168.0.1/",
                     "http://10.0.0.5/x", "http://169.254.169.254/latest", "http://roteador/", "file:///C:/x",
                     "--exec=calc", "ftp://exemplo.com/x", "http://0.0.0.0/", "https://nas.local/x", ""):
            self.assertFalse(link_publico(ruim), ruim)
        for bom in ("https://www.youtube.com/watch?v=abc123", "https://youtu.be/abc", "https://www.instagram.com/reel/x/",
                    "http://8.8.8.8/"):
            self.assertTrue(link_publico(bom), bom)

    def test_cortes_recusa_link_que_vira_opcao(self):
        from darkops import cortes
        with mock.patch.object(cortes, "_ytdlp", side_effect=AssertionError("não devia chamar o yt-dlp")):
            for ruim in ("--exec=calc", "-o C:/x", "http://127.0.0.1:8765/"):
                with self.assertRaises(SystemExit):
                    cortes.informacoes(ruim)

    def test_rodar_claude_sem_segredos(self):
        from darkops import leva
        capturado = {}

        def falso(args, **kw):
            capturado.update(args=args, env=kw["env"], entrada=kw["input"])
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps({"result": "ok"}), stderr="")

        with mock.patch.object(leva, "_claude", return_value="claude"), \
                mock.patch("subprocess.run", side_effect=falso), \
                mock.patch("darkops.custos.registrar", side_effect=lambda proc, tarefa: proc), \
                mock.patch.dict(os.environ, {"EXEMPLO_API_KEY": "nao-pode", "NUVEM_TOKEN": "nao-pode"}):
            leva.rodar_claude("pedido com & e | dentro", tarefa="descricao")
        args = capturado["args"]
        self.assertEqual(args[args.index("--tools") + 1], "")  # sem ferramenta nenhuma
        self.assertNotIn("--permission-mode", args)
        self.assertNotIn("pedido com", " ".join(args))  # o pedido vai pela entrada padrão, nunca como argumento
        self.assertEqual(capturado["entrada"], "pedido com & e | dentro")
        for negado in ("Read(./.env)", "Read(./dados/**)", "Read(~/.claude/**)", "Read(~/.n8n/**)"):
            self.assertIn(negado, args)
        self.assertNotIn("EXEMPLO_API_KEY", capturado["env"])
        self.assertNotIn("NUVEM_TOKEN", capturado["env"])

    def test_registrar_falha_do_n8n_limpa_o_shell(self):
        modelo = json.loads((RAIZ / "n8n" / "workflow.modelo.json").read_text(encoding="utf-8"))
        comando = next(n["parameters"]["command"] for n in modelo["nodes"] if n["name"] == "Registrar falha")
        classe = comando.split(".replace(/[", 1)[1].split("]/g", 1)[0]
        for c in "\"%&|<>^$`'!":
            self.assertIn(c, classe)
        self.assertIn(".replace(/\\\\/g, '/')", comando)  # barra invertida no fim não escapa a aspa no sh


if __name__ == "__main__":
    unittest.main()
