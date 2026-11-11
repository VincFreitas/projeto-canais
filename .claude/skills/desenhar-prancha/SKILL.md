---
name: desenhar-prancha
description: Escreve cenas/<slug>.prancha.json, a animação de um vídeo no motor Prancha de Campo (prancha técnica em traço que se desenha sozinha, sincronizada com a fala). Use depois do roteiro, em canal com "motor_cena": "prancha", ou para refazer a animação de um roteiro existente.
---

# Desenhar prancha

Argumento: o roteiro (`perfis/<perfil>/fila/<arquivo>.json`). Argumentos recebidos: $ARGUMENTS

A prancha é a imagem do vídeo inteiro: fundo grafite, traço verde-água, peças que se desenham, se movem e se explicam
na palavra em que são ditas. Você só escreve JSON: o runtime (`web/prancha/prancha.js`) cuida de moldura, legenda,
cabeçalho, tempo, traço, cor e movimento. Nunca escreva cor, fonte, CSS ou código.

## Passo a passo
1. Leia o roteiro inteiro. Para cada cena escreva `intencao_visual` em uma linha: o que o espectador precisa VER quando
   a frase termina. Mecanismo dito → ele se move. Número dito → aparece num `Contador`/`Ficha`/`Medidor`. Lugar dito → `Mapa`.
2. Liste as peças de que precisa. Use as da biblioteca (`web/prancha/pecas/*.svg`, leia os arquivos para ver pivôs e
   tamanho). Se faltar uma peça importante, desenhe-a em `"pecas"` (seção Peças novas). No máximo 3 peças novas por vídeo.
3. Escreva `cenas/<slug>.prancha.json` (formato abaixo), uma entrada em `cenas` para cada cena do roteiro, na mesma ordem.
4. Teste: `.venv\Scripts\python.exe -m darkops prancha-testar <roteiro.json>`. Ele narra (usa o cache), monta, confere e
   grava a folha de contato. Corrija TODO aviso e todo problema da conferência.
5. Abra a folha (`Read` no caminho impresso) e confira cada quadro contra a `intencao_visual`: o assunto aparece
   grande e reconhecível? A ação dita acontece? Algo cortado, encostado na legenda ou vazio demais? Corrija e teste de
   novo. Até 3 rodadas.

## Tela (1080x1920) e coordenadas
Você desenha no **palco**: 960 x 980 px (x 0–960, y 0–980), que fica entre o cabeçalho e a legenda. A legenda,
o cabeçalho, a barra de capítulos e a ressalva são automáticos e ficam fora do palco.
- O assunto ocupa de 45% a 80% da altura do palco (440 a 780 px) e fica inteiro dentro de x 40–920, y 40–940.
- Pelo menos 40% do palco fica vazio (só o fundo). Um assunto por cena: 1 componente principal e até 2 de apoio.
- Chão: use uma `Linha` horizontal (ex.: `M40,820 L920,820`) e ponha as peças com `base` nela.

## Formato do arquivo
```json
{
  "titulo": "título curto do tema (cabeçalho, até 28 caracteres)",
  "subtitulo": "LUGAR · PR-01",
  "semente": "<slug>",
  "capitulos": [{"nome": "O problema", "de": 0, "ate": 4}, {"nome": "...", "de": 5, "ate": 10}, {"nome": "...", "de": 11, "ate": 15}],
  "pecas": {"nome-da-peca": "<svg ...>...</svg>"},
  "cenas": [
    {"intencao_visual": "...", "halo": "agua", "estado": [{"em": "palavra", "texto": "termo técnico"}],
     "ressalva": "segundo a tradição", "destaque": "palavra", "itens": [{"c": "Peca", "...": "..."}]}
  ]
}
```
- `em`: a palavra da fala da cena em que a coisa acontece (o começo dela). Use a palavra como está no texto (acento não
  importa, basta o começo: "deita" acha "deitada"). `"palavra#2"` = segunda vez; `"palavra+0.4"` = 0,4 s depois;
  número = segundos desde o início da cena. Palavra que não existe na fala vira aviso: corrija.
