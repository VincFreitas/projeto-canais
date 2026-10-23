---
name: configurar
description: Instala e configura o projeto do zero num PC Windows (dependências, voz, n8n, chaves, contas do YouTube e do Instagram, primeiro perfil e postagem automática), guiando o usuário passo a passo e conferindo cada etapa com o diagnóstico. Use quando alguém acabou de clonar o repositório, pedir para instalar, configurar, "fazer funcionar" ou quando o diagnóstico mostrar itens faltando.
---

# Configurar o projeto

Argumentos recebidos: $ARGUMENTS

Objetivo: deixar o usuário com um canal postando sozinho, sem ele precisar mexer em arquivo. Fale em português simples, um passo por vez, e confira cada etapa antes de seguir.

**Regras de segurança (obrigatórias):**
- Criar contas, fazer login, digitar senha, verificar por SMS e aceitar termos é sempre **com o usuário**. Você mostra o caminho e espera.
- **Nunca** peça para colar chave ou token no chat. Chaves vão pelo Estúdio (Conexões) ou direto no `.env`; tokens do Instagram, pelo Estúdio.
- Não mude configurações de segurança do Windows (política de execução, firewall). Use `powershell -ExecutionPolicy Bypass -File ...`, que vale só para aquele comando.
- Antes de instalar algo global (Node, n8n), diga o que é, o tamanho aproximado e peça o ok.

## 0. Perguntar o que a pessoa quer testar (sempre primeiro)
Antes de instalar qualquer coisa, use AskUserQuestion (multiSelect) e deixe claro o que cada opção significa:
- **YouTube**: Shorts ou vídeo convencional, com postagem automática (precisa de um app OAuth do Google, uma vez, e de um clique por canal).
- **Instagram**: Reels, com postagem automática (precisa de conta Profissional, app da Meta e um token por canal, que dura 60 dias).
- **Facebook, TikTok ou Kwai**: o projeto gera o vídeo, mas a postagem é **manual** (ainda não há postagem automática).
- **Só gerar vídeos**: sem publicar, para testar o pipeline (voz, imagens e render).

Pergunte também se é só um teste (vídeos privados ou não listados, sem ligar a postagem) ou se o canal vai postar de verdade.
Depois, diga em uma frase o plano: "Vamos configurar a base e depois <plataformas escolhidas>", e siga **só** os tutoriais das plataformas escolhidas (passos 4 e 5). Pule os outros.

