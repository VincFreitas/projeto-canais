# canais-dark

Infraestrutura de pesquisa e produção de canais dark (vídeos sem rosto) para YouTube, Shorts, TikTok, Reels e Kwai.
Método: oferta e demanda. Achar demanda comprovada, estudar os outliers, extrair o mecanismo, trazer um ângulo novo, testar e multiplicar.

## Fluxo
1. `/pesquisar-nicho <nicho>`: demanda + outliers + transcrições, depois a análise e o banco de ideias em `pesquisa/<nicho>/<data>/analise.md`
2. `/escrever-roteiro <ideia>`: pesquisa os fatos e escreve `roteiros/<slug>-longo.json` + verticais derivados
3. `/produzir-video <roteiro>`: gera o vídeo, a thumbnail e os metadados em `saida/`
4. `/revisar-desempenho`: lê `controle/testes.csv` e decide entre manter, ajustar, dobrar ou abandonar
5. `/titulo-thumb <roteiro>`: 8 títulos com notas, thumbnail e legenda do Instagram (grava só com aprovação)
6. `/planejar-semana`: agenda das 14 postagens (12h e 19h), equilíbrio de temas e ganchos, roteiros que faltam
7. `/responder-comentarios`: lê comentários e rascunha respostas para o usuário aprovar (nunca publica)
- Ganchos: [docs/ganchos.md](docs/ganchos.md) (21 fórmulas). Postagem automática: workflow do n8n em `n8n/pulga-do-saber.json`.

## Comandos (sempre pelo PowerShell, na raiz do projeto)
```
.\dark.ps1 nichos
.\dark.ps1 demanda --nicho misterios            # ou: demanda "termo" --idioma pt
.\dark.ps1 outliers --nicho misterios           # ou: outliers --busca "x" --busca "y" --idioma en
.\dark.ps1 transcrever pesquisa\<nicho>\<data>\outliers.json --top 5
.\dark.ps1 produzir roteiros\<arquivo>.json [outro.json ...]
.\dark.ps1 vozes pt-BR
```
- Rode `produzir` pelo PowerShell, não pelo Bash: o sandbox do Bash às vezes derruba a conexão com o serviço de voz.
- Formato do roteiro: [docs/roteiro.md](docs/roteiro.md).
- Presets de nicho: `config/nichos.json` (idioma + buscas).

## Regras de conteúdo (obrigatórias)
- **Originalidade**: o YouTube desmonetiza conteúdo "inautêntico" (produção em massa, repetitivo, IA sem valor próprio). Todo roteiro precisa de pesquisa própria, estrutura própria e um ângulo que o outlier não cobriu. Nunca reescreva a transcrição de outro canal.
- **Fatos checados**: mistério e curiosidade não autorizam inventar coisas. Confirme cada afirmação com fonte (WebSearch) e guarde os links em `fontes`. Lenda é tratada como lenda ("dizem que", "segundo relatos").
- **Promessa cumprida**: título e thumbnail precisam ser entregues no vídeo; clickbait sem entrega derruba a retenção e pode ser tratado como conteúdo enganoso.
- **Licenças**: só Pexels ou Pixabay (licenças livres), arquivos próprios ou gerados, e música livre (YouTube Audio Library, CC0, CC BY com crédito, ou as trilhas `ambiente`/`animada`). Música só entra no vídeo se estiver em `assets/musica/licencas.csv`; nunca use faixas comerciais (artistas, trilhas de filme, slowed + reverb).
- **Divulgação de IA**: imagem ou vídeo realista gerado por IA exige marcar "conteúdo alterado ou sintético" no YouTube Studio.
- **Publicação**: upload automático é permitido só nos canais oficiais do projeto (Pulga do Saber: YouTube e Instagram @pulgadosaber), pelas APIs oficiais (YouTube Data API, Instagram Graph API), com tokens em segredos e nunca no código. A criação de contas, os logins e as autorizações OAuth continuam com o usuário. Não use contas compradas ("aquecidas").

## Estrutura
- `darkops/`: código (pesquisa.py, narracao.py, visuais.py, render.py, producao.py, __main__.py)
- `pesquisa/`, `roteiros/`, `saida/`: entradas e saídas versionáveis
- `obra/`: intermediários de produção (cache por cena; pode apagar)
- `assets/musica/`: músicas livres; `assets/vozes/`: modelos do Piper
- `controle/testes.csv`: métricas dos vídeos publicados
