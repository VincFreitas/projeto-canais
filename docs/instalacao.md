# Instalação e configuração

Guia único para instalar o Projeto Canais num PC Windows, escrito para **qualquer agente de IA** (Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Windsurf...) ou para uma pessoa seguindo à mão. No Claude Code, a skill `/configurar` segue este mesmo arquivo.

## Antes de começar (para o agente)
- Leia também o [AGENTS.md](../AGENTS.md): regras de segurança, de conteúdo e de publicação do projeto.
- Rode tudo no **PowerShell**, na raiz do projeto. Os comandos não pedem nada no teclado: o `instalar.ps1` percebe quando roda sem terminal interativo e pula as perguntas.
- Confira cada etapa pelo diagnóstico em JSON, que é fácil de ler por programa:
  ```
  .\.venv\Scripts\python.exe -m darkops diagnostico --json
  .\.venv\Scripts\python.exe -m darkops progresso --json
  ```
  `diagnostico --json` devolve `[{"item", "pronto", "como"}]`; `progresso --json` devolve `base`, `plataformas` e `pendencias_do_modo_guiado` (vazia = configuração concluída). O `instalar.ps1` sai com código diferente de 0 quando falha.

## Objetivo
Deixar o usuário com um canal postando sozinho, sem ele precisar mexer em arquivo. Fale em português simples, um passo por vez, e confira cada etapa antes de seguir.

