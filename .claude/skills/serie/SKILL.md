---
name: serie
description: Cria uma série de 2 ou 4 vídeos ligados sobre um assunto, cada parte com um pedaço próprio e postada na ordem. Use quando alguém pedir "série", "parte 1 e 2", "conteúdo em partes" ou trouxer um assunto grande demais para um vídeo só.
---
# Série em partes

Argumentos: $ARGUMENTS (o assunto e, se a pessoa disser, 2 ou 4 partes).

1. Confira que o canal está configurado: `progresso --json`. Sem configuração, a leva fica adiada.
2. Rode `--perfil <id> leva --quantidade N --serie N --tema "<assunto>"`, com N = 2 ou 4. A parte 1 grava o plano da série; as seguintes recebem o plano e o texto das anteriores (seção 3g da skill /escrever-roteiro).
3. A fila garante a ordem: uma parte só sai depois da anterior. Se o Claude falhar numa parte, a série para; continue com `leva --serie-id <id>` (o id fica em `serie` no roteiro).
4. Cada parte é aprovada no Estúdio, como qualquer vídeo. Os títulos levam "(parte K/N)".

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
