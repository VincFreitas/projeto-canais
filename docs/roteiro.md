# Formato do roteiro (JSON)

Um arquivo por vídeo em `roteiros/`. O comando `.\dark.ps1 produzir roteiros\<arquivo>.json` gera:

- `saida/<slug>-<formato>.mp4`
- `saida/<slug>-thumb.jpg` (só no formato longo)
- `saida/<slug>-<formato>-metadados.md` (títulos, descrições, hashtags e capítulos)

```json
{
  "slug": "zona-do-silencio",
  "titulo": "A Zona do Silêncio",
  "idioma": "pt",
  "formato": "longo",
  "motor_voz": "auto",
  "voz": "pt-BR-AntonioNeural",
  "velocidade": "+6%",
  "tipo_visual": "foto",
  "musica": "auto",
  "volume_musica": 0.12,
  "legenda": true,
  "thumbnail": { "texto": "O deserto onde o rádio morre", "arquivo": "imagens/thumb.png" },
  "fontes": ["https://..."],
  "cenas": [
    {
      "capitulo": "O lugar",
      "texto": "Narração da cena. De 1 a 3 frases.",
      "visual": "mexico desert night",
      "arquivo": "imagens/cena01.png",
      "tipo_visual": "video",
      "pausa": 0.35
    }
  ],
  "metadados": {
    "youtube": { "titulo": "...", "descricao": "...", "tags": ["..."] },
    "youtube_shorts": { "titulo": "... #shorts" },
    "tiktok": { "legenda": "...", "hashtags": ["#..."] },
    "instagram": { "legenda": "...", "hashtags": ["#..."] },
    "kwai": { "legenda": "...", "hashtags": ["#..."] }
  }
}
```

| Campo | Obrigatório | O que faz |
|---|---|---|
| `formato` | sim | `longo` (1920x1080) ou `vertical` (1080x1920: Shorts, TikTok, Reels, Kwai) |
| `cenas[].texto` | sim | Narração. Cada cena vira um trecho com um visual; 8 a 15 s por cena mantém o ritmo |
| `cenas[].visual` | não | Busca no Pexels, **em inglês** (ex.: `abandoned hospital corridor`) |
| `cenas[].arquivo` | não | Imagem ou vídeo próprio (caminho relativo ao roteiro). Tem prioridade sobre o Pexels |
| `cenas[].capitulo` | não | Nome do capítulo do YouTube. Precisa de 3 ou mais, e a 1ª cena deve ter um |
| `motor_voz` | não | `auto` (edge e, se falhar, Piper), `edge`, `piper`, `elevenlabs`, `azure`. Padrão: `MOTOR_VOZ` do `.env` |
| `voz` | não | edge/azure: `pt-BR-AntonioNeural`, `pt-BR-FranciscaNeural`... (`.\dark.ps1 vozes pt-BR`); piper: `pt_BR-faber-medium`; elevenlabs: voice_id |
| `velocidade` | não | `+0%` a `+15%` é o comum em canais dark |
| `tipo_visual` | não | `foto` (padrão, com zoom lento), `video` (clipes do Pexels) ou `misto` (alterna clipe e foto) |
| `proporcao_video` | não | Com `misto`: % de cenas com clipe (0 a 100, padrão 50) |
| `musica` | não | `null` = sem música; `ambiente` = trilha de suspense sintetizada; `animada` = trilha alegre sintetizada (tom e andamento variam pelo vídeo); `tema:<pasta>` = sorteia uma faixa de `assets/musica/<pasta>` listada em `assets/musica/licencas.csv` (senão usa `animada`) e põe o crédito CC BY na descrição e na legenda; `auto` = sorteia de `assets/musica/`; ou um caminho |
| `legenda` | não | `true` (padrão). O vertical usa legenda grande palavra a palavra |
| `legenda_fonte` | não | `Arial Black` (padrão), `Impact`, `Segoe UI Black`, `Bahnschrift`, `Verdana`, `Comic Sans MS` |
| `legenda_tamanho` | não | `pequena`, `media` (padrão) ou `grande` |
| `legenda_cor` | não | Cor da palavra falada, `#RRGGBB` (padrão `#FFE500`) |
| `cenas[].movimento` | não | Movimento da foto: `aproxima`, `afasta`, `panoramica_direita`, `panoramica_esquerda` (sem o campo, alterna sozinho) |
| `cenas[].audio` | não | Trecho de narração gravada (caminho relativo ao roteiro). Com ele, a cena usa esse áudio em vez da voz sintética; vem de **Narração pronta** no Estúdio |
| `cenas[].palavras` | não | Com `audio`: lista `{texto, inicio, fim}` (segundos desde o começo da cena) para a legenda sincronizada |
| `cenas[].visual_idioma` | não | Língua da busca de imagem (`en` padrão; `pt` nas buscas montadas de roteiro ou narração prontos) |
| `estilo` | não | Desenho feito no PC a partir de `ilustracao` e `personagem`: `pixel`, `desenho2d`, `pintura`, `foto_antiga`, `anime`, `3d`, `sombrio`, `realista`. `foto_antiga` e `realista` exigem marcar conteúdo sintético |
| `edicao` | não | `simples` (sem elementos na tela), `leve` (palavra-herói e até 2 cards) ou `pro` (tudo; padrão). Vem do perfil |
| `acervo_nasa` | não | `true` usa também o acervo de imagens da NASA (fotos, buscas em inglês) e põe o crédito nos metadados |
| `notas_roteiro` | não | Lista curta com o que o roteiro escolheu e por quê (gancho, ângulo, fontes); aparece na revisão antes de gerar |
| `tema_cards` | não | Tema de edição dos cards de animação: `padrao` (vidro escuro), `arquivo_frio`, `jornal_antigo` ou `moderno_limpo`. Vem do perfil; `animacao.tema` muda só uma cena |
| `sintetico` | não | `true` quando há imagem realista feita por IA (os metadados avisam para marcar no YouTube e no Instagram) |
| `cenas[].variante` | não | Pula as N primeiras opções da busca (o botão **Outra opção** do editor de cenas soma 1) |
| `fontes` | não | Links usados na pesquisa. Não entram no vídeo; servem para checar os fatos |

