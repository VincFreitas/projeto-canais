---
name: escrever-roteiro
description: Escreve o roteiro JSON de um vídeo dark (longo e verticais derivados) a partir de uma ideia, com fatos checados, gancho, capítulos, buscas visuais e metadados por plataforma. Use quando o usuário quiser transformar uma ideia em roteiro pronto para produzir.
---

# Escrever roteiro

Argumento: a ideia (título ou número da ideia num `analise.md`), duração alvo e idioma, se informados. Argumentos recebidos: $ARGUMENTS

Formato do arquivo: [docs/roteiro.md](../../../docs/roteiro.md). Leia antes de escrever.

Perfil do canal (`perfis/<perfil>/perfil.json`, padrão `pulga-do-saber`): quando o usuário não disser outra coisa, use o `formato` (`vertical` ou `longo`) e a `duracao_s` dele como formato e duração alvo (~150 palavras/min a `+0%`, ~165 a `+10%`). Se houver `video_exemplo`, estude o ritmo, a estrutura e o tom dele (transcreva com `.\dark.ps1 transcrever` se precisar), **nunca o texto**. Use também o `ritmo_corte_s` do perfil: cada cena dura mais ou menos isso (cerca de 2,6 palavras por segundo), e a `velocidade` do perfil. Se existir `perfis/<perfil>/controle/referencias.json` (feito em Aprender com referência), siga as palavras por minuto e o ritmo medidos ali. Voz, visual, legenda e música já vêm do padrão do canal; só ponha esses campos no roteiro quando o vídeo precisar ser diferente.

Personalidade do canal: se o perfil tiver `persona_narrador`, `persona_tom`, `persona_publico`, `persona_abertura`, `persona_linguagem` ou `persona_titulos`, siga cada um em todo o roteiro (quem fala, tom, para quem, como a 1ª frase abre, vocabulário e o padrão de título e de texto da capa).

Nível de edição (`edicao` do perfil): `pro` = ponha `animacao` em toda cena com número, data ou comparação e `destaque` nas outras; `leve` = no máximo 2 `animacao` por vídeo, `destaque` onde ajudar; `simples` = nenhum elemento na tela (sem `animacao`, `destaque`, `termo` ou `rotulos`).

Notas para a revisão: grave em `notas_roteiro` (uma lista curta de frases) o que você escolheu e por quê: a fórmula do gancho, o ângulo que o vídeo traz de novo, de onde vêm os fatos principais e qualquer simplificação feita. O Estúdio mostra isso na revisão antes de gerar.

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
- **Estilos desenhados no PC** (`pixel`, padrão do Pulga do Saber, e também `desenho2d`, `pintura`, `foto_antiga`, `anime`, `3d`, `sombrio`, `realista`): escreva em inglês o `personagem` do roteiro (o protagonista e o cenário, igual em todas as cenas) e a `ilustracao` de cada cena (o que se vê, em uma frase, sem texto na imagem). O pipeline desenha a cena no PC; mantenha `visual` como reserva para a busca.
- Use **só** números que estão na narração. Nada de dado novo só na tela.

## 3c. Formato explicativo ("como funciona", 75 a 110 s)
Quando a ideia é explicar como algo funciona, use o formato explicativo de [docs/ganchos.md](../../../docs/ganchos.md#formato-explicativo-você-monta) e os campos de [docs/roteiro.md](../../../docs/roteiro.md#formato-explicativo-tela-cheia-você-monta). Modelo: `roteiros/explicativo-geladeira.json`.
- Use `"layout": "cheio"`, `"legenda_modo": "palavra"` e `"velocidade": "+15%"`, e escreva de 12 a 16 cenas com 1 ou 2 frases cada (cerca de 280 a 320 palavras).
- Não use o bordão. A 1ª frase já é "Se você [ação simples]...".
- Cada ciclo "Mas... / Então você... / Esse é o [termo]" põe o nome técnico em `termo`. Marque as peças com `rotulos` (2 ou 3 palavras, com `em` na palavra falada).
- Ponha uma `expressao` na pulga quando a fala pedir: `preocupada` no problema, `surpresa` na virada, `feliz` na solução e no fim.
- O `personagem` descreve o cenário fixo, e cada `ilustracao` descreve o mesmo objeto no estado daquele passo.
- O CTA vai só na última frase e é um pedido de comentário com uma palavra ("Comenta GELO se...").
- **Palco (padrão do explicativo)**: escreva também `cenas/<slug>.py`, a cena programada em pixel art ([docs/roteiro.md](../../../docs/roteiro.md#palco-animação-feita-em-código-recomendado-para-o-explicativo)). Use como modelo um dos módulos que já existem em `cenas/` (geladeira, motor e tubos; descarga e panela em corte; elevador e para-raios em cenário). Ponha `"palco": "cenas/<slug>.py"` no roteiro e, em cada cena, `nova_peca`/`nova_em` (uma peça por passo "Então você..."), `acao`/`acao_em` (o que se mexe naquele passo), `foco` e `rotulos` com `peca` ou `ponto`. Toda palavra-gatilho precisa estar na fala da cena. Antes de produzir, chame `desenhar` de cada cena num teste rápido. Sem palco, use a cena viva abaixo.
- **Cena viva** ([docs/roteiro.md](../../../docs/roteiro.md#cena-viva-câmera-partículas-e-antesdepois)): cada cena tem de 1 a 3 `efeitos` ligados à física do passo (`fluxo` para corrente, água ou gás; `calor`, `vapor`, `frio`, `faiscas`, `bolhas`, `ondas`, `eletricidade`; `brilhos` no fim). Ponha `ilustracao_depois` + `depois_em` em 2 ou 3 cenas em que o objeto muda de estado, e `alvo` nas etiquetas que apontam uma peça. Use `focos` quando o close precisar cair numa peça específica.
- Simplificar pode, inventar não: cada passo tem fonte em `fontes`.

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
