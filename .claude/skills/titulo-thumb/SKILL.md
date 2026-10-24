---
name: titulo-thumb
description: Gera e testa opções de título, legenda e texto de thumbnail para um roteiro do canal (YouTube Shorts e Instagram Reels), escolhendo a mais forte sem clickbait. Use quando o usuário pedir títulos, thumbnail, legenda ou quiser melhorar o CTR de um vídeo.
---

# Título e thumbnail

Argumento: o roteiro (`perfis/<perfil>/fila/NNN-*.json`) ou o tema. Argumentos recebidos: $ARGUMENTS

1. Leia o roteiro inteiro e ache **a promessa que o vídeo realmente entrega** (o fato mais estranho que aparece na narração).
2. Escreva **8 títulos**, cada um com uma fórmula diferente de [docs/ganchos.md](../../../docs/ganchos.md):
   - até 60 caracteres (Shorts: até 55 para caber o `#shorts`);
   - concreto, com o número ou o objeto do vídeo ("O polvo tem 3 corações", não "Você não vai acreditar");
   - sem mentira e sem exagero que o vídeo não cumpre.
3. Dê nota de 0 a 10 para cada um em: curiosidade, clareza em 1 segundo e fidelidade ao vídeo. Escolha o de maior soma; a fidelidade abaixo de 8 desclassifica.
4. **Thumbnail** (só para vídeos longos): de 2 a 4 palavras que **complementam** o título, sem repetir ("SANGUE AZUL?" para o título do polvo). Sugira a imagem de fundo como busca em inglês para o Pixabay.
5. **Instagram**: legenda de 1 frase com o gancho + "Você sabia?" + chamada para seguir, e até 10 hashtags (3 amplas, 4 do tema, 3 do canal).
6. Mostre a tabela com os 8 títulos e as notas, a escolha e o porquê. Só grave no roteiro (`metadados.youtube_shorts.titulo`, `metadados.instagram`) depois que o usuário aprovar.

## Alcance
Siga [docs/viralizacao.md](../../../docs/viralizacao.md): palavra principal nos 40 primeiros caracteres do título, de 3 a 5 hashtags (o Instagram aceita no máximo 5), 1ª linha da legenda com até ~125 caracteres e sem lista de palavras-chave. A descrição e as tags de cada vídeo ficam em Estúdio > vídeo > Descrição e tags (manual ou pela IA).