Ordem de escolha do visual de cada cena: `arquivo` > o que já foi baixado em `obra/` > Pexels (precisa de `PEXELS_API_KEY`) > Pixabay (precisa de `PIXABAY_API_KEY`) > fundo escuro gerado.

Para trocar o visual de uma cena já produzida, use o **editor de cenas** na prévia do Estúdio (outra opção, nova busca, arquivo do PC ou movimento) e gere a prévia de novo. Só as cenas alteradas são refeitas.

Os campos de voz, visual, velocidade e legenda que o roteiro não traz vêm do **padrão do canal** (`perfis/<id>/perfil.json`, aba Perfil do Estúdio).

## Movimento e animações

- `"tipo_visual": "video"` no roteiro: cada cena busca um **clipe de vídeo real** (o Pixabay filtra mídia gerada por IA, desenho e 3D, e exige o assunto nas 3 primeiras tags). Sem clipe bom, usa foto com zoom lento.
- Todas as cenas entram com uma transição curta do preto; no vertical, a legenda "pula" ao aparecer, e o vídeo final ganha a barra de progresso amarela embaixo e o selo `@pulgadosaber` no topo (troque com `"selo"` no roteiro).
- `cenas[].animacao`: a cena vira um infográfico animado (fundo próprio, legenda vai para baixo). Use **só números que estão na narração**.

| Tipo | Campos | Exemplo |
|---|---|---|
| `contador` | `ate`, `de` (0), `casas` (0), `prefixo`, `sufixo`, `rotulo` | `{"tipo": "contador", "ate": 243, "sufixo": " dias", "rotulo": "1 dia em Vênus"}` |
| `comparacao` | `itens` [{`rotulo`, `valor`}] (até 3), `unidade`, `titulo`, `casas` | `{"tipo": "comparacao", "itens": [{"rotulo": "Bebê", "valor": 300}, {"rotulo": "Adulto", "valor": 206}]}` |
| `linha_do_tempo` | `marcos` [{`valor` (ano; a.C. negativo), `texto`, `rotulo`}] (2 a 5) | `{"tipo": "linha_do_tempo", "marcos": [{"valor": -30, "texto": "30 a.C.", "rotulo": "Cleópatra"}, {"valor": 1969, "texto": "1969", "rotulo": "Lua"}]}` |
| `icones` | `simbolo` (`coracao`, `estrela`, `cubo`, `circulo`), `quantidade` (até 12), `cor` [r,g,b], `rotulo` | `{"tipo": "icones", "simbolo": "coracao", "quantidade": 3, "rotulo": "3 corações"}` |
| `barra` | `valor` (0 a 100), `sufixo` (`%`), `titulo`, `rotulo`, `cor` [r,g,b] | `{"tipo": "barra", "valor": 95, "titulo": "Energia da lâmpada", "rotulo": "vira calor"}` |