**Regras de segurança (obrigatórias):**
- Criar contas, fazer login, digitar senha, verificar por SMS e aceitar termos é sempre **com o usuário**. Você mostra o caminho e espera.
- **Nunca** peça para colar chave ou token no chat. Chaves e tokens vão pelo Estúdio (Ajustes > Contas, ou a tela WhatsApp), que grava no `.env` ou em `perfis/<id>/credenciais/`.
- Não mude configurações de segurança do Windows (política de execução, firewall). Use `powershell -ExecutionPolicy Bypass -File ...`, que vale só para aquele comando.
- **Autonomia (decisão do dono, 2026-11-01):** tudo que é programa o instalador baixa e instala sozinho, sem pedir ok: Python (se faltar), Node.js, n8n e Claude Code. Avise só o tamanho (cerca de 700 MB) e o tempo (de 10 a 20 minutos). Com a pessoa ficam apenas as **contas e chaves**: login do Claude Code, contas e chaves das plataformas e, se quiser, a conta local do n8n.
- **Nunca** instale programa com `npm install -g` nem nada que crie pasta nova no `AppData` pelo terminal do agente. O app Claude para Windows é um pacote MSIX e desvia essas pastas para uma pasta virtual, que o resto do Windows não vê. O instalador põe tudo em `dados\apps\` (a pasta do projeto), visível para todo processo.

**Onde ficam as telas do Estúdio** (http://127.0.0.1:8765): no modo simples, as contas e chaves ficam em **Ajustes > Contas** (no Modo avançado, a mesma tela aparece como **Conexões** na lateral). **Progresso da configuração** e **WhatsApp** ficam na barra lateral; **+ Novo canal** fica no topo dela.

## 0. Perguntar o que a pessoa quer testar (sempre primeiro)
Antes de instalar qualquer coisa, pergunte à pessoa (múltipla escolha; use a ferramenta de perguntas do seu agente, se houver) e deixe claro o que cada opção significa:
- **YouTube**: Shorts ou vídeo convencional, com postagem automática (precisa de um app OAuth do Google, uma vez, e de um clique por canal).
- **Instagram**: Reels, com postagem automática (precisa de conta Profissional, app da Meta, um token por canal que dura 60 dias e uma conta no GitHub, porque o vídeo passa por um repositório público enquanto a Meta baixa).
- **Facebook, TikTok ou Kwai**: o projeto gera o vídeo, mas a postagem é **manual** (ainda não há postagem automática).
- **Só gerar vídeos**: sem publicar, para testar o pipeline (roteiro, voz, imagens e render).

Pergunte também se é só um teste (vídeos privados ou não listados, sem ligar a postagem) ou se o canal vai postar de verdade, e se a pessoa quer **avisos e comandos pelo WhatsApp** (opcional, passo 9).
Depois, diga em uma frase o plano: "Vamos configurar a base e depois <plataformas escolhidas>", e siga **só** os tutoriais das plataformas escolhidas (passos 5 e 6). Pule os outros.

## 1. Ver onde estamos
Se o `.venv` já existe, rode o diagnóstico e o progresso por plataforma (senão, pule para o passo 2):
```
.\.venv\Scripts\python.exe -m darkops diagnostico
.\.venv\Scripts\python.exe -m darkops progresso
```
Mostre o resultado resumido das plataformas escolhidas e siga só os passos que faltam.
Se o `.venv` não existe, vá direto ao passo 2. O Estúdio fica em **modo guiado** até o essencial terminar (.env, voz offline, Claude Code, um canal, imagens e as plataformas marcadas no canal): Início, Novo vídeo e Histórico ficam travados e a tela **Progresso da configuração** mostra o próximo passo, com uma barra por plataforma; siga essa ordem.

## 2. Instalação (um comando, sem perguntas)
Rode o instalador. Ele faz tudo sozinho, e cada download é conferido (SHA-256 ou assinatura digital oficial):
```
powershell -ExecutionPolicy Bypass -File instalar.ps1
```
1. **Python 3.11+**: usa o do PC. Se faltar, baixa o instalador oficial do python.org e instala em `dados\apps\python` (sem administrador e sem mexer no PATH).
2. Cria o `.venv`, instala os pacotes, baixa a voz offline e cria o `.env`.
3. Cria os atalhos **Projeto Canais** na Área de Trabalho e no Menu Iniciar. Rodando por agente, ele não pergunta; dá para mudar em Estúdio > Configurações. Fixar na barra de tarefas é com a pessoa (botão direito no atalho do Menu Iniciar), porque o Windows não deixa programa fazer isso.
4. `python -m darkops instalar-apps`:
   - **Node.js** LTS portátil (zip oficial) e **n8n**, os dois em `dados\apps\`;
   - importa e **liga** o workflow de postagem e aprendizado;
   - põe o n8n para **iniciar com o Windows**;
   - instala o **Claude Code** pelo instalador oficial da Anthropic.

Se uma etapa falhar (internet, por exemplo), o instalador sai com código diferente de 0 e o diagnóstico mostra o quê. Basta rodar de novo, porque o que já está pronto é pulado. Opções: `-Atalhos nenhum` e `-SemApps`.

## 3. Login do Claude Code (com a pessoa)
O instalador já pôs o Claude Code. É ele que escreve os roteiros (Novo vídeo, levas, os 15 vídeos do canal novo) e faz a análise do que funcionou. Mesmo que você seja outro agente (Codex, Gemini CLI, Cursor, Copilot, Windsurf...), o Estúdio chama o CLI `claude`. Falta só a pessoa entrar na conta dela: rodar `claude` uma vez num terminal e fazer o login. Confira com o diagnóstico ("Claude Code (escreve os roteiros)").

## 4. Chaves de serviços (valem para todos os canais)
Abra o Estúdio e mostre **Ajustes > Contas**, que explica cada conector:
```
.\.venv\Scripts\python.exe -m darkops estudio
```
- **Voz: Azure Speech (recomendado, grátis).** Botão **Entrar com a Microsoft e criar a chave** (no card Azure Speech), ou `python -m darkops conectar-azure`. A pessoa só faz o login com o código que aparece. O projeto cria o recurso de voz no nível **grátis F0**, em Brazil South, e salva a chave já testada. Se já existir um F0, ele reaproveita, e nunca cria o S0 pago. Se a conta da Microsoft ainda não tiver assinatura do Azure, a pessoa cria a conta grátis em azure.microsoft.com/free; essa parte é com ela. Para fazer à mão, o caminho continua no próprio card.
- **Imagens: Pixabay (grátis).** pixabay.com/api/docs mostra a chave depois do login (o Pexels pausou chaves novas). Sem chave de imagens o modo guiado não libera, a menos que o desenho local em pixel art (opcional) esteja instalado.
- Sem Azure, a voz cai no Edge e no Piper, que já funcionam.
- **Voz mais natural (opcional): Google Chirp 3 HD.** Grátis até 1 milhão de caracteres por mês (um vídeo de 60 s usa cerca de 900). No card **Google Chirp 3 HD** (Ajustes > Contas > Voz):
  1. console.cloud.google.com com a conta Google (pode ser o mesmo projeto do YouTube).
  2. Ligar o faturamento (Faturamento > Vincular conta de faturamento). Isso é com a pessoa: no Brasil o Google costuma cobrar um valor na ativação, tanto no Pix (R$ 200) quanto no cartão (já vimos R$ 125). Ele vira crédito e só volta ao encerrar a conta de faturamento, e o cartão precisa ter esse limite livre. Depois disso, nada é cobrado dentro da cota. Sugira um alerta de orçamento de R$ 1. Sem cartão, fique com o Gemini TTS, que não pede faturamento.
  3. Ativar a **Cloud Text-to-Speech API**.
  4. APIs e serviços > Credenciais > Criar credenciais > **Chave de API**, e restringir a chave só à Cloud Text-to-Speech API.
  5. Colar a chave no card (é testada na hora) e, se quiser, o nome da voz (Charon, Kore, Fenrir...).
  6. Ajustes > Motor da voz > **Google Chirp 3 HD**.
- **Voz dirigida por instrução (opcional, para testar): Gemini TTS.** aistudio.google.com/apikey > Criar chave de API, sem faturamento. Colar no card **Gemini TTS**, com voz e estilo opcionais ("documentário de mistério, voz grave"). A cota grátis é pequena (há relatos de 10 pedidos por dia, um por cena), então serve para provar o tom; para a leva diária, prefira o Chirp.
- **Voz no próprio PC (opcional): Chatterbox.** Sem chave e sem cota, mas lento (cerca de 3 min para 16 s de fala numa placa de 4 GB). Fica em `dados/apps/vozes`, separado do `.venv`.
- **Escolher a voz do canal ouvindo antes:** no Novo canal (passo **Formato e voz**) e em Ajustes > Voz do narrador aparecem primeiro só 6 vozes recomendadas para o assunto do canal (cada voz é classificada por tema: mistério, terror, curiosidades, animais, história, geopolítica, bizarras, como funciona), com ▶ para ouvir; **Ver mais** abre mais 6 e **Ver todas** abre tudo, inclusive as pagas. As vozes grátis (Azure/Edge e Piper) já vêm com amostra pronta em `assets/vozes/amostras`, em cada língua de público. As pagas (Gemini, Chirp 3 HD, ElevenLabs) pedem a chave no próprio cartão: ela é testada, salva no `.env` e as amostras saem na hora, só para quem tem a chave (`dados/amostras-voz`, fora do Git). Pelo terminal: `.\dark.ps1 vozes-amostras` (grátis que faltam) ou `.\dark.ps1 vozes-amostras --motor gemini --mercado pt-BR`.
- Para ouvir os motores lado a lado com um texto seu: `.\dark.ps1 comparar-vozes` (arquivos em `saida\vozes-teste`).

## 5. YouTube (se escolhido; uma vez por instalação, depois um clique por canal)
App OAuth do Google, **um só para todos os canais** (nunca crie um por canal; com o app em modo de teste, cada Gmail de canal entra em Público > Usuários de teste):
1. console.cloud.google.com, logado na conta do canal: criar o projeto, ativar a **YouTube Data API v3**.
2. Google Auth Platform: Branding (nome do app, e-mail), Público **Externo**, usuário de teste = o Gmail do canal.
3. Acesso a dados: adicionar os escopos em "Adicionar escopos manualmente" (o campo de cima é só filtro): `https://www.googleapis.com/auth/youtube.upload` e `https://www.googleapis.com/auth/youtube.readonly` (e, para ler e responder comentários pelo Estúdio, `https://www.googleapis.com/auth/youtube.force-ssl`), depois Atualizar e Salvar.
4. Para o token não vencer em 7 dias, **publicar o app** (Público > Publicar app). Isso exige página inicial, política de privacidade e termos no Branding: a pasta `site/` tem modelos para publicar no GitHub Pages (workflow `.github/workflows/pages.yml`, Settings > Pages > Source: GitHub Actions **antes** do primeiro push).
5. Clientes > Criar cliente > **App para computador** > Baixar JSON. Salvar como `credenciais/client_secret.json`.
6. No Estúdio, Ajustes > Contas > **Conectar YouTube** e escolher a conta do canal (depois de criar o canal no passo 7, ou no canal de exemplo).

