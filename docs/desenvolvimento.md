# Guia de desenvolvimento

Para quem vai mexer no código do Projeto Canais. A visão das peças está em [arquitetura.md](arquitetura.md), os comandos em [cli.md](cli.md) e as regras que valem para todo agente de IA no [AGENTS.md](../AGENTS.md) (este guia não repete as decisões do dono: confira lá antes de mudar comportamento).

## Preparar o ambiente

1. Instale do zero seguindo [instalacao.md](instalacao.md) (no Claude Code, skill `/configurar`). O `instalar.ps1` (Windows) ou `instalar.sh` (macOS e Linux) cria o `.venv` e põe os programas em `dados/apps/`.
2. Use sempre o Python do projeto: `.venv\Scripts\python.exe` no Windows, `.venv/bin/python` no resto (ou `.\dark.ps1` e `./dark.sh`, que já fazem isso).
3. Confira o estado:
   ```bash
   python -m darkops diagnostico
   ```
   ```bash
   python -m darkops progresso
   ```
4. Abra o Estúdio em `http://127.0.0.1:8765`:
   ```bash
   python -m darkops estudio
   ```
   No preview do Claude Code, a configuração está em `.claude/launch.json` (a porta vem de `PORT`). Nunca rode o Estúdio fora de `127.0.0.1`.

O n8n nunca é ligado pelo terminal de um agente: use `app.ligar_n8n()` (o Estúdio faz isso ao abrir). Não reinicie o n8n nem o Estúdio perto das 12h e das 19h do fuso do canal.

## Testes

| O quê | Comando | Onde roda |
|---|---|---|
| Testes unitários (rápidos, sem rede, sem tocar canal real) | `python -m unittest discover -s tests` | PC e CI |
| Telas do Estúdio no Chromium, Firefox e WebKit, temas claro e escuro, sem script bloqueado pela CSP | `python tests/navegadores.py` | PC (com Playwright) e CI |
| Integridade e segurança do app instalado | `python -m darkops integridade` | PC |
| Falhas conhecidas nas dependências Python | `pip-audit -r requirements.txt` | CI (e à mão num ambiente separado) |

- Arquivos: `test_basico.py` (CLI, cofre, Estúdio protegido, modo escuro, skills), `test_seguranca.py` (cabeçalhos, volta e links seguros, `ocultar`, links colados, Claude sem segredos), `test_postagem.py` (fila, série, horários do PC e da nuvem, cofre do `.env`), `test_alcance.py` (workflow do n8n e regras de alcance), `test_aprovacao.py`, `test_cortes.py`, `test_rotinas.py` e `test_docs.py` (todo comando da CLI documentado em [cli.md](cli.md)).
- Teste que precisa de canal usa uma pasta temporária: `mock.patch.object(perfis, "PERFIS", tmp)` e `perfis.Perfil("teste")` (veja `test_postagem.py`). Nunca escreva em `perfis/` de verdade nem no `.env`.
- Segredo de mentira no teste vai montado em pedaços (`"ghp_" + "ABC..."`): inteiro, a rotina de integridade acusa chave vazada no código.
- Teste da nuvem sempre em simulação (`DARKOPS_SIMULAR=1`); nada de publicar de verdade num teste.
- O GitHub Actions (`.github/workflows/testes.yml`) roda tudo em Windows, macOS e Linux, Python 3.12 e 3.13, as telas nos três navegadores e o `pip-audit`.

## Onde mexer

