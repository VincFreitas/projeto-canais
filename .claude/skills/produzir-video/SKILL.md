---
name: produzir-video
description: Produz vídeo, thumbnail e metadados a partir de roteiros JSON e confere o resultado quadro a quadro. Use quando o usuário pedir para gerar, renderizar ou refazer um vídeo.
---

# Produzir vídeo

Argumento: um ou mais caminhos de roteiro (ou um slug; procure em `roteiros/`). Argumentos recebidos: $ARGUMENTS

1. Valide o JSON: `.\.venv\Scripts\python.exe -m json.tool <roteiro>`.
2. Produza pelo **PowerShell** (no Bash o serviço de voz pode falhar):
   `.\dark.ps1 produzir roteiros\<a>.json roteiros\<b>.json`
   - Sem `PEXELS_API_KEY` no `.env` e sem `arquivo` nas cenas, o visual sai como fundo escuro. Avise o usuário, porque isso não serve para publicar.
   - Se aparecer "usando Piper (offline)", o edge-tts recusou a conexão. O vídeo sai, mas com uma voz de qualidade menor. Ofereça rodar de novo mais tarde ou usar `motor_voz` `azure`/`elevenlabs`.
3. Confira o resultado:
   - Extraia 3 quadros (início, meio, fim) com o ffmpeg do projeto:
     `$ff = .\.venv\Scripts\python.exe -c "import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())"`
     `& $ff -loglevel error -y -ss 10 -i saida\<video>.mp4 -frames:v 1 -vf scale=960:-1 obra\quadro.jpg`
   - Olhe os quadros: a legenda está legível? O visual combina com a narração? Tem algum quadro preto?
   - Olhe a thumbnail em `saida/<slug>-thumb.jpg`.
4. Para trocar o visual de uma cena, apague `obra/<slug>/<formato>/visuais/NN.*` (ou defina `arquivo` na cena) e rode de novo. Só as cenas alteradas são refeitas.
5. Responda com os caminhos dos arquivos, a duração e o que o usuário precisa revisar antes de publicar (checklist no fim do `-metadados.md`). O upload é feito pelo usuário.