Avise: no login aparece **"O Google não verificou este app"**. É o app da própria pessoa, ainda sem a verificação do Google: Avançado > "Acessar (não seguro)". Para o aviso sumir, ela pede a verificação em Google Auth Platform > Central de verificação (console.cloud.google.com/auth/verification). O pedido exige a página inicial e a política de privacidade do site (`site/`), o domínio confirmado no Search Console, a justificativa dos escopos `youtube.upload` e `youtube.readonly` e um vídeo curto mostrando o login. Costuma levar alguns dias. Nada disso se resolve pelo código.

Avise: sem a auditoria do Google ("YouTube API Services Audit"), os vídeos enviados pela API ficam **privados**.

## 6. Instagram (se escolhido)
Uma vez por instalação (com a pessoa, porque são contas):
1. A conta do Instagram precisa ser **Profissional** (Criador ou Empresa), mudança feita no app do Instagram. Com o login do Instagram usado aqui, não precisa de Página do Facebook.
2. App da Meta, tela por tela (o card do Instagram no Estúdio mostra o mesmo, com os nomes em inglês entre parênteses): developers.facebook.com/apps/creation > nome `Projeto Canais` (sem Instagram, Facebook nem Meta) > caso de uso "Gerenciar mensagens e conteúdo no Instagram" (ou "Outro" e tipo "Empresa") > "Não quero conectar um portfólio empresarial agora" > Ir para o painel. Em Instagram > **Configuração da API com login do Instagram**: na etapa 1, **Adicionar conta** com a conta do canal; na etapa 3, **Configurar**, e em **URIs de redirecionamento do OAuth** a pessoa acrescenta o endereço que o card do Instagram mostra (padrão `https://vincfreitas.github.io/projeto-canais/instagram.html`; quem publicar o próprio site troca em `INSTAGRAM_RETORNO`). Depois, em **Configurações do login da empresa**, copia o **ID do app do Instagram** (só números; não é o ID do app do topo do painel) e a **chave secreta do app do Instagram** (32 caracteres) e cola no card.

