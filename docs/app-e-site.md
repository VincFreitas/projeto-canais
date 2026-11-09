# Aplicativo e site: o que já está pronto e o que falta

Plano para o Projeto Canais virar **aplicativo** e **site**. Decisão de 2026-11-01: o modelo é **"cada um roda o seu"**.
O site divulga o projeto e leva ao download. O aplicativo roda no PC de cada pessoa e publica só nos canais dela.
Isso mantém as regras do [AGENTS.md](../AGENTS.md): Estúdio só em `127.0.0.1` e publicação só nos canais do próprio usuário.

Um serviço online com várias pessoas (SaaS) **não** faz parte do plano. Ele exige mudar essas regras e passar pela revisão de segurança do fim deste documento.

> Os requisitos das plataformas mudam. Antes de cada pedido de autorização, confira a documentação oficial do link indicado.

## 1. Pronto (v0.31.0)

| Peça | Onde | Observação |
|---|---|---|
| Política de cookies | `site/cookies.html` | Lista o que existe hoje: só o `consentimento-v1`, necessário. |
| Aviso de consentimento | `site/consentimento.js` | Opcionais ficam desligados até a pessoa aceitar. Recusar é tão fácil quanto aceitar. Respeita o Global Privacy Control. O botão "Preferências de cookies" fica no rodapé. Sem cookie opcional, o aviso não aparece. |
| Privacidade com LGPD | `site/privacidade.html` | Direitos do titular (art. 18), base legal, encarregado, ANPD e WhatsApp. |
| Ambientes local e servidor | `darkops/ambiente.py` | `DARKOPS_AMBIENTE=local` (padrão). `servidor` fica preparado (chave fixa, cookie `__Host-` Secure, origens HTTPS), mas **bloqueado** ao abrir. |
| Cookie do Estúdio | `ambiente.config_flask()` | Um só, necessário: sessão `HttpOnly`, `SameSite=Strict`, sem validade (acaba ao fechar). |
| Instalar como aplicativo (PWA) | `/manifest.webmanifest`, `/sw.js`, `static/icone-*.png` | O Estúdio instala como app no PC pelo Chrome ou pelo Edge ("Instalar Projeto Canais"). O service worker só guarda CSS e ícones e mostra "Estúdio fechado" sem conexão. Nunca guarda fila nem aprovação. |
| Instalação por qualquer agente | `AGENTS.md`, `docs/instalacao.md` | Inclui diagnóstico em JSON. |

### Ligar um serviço opcional no site (ex.: medir visitas)
1. Em `site/consentimento.js`, acrescente a categoria em `OPCIONAIS` e troque `CHAVE` para `consentimento-v2`, para que todos escolham de novo.
2. Carregue o script bloqueado: `<script type="text/plain" data-consentimento="analise" src="..."></script>`.
3. Descreva o cookie na tabela de `site/cookies.html` (nome, tipo, finalidade, duração e quem recebe) e atualize a data.
4. Prefira medição sem cookie e sem dado pessoal. Com ela, o item pode nem precisar de consentimento.

## 2. Site público (divulgação e download)
- [ ] **Domínio próprio**, apontado para o GitHub Pages (Settings > Pages > Custom domain) com HTTPS forçado. Verifique o domínio no Google Search Console (exigido pelo Google para apps OAuth verificados) e no Business Manager da Meta.
- [ ] **Página do produto**, (o site atual, em `site/`): o que faz, prints, requisitos (Windows, Python, Claude Code) e botão de download.
- [ ] **Textos legais do produto**: a privacidade e os termos de hoje descrevem uma "ferramenta interna" do canal. Para o produto, reescreva dizendo que **os dados ficam no PC de quem usa**, que o autor não recebe nada e que cada pessoa autoriza as próprias contas.
- [ ] **Licença**: o PolyForm Shield continua valendo (uso comercial liberado, produto concorrente não). Deixe isso claro na página de download.

## 3. Aplicativo para PC (Windows)
- [x] Atalho, abertura animada, sem janelas de prompt e atualização automática pelo GitHub.
- [x] PWA: instalar pelo navegador.
- [ ] **Instalador único** (ex.: Inno Setup ou MSIX) que traz o Python embutido. Sem isso, ainda é preciso ter Python e Git.
- [ ] **Assinatura de código** (certificado Authenticode). Sem ela, o Windows SmartScreen mostra "editor desconhecido".
- [ ] Opcional: publicar na **Microsoft Store**, que pede MSIX e conta de desenvolvedor.

## 4. Aplicativo no celular
**Já pronto (v0.48.1):** o Estúdio se ajusta a qualquer tela, de celular pequeno (320 px) a monitor grande. No celular, a lateral vira uma barra com o botão **Menu**, as abas rolam para o lado, as tabelas rolam dentro do cartão, os campos usam letra de 16 px (o iPhone não dá zoom sozinho) e a página respeita o recorte da tela (`env(safe-area-inset-*)`). Cada mudança de tela é conferida sem barra de rolagem lateral em 320, 375, 768 e 1920 px.