- `halo`: `agua` (padrão), `ambar` (risco, falha, sol, fogo) ou `osso` (capítulo de prova). A troca marca a troca de assunto.
- `estado`: o termo técnico vai para o campo do cabeçalho, uma vez por termo, nunca repetindo a legenda.
- `ressalva`: só quando a cena é lenda ou hipótese ("segundo a tradição", "segundo a hipótese", "escala exagerada").
- `destaque`: palavra(s) consecutivas da fala que viram ênfase na legenda (ou `null` para nenhuma). Número não vira
  destaque: vira `Contador`.

## Componentes (campo "c")
Coordenadas em px do palco. Todo componente aceita `em`. Os que dizem "id" guardam a peça para `Mover`, `Corda`, `Prumo`...
- `Peca` {peca, id, x (centro), base (y do pé), altura | largura, em, dur, ang, pivo, px, fantasma, cor:"alerta"}:
  coloca e desenha uma peça da biblioteca. `ang`+`pivo` = pose inicial (ex.: deitada); `fantasma: true` = contorno tracejado.
- `Mover` {alvo, passos:[{em, gira (graus, + = horário), pivo, x, y (deslocamento em px), dur, curva, repete, pulso}]}:
  gira em volta de um pivô da peça e/ou desloca. Amplitude legível: pelo menos 8° ou 15% do tamanho.
  Curvas: `entra`, `assenta`, `suave`, `respira`, `linear`, `bate`.
- `Fantasma` {alvo, pivo, de, gira, em, dur}: cópia âmbar tracejada que mostra o que aconteceria (tombar) e some.
- `Prumo` {alvo, apoio:[pivo, pivo], em}: linha do centro de massa (pivô `cm`) até o chão; fica âmbar fora da base.
- `Corda` {de, para, folga, em, tensa, tensa_em, solta_em}: `de`/`para` = [x,y] ou {alvo, ponto: pivô ou [x,y] da peça}.
- `Forca` {de:[x,y] | alvo+ponto, angulo (0 = direita, 90 = baixo), tamanho, cor, rotulo, em}: seta de força.
- `Seta` {d (caminho SVG), em, cor, rotulo}: seta por um caminho.
- `Cota` {de, para, texto, em}: medida com o valor.
- `Linha` {d, classe ("s" osso, "l" verde, "a" âmbar, "d" fina), em, rotulo, rx, ry}: chão, régua, guia.
- `Forma` {x, y, largura, altura | elipse+rx+ry | d, hachura, classe, rotulo, em}: bloco, câmara, corte de terreno.
- `Pessoas` {pose: parado|puxar|segurar, n, x, base, altura, passo, espelhar, id, em}: grupo de figuras de linha
  (`id` + índice: "p0", "p1"... têm o pivô `mao` para a corda).
- `Multidao` {n, area:[x,y,w,h], grupos, raio, cor, em}: pontos que acendem em cascata.
- `Cascata` {peca, n, colunas, x, y, passo_x, passo_y, largura, em}: cópias de uma peça acendendo (ex.: 10 elefantes).
- `Calendario` {n, x, y, lado, em, rotulo}: dias/semanas riscados.
- `Contador` {de, ate, casas, unidade, rotulo, x, y, tam, dur, anel, em}: número que conta até o valor (em algarismos).
- `Medidor` {rotulo, x, y, largura, de, ate, zona:[a,b], valor, unidade, passos:[{em, valor, dur, repete}]}.
- `Ficha` {titulo, x, y, largura, campos:[{rotulo, valor, em}], em}: ficha de dossiê datilografada.
- `Carimbo` {texto, cor: alerta|linha|erro, x, y, em}: só no veredito, até 3 por vídeo.
- `Etiqueta` {texto, ponta:[x,y] | alvo+ponto, x, y, em}: até 2 por cena.
- `Lupa` {alvo, foco (pivô ou [x,y] da peça), raio, zoom, liga_a:[x,y], rotulo, em}: ampliação viva.
- `Destacar` {alvo, parte, em}: acende uma parte (`data-parte`) da peça. `Corte` {alvo, em}: hachura de corte.
- `Mapa` {regiao | paises:[nome em inglês do Natural Earth] + bbox:[lon0,lat0,lon1,lat1], x, y, largura, altura,
  lugares:{nome:[lon,lat]}, pinos:[{lugar, rotulo, em, lado, dy}], rota:{lugares:[...], em, dur, marcador, km},
  rios:[{pontos:[[lon,lat]...], rotulo, em}], escala_km, em}.
