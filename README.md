# canais-dark

Pesquisa e produção de vídeos para canais dark (sem rosto): YouTube longo, Shorts, TikTok, Reels e Kwai.

Método: **oferta e demanda**. Entrar onde já existe demanda comprovada, achar os outliers (vídeos muito acima da média do próprio canal), entender o mecanismo, trazer um ângulo novo, testar e multiplicar o que funcionar.

## Instalar
```powershell
cd C:\Users\Vinic\canais-dark
.\instalar.ps1
```
Depois preencha o `.env` (pelo menos a `PEXELS_API_KEY`, que é grátis, para ter imagens de verdade).

## Usar com o Claude Code (recomendado)
Abra a pasta no Claude Code e use:

| Comando | O que faz |
|---|---|
| `/pesquisar-nicho misterios` | demanda + outliers + transcrições, mecanismos e 20 ideias com ângulo novo |
| `/escrever-roteiro <ideia>` | pesquisa os fatos e escreve o roteiro longo + 2 ou 3 verticais |
| `/produzir-video roteiros\x.json` | narração, visuais, legendas, trilha, thumbnail e metadados |
| `/revisar-desempenho` | lê `controle/testes.csv` e decide entre manter, ajustar, dobrar ou abandonar |

## Usar direto pelo terminal
```powershell
.\dark.ps1 nichos                                   # presets em config\nichos.json
.\dark.ps1 demanda --nicho misterios                # autocomplete do YouTube = o que as pessoas buscam
.\dark.ps1 outliers --nicho misterios               # ranking de outliers (score = views / mediana do canal)
.\dark.ps1 outliers --busca "dark history" --idioma en
.\dark.ps1 transcrever pesquisa\misterios\2026-09-24\outliers.json --top 5
.\dark.ps1 produzir roteiros\exemplo-longo.json roteiros\exemplo-vertical.json
.\dark.ps1 vozes pt-BR
```
A saída fica em `pesquisa\` (CSV abre no Excel) e em `saida\` (vídeo, thumbnail e metadados).

## O que precisa de chave

| Recurso | Sem chave | Com chave |
|---|---|---|
| Pesquisa (outliers, demanda, transcrição) | funciona (yt-dlp) | não precisa |
| Voz | edge-tts (grátis, não oficial, às vezes recusa) e Piper offline como reserva | Azure Speech (grátis até 500 mil caracteres/mês) ou ElevenLabs (pago) |
| Imagens e clipes | fundo escuro gerado (não serve para publicar) ou arquivos próprios | Pexels (grátis) |
| Música | trilha ambiente sintetizada | músicas da YouTube Audio Library em `assets\musica\` |

## Formato do roteiro
Veja [docs/roteiro.md](docs/roteiro.md).

## Regras que evitam desmonetização
- O YouTube corta a monetização de conteúdo **inautêntico ou repetitivo** (produção em massa sem valor próprio). Cada vídeo precisa de pesquisa, estrutura e ângulo próprios.
- Fatos checados e com fonte. Lenda é apresentada como lenda.
- Título e thumbnail precisam ser entregues no vídeo.
- Imagem ou vídeo realista gerado por IA: marque "conteúdo alterado ou sintético" no YouTube Studio.
- Só mídia licenciada (Pexels, própria, gerada, Audio Library).
- Use contas próprias. Conta comprada ("aquecida") viola os termos das plataformas.
- O upload é manual: revise cada vídeo antes de publicar.
