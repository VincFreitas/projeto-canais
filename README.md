# Estúdio de Canais (canais-dark)

Fábrica de canais "dark" (sem rosto) que **roda sozinha**: pesquisa temas que já dão certo, escreve roteiros com fatos checados, gera Shorts e Reels com narração, legendas, clipes reais, animações sincronizadas com a fala, efeitos sonoros e música livre, e **posta no YouTube e no Instagram nos horários marcados**, só o que você aprovou.

Tudo se controla pelo **Estúdio**, um painel no navegador com perfis (um por canal), conexões explicadas por função, fila com prévia e aprovação, editor e histórico.

## Começar em 3 passos (com o Claude Code)

1. Instale o [Claude Code](https://claude.com/claude-code) e o [Python 3.11+](https://www.python.org/downloads/) (marque "Add to PATH").
2. Clone e abra a pasta no Claude Code:
   ```
   git clone https://github.com/VincFreitas/pulga-do-saber.git canais-dark
   cd canais-dark
   claude
   ```
3. Cole este prompt:
   > **Configure este projeto para mim do zero com a skill /configurar. Vá passo a passo, me explique cada conta que eu preciso criar e confira tudo com o diagnóstico no final.**

O Claude instala as dependências, abre o Estúdio e te guia pelas contas (Azure, Pixabay, Google Cloud, Meta e n8n). Logins, senhas e aceites de termos ficam sempre com você.

## Sem o Claude (manual)

```powershell
powershell -ExecutionPolicy Bypass -File instalar.ps1     # dependências, voz offline e .env
.\.venv\Scripts\python.exe -m darkops estudio            # abre o painel em http://127.0.0.1:8765
.\.venv\Scripts\python.exe -m darkops diagnostico        # o que falta configurar
```
O passo a passo completo de cada conta está em [.claude/skills/configurar/SKILL.md](.claude/skills/configurar/SKILL.md).

## Como funciona

| Etapa | Onde |
|---|---|
| Achar temas que bombaram no nicho | `/pesquisar-nicho <nicho>` (Claude Code) |
| Escrever o roteiro com fontes, ganchos e animações | `/escrever-roteiro <ideia>`, banco de ganchos em [docs/ganchos.md](docs/ganchos.md) |
| Gerar a prévia, assistir e aprovar | Estúdio > Fila |
| Postar às 12h e às 19h | n8n (workflow gerado por `python -m darkops n8n-workflow --importar`) |
| Títulos, agenda da semana, comentários | `/titulo-thumb`, `/planejar-semana`, `/responder-comentarios` |
| Medir e decidir | `/revisar-desempenho` |

## Conectores

| Função | Conectores | Custo |
|---|---|---|
| Publicação | YouTube Shorts (OAuth), Instagram Reels (token) · TikTok e Facebook em breve | Grátis |
| Voz | Azure Speech (principal), Edge, Piper offline, ElevenLabs | Grátis no F0 do Azure |
| Imagens e vídeos | Pixabay, Pexels, arquivos próprios (sem mídia de IA, desenho ou 3D) | Grátis |
| Música | Trilhas geradas pelo código, biblioteca própria com licença registrada | Grátis |
| Roteiros e pesquisa | Claude Code, yt-dlp | Conforme o seu plano |
| Automação | n8n local | Grátis |

## Estrutura

- `darkops/`: o código (CLI `python -m darkops`, com `--perfil <id>` em qualquer comando)
- `darkops/estudio/`: o painel (Flask, só em 127.0.0.1)
- `perfis/<id>/`: um canal por perfil (configuração, fila, publicados, controle; credenciais ficam fora do Git). Ao criar o perfil no Estúdio, escolha as plataformas (YouTube, Instagram, Facebook, TikTok, Kwai ou outra), o formato (Shorts/Reels vertical ou vídeo convencional 16:9), a duração de cada vídeo e um link de vídeo de exemplo. Só YouTube e Instagram postam sozinhos.
- `n8n/`: modelo do workflow e lançadores
- `site/`: páginas de privacidade e termos exigidas pelo Google e pela Meta (GitHub Pages)
- `docs/`: formato do roteiro e banco de ganchos

## Regras que mantêm o canal vivo

- Conteúdo com pesquisa e ângulo próprios: o YouTube desmonetiza produção em massa sem valor ("inautêntico").
- Fatos com fonte; lenda tratada como lenda; título e manchete entregues no vídeo.
- Só mídia e música com licença livre; mídia realista gerada por IA exige marcar "conteúdo sintético".
- Contas próprias (nada de contas compradas) e postagem só do que foi aprovado.
- Sem a auditoria do Google, o YouTube deixa os vídeos enviados pela API como privados.