## 1. Ver onde estamos
Rode o diagnóstico e o progresso por plataforma (se o `.venv` ainda não existir, pule para o passo 2):
```
.\.venv\Scripts\python.exe -m darkops diagnostico
.\.venv\Scripts\python.exe -m darkops progresso
```
Mostre o resultado resumido das plataformas escolhidas e siga só os passos que faltam.
O Estúdio fica em **modo guiado** até essas etapas terminarem: Fila, Novo vídeo e Histórico ficam travados e a tela Progresso mostra o próximo passo; siga essa ordem. Mostre também a tela **Progresso da configuração** do Estúdio (menu Geral, http://127.0.0.1:8765/progresso), que tem uma barra por plataforma e se atualiza a cada etapa.

## 2. Dependências (Python 3.11+)
- Confira `python --version`. Sem Python: peça para instalar em python.org (marcar "Add to PATH").
- Rode o instalador (cria o `.venv`, instala os pacotes, baixa a voz offline e cria o `.env`):
  ```
  powershell -ExecutionPolicy Bypass -File instalar.ps1
  ```

## 3. Chaves de serviços (valem para todos os perfis)
Abra o Estúdio e mostre a aba **Conexões**, que explica cada conector:
```
.\.venv\Scripts\python.exe -m darkops estudio
```
- **Voz: Azure Speech (recomendado, grátis).** portal.azure.com, criar recurso "Serviço de Fala", nível **Free F0** (confira duas vezes, o S0 é pago), região Brazil South. Em "Chaves e Ponto de Extremidade", copiar a CHAVE 1. Se a conta grátis for recusada, a de pagamento conforme o uso funciona com o F0 sem cobrar; sugira um alerta de orçamento de R$ 1.
- **Imagens: Pixabay (grátis).** pixabay.com/api/docs mostra a chave depois do login.
- Sem Azure, a voz cai no Edge e no Piper, que já funcionam.

## 4. YouTube (se escolhido; uma vez por instalação, depois um clique por canal)
App OAuth do Google, que vale para todos os perfis:
1. console.cloud.google.com, logado na conta do canal: criar o projeto, ativar a **YouTube Data API v3**.
2. Google Auth Platform: Branding (nome do app, e-mail), Público **Externo**, usuário de teste = o Gmail do canal.
3. Acesso a dados: adicionar os escopos em "Adicionar escopos manualmente" (o campo de cima é só filtro): `https://www.googleapis.com/auth/youtube.upload` e `https://www.googleapis.com/auth/youtube.readonly`, depois Atualizar e Salvar.
4. Para o token não vencer em 7 dias, **publicar o app** (Público > Publicar app). Isso exige página inicial, política de privacidade e termos no Branding: a pasta `site/` tem modelos para publicar no GitHub Pages (workflow `.github/workflows/pages.yml`, Settings > Pages > Source: GitHub Actions **antes** do primeiro push).
5. Clientes > Criar cliente > **App para computador** > Baixar JSON. Salvar como `credenciais/client_secret.json`.
6. No Estúdio, Conexões > **Conectar YouTube** e escolher a conta do canal.

Avise: sem a auditoria do Google ("YouTube API Services Audit"), os vídeos enviados pela API ficam **privados**.

## 5. Instagram (se escolhido; por canal)
1. A conta do Instagram precisa ser **Profissional** (Criador) e estar ligada a uma Página do Facebook.
2. developers.facebook.com > criar app > caso de uso "Gerenciar mensagens e conteúdo no Instagram".
3. Instagram > Configuração da API com login do Instagram > etapa 2 **Adicionar conta** (com o @ do canal) > **Gerar token**.
4. Colar o token no Estúdio, em Conexões. Ele dura 60 dias.

## 6. Perfil e primeiros vídeos
- No Estúdio, **+ Novo perfil** (ou use o exemplo `pulga-do-saber`), preencha nome, @, nicho e foto.
- Para encher a fila com qualidade, use `/pesquisar-nicho <nicho>` e depois `/escrever-roteiro <ideia>`; salve os roteiros em `perfis/<perfil>/fila/NNN-slug.json`.
- No Estúdio: abra cada vídeo, **Gerar prévia**, assista e **Aprovar**. Só os aprovados vão ao ar.

## 7. Postagem automática (n8n)
1. Node.js LTS (nodejs.org), depois `npm install -g n8n` (cerca de 10 minutos; peça o ok).
2. Inicie o n8n: `powershell -ExecutionPolicy Bypass -File n8n\n8n.ps1` e crie a conta local no primeiro acesso (http://localhost:5678).
3. Gere e importe o workflow desta pasta: `.\.venv\Scripts\python.exe -m darkops n8n-workflow --importar`
4. No n8n, abra "Canais dark - postagem automática" e **ative**. Posta às 12h e às 19h (horário de Brasília) o próximo vídeo aprovado de cada perfil ligado.
5. Opcional: iniciar com o Windows (`powershell -ExecutionPolicy Bypass -File n8n\iniciar-com-windows.ps1`) e suspensão do PC em "Nunca" na tomada.

## 8. Conferir
Depois de cada plataforma, rode `.\.venv\Scripts\python.exe -m darkops progresso` e mostre a barra dela. No fim, rode o diagnóstico de novo e mostre o que ficou pronto e o que é opcional.
No perfil (Estúdio > Novo perfil ou aba Perfil), as plataformas aparecem como **pronta**, **falta configurar** ou **manual**. Marque só as que a pessoa escolheu. Lembre que em **Sobre o projeto > Enviar sugestão** dá para mandar o que travou. Termine dizendo, em uma linha, o que o usuário faz no dia a dia: abrir o Estúdio, gerar prévias, aprovar.
