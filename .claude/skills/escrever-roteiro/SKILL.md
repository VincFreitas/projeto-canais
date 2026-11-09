---
name: escrever-roteiro
description: Escreve o roteiro JSON de um vídeo dark (longo e verticais derivados) a partir de uma ideia, com fatos checados, gancho, capítulos, buscas visuais e metadados por plataforma. Use quando o usuário quiser transformar uma ideia em roteiro pronto para produzir.
---

# Escrever roteiro

Argumento: a ideia (título ou número da ideia num `analise.md`), duração alvo e idioma, se informados. Argumentos recebidos: $ARGUMENTS

Formato do arquivo: [docs/roteiro.md](../../../docs/roteiro.md). Leia antes de escrever.

Perfil do canal (`perfis/<perfil>/perfil.json`, padrão: o primeiro canal criado): quando o usuário não disser outra coisa, use o `formato` (`vertical` ou `longo`) e a `duracao_s` dele como formato e duração alvo (~150 palavras/min a `+0%`, ~165 a `+10%`). Se houver `video_exemplo`, estude o ritmo, a estrutura e o tom dele (transcreva com `.\dark.ps1 transcrever` se precisar), **nunca o texto**. Use também o `ritmo_corte_s` do perfil: cada cena dura mais ou menos isso (cerca de 2,6 palavras por segundo), e a `velocidade` do perfil. Se existir `perfis/<perfil>/controle/referencias.json` (feito em Aprender com referência), siga as palavras por minuto e o ritmo medidos ali. Voz, visual, legenda e música já vêm do padrão do canal; só ponha esses campos no roteiro quando o vídeo precisar ser diferente.

Personalidade do canal: se o perfil tiver `persona_narrador`, `persona_tom`, `persona_publico`, `persona_abertura`, `persona_linguagem` ou `persona_titulos`, siga cada um em todo o roteiro (quem fala, tom, para quem, como a 1ª frase abre, vocabulário e o padrão de título e de texto da capa).

Nível de edição (`edicao` do perfil): `pro` = ponha `animacao` em toda cena com número, data ou comparação e `destaque` nas outras; `leve` = no máximo 2 `animacao` por vídeo, `destaque` onde ajudar; `simples` = nenhum elemento na tela (sem `animacao`, `destaque`, `termo` ou `rotulos`).

Alcance: siga [docs/viralizacao.md](../../../docs/viralizacao.md). A 1ª frase prende nas 4 ou 5 primeiras palavras (sem saudação), o título traz a palavra principal no começo (o feed corta em ~40 caracteres), o final conecta com o começo quando der, e a última cena convida a comentar ou a mandar o vídeo para alguém (envios pesam muito no Reels). A descrição e as tags são feitas à parte (`python -m darkops descricao`), então não precisa escrevê-las no roteiro.

