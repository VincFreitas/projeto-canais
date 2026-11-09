# Monetização dos canais (pesquisa de 2026-11-02)

Resumo do que paga em cada plataforma que o projeto usa (YouTube, Instagram) ou vai usar (Facebook, TikTok, Kwai),
e o que o Projeto Canais faz para chegar lá mais rápido. Números de RPM e metas que não vêm da página oficial são
estimativas de guias de terceiros: a palavra final é o painel de cada plataforma (YouTube Studio > Monetização,
Instagram > Painel profissional > Monetização, TikTok > Studio de criação, Kwai > Programa de Criadores).

## A regra que vale para todas: conteúdo original

Desde 2025-07-15 o YouTube chama de **conteúdo inautêntico** o que é produzido em massa, repetitivo ou feito por
modelo sem valor próprio (leitura de texto copiado com voz sintética, slides iguais, compilações sem comentário).
Canal sem rosto e IA são permitidos; o que derruba a monetização é o resultado parecer fábrica. TikTok, Kwai e
Meta seguem a mesma linha ("conteúdo original" é requisito de todos os programas). No projeto isso já é regra
(AGENTS.md: pesquisa própria, fatos com fonte, ângulo novo). Para não parecer fábrica:

- cada vídeo com estrutura e ganchos diferentes (`docs/ganchos.md` tem 21 fórmulas; o `/planejar-semana` equilibra);
- visuais ligados ao assunto do vídeo (imagens geradas da cena, painéis com os dados do caso), não clipes genéricos;
- nada de reaproveitar o mesmo vídeo entre canais do projeto;
- imagem realista de IA sempre marcada como "conteúdo alterado ou sintético" (o upload já marca sozinho quando o
  estilo do canal ou do roteiro é `realista` ou `foto_antiga`) e etiqueta "reconstituição ilustrativa" na tela.

## YouTube (Programa de Parcerias)

- **Nível inicial** (Clubes, Super Thanks, Super Chat): 500 inscritos + 3.000 h em 12 meses **ou** 3 milhões de
  visualizações de Shorts em 90 dias. **Completo** (anúncios): 1.000 inscritos + 4.000 h **ou** 10 milhões de
  Shorts em 90 dias; a partir de 2027-02-01, 8.000 h ou 20 milhões (ver `darkops/monetizacao.py`).
- **Quanto paga:** o criador fica com 45% da receita de anúncios dos Shorts (55% nos vídeos longos). Shorts com
  público brasileiro rendem centavos por mil visualizações; vídeo longo rende de 10 a 50 vezes mais por mil.
- **Caminho mais curto:** os Shorts trazem inscritos; as horas vêm de vídeos longos. 4.000 h são, por exemplo,
  30 mil visualizações de um vídeo de 8 min assistido pela metade. Vídeo com 8 min ou mais aceita anúncio no meio.
- **No projeto:** a tela Resultados > Monetização mostra a barra de inscritos, horas e Shorts de cada canal e qual
  caminho está mais perto. Próximo passo sugerido: um vídeo longo por semana por canal (`formato: longo`), feito a
  partir dos Shorts que mais reteram.

## Instagram

- **Presentes nos Reels:** cerca de 500 seguidores. **Assinaturas:** cerca de 10 mil. **Bônus:** só por convite.
  **Parcerias pagas e Marketplace de criadores:** sem mínimo fixo (marcas procuram nicho e engajamento).
- Brasil está entre os países liberados para Presentes e Assinaturas.
- O Instagram quase não paga por visualização: a receita real vem de marcas e de afiliados.

## Facebook (próximo passo barato)

- O **Content Monetization** (Reels, vídeos e posts) substituiu os programas antigos e é **por convite**, sem número
  mínimo publicado. O convite aparece no Painel profissional da Página.
- Postar os mesmos Reels numa Página do Facebook do canal aumenta a chance do convite sem custo extra de produção.
  O perfil já tem o campo `facebook`; a publicação automática no Facebook ainda não existe no projeto.

## TikTok (futuro)

- **Creator Rewards:** 10 mil seguidores, 100 mil visualizações em 30 dias, 18 anos, conta pessoal, país liberado
  (Brasil está na lista) e **vídeo original com mais de 1 minuto**. Só contam vídeos postados depois de entrar.
- Por isso os canais que vão para o TikTok devem ter vídeos de 61 a 90 s (`duracao_s` no perfil). Um canal de mistérios
  passou para 80 s.
- TikTok Shop afiliados: venda de produtos com comissão; serve mais a canais sobre objetos do dia a dia.

## Kwai (futuro)

- **Programa de Criadores:** os números divergem entre fontes (de 1 mil a 10 mil seguidores e de 1 mil a 100 mil
  visualizações). Conferir no app (Perfil > Programa de Criadores). Paga por Pix ou PayPal.
- Lives liberam com cerca de 100 seguidores; Kwai Shop afiliados com cerca de 1 mil.

## Fontes extras de receita (todas as plataformas)

- **Afiliados:** Amazon Associados e Shopee Afiliados com link na bio e na descrição (livros e documentários sobre
  o caso num canal de mistério; o objeto num canal explicativo). Comissão sem precisar de mínimo de seguidores.
- **Patrocínio:** depois de uns 10 mil seguidores somados, marcas do nicho pagam por menção.
- **Produto próprio:** e-book "50 mistérios" ou coleção de curiosidades, vendido pelo link da bio.

## Plano em ordem (para monetizar o quanto antes)

1. Manter as 2 postagens por dia em todos os canais (consistência pesa no alcance).
2. Canal de mistério com a edição dossiê (`tema_cards: dossie`, `estilo: realista`), 80 s, gancho com título fixo.
3. Ligar a Página do Facebook de cada canal e repostar os Reels (convite do Content Monetization).
4. Assim que um canal passar de 500 seguidores no Instagram, ativar os Presentes; 500 inscritos no YouTube, o nível
   inicial.
5. Começar um vídeo longo por semana no canal que tiver mais retenção nos Shorts (horas para o programa completo).
6. Abrir TikTok e Kwai com os mesmos vídeos de 61 a 90 s (sem marca d'água de outra rede) quando a postagem
   automática dessas redes existir.
7. Links de afiliado na bio e na descrição desde já.

## Fontes consultadas

- YouTube, requisitos: support.google.com/youtube/answer/72851 (conferido em 2026-11-02, ver `monetizacao.py`).
- Conteúdo inautêntico e IA: vidiq.com/blog/post/youtube-reused-content-policy-guide, eweek.com/news/youtube-responds-to-ai-concerns, storyboard18.com (atualização de 2025-07).
- RPM de Shorts: aishortgen.com/blog/youtube-shorts-monetization-ai-content, gyre.pro/blog/the-most-profitable-youtube-shorts-niches-for-beginners.
- TikTok Creator Rewards: onestream.live/blog/what-is-the-tiktok-creator-rewards-program, postlinkapp.com/blog/tiktok-creator-rewards-program.
- Kwai: techtudo.com.br/guia/2025/07/como-ganhar-dinheiro-no-kwai-postando-video-veja-se-e-confiavel-edapps.ghtml, enjai.com.br/blog/como-monetizar-o-kwai.
- Instagram: influencermarketinghub.com/instagram-reels-monetization, identitykit.in/blog/instagram-monetization-2026.
- Facebook: shortsync.app/resources/facebook-content-monetization-program-2026, buffer.com/resources/how-to-make-money-on-facebook.