**Ainda falta:** o celular alcançar o Estúdio. O Estúdio só aceita 127.0.0.1, e abrir para a rede está **bloqueado** pelas regras de segurança. O aviso pelo WhatsApp está desligado desde 2026-11-07, por decisão do dono. Caminhos possíveis, do mais simples ao mais trabalhoso, todos pedindo antes a revisão de segurança da seção 7:
- **Rede privada (Tailscale ou WireGuard)**: só os aparelhos do dono entram, sem porta aberta na internet. Pede login no Estúdio e liberar o endereço da rede privada em `ambiente.py`.
- **PWA por túnel com login (ex.: Cloudflare Access)**: abre de qualquer lugar e a porta do PC continua fechada.
- **App na Google Play por TWA (Trusted Web Activity)**: o mesmo PWA dentro de um app de loja, que exige o Estúdio num endereço HTTPS.

## 5. Autorizações das plataformas

### Google (YouTube)
Hoje cada pessoa cria o **próprio** app OAuth ("App para computador"), e por isso nenhuma verificação é necessária. Se o produto passar a usar **um app OAuth do autor** para todos:
- [ ] Tela de consentimento com domínio verificado, privacidade e termos do produto.
- [ ] **Verificação do app OAuth**: `youtube.upload`, `youtube.readonly`, `youtube.force-ssl` (comentários) e `yt-analytics.readonly` são escopos que o Google trata como sensíveis. Pede vídeo de demonstração e justificativa de cada escopo. https://support.google.com/cloud/answer/13463073
- [ ] **YouTube API Services Audit**: sem ela, os vídeos enviados pela API ficam privados. Ela também é o caminho para pedir mais cota. https://support.google.com/youtube/contact/yt_api_form
- [ ] Respeitar a Política de Dados do Usuário (Uso Limitado), já citada na privacidade.

### Meta (Instagram e WhatsApp)
Hoje cada pessoa cria o próprio app, e o token vale só para as contas dela (função de administrador ou testador no app).
- [ ] Para um app do autor servir contas de outras pessoas: **Verificação da Empresa** e **App Review** com **Acesso Avançado** de `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights` e `instagram_business_manage_comments`. https://developers.facebook.com/docs/instagram-platform/app-review
- [ ] WhatsApp em produção (fora do número de teste): número próprio verificado, aprovação do nome de exibição, **modelos de mensagem aprovados** para avisos fora da janela de 24 h e token permanente de usuário do sistema. https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
- [ ] O URL de exclusão de dados e o de política de privacidade do app apontam para o site.

### GitHub (nuvem e passagem do Instagram)
- [x] Token fine-grained por pessoa, só nos repositórios dela.
- [ ] Com muitos usuários, troque o token por um **GitHub App** (permissões por repositório e sem token pessoal).

### Claude Code
- [x] Cada pessoa usa a própria conta. Para o produto, deixe claro nos requisitos que é necessário ter uma conta da Anthropic.

## 6. LGPD (Lei 13.709/2018)
- [x] Política de privacidade com direitos do titular, base legal, encarregado e contato.
- [x] Cookies: só os necessários, e opcionais apenas com consentimento livre, que pode ser revogado.
- [ ] No modelo "cada um roda o seu", o autor não trata dados de usuários. Isso diminui muito as obrigações, mas vale manter escrito na privacidade do produto.
- [ ] Se algum dia houver servidor: registro das operações de tratamento, relatório de impacto (RIPD) quando houver risco, contrato com operadores (hospedagem) e plano de incidente (avisar a ANPD e os titulares, conforme a Resolução CD/ANPD nº 15/2024).

## 7. Revisão de segurança antes de qualquer modo servidor
O modo `servidor` em `darkops/ambiente.py` só pode ser destravado depois que **todos** os itens abaixo estiverem feitos e o dono decidir mudar a regra no AGENTS.md:
- [ ] Login de verdade (OAuth com Google ou senha forte com segundo fator) e sessão por usuário.
- [ ] HTTPS com HSTS, cookie `__Host-` Secure (já preparado) e CSRF por token em todo formulário, além da checagem de origem.
- [ ] Separação por usuário: perfis, fila, credenciais e processos de cada conta isolados.
- [ ] Tokens das plataformas **criptografados** por usuário (chave fora do banco, ex.: KMS), nunca em arquivo aberto.
- [ ] Limite de pedidos, registro de auditoria sem segredos (`seguranca.ocultar`) e backup.
- [ ] O Claude Code e o ffmpeg rodando em sandbox, nunca com acesso ao servidor inteiro.
- [ ] Teste de invasão básico (OWASP Top 10) antes de abrir para outras pessoas.
