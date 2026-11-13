---
name: verificar-app
description: Confere a integridade e a segurança do Projeto Canais (arquivos do app, segredos, programas instalados, pacotes, falhas conhecidas, proteções do Estúdio) e as atualizações de terceiros, explica cada problema e propõe a correção. Use quando alguém pedir para verificar, auditar, checar a segurança ou a saúde do app, ou quando a tela Saúde do app mostrar problema.
---
# Verificar o app

Comandos na raiz do projeto (Windows: `.\dark.ps1 <comando>`; macOS e Linux: `./dark.sh <comando>`).

1. Rode `integridade` (sai com código 1 se houver problema). Leia cada linha: `OK`, `AVISO` ou `PROBLEMA`.
2. Rode `atualizar-dependencias` (só lista). Itens com `[SEGURANÇA]` vêm primeiro. Atualizar não precisa de ok (decisão do dono em 2026-11-13): rode `rotinas --rodar atualizacoes`, que aplica, confere o app e desfaz o que quebrar.
3. Explique para a pessoa, em poucas linhas, cada problema e cada aviso: o que é, o risco e a correção.
4. Correções que a pessoa precisa aprovar antes, numa mensagem só com a lista:
   - `cofre-proteger` (cifra os segredos que estão em claro);
   - reinstalar um programa trocado (`instalar-apps`) ou os pacotes Python alterados
     (`python -m pip install --force-reinstall -r requirements.txt`).
5. Depois de corrigir, rode `rotinas --rodar integridade` para a tela Saúde do app mostrar o resultado novo.

Nunca:
- mostrar valor de token, chave ou senha (a saída já esconde; não abra `.env`, `credenciais/` nem `dados/cofre.chave`);
- desligar uma proteção do Estúdio;
- instalar ferramenta nova (sugerida) sem o ok da pessoa;
- atualizar o n8n ou reiniciar algo perto das 12h e das 19h do fuso do canal (horário de postagem).

<!-- SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0 -->
<!-- Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais -->
