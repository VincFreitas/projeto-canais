---
name: estudar-referencia
description: Mede o estilo de vídeos de referência (duração, cortes, ritmo da fala, legenda, música) e propõe o padrão do canal a partir deles, sem copiar a obra. Use quando o dono mandar links de vídeos de que ele gosta e quiser "um canal assim" ou "deixar o canal parecido com este".
---
# Estudar vídeos de referência

Argumentos: $ARGUMENTS (um ou mais links).

1. Rode `--perfil <id> referencia <link> [<link> ...]`. Ele baixa só o necessário para medir e grava a medição em `perfis/<id>/controle/referencias.json`.
2. Explique o que foi medido: duração, cortes por minuto, palavras por minuto, tipo de legenda, música e efeitos.
3. Proponha o padrão do canal tirando só a **técnica** (ritmo, duração, tipo de legenda). Nunca a obra: personagens, marca, cores, fonte, mascote, frases ou trilha de outro canal (regra de identidade própria do AGENTS.md).
4. Para aplicar, use a skill /ajustar-canal com o pedido montado a partir da proposta (o dono aprova no Estúdio).

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
