# Referência da CLI

Todo o app roda por comandos `python -m darkops <comando>` (com o Python do `.venv`). Atalhos na raiz do projeto: `.\dark.ps1 <comando>` no Windows (PowerShell) e `./dark.sh <comando>` no macOS e no Linux. O Estúdio, o n8n, a nuvem e as skills chamam estes mesmos comandos. Visão das peças em [arquitetura.md](arquitetura.md); como criar um comando novo em [desenvolvimento.md](desenvolvimento.md).

Opções que valem para qualquer comando:

| Opção | O que faz |
|---|---|
| `--perfil <id>` | canal (pasta em `perfis/`); padrão: `DARKOPS_PERFIL` ou o primeiro canal criado |
| `--version` | mostra a versão do app |

`python -m darkops <comando> --help` mostra a mesma ajuda desta página. Comandos com `--json` são para agentes de IA e scripts; os marcados como "usados pelo n8n" ou "no GitHub Actions" rodam sozinhos na automação e raramente à mão.

No Windows, rode `produzir` pelo PowerShell, não pelo Bash: o sandbox do Bash às vezes derruba a conexão com o serviço de voz.

## Estúdio, instalação e app

### `estudio`

Abre o Estúdio (painel local no navegador).

```bash
python -m darkops estudio [opções]
```

| Argumento | O que faz |
|---|---|
| `--porta` `<porta>` | porta local (padrão: 8765) |
| `--sem-navegador` | não abre o navegador |

### `abrir`

Abre o Estúdio (o que o atalho da Área de Trabalho roda).

```bash
python -m darkops abrir
```

### `atalhos`

Cria (ou remove) os atalhos do Projeto Canais no Windows.

```bash
python -m darkops atalhos [opções]
```

| Argumento | O que faz |
|---|---|
| `--area-de-trabalho` | atalho na Área de Trabalho |
| `--menu-iniciar` | atalho no Menu Iniciar |
| `--barra-de-tarefas` | cria no Menu Iniciar e explica como fixar |
| `--remover` | apaga os atalhos criados |

### `diagnostico`

O que está pronto e o que falta configurar.

```bash
python -m darkops diagnostico [opções]
```

| Argumento | O que faz |
|---|---|
| `--json` | saída em JSON (para agentes de IA e scripts) |

### `progresso`

Progresso da configuração de cada plataforma (YouTube, Instagram...).

```bash
python -m darkops progresso [opções]
```

| Argumento | O que faz |
|---|---|
| `--json` | saída em JSON (para agentes de IA e scripts) |

### `instalar-apps`

Instala sozinho o Node.js, o n8n e o Claude Code (na pasta do projeto).

```bash
python -m darkops instalar-apps [opções]
```

| Argumento | O que faz |
|---|---|
| `--sem-claude` | não instala o Claude Code |
| `--sem-n8n` | não instala o n8n |
| `--sem-logon` | não liga o n8n junto com o Windows |

### `atualizar`

Busca a versão nova no GitHub e atualiza esta pasta.

```bash
python -m darkops atualizar [opções]
```

| Argumento | O que faz |
|---|---|
| `--verificar` | só mostra se há versão nova |

### `atualizar-dependencias`

Verifica (e atualiza) tudo de terceiros: Python, n8n, Node, HyperFrames, Claude Code.

```bash
python -m darkops atualizar-dependencias [opções]
```

| Argumento | O que faz |
|---|---|
| `--aplicar` | instala as versões novas (com conferência e volta) |
| `--itens` `<itens> [...]` | só estes ids (py:yt-dlp, n8n, node, npm:gsap, claude...) |
| `--json` | saída em JSON |

### `mcp`

Servidor MCP pela entrada padrão (para Claude, Codex, Gemini, Cursor, Copilot...).

```bash
python -m darkops mcp
```

### `mcp-configurar`

Grava a configuração do servidor MCP para cada agente de IA.

```bash
python -m darkops mcp-configurar [opções]
```

| Argumento | O que faz |
|---|---|
| `--usuario` | também no Codex e no Windsurf (pasta do usuário) |
| `--mostrar` | só mostra o bloco para colar em outro cliente |

### `marcar-arquivos`

Põe o cabeçalho de autoria nos arquivos de código e docs que não têm.

```bash
python -m darkops marcar-arquivos
```

### `vitrine`

Números reais do canal de teste do autor no README e no site, no GitHub.

