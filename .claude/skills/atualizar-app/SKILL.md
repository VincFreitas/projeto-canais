---
name: atualizar-app
description: Atualiza o Projeto Canais para a versão nova do GitHub e confere as dependências de terceiros, sem cortar uma postagem no meio. Use quando alguém pedir para atualizar o app, "pegar a versão nova" ou quando a tela Saúde do app mostrar atualizações.
---
# Atualizar o app

1. Confira o horário: perto das 12h e das 19h do fuso do canal, espere (postagem em andamento).
2. `atualizar --verificar` mostra se há versão nova. Com versão nova, rode `atualizar`; o Estúdio aberto reinicia sozinho quando nenhuma tarefa estiver rodando. Se a atualização parar porque um arquivo local mudou, mostre qual e pergunte à pessoa; nunca descarte mudança dela.
3. `atualizar-dependencias` lista o que é de terceiros com versão nova (Python, n8n, Node, HyperFrames, Claude Code...). Atualizar é com o ok da pessoa: `atualizar-dependencias --aplicar --itens <ids>`, com o n8n fechado.
4. No fim, rode `integridade` e `diagnostico` para conferir que nada quebrou.

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
