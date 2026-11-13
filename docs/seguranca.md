# Segurança do Projeto Canais (revisão de 2026-10-24)

O projeto roda no seu PC, guarda tokens das suas contas e dispara comandos (produção, publicação, Claude Code).
Estas são as proteções em vigor e o motivo de cada uma.

## Estúdio (painel em http://127.0.0.1:8765)

| Proteção | Contra o quê | Onde |
|---|---|---|
| Só escuta em 127.0.0.1 e recusa conexões de outros endereços | outra máquina da rede abrir o painel | `estudio/__init__.py` (`rodar`, `_so_local`) |
| Confere o cabeçalho Host (só `127.0.0.1`, `localhost`, `[::1]`) | **DNS rebinding**: um site aponta o próprio domínio para 127.0.0.1 e lê o painel pelo seu navegador ([NCC Group](https://github.com/nccgroup/singularity/wiki/Preventing-DNS-Rebinding-Attacks)) | `_so_local` |
| Toda ação (POST) exige Origin ou Referer do próprio Estúdio | **CSRF**: um site manda seu navegador apertar um botão do painel | `_so_local` |
| `X-Frame-Options: DENY` e CSP `frame-ancestors 'none'` | **clickjacking**: o painel escondido dentro de outro site ([OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)) | `_cabecalhos` |
| CSP `default-src 'self'` (sem scripts de outros sites), `nosniff`, `Referrer-Policy: same-origin` | script de fora, arquivo interpretado com outro tipo, endereço vazando em links ([OWASP](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet)) | `_cabecalhos` |
| Cookie de sessão `SameSite=Strict` e `HttpOnly`; chave de sessão nova a cada início | sessão reaproveitada por outro site ou por script | `app.config` |
| Envio de arquivo limitado a 512 MB, só extensões permitidas, nomes gerados pelo Estúdio | disco cheio e arquivo gravado fora da pasta | `MAX_CONTENT_LENGTH`, rotas de envio |
| Nomes de arquivo conferidos por expressão regular e caminhos presos à pasta do perfil | **path traversal** (`../`) | `_arquivo_fila`, `midia`, `visual_cena` |
| Modo de depuração desligado | página de erro mostrando código e variáveis | `app.run(debug=False)` |

### Cookies, ambiente e aplicativo instalável
- O Estúdio tem um único cookie, o de sessão (avisos entre telas), necessário: `HttpOnly`, `SameSite=Strict` e sem validade; a chave muda a cada abertura. A configuração sai de `darkops/ambiente.py`.
- `DARKOPS_AMBIENTE=servidor` deixa pronta a configuração de um futuro modo hospedado (chave fixa em `DARKOPS_CHAVE_SECRETA`, cookie `__Host-` só por HTTPS, origens em `DARKOPS_ORIGENS`), mas o Estúdio **se recusa a abrir** nesse modo. A lista do que falta antes de liberar está em [app-e-site.md](app-e-site.md).
- O service worker do aplicativo instalável (`/sw.js`) só guarda CSS e ícones; páginas e ações sempre vão ao Estúdio, e nada de POST passa por ele.
- O site (`site/`) não usa cookies opcionais; `site/consentimento.js` só libera um script opcional depois do consentimento.

### Programas baixados pelo instalador (`instalar.ps1`, `darkops/apps.py`)
- Tudo vai para `dados/apps/` (fora do Git), sem administrador e sem mexer no PATH do Windows.
- **Python** (só se faltar): instalador oficial do python.org, aceito só com assinatura digital válida da Python Software Foundation.
- **Node.js**: zip oficial do nodejs.org, conferido pelo SHA-256 do `SHASUMS256.txt` publicado e pela assinatura da OpenJS Foundation no `node.exe`.
- **n8n**: `npm install --prefix dados/apps/n8n` do registro oficial do npm, travado na versão principal 2 (a atualização só sobe dentro dela).
- **Claude Code**: instalador oficial da Anthropic (`claude.ai/install.ps1`); o `claude.exe` só é aceito com a assinatura da Anthropic.
- O n8n é aberto pelo atalho de logon via `explorer.exe`, para não ficar preso à árvore de processos de um agente (no app Claude, morreria junto com o app).

### Contas por login (`darkops/contas.py`)
- **GitHub**: o GitHub CLI portátil (release oficial, conferido pelo SHA-256 da API do GitHub) faz o login por código de dispositivo, com os escopos `repo` e `workflow`. O acesso fica no Gerenciador de Credenciais do Windows e no `.env` (`NUVEM_TOKEN`). Ele vale para todos os seus repositórios, mais do que o token fine-grained manual. Quem quiser o mínimo usa "Ou faça à mão".
- **Azure**: o Azure CLI portátil (zip oficial da Microsoft, conferido pelo Content-MD5 do servidor e pela assinatura da PSF no Python de dentro), com a configuração em `dados/apps/azure-config`. Só cria e só guarda chave de recurso de voz no nível **F0 (grátis)**: há uma trava antes de salvar.
- **Instagram**: OAuth do Instagram Login. A Meta só aceita retorno https, então a página `site/instagram.html` (GitHub Pages) repassa o `code` para `http://127.0.0.1:<porta>/instagram/retorno`, sem guardar nada e sem Referer. O `state` é aleatório, de uso único, vale 15 minutos e fica no servidor do Estúdio (o cookie Strict não volta de outro site). O `code` sozinho não serve: a troca pelo token exige a chave secreta do app, que só existe no `.env` deste PC.

## Tokens e chaves

- `.env` e `credenciais/` ficam fora do Git (`.gitignore`); o histórico foi conferido em 2026-10-24 e não tem chave nem token.
- Mensagens de erro, avisos das estatísticas e `falhas.log` passam por `seguranca.ocultar()`, que troca `access_token=...`, tokens da Meta e do Google e chaves de API por `***`.
- A tela de chaves só mostra o valor das variáveis que não são segredo.
- **Cofre** (`darkops/cofre.py`, 2026-11-12): os tokens dos canais, tudo em `credenciais/` e os valores secretos do `.env` ficam cifrados no disco (XSalsa20-Poly1305, SecretBox do PyNaCl).
  - Windows: a chave é protegida pelo DPAPI e só abre no mesmo usuário do mesmo PC.
  - macOS e Linux: a chave fica no chaveiro do sistema; sem chaveiro, num arquivo só do dono fora da pasta do projeto.
  - Copiar a pasta para outro computador não leva os segredos legíveis.
  - O Estúdio cifra o que estiver em claro ao abrir; `cofre-proteger` faz isso à mão.
- **Rotina de integridade e segurança** (todo dia, tela Saúde do app):
  - arquivos do app contra o Git;
  - segredos fora do Git e nenhuma chave no código;
  - SHA-256 dos programas baixados e de cada arquivo dos pacotes Python (RECORD do pip);
  - falhas conhecidas (OSV.dev e `npm audit`);
  - teste real das travas do Estúdio (Host de fora e POST sem Origin precisam dar 403).
  - No GitHub, `pip-audit` e o Dependabot fazem o mesmo para o repositório público.
- Criar conta, senha, códigos por SMS ou e-mail, CAPTCHA e chaves secretas são sempre com você. Com a skill `/conectar-contas`, o agente pode fazer no seu Chrome as telas de configuração e clicar em Permitir nas autorizações do seu próprio app, só depois do seu ok no chat.

## Claude Code chamado pelo projeto (leva, descrição, análise, ajuste do canal)

- O pedido vai pela **entrada padrão**, nunca como argumento: no Windows, um `.cmd` passa os argumentos pelo cmd.exe, que interpreta `&`, `|` e `^` (falha **BatBadBut**, [SecurityWeek](https://www.securityweek.com/batbadbut-command-injection-vulnerability-affects-multiple-programming-languages/)). O `claude.exe` é preferido ao `claude.cmd`.
- Na leva, o Claude lê páginas da internet, então:
  - só pode **gravar os roteiros da fila e o palco 3D** (`cenas/*.3d.js`, que roda isolado no Chromium). Um `.py` em `cenas/` viraria código rodando no PC, por isso fica proibido desde a auditoria de 2026-11-12;
  - só roda `palco-testar` e `roteiro-auditar` com o Python do projeto, não qualquer Python;
  - sem `acceptEdits`: o resto é negado.
- Toda chamada leva:
  - `--tools` com só as ferramentas da tarefa (sem isso, ler arquivos fica livre no modo `-p`);
  - `--disallowedTools` para `.env`, `credenciais/` e `dados/`;
  - um ambiente sem as chaves do `.env`.

  Um comentário ou página com instrução escondida não consegue ler nem vazar segredo.
- Descrição, análise, comentários e ajuste do canal ("Como você quer o canal?") rodam com `--tools ""`, sem ferramenta nenhuma: só devolvem texto.
- O nome do arquivo da fila vai dentro do comando do n8n e da nuvem, então nada de `$`, crase, aspas ou `;`. Roteiro com slug, palco ou mídia fora do projeto é recusado antes de produzir.
- O servidor MCP (`python -m darkops mcp`) deixa qualquer IA consultar e preparar, mas não publicar, aprovar, responder comentário, excluir canal nem mexer em contas.
- Sugestões da análise e propostas do ajuste do canal só mudam campos permitidos do perfil, e só com a sua aprovação.
- Nuvem de reserva: a fila fica num repositório **privado** seu; o token do GitHub (`NUVEM_TOKEN`, criado por você com acesso só a esse repositório) fica no `.env`; os tokens do YouTube e do Instagram vão como Secrets criptografados (sealed box do GitHub) e só existem dentro do job do Actions.
- Chaves coladas no Estúdio são testadas no próprio serviço antes de salvar; a recusada não entra no `.env`, e a mensagem passa por `seguranca.ocultar()`.

## Automação (n8n)

- O lançador (`n8n/n8n.ps1`) prende o n8n ao PC (`N8N_LISTEN_ADDRESS=127.0.0.1`). Isso importa porque o nó Execute Command roda comandos no PC, e quem entrar no n8n poderia usá-lo ([GitHub Advisory GHSA-365g-vjw2-grx8](https://advisories.gitlab.com/npm/n8n/GHSA-365g-vjw2-grx8/)). Use uma senha forte na conta local do n8n e mantenha-o atualizado.

## WhatsApp (avisos e comandos)

- Só a API oficial da Meta (WhatsApp Cloud API). O token, o ID do número, o número do dono e a chave secreta do app ficam no `.env`; na nuvem, os quatro necessários para avisar vão como Secrets do repositório de fila.
- Só o número do dono (`WHATSAPP_PARA`) é ouvido; mensagem de outro número é ignorada.
- Para os comandos chegarem, um túnel temporário da Cloudflare (`cloudflared`, baixado da página oficial e aceito só com a assinatura digital da Cloudflare) leva a internet a um porteiro local em `127.0.0.1:5680`, e a mais nada. O porteiro só aceita o caminho `/webhook/whatsapp`, confere a assinatura `X-Hub-Signature-256` de cada entrega com a chave secreta do app (sem ela: 403) e responde a verificação da Meta só com o `WHATSAPP_VERIFICAR`. O n8n e o Estúdio continuam presos a 127.0.0.1.
- A entrega vira um arquivo em `dados/whatsapp/entrada/` e o n8n recebe só o nome dele (o comando filtra para letras, números, ponto e hífen); o texto da mensagem nunca vira parte de um comando no cmd.exe. O tema de "criar sobre <tema>" vai como argumento separado, sem shell.
- Aprovar pelo WhatsApp segue a regra do Estúdio: só vídeo com prévia pronta. Recusar move o roteiro para `recusados/` (nada é apagado). Ajustes do canal pela IA só valem depois do botão Aplicar.

## O que fica com você

- Senha forte e verificação em duas etapas nas contas do Google, do YouTube, da Meta e do n8n.
- Renovar o token do Instagram a cada 60 dias (o Estúdio avisa) e revogar acessos que não usa mais.
- Não instalar o projeto num PC compartilhado sem conta separada no Windows.

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