```bash
python -m darkops vitrine
```

## Canais e contas

### `perfis`

Lista os perfis.

```bash
python -m darkops perfis
```

### `perfis-ativos`

Perfis com postagem ligada (saída JSON para o n8n).

```bash
python -m darkops perfis-ativos [opções]
```

| Argumento | O que faz |
|---|---|
| `--na-hora` | só os que chegaram agora a um horário (fuso do mercado) |

### `mercados`

Línguas e regiões de público disponíveis para os canais.

```bash
python -m darkops mercados
```

### `contas-guia`

Contas do canal em JSON: ordem, nomes sugeridos, links e o que já está pronto.

```bash
python -m darkops contas-guia
```

### `pegar-app-google`

Move o JSON do app do Google (client_secret_...json) de Downloads para credenciais/client_secret.json.

```bash
python -m darkops pegar-app-google
```

### `autorizar-youtube`

Autoriza o canal uma vez pelo navegador e salva o token.

```bash
python -m darkops autorizar-youtube [opções]
```

| Argumento | O que faz |
|---|---|
| `--analytics` | também libera minutos assistidos e retenção |
| `--comentarios` | também libera responder comentários |

### `conta-instagram`

Confere o token do Instagram.

```bash
python -m darkops conta-instagram
```

### `conectar-github`

Login no GitHub; cria os repositórios da nuvem e da passagem do Instagram.

```bash
python -m darkops conectar-github [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | nome do repositório privado da fila (padrão projeto-canais-fila) |
| `--passagem` `<passagem>` | nome do repositório público de passagem (padrão projeto-canais-videos) |

### `conectar-azure`

Login na Microsoft; cria o recurso de voz grátis (F0) e salva a chave.

```bash
python -m darkops conectar-azure
```

### `identidade`

Foto, capa, marca d'água e bio das contas (gerar, aprovar, pacote, aplicada).

```bash
python -m darkops identidade [<acao>] [opções]
```

| Argumento | O que faz |
|---|---|
| `<acao>` | o que fazer (padrão: estado) (`estado`, `gerar`, `aprovar`, `pacote`, `bloco`, `aplicada`) |
| `--plataforma` `<plataforma>` | com 'aplicada': youtube ou instagram |
| `--por` `<por>` | com 'aprovar': quem aprovou |
| `--arquivo` `<arquivo>` | com 'bloco' (`foto`, `marca`, `capa`) |
| `--numero` `<numero>` | com 'bloco': número do pedaço (0, 1, 2...) |

### `ajustar-canal`

A IA transforma a descrição do canal em mudanças do perfil (pede aprovação).

```bash
python -m darkops ajustar-canal <pedido>
```

| Argumento | O que faz |
|---|---|
| `<pedido>` | o pedido em texto livre (ex.: "vídeos mais rápidos") |

## Pesquisa

### `nichos`

Lista os nichos de config/nichos.json.

```bash
python -m darkops nichos
```

### `demanda`

Mapa de demanda pelo autocomplete do YouTube.

```bash
python -m darkops demanda [<termo> [...]] [opções]
```

| Argumento | O que faz |
|---|---|
| `<termo>` | termo de busca (ou use --nicho) |
| `--nicho` `<nicho>` | preset de config/nichos.json |
| `--idioma` `<idioma>` | idioma das sugestões (padrão: pt) |
| `--top` `<top>` | quantos termos mostrar (padrão: 25) |
| `--rapido` | sem expansões a-z |

### `outliers`

Vídeos muito acima da mediana do próprio canal.

```bash
python -m darkops outliers [opções]
```

| Argumento | O que faz |
|---|---|
| `--nicho` `<nicho>` | preset de config/nichos.json |
| `--busca` `<busca>` | pode repetir; substitui as buscas do nicho |
| `--idioma` `<idioma>` | idioma da busca (padrão: pt) |
| `--por-busca` `<por_busca>` | vídeos lidos por busca (padrão: 30) |
| `--min-views` `<min_views>` | mínimo de visualizações (padrão: 10000) |
| `--top` `<top>` | quantos outliers guardar (padrão: 30) |
| `--detalhar` `<detalhar>` | quantos buscam data e views/dia (lento) |
| `--nome` `<nome>` | pasta em pesquisa/ para uma busca avulsa (padrão: avulso) |

### `transcrever`

Transcrição de um vídeo ou dos top de um outliers.json.

```bash
python -m darkops transcrever <alvo> [opções]
```

| Argumento | O que faz |
|---|---|
| `<alvo>` | URL do vídeo ou caminho de outliers.json |
| `--top` `<top>` | quantos vídeos do outliers.json (padrão: 5) |
| `--idioma` `<idioma>` | idioma da legenda (padrão: pt) |

### `tendencias`

Assuntos em alta agora no país do público (pauta dos canais de notícias).

```bash
python -m darkops tendencias [opções]
```

| Argumento | O que faz |
|---|---|
| `--mercado` `<mercado>` | público (pt-BR, en-US...; padrão: pt-BR) |
| `--quantidade` `<quantidade>` | quantos assuntos (padrão: 10) |

### `referencia`

Mede o estilo de vídeos de referência e propõe o padrão do perfil.

```bash
python -m darkops referencia <url> [...]
```

| Argumento | O que faz |
|---|---|
| `<url>` | links dos vídeos de referência (até 5) |

### `ouvir`

Transcreve um áudio ou vídeo no PC (faster-whisper).

```bash
python -m darkops ouvir <arquivo> [opções]
```

| Argumento | O que faz |
|---|---|
| `<arquivo>` | áudio ou vídeo do PC |
| `--idioma` `<idioma>` | idioma da fala (padrão: pt) |

## Roteiros e levas

### `leva`

Cria vários vídeos de uma vez (roteiro pelo Claude Code + prévia).

```bash
python -m darkops leva [opções]
```

| Argumento | O que faz |
|---|---|
| `--quantidade` `<quantidade>` | quantos vídeos (padrão: leva_quantidade do canal, ou 4) |
| `--se-faltar` | só cria se a fila estiver no mínimo do perfil |
| `--fundo` | roda num processo separado e volta na hora |
| `--tema` `<tema>` | assunto do vídeo (sem ele, o Claude escolhe um tema forte) |
| `--formato` `<formato>` | curto (vertical) ou longo; sem ele, o do perfil (`vertical`, `longo`) |
| `--serie` `<serie>` | série em partes sobre o tema (2 ou 4 vídeos ligados) (`2`, `4`) |
| `--serie-id` `<serie_id>` | continua uma série já começada (o id fica em "serie" no roteiro) |

### `roteiro-auditar`

Confere gancho, estrutura e CTA de roteiros (sai com erro se faltar algo).

```bash
python -m darkops roteiro-auditar <roteiros> [...]
```

| Argumento | O que faz |
|---|---|
| `<roteiros>` | um ou mais roteiros JSON |

### `palco-testar`

Desenha alguns quadros de cada cena do palco de um roteiro (sem gravar).

```bash
python -m darkops palco-testar <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON com palco 3D |