- `LinhaDoTempo` {marcos:[{ano (negativo = a.C.), rotulo, em, destaque}], x, y, largura, de, ate, em}.
- `Engrenagens` {trem:[{dentes, raio, x, y, rotulo}], rps, em, para_em}: dentes e razões de verdade.
- `Onda` {origem:[x,y], raio, n, atraso, cor, arco, em}: som, eco, tremor.
- `Feixe` {de, para, largura, alvo_acende:[x,y], em, dur}: luz entrando. `Sol` {arco:[x0,y0,x1,y1,xc,yc], rotulo, em, dur}.
- `Voronoi` {x, y, largura, altura, n, semente, juntas, em}: muro de pedras poligonais encaixadas.
- `TelaDividida` {simbolo, esq:{titulo, cor, itens:[...]}, dir:{...}, em}: comparação; cada lado desenha em x 0–440.
- `Planta` {inclinacao (graus), em, em_sobe, some_em, itens:[...]}: plano visto de cima, deitado em perspectiva.
- `Trajeto` {pontos:[[x,y]...], pegadas, marcador (peça), marcador_altura, balanco, passos, em, dur}: algo andando.
- `Grupo` {entra_em, some_em, itens:[...]}: troca de quadro no meio da cena.
- `Texto` {texto, x, y, classe (rot, rot-linha, num, item), estilo, pulso, em}. Use pouco.
- `Resumo` {x, y, itens:[{texto, em}], risco:{peca, x, base, altura, em}}: fechamento com checks e um item riscado.

## Peças novas (dialeto SVG)
Uma peça é um `<svg>` com `viewBox="0 0 L A"`, `data-pivos="nome:x y;nome:x y"` (inclua `cm` e os cantos da base) e
`data-medidas="altura_m:...;fonte:..."`. Só `path line circle ellipse rect polyline polygon`; nada de `text image
foreignObject script href filter gradient`. Classes: `l` (contorno principal, obrigatório), `d` (detalhe fino), `s` (osso),
`a` (âmbar), `m` (preenchimento leve, um caminho com a silhueta inteira), `sombra` (cavidade escura). `data-ordem="1..n"`
dá a ordem do traço; `data-parte="base"` nomeia partes para `Destacar`. Até 80 elementos, coordenadas com 1 casa.
Vista canônica sempre (frente, perfil, planta ou corte), proporção real (até 15% de diferença), silhueta reconhecível
de longe: o que identifica o objeto (nariz e testa de uma estátua, dentes de engrenagem, degraus de pirâmide) precisa
ser grande e nítido.

## Regras
- A peça entra na palavra em que é dita, não antes. Nenhum trecho de mais de 3,5 s sem algo se mover ou entrar.
  Cena de mais de 4 s tem pelo menos 2 batidas (`em`).
- O objeto principal persiste e se transforma entre cenas (mesma peça, mesma posição de chão); o mapa ou a peça da
  abertura volta no fim para fechar a promessa.
- Texto na tela nunca repete a legenda; número sempre em algarismo com unidade, só os números da fala.
- Fato antes de forma: lenda ou hipótese ganha `ressalva`; reconstituição de pintura ou inscrição é desenho de linha
  próprio, nunca decalque de foto; nada de rosto de pessoa real.
- Proibido: clarão, tremor de tela, poeira na frente do assunto, tela escura vazia, objeto abaixo de 45% da altura
  do palco, coordenada de câmera.