Por canal:
3. O app da Meta é **um só para todos os canais**: nunca crie outro. Para cada canal novo, adicione a conta do Instagram dele no mesmo app (Instagram > Configuração da API com login do Instagram > 1. Gerar tokens de acesso > Adicionar conta). Não precisa de Página nem de grupo do Facebook. Depois, botão **Entrar com Instagram**: a pessoa entra na conta do canal e autoriza. O token de 60 dias chega sozinho e se renova sozinho depois de 40 dias, no próprio uso. A autorização já pede a permissão de comentários (`instagram_business_manage_comments`), que a tela Resultados > Comentários usa para ler e responder; quem conectou antes da v0.46.0 precisa entrar com o Instagram de novo. Colar um token à mão continua como alternativa.

Uma vez por instalação, o **repositório de passagem** (sem ele o Reel não sobe: a Meta só baixa o vídeo por um link público):
4. Em Ajustes > Contas > **Nuvem**, botão **Entrar com o GitHub e preparar tudo** (ou `python -m darkops conectar-github`). A pessoa só aprova o código que aparece. O projeto cria o repositório **privado** de fila e o **público** de passagem, grava o acesso e prepara a nuvem (postagem às 12:20 e 19:20 com o PC desligado). Depois, **Testar o Instagram (não publica)**. O jeito manual (token fine-grained) continua em "Ou faça à mão".

## 7. Canal e primeiros vídeos
- **O que se faz uma vez só** (vale para todos os canais): app do Google, app da Meta, GitHub (fila e passagem), chaves de voz e imagens, n8n e WhatsApp. **O que se repete a cada canal novo:** o Gmail (opcional), o canal de marca do YouTube, a conta Profissional do Instagram (e adicioná-la no app da Meta que já existe), além de Conectar YouTube e Entrar com Instagram. O Estúdio mostra essa divisão em Ajustes > Contas ("Deste canal" e "Uma vez só") e no guia Criar as contas.
- No Estúdio, **+ Novo canal**: um assistente de 6 passos (nicho, nome com sugestões da IA, formato e duração, redes, contas, revisão). O passo Contas e a aba **Ajustes > Criar as contas** mostram, na ordem, o Gmail, o canal do YouTube, o Instagram, o app do Google, o app da Meta, o GitHub (com os nomes dos dois repositórios) e a Microsoft, cada um com nomes sugeridos a partir do nome do canal e o link oficial do passo. O Gmail próprio do canal é opcional: o canal do YouTube pode ser um canal de marca no Gmail da pessoa, e o Instagram aceita o apelido `seuemail+canal@gmail.com`. Avise que o Google limita quantas contas um mesmo celular confirma ("Tente usar outro dispositivo para fazer a verificação"): nesse caso, a pessoa marca **O Google bloqueou** no guia, e o Estúdio estima quando tentar de novo (24 h, depois 48 h, depois 7 dias se bloquear de novo; o Google não divulga o prazo). Insistir antes disso pode alongar a espera. Marque só as redes escolhidas no passo 0. Ou use o canal de exemplo `pulga-do-saber`.
- Ao criar, o canal **já começa os 15 primeiros vídeos** (escreve cada roteiro com o Claude Code e gera a prévia). Avise que leva um tempo (a tela mostra a estimativa) e que o PC precisa ficar ligado.
- Para temas mais fortes, use as skills `pesquisar-nicho` e `escrever-roteiro` (no Claude Code: `/pesquisar-nicho <nicho>` e `/escrever-roteiro <ideia>`; em outro agente, leia `.claude/skills/<nome>/SKILL.md` e siga); os roteiros vão para `perfis/<canal>/fila/NNN-slug.json`.
- No Início: assistir cada prévia e **Aprovar**. Só os aprovados vão ao ar.
- Depois dos 15 vídeos no ar há 2 dias, o canal se ajusta sozinho pelo que funcionou (Resultados > **O que funcionou**, com Desfazer). Isso roda no n8n às 20h (passo 8).

