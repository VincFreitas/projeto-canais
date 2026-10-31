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

## Tokens e chaves

- `.env` e `credenciais/` ficam fora do Git (`.gitignore`); o histórico foi conferido em 2026-10-24 e não tem chave nem token.
- Mensagens de erro, avisos das estatísticas e `falhas.log` passam por `seguranca.ocultar()`, que troca `access_token=...`, tokens da Meta e do Google e chaves de API por `***`.
- A tela de chaves só mostra o valor das variáveis que não são segredo.
- Logins e autorizações OAuth são sempre feitos por você, no navegador.

## Claude Code chamado pelo projeto (leva, descrição, análise, ajuste do canal)

- O pedido vai pela **entrada padrão**, nunca como argumento: no Windows, um `.cmd` passa os argumentos pelo cmd.exe, que interpreta `&`, `|` e `^` (falha **BatBadBut**, [SecurityWeek](https://www.securityweek.com/batbadbut-command-injection-vulnerability-affects-multiple-programming-languages/)). O `claude.exe` é preferido ao `claude.cmd`.
- Na leva, o Claude lê páginas da internet, então só pode **gravar na fila do perfil e em `cenas/`** e só roda **um** comando (`darkops palco-testar`), não qualquer Python. Sem `acceptEdits`: o resto é negado.
- Descrição, análise e ajuste do canal ("Como você quer o canal?") rodam sem ferramentas: só devolvem texto.
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
