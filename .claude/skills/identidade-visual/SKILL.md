---
name: identidade-visual
description: Gera e aplica a identidade visual das contas de um perfil (foto de perfil, capa do YouTube, marca d'água, bio do Instagram e descrição do YouTube), sempre depois da aprovação de quem está testando. Use quando o usuário pedir para "deixar as contas prontas", colocar foto, capa, banner, bio ou descrição, ou quando a skill /configurar chegar nessa etapa.
---

# Identidade visual das contas

Argumentos recebidos: $ARGUMENTS (id do perfil; padrão `pulga-do-saber`)

Objetivo: as contas do canal ficam com a mesma cara dos vídeos (pixel art). A aplicação só acontece depois de alguém aprovar. Fale em português, um passo por vez.

**Regras (obrigatórias):**
- **Só aplique o que foi aprovado.** Confira com `identidade estado`: `aprovada` precisa ser `true`. Sem aprovação, mostre a prévia e peça a aprovação no Estúdio (aba **Identidade**) ou no chat. Uma resposta clara no chat ("pode aplicar") vale: registre com `identidade aprovar --por "<nome>"`.
- Login, senha e verificação são **sempre do usuário**. Ele abre o YouTube Studio e o Instagram, logado na conta do canal, no navegador interno. Nunca saia da conta, nunca mude outros campos (nome, @, e-mail, links) e nunca aceite termos.
- Antes de clicar em **Publicar** (YouTube) ou **Enviar** (Instagram), confira que só mudaram os itens aprovados.

Todos os comandos rodam na raiz do projeto, com `$env:PYTHONIOENCODING='utf-8'` no PowerShell:
`.\.venv\Scripts\python.exe -m darkops --perfil <id> identidade <ação>`

## 1. Gerar e mostrar a prévia
1. Se `identidade estado` não tiver `gerada`, rode `identidade gerar`. O fundo da capa é desenhado no PC (cerca de 3 min, com o stable-diffusion.cpp em `modelos/`); sem o gerador, sai um céu pixel.
2. Mostre as artes em `perfis/<id>/marca/` (`capa-youtube.png`, `foto-perfil.png`, `marca-dagua.png`) com SendUserFile e os textos de `textos.json` (`bio_instagram`, até 150 caracteres, e `descricao_youtube`).
3. Peça a aprovação com AskUserQuestion: "Pode aplicar" ou "Quero ajustar". Para ajustar, edite no Estúdio (aba Identidade: textos, título e subtítulo da capa) ou mude `textos.json` e rode `identidade gerar` de novo. Mudar algo **desfaz a aprovação**.

## 2. Preparar o envio
- `identidade pacote` cria `marca/pacote.json` com o base64 das versões leves e o hash de cada pedaço. Ele só funciona com a identidade aprovada.
- Para ver um pedaço: `identidade bloco --arquivo foto|marca|capa --numero N`. O stdout traz o base64 cru e o stderr traz `SHA8 xxxxxxxx`.
- Por que assim: o navegador interno não envia arquivo do disco e a página logada bloqueia o `localhost` (CSP, conteúdo misto, rede privada). Por isso o arquivo é montado **dentro da página**, a partir do base64.

## 3. Levar os arquivos para a página (vale para as duas contas)
Em cada página, defina o ajudante e depois cole os pedaços, um `javascript_tool` por pedaço, **copiando o base64 exatamente**:
```js
window.__b = window.__b || {}; window.__p = window.__p || {};
window.__h = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))].map(x => x.toString(16).padStart(2, '0')).join('');
// para cada pedaço N do arquivo K:
(window.__p['K'] = window.__p['K'] || [])[N] = '<BASE64 DO PEDAÇO>'; (await window.__h(window.__p['K'][N])).slice(0, 8)
```
- O hash que volta precisa ser igual ao `SHA8` do comando `bloco`. Se não for, cole **só aquele pedaço** de novo (copiar base64 à mão erra fácil; confira sempre).
- Ao final, `window.__b.K = window.__p.K.join('')` e confira `(await window.__h(window.__b.K)).slice(0, 12)` contra o `sha12` do `pacote`.
- Para montar o arquivo e entregá-lo ao campo de envio:
```js
window.__arquivo = async (k, nome) => {
  let bytes = Uint8Array.from(atob(window.__b[k]), c => c.charCodeAt(0));
  if (k === 'capa') {  // a capa vai em 640x360 e é ampliada 4x sem suavizar, para 2560x1440
    const img = new Image(); img.src = 'data:image/png;base64,' + window.__b.capa; await img.decode();
    const cv = document.createElement('canvas'); cv.width = 2560; cv.height = 1440;
    const g = cv.getContext('2d'); g.imageSmoothingEnabled = false; g.drawImage(img, 0, 0, 2560, 1440);
    bytes = new Uint8Array(await (await new Promise(r => cv.toBlob(r, 'image/png'))).arrayBuffer());
  }
  return new File([bytes], nome, {type: 'image/png'});
};
window.__enviar = async (input, k, nome) => {
  const dt = new DataTransfer(); dt.items.add(await window.__arquivo(k, nome));
  input.files = dt.files; input.dispatchEvent(new Event('change', {bubbles: true}));
};
```

## 4. YouTube (se o perfil posta no YouTube)
1. Peça ao usuário para abrir, no navegador interno e logado no canal, `https://studio.youtube.com` > **Personalização** > **Perfil**. Antes, chame `tabs_context` e confira que o painel do navegador está visível.
2. A página tem 3 `input[type=file]`, nesta ordem: **banner**, **foto**, **marca d'água**. Envie um de cada vez com `window.__enviar(document.querySelectorAll('input[type=file]')[i], ...)`. Depois de cada envio, abre uma janela de recorte: clique no **Pronto** visível com JS, porque o clique por coordenada falha quando o painel muda de tamanho:
   ```js
   const b = [...document.querySelectorAll('ytcp-button')].find(b => b.innerText.trim() === 'Pronto' && b.getBoundingClientRect().width > 0); (b.querySelector('button') || b).click();
   ```
   Espere a janela fechar antes do próximo envio.
3. Descrição: é um `contenteditable` (`#textbox` com `aria-label` começando por "Fale um pouco"). Não use `ctrl+a`, que seleciona a página toda. Use:
   ```js
   el.focus(); const r = document.createRange(); r.selectNodeContents(el); getSelection().removeAllRanges(); getSelection().addRange(r);
   document.execCommand('insertText', false, '<descricao_youtube>');
   ```
4. Confira os campos (nome e @ iguais ao que eram, descrição nova) e clique em **Publicar** (o mesmo jeito de clicar do Pronto).
5. Recarregue a página e confira que banner, foto e marca d'água mostram **Alterar/Remover** e que a descrição ficou salva. A página pública pode levar alguns minutos para mostrar a capa e a foto.
6. Rode `identidade aplicada --plataforma youtube`.

## 5. Instagram (se o perfil posta no Instagram)
1. O usuário abre `https://www.instagram.com/accounts/edit/`, logado na conta do canal.
2. Foto: o primeiro `input[type=file]` (accept `image/jpeg,image/png`) recebe `window.__enviar(input, 'foto', 'foto-perfil.png')`. O Instagram troca a foto na hora.
3. Bio: clique no campo **Bio**, depois `ctrl+a` (dentro do textarea vale) e digite o texto com `computer type` (as quebras de linha vão com `\n`). Confira com `document.querySelector('textarea').value` e clique em **Enviar**.
4. Abra o perfil (`instagram.com/<arroba>/`) e confira a foto e a bio.
5. Rode `identidade aplicada --plataforma instagram`.

## 6. Fechar
Mostre `identidade estado` e diga, em uma linha por conta, o que foi aplicado e onde conferir. Se algo falhou, diga o que ficou de fora; não marque como aplicada.
