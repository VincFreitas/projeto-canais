# Como os vídeos curtos ganham alcance (pesquisa de 2026-10-24)

Resumo do que as plataformas dizem oficialmente e do que os guias de criadores repetem, com o que o projeto aplica.
Números de guias de terceiros (ex.: "70% de retenção") não são oficiais: servem de referência, não de meta.

## O que pesa na distribuição

| Plataforma | Sinal | Fonte |
|---|---|---|
| YouTube Shorts | Quantos **escolhem assistir** em vez de passar (viewed vs swiped away) e quanto do vídeo é visto. O Short é testado num público pequeno e ganha ou perde alcance pela resposta | [outlierkit (citando o YouTube)](https://outlierkit.com/resources/youtube-shorts-algorithm/), [vidIQ](https://vidiq.com/blog/post/youtube-shorts-algorithm/) |
| Instagram Reels | **Tempo assistido**, **envios por alcance** (quando alguém manda o Reel por DM, o sinal mais citado para chegar a quem não segue) e curtidas por alcance | [socialpilot](https://www.socialpilot.co/de/blog/instagram-reels-algorithm), [eclincher](https://www.eclincher.com/articles/how-the-instagram-algorithm-works-in-2026) |
| Instagram Reels | Conteúdo **original**: marca d'água de outro app, borda, baixa resolução, vídeo mudo ou só repostado sai da recomendação (Explorar e aba Reels) | [Instagram: diretrizes de conteúdo original](https://creators.instagram.com/original-content-guidelines/), [Instagram: recomendações](https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators) |

## Descrição, hashtags e tags

- **YouTube, hashtags:** precisam ter relação com o vídeo; acima de 60, todas são ignoradas e o vídeo pode sair da busca ([Ajuda do YouTube](https://support.google.com/youtube/answer/6390658)).
- **YouTube, tags:** pesam pouco na descoberta (título, miniatura e descrição pesam mais); ajudam em palavras que as pessoas costumam escrever errado. Encher a descrição de palavras-chave viola as regras de spam ([Ajuda do YouTube](https://support.google.com/youtube/answer/146402)).
- **Instagram, hashtags:** limite de 5 por post desde dezembro de 2025, somando legenda e comentários; funcionam como rótulo de assunto. A busca lê as palavras da legenda, então a palavra-chave entra na frase ([socialk.it](https://socialk.it/de/blog/instagram-hashtag-strategy), [Later](https://later.com/blog/instagram-hashtags/amp)).
- **Instagram, legenda:** aceita 2.200 caracteres, mas o feed corta em ~125, então o gancho vem na 1ª linha.

## O vídeo

- **Gancho em 1 a 2 segundos:** o assunto ou uma pergunta logo na 1ª frase, sem "olá", vinheta ou logo; não entregue a resposta de cara ([JoinBrands](https://joinbrands.com/blog/youtube-shorts-best-practices/), [Subscribr](https://subscribr.ai/youtube-strategy/perfect-youtube-short-length-structure-hooks)).
- **Final que conecta com o começo:** um Short que "fecha o círculo" é revisto, e a revisão conta como tempo assistido.
- **Título:** a palavra principal no começo; o feed do Shorts corta o título por volta de 40 caracteres ([vidIQ](https://vidiq.com/fr/blog/post/youtube-shorts-titles)).
- **Promessa cumprida:** título e capa entregues no vídeo (regra do projeto; clickbait derruba a retenção).

## O que o projeto aplica

- **Descrição e tags pela IA** (`darkops/descricao.py`): 1ª linha de até 125 caracteres com a palavra-chave e o gancho, 2 ou 3 frases, convite para **comentar e mandar para alguém** (envios), fontes; de 3 a 5 hashtags; tags do mais específico ao mais geral, com grafias erradas comuns, até 500 caracteres; nunca lista de palavras-chave.
- **Checagens** (`conferir` e revisão antes de gerar): 1ª frase curta e sem saudação, palavra principal nos 40 primeiros caracteres do título, chamada para comentar ou compartilhar na última cena, até 5 hashtags, 1ª linha da descrição até 125 caracteres, vídeo sem silêncio, sem tela preta e na resolução certa.
- **Originalidade:** só o @ do próprio canal aparece no vídeo; nunca reposte material de outro canal nem use marca d'água de outro app.