### `prancha-testar`

Monta e confere a Prancha de Campo de um roteiro e grava a folha de contato.

```bash
python -m darkops prancha-testar <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON com cenas/<slug>.prancha.json |

### `prancha-escrever`

Pede ao Claude a Prancha de Campo de roteiros já escritos.

```bash
python -m darkops prancha-escrever <roteiros> [...] [opções]
```

| Argumento | O que faz |
|---|---|
| `<roteiros>` | um ou mais roteiros JSON |
| `--refazer` | reescreve mesmo se já existir |

### `descricao`

Cria pela IA a descrição e as tags do vídeo que estiverem no modo automático.

```bash
python -m darkops descricao <roteiro> [opções]
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON da fila |
| `--refazer` | escreve de novo mesmo se já houver descrição |

### `carrossel`

Carrossel do Instagram (7 a 10 slides) a partir do roteiro, para aprovar.

```bash
python -m darkops carrossel <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON (perfis/<id>/fila/...) |

### `cortes`

Cortes verticais de uma live que já acabou (YouTube, Twitch ou Kick), na fila para aprovar; --vigiar corta as lives novas dos streamers autorizados.

```bash
python -m darkops cortes [<live>] [opções]
```

| Argumento | O que faz |
|---|---|
| `<live>` | link da live gravada |
| `--quantidade` `<quantidade>` | quantos cortes tirar da live (padrão: o do canal, ou 3) |
| `--autorizado` | registra que você tem autorização do streamer (por escrito ou no programa de cortes dele) |
| `--como` `<como>` | como foi a autorização (fica anotado no canal) |
| `--vigiar` | procura lives novas dos streamers autorizados e corta |
| `--fonte` `<fonte>` | só registra o canal do streamer como autorizado (link do canal) e sai |

## Produção, voz e conferência

### `produzir`

Gera vídeo, thumbnail e metadados a partir de roteiro(s) JSON.

```bash
python -m darkops produzir <roteiro> [...] [opções]
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | um ou mais roteiros JSON |
| `--sem-legenda` | vídeo sem legenda queimada |

