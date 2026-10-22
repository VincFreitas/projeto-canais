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
| `tipo_visual` | não | `foto` (padrão, com zoom lento) ou `video` (clipes do Pexels) |
| `musica` | não | `null` = sem música; `ambiente` = trilha de suspense sintetizada; `animada` = trilha alegre sintetizada (tom e andamento variam pelo vídeo); `tema:<pasta>` = sorteia uma faixa de `assets/musica/<pasta>` listada em `assets/musica/licencas.csv` (senão usa `animada`) e põe o crédito CC BY na descrição e na legenda; `auto` = sorteia de `assets/musica/`; ou um caminho |
| `legenda` | não | `true` (padrão). O vertical usa legenda grande palavra a palavra |
| `fontes` | não | Links usados na pesquisa. Não entram no vídeo; servem para checar os fatos |

Ordem de escolha do visual de cada cena: `arquivo` > o que já foi baixado em `obra/` > Pexels (precisa de `PEXELS_API_KEY`) > Pixabay (precisa de `PIXABAY_API_KEY`) > fundo escuro gerado.

Para trocar o visual de uma cena já produzida, apague `obra/<slug>/<formato>/visuais/NN.*` e rode de novo. Só as cenas alteradas são refeitas.

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

## Sincronia, destaques e efeitos

- `cenas[].animacao.em`: palavras faladas que disparam cada elemento, na ordem. Sem `em`, o código procura o número de cada barra, o ano de cada marco ou a última palavra do rótulo dos ícones.
- `cenas[].destaque`: de 1 a 3 palavras que aparecem gigantes, com um pulo, no segundo em que são faladas (só em cenas sem animação). `destaque_em`: a palavra falada, se for diferente do texto mostrado.
- Efeitos sonoros sintetizados: whoosh na troca de cena e na entrada do card, pop em cada elemento, ding quando o contador termina e thud na palavra-herói. `"efeitos": false` desliga.
- `"mascote": false` tira a pulga em pixel art do canto; `"selo"` troca o `@pulgadosaber` do topo.

## Layout "post" (estilo post de rede social)

- `"layout": "post"`: o vídeo final continua 1080x1920, mas fica num **fundo branco** com o avatar do canal (a pulga num círculo amarelo), o nome, o @ e a `manchete` em texto, e as cenas passam numa **janela** de 1080x780 no meio (`config.JANELA_POST`), com a barra de progresso embaixo dela.
- `"manchete"`: frase completa de 8 a 14 palavras, que resume o vídeo (as linhas se equilibram sozinhas). Sem ela, usa o `titulo`.
- Nas cenas da janela, a legenda e a palavra-herói usam o estilo grande de Shorts e o card das animações ocupa a janela. O mascote do canto e o selo do topo não aparecem: o avatar faz esse papel.