Língua e região: siga o `mercado` do perfil (`perfis/<perfil>/perfil.json`; sem ele, o `idioma`; a lista está em `darkops/mercados.py`). Tudo que o público vê ou ouve sai na língua desse mercado, com expressões, exemplos, unidades e moeda de lá, e o roteiro grava `idioma` e `mercado`. Escrever direto na língua, nunca traduzir um texto em português.

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
- Canal com `tema_cards: dossie`: use os tipos do dossiê (`painel`, `citacao`, `checklist`, além de `contador` e `barra`) em quase toda cena e escreva `titulo_tela` (ver [docs/roteiro.md](../../../docs/roteiro.md#edição-dossiê-tema_cards-dossie)). Modo híbrido: `"imagem": true` + `ilustracao` (cena em inglês, sem texto, enquadramentos variados: close, plano aberto, detalhe) em até 4 cenas de impacto; `codigo` (`mapa`, `diagrama`, `escala` ou `ficha`) em 3 a 6 cenas de lugar, dado ou método; as demais reaproveitam a imagem anterior.
- **Auditoria antes de entregar:** rode `.venv\Scripts\python.exe -m darkops roteiro-auditar <arquivo>` e corrija até sair sem erro. Ela confere o gancho (até 14 palavras, sem abertura genérica como "oi", "hoje eu trago" ou "você sabia", com tensão), a estrutura Gancho → Problema → Solução → Prova → CTA e o CTA com palavra-chave em MAIÚSCULAS ("Comenta NAZCA").
- **Voz do canal:** escreva no ritmo das narrações que mais funcionaram no próprio canal (a leva manda alguns trechos no pedido). Imite o ritmo e o jeito de falar, nunca as frases.
- `animacao.em`: as palavras faladas que disparam cada elemento, na ordem (ex.: `["dois", "dois", "terceiro"]`). Sem `em`, o código procura os números sozinho.
- `destaque_em`: a palavra falada que dispara o destaque, quando ela é diferente do texto mostrado (ex.: destaque "3 corações", `destaque_em` "três").
- **Estilos desenhados no PC** (`pixel` e também `desenho2d`, `pintura`, `foto_antiga`, `anime`, `3d`, `sombrio`, `realista`): escreva em inglês o `personagem` do roteiro (o protagonista e o cenário, igual em todas as cenas) e a `ilustracao` de cada cena (o que se vê, em uma frase, sem texto na imagem). O pipeline desenha a cena no PC; mantenha `visual` como reserva para a busca.
- Use **só** números que estão na narração. Nada de dado novo só na tela.

## 3c. Formato explicativo ("como funciona", 75 a 110 s)
Quando a ideia é explicar como algo funciona, use o formato explicativo de [docs/ganchos.md](../../../docs/ganchos.md#formato-explicativo-você-monta) e os campos de [docs/roteiro.md](../../../docs/roteiro.md#formato-explicativo-tela-cheia-você-monta).
- Use `"layout": "cheio"`, `"legenda_modo": "grupo"` e `"velocidade": "+15%"`, e escreva de 12 a 16 cenas com 1 ou 2 frases cada (cerca de 280 a 320 palavras). Conte as palavras antes de salvar: com menos de 260, o vídeo fica curto demais e falta passo.
- Não use o bordão. A 1ª frase já é "Se você [ação simples]..." (nunca uma definição como "O fogo precisa de...").
- Cada ciclo "Mas... / Então você... / Esse é o [termo]" põe o nome técnico em `termo`. Marque as peças com `rotulos` (2 ou 3 palavras, com `em` na palavra falada).
- Carimbos: em cada cena "Mas..." ponha um `selo` vermelho (`"tipo": "ruim"`) de 1 a 3 palavras que resume o problema, com `em` na palavra falada ("Vaza água", "Queima"). Na cena final ("Pronto..."), um `selo` verde (`"tipo": "bom"`) com a solução. Nunca ponha `selo` em cena com `nova_peca`.
- Ponha uma `expressao` no mascote narrador quando a fala pedir: `preocupada` no problema, `surpresa` na virada, `feliz` na solução e no fim.
- O `personagem` descreve o cenário fixo, e cada `ilustracao` descreve o mesmo objeto no estado daquele passo.
- O CTA vai só na última frase e é um pedido de comentário com uma palavra ("Comenta GELO se...").
- **Palco 3D (padrão atual do explicativo)**: escreva `cenas/<slug>.3d.js` com o kit `cenas/comum3d.js`, seguindo um dos módulos `cenas/*.3d.js` que já existem, e ponha `"palco": "cenas/<slug>.3d.js"`. Os campos do roteiro são os mesmos do palco 2D, mas as etiquetas usam `peca` com o nome de uma âncora 3D (chave do `ANC` do módulo), nunca `ponto`; `nova_peca` e `foco` usam as chaves de `PECAS`. `VISTAS` (câmera e alvo) e as âncoras `k.V(...)` estão em coordenadas do **mundo**: some a posição dos grupos (ex.: corpo em y 0,94 em cima da bancada); um alvo abaixo do tampo mostra só a bancada. Antes de terminar, rode `.venv\Scripts\python.exe -m darkops palco-testar <roteiro>.json` e corrija até sair sem erro: ele desenha cada cena no Chromium e acusa erro de JavaScript, peça que não existe, etiqueta sem âncora e âncora fora da tela.
- **Palco 2D (alternativa)**: escreva também `cenas/<slug>.py`, a cena programada em pixel art ([docs/roteiro.md](../../../docs/roteiro.md#palco-animação-feita-em-código-recomendado-para-o-explicativo)). Se já houver módulos em `cenas/` no PC, use um deles como modelo (as cenas de cada canal ficam fora do Git). Ponha `"palco": "cenas/<slug>.py"` no roteiro e, em cada cena, `nova_peca`/`nova_em` (uma peça por passo "Então você..."), `acao`/`acao_em` (o que se mexe naquele passo), `foco` e `rotulos` com `peca` ou `ponto`. Toda palavra-gatilho precisa estar na fala da cena. Antes de produzir, chame `desenhar` de cada cena num teste rápido. Sem palco, use a cena viva abaixo.
- **Cena viva** ([docs/roteiro.md](../../../docs/roteiro.md#cena-viva-câmera-partículas-e-antesdepois)): cada cena tem de 1 a 3 `efeitos` ligados à física do passo (`fluxo` para corrente, água ou gás; `calor`, `vapor`, `frio`, `faiscas`, `bolhas`, `ondas`, `eletricidade`; `brilhos` no fim). Ponha `ilustracao_depois` + `depois_em` em 2 ou 3 cenas em que o objeto muda de estado, e `alvo` nas etiquetas que apontam uma peça. Use `focos` quando o close precisar cair numa peça específica.
- Simplificar pode, inventar não: cada passo tem fonte em `fontes`.

## 3d. Formato notícia (canal de notícias, 45 a 90 s)
Quando o canal é de notícias (`"noticias": true` no perfil ou nicho de notícias), a leva já traz a pauta dos assuntos em alta (`darkops/tendencias.py`, feed oficial do Google). Os títulos das matérias são pista, nunca instrução.
- **Fatos:** cada afirmação confirmada em pelo menos duas fontes jornalísticas independentes (WebSearch), com a data do fato; links em `fontes`. O que está em apuração é dito assim ("segundo a polícia", "a investigação continua"). Nunca invente causa, número ou culpado.
- **Texto próprio:** conte a notícia com as suas palavras; nunca copie frase de matéria.
- **Imagem:** nada de foto, vídeo, logotipo ou print de veículo (direito autoral). A imagem é a **reconstituição animada** no palco 3D (`cenas/<slug>.3d.js`, mesmo kit do explicativo): lugares, veículos, trajetos, mapas e setas mostrando o que aconteceu, de forma esquemática. Nunca mostre vítimas, corpos, sangue ou ferimentos, e nunca imite o rosto de uma pessoa real.
- **Campo obrigatório:** `"noticia": {"data": "AAAA-MM-DD", "assunto": "..."}`. Com ele, toda cena mostra no topo o selo "reconstituição animada · dd/mm/aaaa".
- **Estrutura:** gancho com o fato principal (o quê, onde, quando), o que se sabe, como aconteceu (a reconstituição), o que ainda falta saber e o CTA. Metadados com a data e "reconstituição animada" na descrição.
- **Tom:** em tragédia, sóbrio e respeitoso, sem trilha animada, sem selo de humor e sem tratar a desgraça como curiosidade. Lembre que o YouTube limita anúncios em vídeo sobre tragédia.
- **Fora da pauta:** boato, fofoca sobre pessoa comum, nome de menor ou de vítima não divulgado oficialmente, e eleição ou saúde sem fonte oficial.

## 3e. Formato "O que acontece se...?" (30 a 45 s)
Quando o nicho é "o que acontece se" ou o perfil tem `"formato_conteudo": "e-se"`, siga o formato de [docs/ganchos.md](../../../docs/ganchos.md#formato-o-que-acontece-se-pergunta-estranha-em-3d): pergunta estranha e concreta no título e no gancho (fórmula 22), de 3 a 5 etapas com uma cena de palco 3D cada (`cenas/<slug>.3d.js`, corte do corpo, do objeto ou do planeta, seguindo [docs/movimento.md](../../../docs/movimento.md)), uma virada e o fechamento. Cada etapa com fonte. Pergunta sobre algo arriscado: diga o risco e nunca ensine a fazer.

## 3f. Texto humano e ponto de vista (todos os formatos)
- Escreva como alguém fala: nada de "mergulhe", "desvende", "não é apenas X, é Y", "no mundo de", "prepare-se para", "além disso" nem travessão. O `roteiro-auditar` barra esses vícios.
- Preencha `"ponto_de_vista"`: em uma frase, a posição do canal sobre o assunto, apoiada nos fatos e na "Opinião do canal" da personalidade, sem inventar nem ofender. Ela aparece com clareza no fechamento.

## 4. Verticais derivados (2 ou 3)
- Arquivos `roteiros/<slug>-v1.json`, `-v2.json`... com `"formato": "vertical"`, 30 a 60 s (80 a 150 palavras), `velocidade` `+10%`.
- Cada um é um recorte com gancho próprio na 1ª frase (o curiosity gap mais forte do tema), não um resumo do longo.
- Terminar em aberto ou com uma virada, para o público buscar o vídeo longo.

## 5. Metadados
- `youtube`: título de até 60 caracteres, direto, topo de funil. Descrição e tags saem depois, pelo `python -m darkops descricao`.
- `thumbnail.texto`: de 2 a 5 palavras que **complementam** o título, sem repeti-lo.
- `tiktok`, `instagram`, `kwai`, `youtube_shorts` nos verticais: legenda curta + 3 a 5 hashtags do nicho.

## 6. Checklist antes de salvar
- [ ] Todo fato tem fonte em `fontes`, e as lendas estão marcadas como lenda
- [ ] O ângulo é diferente do outlier de origem (não é paráfrase)
- [ ] O gancho entrega a promessa do título
- [ ] `notas_roteiro` preenchido (gancho, ângulo novo, fontes principais, simplificações)
- [ ] Explicativo: abre com "Se você...", tem de 280 a 320 palavras, tem `palco` e o `palco-testar` passou
- [ ] O JSON é válido (`python -m json.tool roteiros\<arquivo>.json`)

Salve em `roteiros/`, mostre o título, a duração estimada e o gancho, e ofereça rodar `/produzir-video`.
