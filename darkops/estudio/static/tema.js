// SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
// Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
// Tema do Estúdio: claro, escuro ou automático (segue o sistema). Carregado no <head>, sem defer, para pôr
// data-tema no <html> antes da primeira pintura: assim a página nunca pisca branco no modo escuro.
// A escolha fica no localStorage do navegador; os botões ficam no rodapé da lateral (base.html).
(function () {
  const CHAVE = "estudio-tema";
  const raiz = document.documentElement;
  const sistemaEscuro = window.matchMedia ? matchMedia("(prefers-color-scheme: dark)") : null;

  function escolha() {
    try {
      const valor = localStorage.getItem(CHAVE);
      return valor === "claro" || valor === "escuro" ? valor : "auto";
    } catch (erro) {
      return "auto";  // navegador sem localStorage: segue o sistema
    }
  }

  function aplicar() {
    const quer = escolha();
    const tema = quer === "auto" ? (sistemaEscuro && sistemaEscuro.matches ? "escuro" : "claro") : quer;
    raiz.setAttribute("data-tema", tema);
    const cor = document.querySelector('meta[name="theme-color"]');
    if (cor) cor.setAttribute("content", tema === "escuro" ? "#111113" : "#f5f5f7");
    document.querySelectorAll("[data-escolher-tema]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.getAttribute("data-escolher-tema") === quer)));
  }

  aplicar();
  // Automático acompanha o sistema na hora; outra aba que trocar o tema troca esta também
  if (sistemaEscuro) {
    if (sistemaEscuro.addEventListener) sistemaEscuro.addEventListener("change", aplicar);
    else if (sistemaEscuro.addListener) sistemaEscuro.addListener(aplicar);
  }
  addEventListener("storage", e => { if (e.key === CHAVE) aplicar(); });
  document.addEventListener("DOMContentLoaded", aplicar);  // marca o botão da escolha atual
  document.addEventListener("click", e => {
    const botao = e.target.closest && e.target.closest("[data-escolher-tema]");
    if (!botao) return;
    try { localStorage.setItem(CHAVE, botao.getAttribute("data-escolher-tema")); } catch (erro) { /* só nesta página */ }
    aplicar();
  });
})();
