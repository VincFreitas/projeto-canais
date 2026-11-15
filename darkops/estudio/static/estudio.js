// SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
// Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
/* Comportamentos das telas do Estúdio sem JavaScript dentro do HTML.

A CSP do Estúdio não aceita onclick="...", onchange="..." nem javascript: (revisão de segurança de 2026-11-15): um
link ou texto malicioso que chegasse a uma tela não consegue rodar script. Cada elemento diz o que quer por data-* e
este arquivo liga os eventos. As funções próprias de uma tela continuam no <script nonce> dela.

  data-pergunta="texto"        confirma antes de enviar (form) ou de clicar (botão)
  data-enviando="texto"        troca o texto do botão quando o form é enviado
  data-ao-clicar="funcao"      chama funcao(elemento, data-arg); se ela devolver false, o clique não segue
  data-ao-mudar="funcao"       chama funcao(elemento) no change; data-ao-mudar-form="funcao" chama funcao(form)
  data-ao-digitar-form="f"     chama f(form) a cada tecla
  data-mostra="#id" data-quando="valor"   mostra o elemento #id só quando o campo vale "valor"
  data-enviar-ao-mudar         envia o form quando o campo muda (escolher arquivo)
  data-enviar-ao-colar[="campo"]          envia o form ao colar (e só se o outro campo também estiver preenchido)
  data-mostra-valor            mostra o valor do controle deslizante no <output> do rótulo de cima
  data-contador="max"          mostra "n / max" no elemento seguinte
  data-confere-nome            libera o botão [data-confirmar] do form só com o nome do canal digitado
  data-copiar-de="#id"         copia o valor do campo #id
  data-abrir-dialogo="#id"     abre o <dialog> #id; data-fechar-dialogo fecha o diálogo em volta
  data-menu                    abre e fecha a lateral no celular
  data-previa-hover            vídeo toca com o mouse em cima
  data-sem-previa              imagem que não carrega vira "sem prévia"
*/
(function () {
  const chamar = (nome, ...args) => (typeof window[nome] === 'function' ? window[nome](...args) : undefined);

  document.addEventListener('click', e => {
    const el = e.target.closest('[data-pergunta]:not(form), [data-ao-clicar], [data-copiar-de], [data-abrir-dialogo], '
                                + '[data-fechar-dialogo], [data-menu]');
    if (!el) return;
    if (el.matches('[data-pergunta]:not(form)') && !confirm(el.dataset.pergunta)) { e.preventDefault(); return; }
    if (el.dataset.aoClicar && chamar(el.dataset.aoClicar, el, el.dataset.arg) === false) { e.preventDefault(); return; }
    if (el.dataset.copiarDe) {
      const origem = document.querySelector(el.dataset.copiarDe);
      if (origem) navigator.clipboard.writeText(origem.value ?? origem.textContent).then(() => { el.textContent = 'Copiado'; });
    }
    if (el.dataset.abrirDialogo) document.querySelector(el.dataset.abrirDialogo)?.showModal();
    if (el.hasAttribute('data-fechar-dialogo')) el.closest('dialog')?.close();
    if (el.hasAttribute('data-menu')) {
      const lateral = el.closest('.lateral');
      lateral.classList.toggle('aberta');
      el.setAttribute('aria-expanded', lateral.classList.contains('aberta'));
    }
  });

  document.addEventListener('submit', e => {
    const form = e.target;
    if (form.dataset.pergunta && !confirm(form.dataset.pergunta)) { e.preventDefault(); return; }
    if (form.dataset.enviando) {
      const botao = form.querySelector('button');
      if (botao) botao.textContent = form.dataset.enviando;
    }
  });

  document.addEventListener('change', e => {
    const el = e.target;
    if (el.dataset.aoMudar) chamar(el.dataset.aoMudar, el);
    if (el.dataset.aoMudarForm) chamar(el.dataset.aoMudarForm, el.form);
    if (el.dataset.mostra) {
      const alvo = document.querySelector(el.dataset.mostra);
      if (alvo) alvo.hidden = el.value !== el.dataset.quando;
    }
    if (el.hasAttribute('data-enviar-ao-mudar')) el.form.submit();
  });

  document.addEventListener('input', e => {
    const el = e.target;
    if (el.dataset.aoDigitarForm) chamar(el.dataset.aoDigitarForm, el.form);
    if (el.hasAttribute('data-mostra-valor')) {
      const saida = el.previousElementSibling?.querySelector('output');
      if (saida) saida.value = el.value;
    }
    if (el.dataset.contador && el.nextElementSibling) el.nextElementSibling.textContent = `${el.value.length} / ${el.dataset.contador}`;
    if (el.hasAttribute('data-confere-nome')) {
      const botao = el.form.querySelector('[data-confirmar]');
      if (botao) botao.disabled = el.value.trim().toLowerCase() !== (el.dataset.nome || '').trim().toLowerCase();
    }
  });

  document.addEventListener('paste', e => {
    const el = e.target.closest && e.target.closest('[data-enviar-ao-colar]');
    if (!el) return;
    setTimeout(() => {
      const outro = el.dataset.enviarAoColar;
      if (outro && !(el.form.elements[outro]?.value.trim() && el.value.trim())) return;
      el.form.requestSubmit();
    }, 50);
  });

  document.addEventListener('mouseover', e => { if (e.target.matches?.('video[data-previa-hover]')) e.target.play().catch(() => {}); });
  document.addEventListener('mouseout', e => { if (e.target.matches?.('video[data-previa-hover]')) e.target.pause(); });

  // o evento error não sobe pela página: escuta na captura e confere as imagens que falharam antes deste arquivo
  const semPrevia = img => {
    const aviso = document.createElement('span');
    aviso.className = 'suave';
    aviso.textContent = 'sem prévia';
    img.replaceWith(aviso);
  };
  document.addEventListener('error', e => { if (e.target.matches?.('img[data-sem-previa]')) semPrevia(e.target); }, true);
  document.querySelectorAll('img[data-sem-previa]').forEach(img => { if (img.complete && !img.naturalWidth) semPrevia(img); });
})();
