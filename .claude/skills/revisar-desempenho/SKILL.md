---
name: revisar-desempenho
description: Analisa as métricas dos vídeos publicados em perfis/<perfil>/controle/testes.csv, diagnostica flops e decide entre manter, ajustar, dobrar ou abandonar cada linha de conteúdo. Use quando o usuário trouxer números do YouTube Studio, TikTok ou Instagram.
---

# Revisar desempenho

Argumentos recebidos: $ARGUMENTS

1. Se o usuário colou números no chat, acrescente as linhas em `perfis/<perfil>/controle/testes.csv` (colunas no cabeçalho do arquivo; datas no formato AAAA-MM-DD, separador `;`).
2. Para cada vídeo com 48 h ou mais, compare com os outros do mesmo canal e com o outlier de origem.
3. Diagnóstico de flop, na ordem:
   1. **Demanda**: o tema tinha busca e interesse (veja o `demanda.md` e os outliers do nicho)?
   2. **Motivo para clicar**: impressões altas e CTR baixo (abaixo de 4% no longo) indicam problema de título ou thumbnail.
   3. **Ideia nova**: o ângulo era diferente do que já existe? É "80% do jogo".
   4. **Entrega**: retenção caindo antes de 30 s indica gancho fraco ou promessa não cumprida.
   5. **Contexto do canal**: o vídeo conversa com o público que o canal já tem?
4. Decisão por linha de conteúdo:
   - **dobrar**: produza 3 a 5 variações do mecanismo que funcionou
   - **manter**: siga no ritmo atual
   - **ajustar**: diga o que muda (título, gancho, ângulo, duração)
   - **abandonar**: explique o motivo
5. Registre a decisão na coluna `decisao` e responda com uma tabela curta + os próximos 3 roteiros sugeridos.