| Quero mudar... | Arquivo |
|---|---|
| Um comando da CLI ou criar outro | `darkops/__main__.py` (`cmd_<nome>` e o `add_parser` em `main()`); documente em [cli.md](cli.md) |
| Uma tela do Estúdio | rota em `darkops/estudio/__init__.py`, template em `darkops/estudio/templates/`, estilo em `static/estudio.css` (cores só por variável), comportamento comum em `static/estudio.js` |
| Uma tarefa longa do Estúdio | `_iniciar_job(perfil, título, [[args da CLI]])` e a estimativa e a frase de pronto em `estudio/tarefas.py` (`_TIPOS`) |
| O pedido do roteiro | `darkops/leva.py` (`_escrever_roteiro`, `_formato_e_tamanho`) e a skill `.claude/skills/escrever-roteiro/SKILL.md` |
| Esforço ou modelo de uma tarefa da IA | `leva.ESFORCO` e `leva.MODELO` |
| As checagens do texto | `darkops/auditoria.py` |
| A montagem do vídeo | `darkops/producao.py` (fluxo), `render.py` (ffmpeg), `hyperframes.py` (camada animada), `prancha.py` (Prancha de Campo) |
| As regras de movimento | [movimento.md](movimento.md), `TEMPO` e `CURVA` em `hyperframes.py`; rode `hyperframes lint` |
| A voz | `darkops/narracao.py` (motores), `vozes.py` (catálogo; rode `vozes-amostras` ao mudar) |
| A postagem automática | `n8n/workflow.modelo.json` (todo nó por canal com `"executeOnce": false`), `fila.py`, `publicar.py`, `instagram.py` |
| A nuvem | `darkops/nuvem.py` e `n8n/nuvem.actions.yml` |
| Algo que muda entre sistemas | `darkops/sistema.py` (nunca `.exe`, `Scripts\python.exe`, `;` no PATH ou `CREATE_NO_WINDOW` direto) |
| Um segredo novo | nome com KEY, TOKEN, SECRET, SENHA, PASSWORD ou VERIFICAR no `.env` (o cofre cifra sozinho); leia com `cofre.ler` |
| A integridade ou as atualizações | `darkops/integridade.py`, `terceiros.py`, `rotinas.py` |
| A logo | `app.LOGO_ESTRELA` e `LOGO_AMARELO`; `app.desenhar_logos()` regrava os arquivos |

## Convenções

- **Português do Brasil** em código (nomes), mensagens, docs, commits e telas.
- **Subprocessos**: sempre lista de argumentos, nunca `shell=True`; no Windows, `**sistema.sem_janela()`. Texto que veio de fora (roteiro, página, comentário, link) nunca vira argumento de cmd.exe: vai pela entrada padrão ou por arquivo.
- **Claude Code** só por `leva.rodar_claude(pedido, ferramentas, tarefa=...)`, com o mínimo de ferramentas. Nunca `--permission-mode acceptEdits`, nunca Bash genérico num pedido que lê a internet (use `comando_permitido("<comando da CLI>")`).
- **Mensagens**: toda mensagem que pode conter URL ou erro de API passa por `seguranca.ocultar()` antes de ir para log, tela ou arquivo.
- **Links**: link colado pelo usuário que o app vai abrir sozinho passa por `seguranca.link_publico()`; link que vem de dado e vai para um template usa o filtro `|link`; endereço de volta usa `volta_segura`.
- **Estúdio**: não afrouxe as travas de `_so_local` nem os cabeçalhos de `_cabecalhos`. Script em template só com `<script nonce="{{ csp_nonce() }}">`; nunca `onclick=`, `onchange=`... nem `javascript:` (a CSP bloqueia e `test_templates_sem_javascript_no_html` falha): use os `data-*` descritos no topo de `static/estudio.js` (`data-pergunta` para confirmar, `data-ao-clicar="funcao"` para chamar uma função da tela, `data-mostra`, `data-copiar-de`...). Toda tela cabe de 320 px a monitor grande, sem rolagem lateral, nos temas claro e escuro. Opção nova fica escondida em "Mostrar mais opções" ou no modo avançado; não apague opções.
- **Erros**: `SystemExit("frase para a pessoa")` para erro esperado da CLI; `except Exception` só com comentário dizendo por que é seguro seguir, e nunca engolindo falha de postagem.
- **Animação** determinística: GSAP em timeline pausada, nada de `Math.random` sem semente.
- **Autoria**: código novo começa com o cabeçalho SPDX; Markdown e HTML terminam com ele. `python -m darkops marcar-arquivos` põe o que faltar.
- **Versão**: suba `darkops/__init__.py` (`__version__`) e `.claude-plugin/plugin.json` a cada entrega que muda o comportamento (correção 0.x.y+1, recurso 0.x+1.0).
- **Docs**: regra e decisão do dono vão no `AGENTS.md`; o funcionamento vai em `docs/`. Não duplique.

## Antes de entregar

1. `python -m unittest discover -s tests` sem falha.
2. Mexeu em tela: `python tests/navegadores.py` e a conferência em 320, 375, 768 e 1920 px.
3. Mexeu em animação: `hyperframes lint` sem erro nem aviso.
4. `python -m darkops integridade` sem problema novo.
5. Versão, `AGENTS.md` (se mudou uma regra) e docs atualizados.

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
