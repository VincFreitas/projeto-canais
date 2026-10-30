# canais-dark

Infraestrutura de pesquisa e produção de canais dark (vídeos sem rosto) para YouTube, Shorts, TikTok, Reels e Kwai.
Método: oferta e demanda. Achar demanda comprovada, estudar os outliers, extrair o mecanismo, trazer um ângulo novo, testar e multiplicar.

## Fluxo
1. `/pesquisar-nicho <nicho>`: demanda + outliers + transcrições, depois a análise e o banco de ideias em `pesquisa/<nicho>/<data>/analise.md`
2. `/escrever-roteiro <ideia>`: pesquisa os fatos e escreve `roteiros/<slug>-longo.json` + verticais derivados
3. `/produzir-video <roteiro>`: gera o vídeo, a thumbnail e os metadados em `saida/`
4. `/revisar-desempenho`: lê `perfis/<perfil>/controle/testes.csv` e decide entre manter, ajustar, dobrar ou abandonar
5. `/titulo-thumb <roteiro>`: 8 títulos com notas, thumbnail e legenda do Instagram (grava só com aprovação)
6. `/planejar-semana`: agenda das 14 postagens (12h e 19h), equilíbrio de temas e ganchos, roteiros que faltam
7. `/responder-comentarios`: lê comentários e rascunha respostas para o usuário aprovar (nunca publica)
8. `/identidade-visual <perfil>`: foto de perfil, capa, marca d'água, bio e descrição das contas; gera, pede aprovação e só então aplica pelo navegador (Estúdio > Identidade para revisar)
- **Estúdio** (`python -m darkops estudio`): enxuto por padrão (Início com aprovação, Novo vídeo em uma linha, Resultados e Ajustes com "Como você quer o canal?"). O resto fica em "Mostrar mais opções" ou no **Modo avançado** (`DARKOPS_AVANCADO=1`, botão no rodapé da lateral): fila, conexões, chaves, histórico, identidade e configurações. Não apague opções: esconda. Ao abrir (atalho, `abrir` ou `estudio`), o Estúdio liga o n8n escondido com `app.ligar_n8n()` (`n8n/n8n.ps1 -NoOpen`, `CREATE_NO_WINDOW`, nunca `DETACHED_PROCESS`). Modo duplo: PC (n8n local 12:00/19:00) e nuvem (`darkops/nuvem.py`, GitHub Actions num repositório PRIVADO de fila, `NUVEM_REPO`/`NUVEM_TOKEN` no `.env`, 12:20/19:20, mesmo workflow do n8n sem produzir). `slots.json` + `estado.json` compartilhados evitam post duplicado; `nuvem-preparar`/`nuvem-devolver` só rodam no Actions; teste da nuvem sempre em simulação (`DARKOPS_SIMULAR=1`). Ajuste do canal pela IA: `ajustar-canal "pedido"` (proposta pendente até aprovar); vídeo com tema: `leva --quantidade 1 --tema "..."`. Comandos da CLI aceitam `--perfil <id>` (padrão `pulga-do-saber`).
- Ganchos: [docs/ganchos.md](docs/ganchos.md) (21 fórmulas). Alcance e viralização: [docs/viralizacao.md](docs/viralizacao.md) (regras aplicadas na descrição, nas tags e nas checagens). Postagem automática: modelo do workflow em `n8n/workflow.modelo.json` (gere com `python -m darkops n8n-workflow --importar`). Instalação do zero: skill `/configurar`, que começa perguntando quais plataformas a pessoa quer testar e segue só os tutoriais delas; confira com `python -m darkops diagnostico` e `python -m darkops progresso` (tela **Progresso da configuração** no Estúdio). Se a pasta ainda não tem `.venv` (repositório recém-clonado), ofereça o `/configurar` antes de qualquer outra coisa.

## Comandos (sempre pelo PowerShell, na raiz do projeto)
```
.\dark.ps1 nichos
.\dark.ps1 demanda --nicho misterios            # ou: demanda "termo" --idioma pt
.\dark.ps1 outliers --nicho misterios           # ou: outliers --busca "x" --busca "y" --idioma en
.\dark.ps1 transcrever pesquisa\<nicho>\<data>\outliers.json --top 5
.\dark.ps1 produzir roteiros\<arquivo>.json [outro.json ...]
.\dark.ps1 vozes pt-BR
.\dark.ps1 referencia <link> [<link> ...]      # mede o estilo de vídeos de referência e propõe o padrão do perfil
.\dark.ps1 conferir saida\<slug>-vertical.mp4  # tela preta, silêncio, volume, duração e resolução do vídeo pronto
.\dark.ps1 descricao perfis\<perfil>\fila\<roteiro>.json [--refazer]  # descrição e tags pela IA (manual ou automático por vídeo)
.\dark.ps1 atualizar [--verificar]                # traz a versão nova do GitHub (o Estúdio aberto reinicia sozinho)
.\dark.ps1 atualizar-dependencias [--aplicar]   # pacotes Python (yt-dlp), n8n e Claude Code
.\dark.ps1 atalhos --area-de-trabalho --menu-iniciar   # atalhos para abrir sem PowerShell
.\dark.ps1 leva --quantidade 7                  # escreve N roteiros com o Claude Code e gera as prévias (--se-faltar --fundo: reabastecimento pelo n8n)
```
- Rode `produzir` pelo PowerShell, não pelo Bash: o sandbox do Bash às vezes derruba a conexão com o serviço de voz.
- Formato do roteiro: [docs/roteiro.md](docs/roteiro.md).
- Presets de nicho: `config/nichos.json` (idioma + buscas).