### `conferir`

Confere o vídeo pronto: tela preta, silêncio, volume, duração e resolução.

```bash
python -m darkops conferir <video>
```

| Argumento | O que faz |
|---|---|
| `<video>` | arquivo MP4 pronto (saida/...) |

### `revisar-visual`

A IA olha 12 quadros do vídeo pronto e aponta problemas visuais.

```bash
python -m darkops revisar-visual <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON (perfis/<id>/fila/...) |

### `vozes`

Lista vozes do edge-tts.

```bash
python -m darkops vozes [<prefixo>]
```

| Argumento | O que faz |
|---|---|
| `<prefixo>` | começo do código da voz (padrão: pt-BR) |

### `vozes-amostras`

Amostras das vozes para escolher a voz do canal (grátis ou, com a chave, pagas).

```bash
python -m darkops vozes-amostras [opções]
```

| Argumento | O que faz |
|---|---|
| `--mercado` `<mercado>` | só um público, ex.: pt-BR |
| `--motor` `<motor>` | opção paga (precisa da chave) (`gemini`, `chirp`, `elevenlabs`) |
| `--minha-voz` | amostra da sua própria voz (gravação em dados/minha-voz) |
| `--refazer` | gera de novo as amostras que já existem |

### `comparar-vozes`

Gera o mesmo trecho em cada motor de voz para ouvir lado a lado.

```bash
python -m darkops comparar-vozes [opções]
```

| Argumento | O que faz |
|---|---|
| `--texto` `<texto>` | trecho a narrar (padrão: um texto de exemplo) |

### `instalar-voz-local`

Voz Kokoro e transcrição faster-whisper no PC (grátis, sem chave).

```bash
python -m darkops instalar-voz-local
```

### `efeitos-baixar`

Baixa efeitos sonoros CC0 do Openverse para assets/efeitos.

```bash
python -m darkops efeitos-baixar [opções]
```

| Argumento | O que faz |
|---|---|
| `--por-tipo` `<por_tipo>` | quantos efeitos por tipo de som (padrão: 6) |

## Postagem (usados pelo n8n)

### `n8n-workflow`

Gera n8n/workflow.json para esta pasta (e importa com --importar).

```bash
python -m darkops n8n-workflow [opções]
```

| Argumento | O que faz |
|---|---|
| `--importar` | importa no n8n (vale depois de reiniciar o n8n) |

### `fila-proximo`

Próximo roteiro aprovado da fila do perfil (saída JSON para o n8n).

```bash
python -m darkops fila-proximo
```

### `fila-produzir`

Produz um roteiro e devolve o vídeo em JSON.

```bash
python -m darkops fila-produzir <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON da fila |

### `publicar-youtube`

Envia o vídeo produzido de um roteiro ao YouTube.

```bash
python -m darkops publicar-youtube <roteiro> [opções]
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON com o vídeo produzido |
| `--privacidade` `<privacidade>` | padrão: o configurado no perfil (`private`, `unlisted`, `public`) |

### `publicar-instagram`

Publica o vídeo vertical de um roteiro como Reel.

```bash
python -m darkops publicar-instagram <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON com o vídeo vertical produzido |

### `fila-concluir`

Move o roteiro publicado e anota no testes.csv do perfil.

```bash
python -m darkops fila-concluir <roteiro>
```

| Argumento | O que faz |
|---|---|
| `<roteiro>` | roteiro JSON publicado |

### `registrar-falha`

Anota um erro do workflow em controle/falhas.log.

```bash
python -m darkops registrar-falha [opções]
```

| Argumento | O que faz |
|---|---|
| `--etapa` `<etapa>` | nome do nó do n8n que falhou |
| `--mensagem` `<mensagem>` | mensagem de erro (passa por ocultar) |

## Nuvem (GitHub Actions)

### `nuvem-configurar`

Prepara o repositório privado de fila (workflow, segredos e vídeos).