## Sincronia, destaques e efeitos

- `cenas[].animacao.em`: palavras faladas que disparam cada elemento, na ordem. Sem `em`, o código procura o número de cada barra, o ano de cada marco ou a última palavra do rótulo dos ícones.
- `cenas[].destaque`: de 1 a 3 palavras que aparecem gigantes, com um pulo, no segundo em que são faladas (só em cenas sem animação). `destaque_em`: a palavra falada, se for diferente do texto mostrado.
- Efeitos sonoros sintetizados: whoosh na troca de cena e na entrada do card, pop em cada elemento, ding quando o contador termina e thud na palavra-herói. `"efeitos": false` desliga.
- `"mascote": false` tira a pulga em pixel art do canto; `"selo"` troca o `@pulgadosaber` do topo.

## Layout "post" (estilo post de rede social)

- `"layout": "post"`: o vídeo final continua 1080x1920, mas fica num **fundo branco** com o avatar do canal (a pulga num círculo amarelo), o nome, o @ e a `manchete` em texto, e as cenas passam numa **janela** de 1080x780 no meio (`config.JANELA_POST`), com a barra de progresso embaixo dela.
- `"manchete"`: frase completa de 8 a 14 palavras, que resume o vídeo (as linhas se equilibram sozinhas). Sem ela, usa o `titulo`.
- Nas cenas da janela, a legenda e a palavra-herói usam o estilo grande de Shorts e o card das animações ocupa a janela. O mascote do canto e o selo do topo não aparecem: o avatar faz esse papel.

