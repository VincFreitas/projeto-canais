---
name: ajustar-canal
description: Ajusta a configuração de um canal a partir de um pedido em linguagem natural (voz, ritmo, legenda, formato, horários, público, tema visual), gerando uma proposta que o dono aprova no Estúdio. Use quando alguém pedir para mudar o jeito do canal ("quero vídeos mais rápidos", "troque a voz", "poste às 18h").
---
# Ajustar o canal

Argumentos: $ARGUMENTS (o pedido; se faltar o canal, pergunte qual, com a lista de `perfis`).

1. Rode `--perfil <id> ajustar-canal "<pedido>"`. A IA lê a configuração atual e grava uma proposta pendente; nada muda ainda.
2. Mostre à pessoa o que vai mudar (campo, valor atual e valor novo), em português simples.
3. A aprovação é no Estúdio: Ajustes do canal, no alto, **Aprovar** ou **Recusar**. Se o Estúdio não estiver aberto, rode `estudio`.
4. Ajustes que mexem nas contas (descrição do canal, palavras-chave) vão para o YouTube ao salvar, se "atualizar também as contas conectadas" estiver marcado.

Não edite `perfis/<id>/perfil.json` à mão para contornar a aprovação. O gancho final `app` (divulgar o projeto) só vale nos canais do dono.

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