## Regras de conteúdo (obrigatórias)
- **Originalidade**: o YouTube desmonetiza conteúdo "inautêntico" (produção em massa, repetitivo, IA sem valor próprio). Todo roteiro precisa de pesquisa própria, estrutura própria e um ângulo que o outlier não cobriu. Nunca reescreva a transcrição de outro canal.
- **Fatos checados**: mistério e curiosidade não autorizam inventar coisas. Confirme cada afirmação com fonte (WebSearch) e guarde os links em `fontes`. Lenda é tratada como lenda ("dizem que", "segundo relatos").
- **Promessa cumprida**: título e thumbnail precisam ser entregues no vídeo; clickbait sem entrega derruba a retenção e pode ser tratado como conteúdo enganoso.
- **Licenças**: só Pexels ou Pixabay (licenças livres), o acervo de imagens da NASA (images.nasa.gov, domínio público, com o crédito "NASA" na descrição e sem sugerir apoio da NASA; ligado por perfil em `acervo_nasa`), arquivos próprios ou gerados, e música livre (YouTube Audio Library, CC0, CC BY com crédito, ou as trilhas `ambiente`/`animada`). Música só entra no vídeo se estiver em `assets/musica/licencas.csv`; nunca use faixas comerciais (artistas, trilhas de filme, slowed + reverb).
- **Divulgação de IA**: imagem ou vídeo realista gerado por IA exige marcar "conteúdo alterado ou sintético" no YouTube Studio.
- **Publicação**: upload automático é permitido só nos canais do próprio usuário cadastrados como perfis no Estúdio (hoje: Pulga do Saber, YouTube e Instagram @pulgadosaber), só de vídeos que ele aprovou, pelas APIs oficiais (YouTube Data API, Instagram Graph API), com tokens em segredos e nunca no código. A criação de contas, os logins e as autorizações OAuth continuam com o usuário. Não use contas compradas ("aquecidas").

## Autoria, versão e testadores
- Autor: Vinicius Freitas. Licença PolyForm Noncommercial (`LICENSE`); nunca remova o `LICENSE` nem o crédito do README (o Estúdio confere em `darkops/autoria.py` e avisa "cópia modificada").
- Versão em `darkops/__init__.py` (`__version__`, aparece no Estúdio e em `--version`). Suba a versão a cada entrega que muda o comportamento (correção: 0.9.x; recurso novo: 0.x.0).
- Modo guiado: enquanto `plataformas.pendencias()` não estiver vazia, o Estúdio trava Fila, Novo vídeo e Histórico e mostra o próximo passo em Progresso (`DARKOPS_MODO_GUIADO=0` no `.env` desliga).
- Guia **Estatísticas** (`/p/<perfil>/estatisticas`, `darkops/estatisticas.py` e `darkops/analise.py`): números do canal e de cada vídeo pelas APIs oficiais e análise da IA. Toda sugestão fica pendente até o usuário aprovar; só campos permitidos do perfil mudam, e diretrizes aprovadas (`diretrizes` no perfil) entram no pedido de roteiros. Nunca aplique sugestão sem aprovação.
- Guia **Sobre o projeto** (`/sobre`): apresentação, apoio (estrela, seguir, compartilhar, LinkedIn) e **Enviar sugestão**, que abre uma issue pré-preenchida em VincFreitas/projeto-canais.

## Segurança (obrigatória; detalhes em [docs/seguranca.md](docs/seguranca.md))
- O Estúdio só aceita 127.0.0.1, confere o Host (DNS rebinding) e exige Origin/Referer local em todo POST; não afrouxe isso nem rode o Estúdio fora de 127.0.0.1.
- Chame o Claude Code só por `leva.rodar_claude` (pedido pela entrada padrão, ferramentas listadas). Nunca use `--permission-mode acceptEdits` nem libere Python/Bash genérico para um pedido que lê a internet.
- Toda mensagem que pode conter URL ou erro de API passa por `seguranca.ocultar()` antes de ir para log, tela ou arquivo.
- Nada de token, chave ou senha em código, commit, log ou chat.

## Estrutura
- `darkops/`: código (pesquisa.py, narracao.py, visuais.py, render.py, producao.py, __main__.py)
- `pesquisa/`, `roteiros/`, `saida/`: entradas e saídas versionáveis
- `obra/`: intermediários de produção (cache por cena; pode apagar)
- `assets/musica/`: músicas livres; `assets/vozes/`: modelos do Piper
- `perfis/<id>/`: um canal por perfil: `perfil.json` (nome, @, plataformas, `formato` vertical/longo, `duracao_s`, `video_exemplo`, estilo, postagem ligada), `credenciais/` (tokens, fora do Git), `fila/` (só sai o que tem `"aprovado": true`), `publicados/` e `controle/` (estado.json, testes.csv, falhas.log)
- `darkops/estudio/`: o Estúdio, painel local em Flask (`.\.venv\Scripts\python.exe -m darkops estudio`, em http://127.0.0.1:8765)
