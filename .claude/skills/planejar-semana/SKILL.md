---
name: planejar-semana
description: Monta o plano da semana do canal (o que postar, em que ordem e quando), equilibrando temas e fórmulas de gancho e apontando quantos roteiros faltam na fila. Use quando o usuário pedir planejamento, calendário, agenda de posts ou "o que postar".
---

# Planejar a semana

Argumentos recebidos: $ARGUMENTS

1. Leia `roteiros/fila/*.json` (ordem do nome = ordem de postagem) e `controle/testes.csv` (o que já saiu e como foi).
2. Horários: o workflow do n8n posta às **12h e às 19h** (horário de Brasília), 2 vídeos por dia = 14 por semana.
3. Monte a tabela da semana (dia, horário, número do roteiro, tema, fórmula do gancho) seguindo estas regras:
   - não repetir o mesmo tema (corpo, animais, espaço, história, cotidiano) em dois posts seguidos;
   - não repetir a mesma fórmula de gancho de [docs/ganchos.md](../../../docs/ganchos.md) no mesmo dia;
   - o vídeo com o gancho mais forte vai para as 19h de quinta ou sexta;
   - se o `/revisar-desempenho` mostrou um tema que foi bem, dobre esse tema na semana.
4. Se a ordem ideal for diferente da atual, proponha renomear os arquivos (`003-...` → `005-...`) e **espere o ok** antes de renomear.
5. Diga quantos roteiros faltam para fechar a semana e sugira os temas que faltam (com o ângulo e a fórmula de gancho), para rodar `/escrever-roteiro`.
6. Salve o plano em `controle/agenda.md` (substitua a semana anterior, mantenha o histórico embaixo).
