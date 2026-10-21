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
| `musica` | não | `null` = sem música; `ambiente` = trilha sintetizada; `auto` = sorteia de `assets/musica/`; ou um caminho |
| `legenda` | não | `true` (padrão). O vertical usa legenda grande palavra a palavra |
| `fontes` | não | Links usados na pesquisa. Não entram no vídeo; servem para checar os fatos |

Ordem de escolha do visual de cada cena: `arquivo` > o que já foi baixado em `obra/` > Pexels (precisa de `PEXELS_API_KEY`) > Pixabay (precisa de `PIXABAY_API_KEY`) > fundo escuro gerado.

Para trocar o visual de uma cena já produzida, apague `obra/<slug>/<formato>/visuais/NN.*` e rode de novo. Só as cenas alteradas são refeitas.
