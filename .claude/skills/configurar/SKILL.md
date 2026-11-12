---
name: configurar
description: Instala e configura o projeto do zero num PC Windows (dependências, voz, Claude Code, n8n, chaves, contas do YouTube e do Instagram, primeiro canal, postagem automática e WhatsApp opcional), guiando o usuário passo a passo e conferindo cada etapa com o diagnóstico. Use quando alguém acabou de clonar o repositório, pedir para instalar, configurar, "fazer funcionar" ou quando o diagnóstico mostrar itens faltando.
---

# Configurar o projeto

Argumentos recebidos: $ARGUMENTS

O passo a passo fica em [docs/instalacao.md](../../../docs/instalacao.md), um guia único que serve para qualquer agente de IA. **Leia o arquivo inteiro antes de começar e siga-o na ordem**, com as regras de segurança dele.

No Claude Code:
- Faça as perguntas de múltipla escolha do passo 0 (plataformas) com AskUserQuestion (multiSelect). Programas (Python, Node.js, n8n, Claude Code) o instalador põe sozinho, sem pedir ok; com a pessoa ficam só contas e chaves.
- YouTube e Instagram (passos 5 e 6): com o Claude no Chrome, rode a skill `/conectar-contas <canal>`, que faz as telas de configuração e as conexões no Chrome da pessoa; com ela ficam só criar a conta, senha, códigos, CAPTCHA e a chave secreta da Meta.
- Identidade visual (passo 7b): rode a skill `/identidade-visual <canal>` e aplique pelo navegador interno, só depois da aprovação.
- Pesquisa e roteiros (passo 7): `/pesquisar-nicho <nicho>` e `/escrever-roteiro <ideia>`.
- Confira cada etapa com `.\.venv\Scripts\python.exe -m darkops progresso` (ou `--json`).
