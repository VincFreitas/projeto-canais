---
name: escrever-roteiro
description: Escreve o roteiro JSON de um vídeo dark (longo e verticais derivados) a partir de uma ideia, com fatos checados, gancho, capítulos, buscas visuais e metadados por plataforma. Use quando o usuário quiser transformar uma ideia em roteiro pronto para produzir.
---

# Escrever roteiro

Argumento: a ideia (título ou número da ideia num `analise.md`), duração alvo e idioma, se informados. Argumentos recebidos: $ARGUMENTS

Formato do arquivo: [docs/roteiro.md](../../../docs/roteiro.md). Leia antes de escrever.

## 1. Pesquisar
- Se a ideia veio de um `analise.md`, releia o mecanismo e a transcrição do outlier de origem. Use-os como referência de estrutura e ritmo, **nunca de texto**.
- Levante os fatos com WebSearch/WebFetch. Guarde de 3 a 8 links confiáveis em `fontes`.
- Separe o que é fato comprovado, o que é hipótese e o que é lenda. A narração precisa deixar essa diferença clara.

## 2. Estrutura do longo (padrão: 8 a 12 min, 1.200 a 1.800 palavras, ~150 palavras/min)
1. **Gancho (0 a 15 s)**: a promessa do título + uma pergunta aberta. Nada de "olá, bem-vindos" nem pedido de inscrição.
2. **Contexto rápido (15 a 45 s)**: por que isso importa e o que vem pela frente.
3. **Blocos** (um `capitulo` cada): cada bloco abre um loop e fecha o anterior. A cada 60 a 90 s, uma virada ("mas tem um detalhe que muda tudo").
4. **Clímax**: a melhor informação guardada para o fim.
5. **Fechamento**: resposta honesta à pergunta do gancho + convite para outro vídeo do canal. O CTA fica só aqui.

## 3. Cenas
- 1 a 3 frases por cena (8 a 15 s). Troca de visual frequente segura a retenção.
- Frases curtas, voz ativa, linguagem falada. Escreva números por extenso quando soar melhor ("mil novecentos e setenta" em vez de "1970" se a voz ler errado).
- `visual`: busca em **inglês**, concreta e fotografável (`foggy abandoned asylum hallway`, não `mystery`). Varie entre as cenas.
- `capitulo` na 1ª cena e no início de cada bloco (3 ou mais no total).

## 3b. Gancho, animações e destaques (Shorts e Reels)
- Escolha o gancho em [docs/ganchos.md](../../../docs/ganchos.md). Não repita a fórmula do vídeo anterior da fila.
- Cada cena tem **ou** uma `animacao` (quando a fala traz um número, uma comparação ou uma data) **ou** um `destaque` (de 1 a 3 palavras-chave que aparecem gigantes no segundo em que são faladas).
- `animacao.em`: as palavras faladas que disparam cada elemento, na ordem (ex.: `["dois", "dois", "terceiro"]`). Sem `em`, o código procura os números sozinho.
- `destaque_em`: a palavra falada que dispara o destaque, quando ela é diferente do texto mostrado (ex.: destaque "3 corações", `destaque_em` "três").
- **Estilo pixel art** (padrão do Pulga do Saber): escreva em inglês o `personagem` do roteiro (o protagonista e o cenário, igual em todas as cenas) e a `ilustracao` de cada cena (o que se vê, em uma frase, sem texto na imagem). O pipeline desenha a cena no PC; mantenha `visual` como reserva para a busca.
- Use **só** números que estão na narração. Nada de dado novo só na tela.

## 4. Verticais derivados (2 ou 3)
- Arquivos `roteiros/<slug>-v1.json`, `-v2.json`... com `"formato": "vertical"`, 30 a 60 s (80 a 150 palavras), `velocidade` `+10%`.
- Cada um é um recorte com gancho próprio na 1ª frase (o curiosity gap mais forte do tema), não um resumo do longo.
- Terminar em aberto ou com uma virada, para o público buscar o vídeo longo.

## 5. Metadados
- `youtube`: título de até 60 caracteres, direto, topo de funil. A descrição tem 2 linhas de gancho, um resumo e as fontes. De 5 a 10 tags.
- `thumbnail.texto`: de 2 a 5 palavras que **complementam** o título, sem repeti-lo.
- `tiktok`, `instagram`, `kwai`, `youtube_shorts` nos verticais: legenda curta + 3 a 5 hashtags do nicho.

## 6. Checklist antes de salvar
- [ ] Todo fato tem fonte em `fontes`, e as lendas estão marcadas como lenda
- [ ] O ângulo é diferente do outlier de origem (não é paráfrase)
- [ ] O gancho entrega a promessa do título
- [ ] O JSON é válido (`python -m json.tool roteiros\<arquivo>.json`)

Salve em `roteiros/`, mostre o título, a duração estimada e o gancho, e ofereça rodar `/produzir-video`.