## 7b. Identidade visual das contas (depois de conectar YouTube e/ou Instagram)
- Siga a skill `identidade-visual` (no Claude Code: `/identidade-visual <canal>`; em outro agente: `.claude/skills/identidade-visual/SKILL.md`): ela gera a foto de perfil, a capa do YouTube, a marca d'água, a bio do Instagram e a descrição do YouTube no estilo do canal.
- Mostre a prévia e peça a aprovação de quem está testando (no chat ou no Estúdio, em Ajustes > **Foto, capa e bio das contas**). **Só depois de aprovada**, aplique nas contas que a pessoa abriu e logou no navegador que você controla (se o seu agente não controla um navegador, a pessoa aplica à mão com os arquivos gerados).
- Se a pessoa não quiser mexer nas contas agora, deixe gerado e aprovado; dá para aplicar depois com `/identidade-visual`.

## 8. Postagem automática e aprendizado (n8n)
O instalador já fez esta parte: n8n na pasta do projeto, workflow importado e ligado, início com o Windows. O Estúdio também liga o n8n escondido toda vez que abre.
1. Confira no diagnóstico os itens **"n8n"** e **"Postagem automática ligada no n8n"**. O workflow posta às 12h e às 19h (horário de Brasília) o próximo vídeo aprovado de cada canal ligado e, às 20h, roda a análise do que funcionou.
2. Opcional, com a pessoa: abrir http://localhost:5678 e criar a conta local do n8n, que protege o editor.
3. Peça para deixar a suspensão do PC em "Nunca" quando estiver na tomada. É configuração do Windows, então fica com a pessoa.
4. Se algo falhar: `.\.venv\Scripts\python.exe -m darkops instalar-apps` refaz o que faltar, e `n8n-workflow --importar` reimporta o workflow (fora das 12h e 19h de Brasília, porque reinicia o n8n).

## 9. WhatsApp (opcional; uma vez, vale para todos os canais)
> **Desligado por enquanto (2026-11-07).** Pule esta etapa. O WhatsApp só aparece no Estúdio com `DARKOPS_WHATSAPP=1` no `.env`.

Avisos (vídeo no ar, falha, fila acabando, vídeo novo com Aprovar e Recusar, resumo das 21h) e comandos (`status`, `fila`, `criar 3`, `aprovar`, `pausar`...). Usa a API oficial da Meta com um app **separado** do Instagram (a Meta não aceita "WhatsApp" no nome do app).
- Abra a tela **WhatsApp** na barra lateral e siga o passo a passo dela (criar o app com o produto WhatsApp, número de teste, o seu número como destinatário, token e App Secret). Os campos são colados lá, nunca no chat.
- Ao salvar, o Estúdio importa o workflow de comandos no n8n, baixa o `cloudflared` oficial (confere a assinatura da Cloudflare) e registra o webhook. Espere a tela mostrar **ligado**.
- Teste: `.\.venv\Scripts\python.exe -m darkops whatsapp testar`. Depois peça para a pessoa mandar "oi" para o número de teste: isso abre a janela de 24 h em que os avisos chegam sem modelo aprovado.

## 10. Conferir
Depois de cada plataforma, rode `.\.venv\Scripts\python.exe -m darkops progresso` e mostre a barra dela. No fim, rode o diagnóstico de novo e mostre o que ficou pronto e o que é opcional.
No canal (Ajustes), as plataformas aparecem como **pronta**, **falta configurar** ou **manual**. Lembre que em **Sobre o projeto > Enviar sugestão** dá para mandar o que travou. Termine dizendo, em uma linha, o que o usuário faz no dia a dia: abrir o Estúdio pelo atalho, assistir as prévias e aprovar, e responder os comentários em Resultados > Comentários.
