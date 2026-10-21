---
name: pesquisar-nicho
description: Pesquisa de oferta e demanda para canal dark. Roda demanda, outliers e transcrições de um nicho, extrai o mecanismo de cada outlier e gera um banco de ideias com ângulo novo. Use quando o usuário quiser escolher nicho, achar ideias ou estudar concorrentes.
---

# Pesquisar nicho

Argumento: nome de um nicho de `config/nichos.json` ou termos livres (e idioma, se não for pt). Argumentos recebidos: $ARGUMENTS

## 1. Coletar (PowerShell, na raiz do projeto)
- Nicho existente: `.\dark.ps1 demanda --nicho <nicho>` e `.\dark.ps1 outliers --nicho <nicho>`
- Termos livres: `.\dark.ps1 demanda "<termo>" --idioma <pt|en|es>` e `.\dark.ps1 outliers --busca "<termo 1>" --busca "<termo 2>" --idioma <idioma>`
- Se o usuário quiser um nicho novo recorrente, adicione um preset em `config/nichos.json` (4 buscas amplas, topo de funil).
- Depois: `.\dark.ps1 transcrever pesquisa\<nicho>\<data>\outliers.json --top 5`

Os outliers levam alguns minutos. Rode em segundo plano se houver outra coisa para fazer.

## 2. Ler
- `outliers.md`: `score` = views ÷ mediana do canal. Acima de 5x é sinal forte; acima de 20x é muito forte. Canal pequeno com outlier grande vale mais que canal grande (a audiência veio de fora da base).
- `views_por_dia` separa tendência atual de sucesso antigo.
- `demanda.md`: sugestões que se repetem em várias expansões são buscas recorrentes.
- `transcricoes/*.txt`: os primeiros 30 segundos mostram o gancho; o resto mostra estrutura e ritmo.

## 3. Escrever `pesquisa/<nicho>/<data>/analise.md`
1. **Veredito do nicho**: a demanda é recorrente? Está concentrada em poucos canais grandes ou há canais pequenos furando? Idioma e CPM esperado (inglês paga bem mais).
2. **Mecanismos** (top 5 a 10 outliers): para cada um, registre
   - objeto/tema (o que a pessoa reconhece na hora)
   - promessa do título e padrão de escrita (número, superlativo, pergunta, "que ninguém explica"...)
   - formato (lista, história única, compilação), duração e ritmo
   - gancho dos primeiros 30 s (da transcrição)
   - por que furou a bolha (hipótese)
3. **Padrões repetidos** entre os outliers e **gaps**: o que a audiência consome e ninguém está entregando com qualidade.
4. **Banco de ideias**: 20 ideias com ângulo novo. Cada ideia mantém um mecanismo comprovado e troca o objeto ou o ângulo. Tabela: título curto (topo de funil, entendido em 1 segundo) | mecanismo de origem (link do outlier) | ângulo novo | formato (longo/vertical) | risco (demanda baixa? repetitiva?).
   - Descarte ideias de fundo de funil ("mistérios do sertão do Piauí") e cópias diretas.
5. **Plano de teste**: as 10 melhores ideias divididas em até 3 posicionamentos de canal.

## 4. Responder
Resuma em até 10 linhas: veredito, 3 mecanismos mais fortes, 5 melhores ideias. Aponte o caminho do `analise.md` e ofereça rodar `/escrever-roteiro` na ideia número 1.
