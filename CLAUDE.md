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
- **Estúdio** (`python -m darkops estudio`): perfis, conexões (YouTube por OAuth, token do Instagram), chaves, fila com prévia e aprovação, novo vídeo e histórico. Comandos da CLI aceitam `--perfil <id>` (padrão `pulga-do-saber`).
- Ganchos: [docs/ganchos.md](docs/ganchos.md) (21 fórmulas). Postagem automática: modelo do workflow em `n8n/workflow.modelo.json` (gere com `python -m darkops n8n-workflow --importar`). Instalação do zero: skill `/configurar`, que começa perguntando quais plataformas a pessoa quer testar e segue só os tutoriais delas; confira com `python -m darkops diagnostico` e `python -m darkops progresso` (tela **Progresso da configuração** no Estúdio). Se a pasta ainda não tem `.venv` (repositório recém-clonado), ofereça o `/configurar` antes de qualquer outra coisa.

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
- **Publicação**: upload automático é permitido só nos canais do próprio usuário cadastrados como perfis no Estúdio (hoje: Pulga do Saber, YouTube e Instagram @pulgadosaber), só de vídeos que ele aprovou, pelas APIs oficiais (YouTube Data API, Instagram Graph API), com tokens em segredos e nunca no código. A criação de contas, os logins e as autorizações OAuth continuam com o usuário. Não use contas compradas ("aquecidas").

## Autoria, versão e testadores
- Autor: Vinicius Freitas. Licença PolyForm Noncommercial (`LICENSE`); nunca remova o carimbo, o `LICENSE` nem o crédito do README (o Estúdio confere em `darkops/autoria.py` e avisa "cópia modificada").
- Versão em `darkops/__init__.py` (`__version__`, aparece no Estúdio e em `--version`). Suba a versão a cada entrega que muda o comportamento (correção: 0.9.x; recurso novo: 0.x.0).
- Modo guiado: enquanto `plataformas.pendencias()` não estiver vazia, o Estúdio trava Fila, Novo vídeo e Histórico e mostra o próximo passo em Progresso (`DARKOPS_MODO_GUIADO=0` no `.env` desliga).
- Guia **Sobre o projeto** (`/sobre`): apresentação, apoio (estrela, seguir, compartilhar, LinkedIn) e **Enviar sugestão**, que abre uma issue pré-preenchida em VincFreitas/pulga-do-saber.

## Estrutura
- `darkops/`: código (pesquisa.py, narracao.py, visuais.py, render.py, producao.py, __main__.py)
- `pesquisa/`, `roteiros/`, `saida/`: entradas e saídas versionáveis
- `obra/`: intermediários de produção (cache por cena; pode apagar)
- `assets/musica/`: músicas livres; `assets/vozes/`: modelos do Piper
- `perfis/<id>/`: um canal por perfil: `perfil.json` (nome, @, plataformas, `formato` vertical/longo, `duracao_s`, `video_exemplo`, estilo, postagem ligada), `credenciais/` (tokens, fora do Git), `fila/` (só sai o que tem `"aprovado": true`), `publicados/` e `controle/` (estado.json, testes.csv, falhas.log)
- `darkops/estudio/`: o Estúdio, painel local em Flask (`.\.venv\Scripts\python.exe -m darkops estudio`, em http://127.0.0.1:8765)