## Formato explicativo (tela cheia, "você monta")
Roteiro em cadeia problema-solução (veja [ganchos.md](ganchos.md#formato-explicativo-você-monta)), com 75 a 110 s, 12 a 16 cenas de 5 a 8 s e `velocidade` `+15%` (cerca de 180 palavras/min). Exemplo: `roteiros/explicativo-geladeira.json`.

| Campo | Onde | O que faz |
|---|---|---|
| `"layout": "cheio"` | roteiro | Tela cheia 1080x1920, sem a moldura do layout post. No pixel art, o desenho já sai em pé (768x1344) |
| `"legenda_modo": "palavra"` | roteiro | Uma palavra por vez, branca e grande, abaixo do centro. As palavras do `termo` saem na `legenda_cor` (laranja `#FF9F1C` no exemplo) |
| `termo` (`termo_em`) | cena | O nome técnico ("evaporador") aparece no topo, em caixa alta, no segundo em que é falado, e fica até o fim da cena |
| `rotulos` | cena | Etiquetas brancas presas ao objeto: `[{"texto": "gás refrigerante", "x": 0.5, "y": 0.6, "em": "refrigerante"}]`. `x` e `y` vão de 0 a 1 na tela, e `em` é a palavra falada que faz a etiqueta aparecer (sem `em`, vale o texto) |
| `expressao` | cena | Rosto da pulga narradora: `normal`, `feliz`, `surpresa` ou `preocupada` |
| `personagem` | roteiro | No explicativo, descreve o **cenário fixo** (a mesma cozinha, a mesma caixa) para o objeto ir mudando na mesma cena |

- Com `narrador`, o mascote do canto sai sozinho (`"mascote": true` traz de volta) e a pulga desce para o canto de baixo.
- Animação nova, `barra`: `{"tipo": "barra", "valor": 95, "titulo": "Energia da lâmpada", "rotulo": "vira calor"}`. A barra enche até `valor`% no segundo em que o número é falado.

### Cena viva (câmera, partículas e antes/depois)
No pixel art em tela cheia, toda cena desenhada vira uma **cena viva** (`darkops/cinema.py`). Para desligar, use `"cena_viva": false` no roteiro.
- **Câmera**:
  - Entrada com zoom rápido, chicote lateral ou clarão, alternando entre as cenas.
  - Deriva lenta, para a imagem nunca parar.
  - Cortes entre o quadro aberto e closes de 1,5x a 2x.
  - Soco de câmera com tremor no `termo` e na palavra-herói.
- **`focos`** (cena): `[{"x": 0.5, "y": 0.6, "zoom": 2, "em": "palavra"}]` diz onde e quando a câmera faz o close. Sem `focos`, ela escolhe sozinha (etiquetas, depois efeitos, depois o centro).
- **`efeitos`** (cena): partículas em pixel art desenhadas por cima da imagem, sempre em movimento. A `poeira` entra em toda cena.

| Tipo | Campos | Uso |
|---|---|---|
| `fluxo` | `caminho` [[x,y], ...], `cor` | pontos de luz correndo num caminho (corrente, água, gás, tinta) |
| `eletricidade` | `caminho` | faísca em zigue-zague que pisca |
| `vapor`, `bolhas`, `calor`, `faiscas`, `ondas` | `x`, `y`, `raio`, `cor` | sobem, borbulham, tremem, espirram ou se espalham a partir do ponto |
| `frio`, `poeira` | `cor` | cristais caindo ou partículas flutuando na tela toda |
| `brilhos` | `x`, `y`, `raio` | estrelinhas que piscam em volta do objeto |

- **Antes/depois** (cena): `"ilustracao_depois"` (o mesmo objeto depois da mudança, em inglês) e `"depois_em"` (a palavra falada que faz a troca, com clarão e whoosh). A segunda imagem usa a mesma semente, então a composição fica parecida. Cada uma custa mais um desenho, de 2 a 5 min.
- **Etiquetas**: as `rotulos` passam a andar com a câmera, presas ao objeto. Com `"alvo": [x, y]`, a etiqueta ganha uma linha até a peça, com um ponto que pulsa.

## Estilo cartoon

- `"estilo": "cartoon"`: a legenda vai para baixo da imagem, para não cobrir o personagem.
- `"narrador": true`: a pulga mascote (vetorial, `darkops/narrador.py`) aparece no canto de baixo e mexe a boca conforme o volume da narração, pisca e balança as antenas.
- Ilustração de cada cena em `cenas[].arquivo` (ex.: `../midia/<slug>/cena1.png`, relativo à pasta da fila). Para manter o mesmo estilo e personagem, gere a 1ª imagem e use-a como **referência** nas outras, com o mesmo trecho de estilo no prompt: *"Flat 2D cartoon illustration in a clean vector explainer style (Kurzgesagt-inspired): bold simple shapes, soft gradients, vibrant saturated colors, rounded forms, NO text, NO letters, NO watermark"*. Proporção 4:3 para a janela do layout post.
- Cartoon gerado por IA não é "realista", então não precisa da marcação de conteúdo sintético; mesmo assim, cite no roteiro (`"ilustracoes": "IA"`) para controle.

## Estilo pixel art (padrão do Pulga do Saber)
- `"estilo": "pixel"` liga o visual de videogame 16 bits; `"pixel": 5` é o tamanho de cada pixel na tela. O perfil já traz esses valores, então o roteiro não precisa repetir.
- `"personagem"` (no roteiro) e `"ilustracao"` (em cada cena), em inglês: o pipeline desenha a cena no PC com stable-diffusion.cpp + Z-Image-Turbo (de 2 a 5 min por cena, grátis), reduz à grade de pixels e guarda em `obra/`. A mesma semente (o slug) e o mesmo `personagem` mantêm o visual entre as cenas.
- Sem `ilustracao`, ou sem os modelos em `modelos/`, a cena usa a busca normal e o clipe também é pixelado. Com `arquivo`, vale a imagem indicada.
- O render amplia sem suavizar e faz a panorâmica em degraus de pixel, sem zoom. A pulga narradora, o card dos infográficos (com poucas cores) e o avatar da moldura também saem pixelados. A legenda fica embaixo.
- `"musica": "chiptune"` usa a trilha sintetizada com onda quadrada (som de 8 bits); a música licenciada por tema também funciona.
- Instalar o desenho local: baixe para `modelos/` o `sd-cli` Vulkan (github.com/leejet/stable-diffusion.cpp, releases), `z_image_turbo-Q4_K.gguf` (huggingface.co/leejet/Z-Image-Turbo-GGUF), `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) e `ae.safetensors` (huggingface.co/Comfy-Org/z_image_turbo). São cerca de 6,7 GB e rodam numa placa de 4 GB.