```bash
python -m darkops nuvem-configurar [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-sincronizar`

Troca o estado com a nuvem e envia os vídeos aprovados.

```bash
python -m darkops nuvem-sincronizar [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-segredos`

Reenvia os tokens do YouTube e do Instagram para a nuvem.

```bash
python -m darkops nuvem-segredos [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-status`

Quantos vídeos a nuvem tem e quem postou por último.

```bash
python -m darkops nuvem-status [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-agenda`

Acerta os horários da nuvem com o fuso do mercado de cada canal.

```bash
python -m darkops nuvem-agenda [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-testar`

Roda o workflow da nuvem agora, em simulação (não publica).

```bash
python -m darkops nuvem-testar [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-instagram`

Testa o link de passagem do Instagram sem publicar nada.

```bash
python -m darkops nuvem-instagram [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-preparar`

(usado no GitHub Actions) monta a fila, os vídeos e as credenciais.

```bash
python -m darkops nuvem-preparar [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

### `nuvem-devolver`

(usado no GitHub Actions) devolve o estado para o repositório de fila.

```bash
python -m darkops nuvem-devolver [opções]
```

| Argumento | O que faz |
|---|---|
| `--fila` `<fila>` | pasta do repositório de fila (só no Actions) |

## Resultados e comentários

### `estatisticas`

Busca nas plataformas os números do canal e de cada vídeo.

```bash
python -m darkops estatisticas
```

### `analisar`

A IA analisa as estatísticas e sugere mudanças (cada uma pede aprovação).

```bash
python -m darkops analisar
```

### `aprender`

Analisa o que funcionou a cada 14 vídeos no ar e ajusta o canal sozinho.

```bash
python -m darkops aprender [opções]
```

| Argumento | O que faz |
|---|---|
| `--forcar` | analisa agora, mesmo sem completar o ciclo |
| `--perfil-unico` | só o perfil de --perfil (sem isso: todos os ativos) |

### `aprender-desfazer`

Volta as mudanças da última análise automática.

```bash
python -m darkops aprender-desfazer
```

### `comentarios`

Busca os comentários novos, classifica pela IA e rascunha respostas.

```bash
python -m darkops comentarios [opções]
```

| Argumento | O que faz |
|---|---|
| `--todos` | todos os perfis ativos (o que o n8n roda) |
| `--sem-ia` | só busca, sem classificar nem responder |

### `comentario-responder`

Publica a resposta de um comentário (o rascunho aprovado).

```bash
python -m darkops comentario-responder <id> [opções]
```

| Argumento | O que faz |
|---|---|
| `<id>` | id do comentário (tela Comentários) |
| `--texto` `<texto>` | outra resposta no lugar do rascunho |

## Manutenção e segurança

### `integridade`

Confere arquivos, segredos, programas, pacotes e falhas conhecidas.

```bash
python -m darkops integridade [opções]
```

| Argumento | O que faz |
|---|---|
| `--json` | saída em JSON |

### `rotinas`

Rotinas automáticas (integridade, atualizações, ferramentas novas).

```bash
python -m darkops rotinas [opções]
```

| Argumento | O que faz |
|---|---|
| `--rodar` `<rodar>` | roda uma rotina agora (`integridade`, `atualizacoes`, `ferramentas`, `vitrine`) |
| `--vencidas` | roda só as que passaram do prazo (o n8n usa) |

### `ferramentas-buscar`

Pesquisa ferramentas abertas novas que melhorariam o app (só sugere).

```bash
python -m darkops ferramentas-buscar
```

### `cofre-proteger`

Cifra os segredos que ainda estão em claro no disco.

```bash
python -m darkops cofre-proteger
```

## WhatsApp (desligado por padrão)

### `whatsapp`

WhatsApp do dono: testar, status, resumo, versao (avisa a versão nova) ou n8n (importa o workflow de comandos).

```bash
python -m darkops whatsapp [<acao>]
```

| Argumento | O que faz |
|---|---|
| `<acao>` | o que fazer (padrão: status) (`testar`, `status`, `resumo`, `versao`, `n8n`) |

### `whatsapp-receber`

Processa uma mensagem recebida do WhatsApp (chamado pelo n8n).

```bash
python -m darkops whatsapp-receber [opções]
```

| Argumento | O que faz |
|---|---|
| `--arquivo` `<arquivo>` | nome do arquivo em dados/whatsapp/entrada/ |

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
