// SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
// Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
// Consentimento de cookies (LGPD). Hoje o site não usa nenhum cookie opcional, então o aviso não aparece.
// Para ligar um serviço opcional no futuro (ex.: medir visitas):
//   1. acrescente a categoria em OPCIONAIS abaixo e descreva-a em cookies.html;
//   2. carregue o script dele bloqueado: <script type="text/plain" data-consentimento="analise" src="..."></script>
// O script só roda depois que a pessoa aceitar aquela categoria. Recusar é tão fácil quanto aceitar,
// a escolha fica salva neste navegador e pode ser mudada a qualquer hora no rodapé ("Preferências de cookies").
(function () {
  "use strict";

  var OPCIONAIS = {
    // analise: "Medir visitas de forma agregada, para saber quais páginas são úteis",
    // marketing: "Anúncios e medição de campanhas",
  };
  var CHAVE = "consentimento-v1";  // mude a versão quando as categorias mudarem: todos escolhem de novo

  function ler() {
    try { return JSON.parse(localStorage.getItem(CHAVE) || "null"); } catch (e) { return null; }
  }

  function gravar(aceitas) {
    var escolha = { aceitas: aceitas, quando: new Date().toISOString() };
    try { localStorage.setItem(CHAVE, JSON.stringify(escolha)); } catch (e) { /* navegação privada: vale só nesta página */ }
    return escolha;
  }

  function ativar(escolha) {
    var aceitas = (escolha && escolha.aceitas) || [];
    document.querySelectorAll('script[type="text/plain"][data-consentimento]').forEach(function (bloqueado) {
      if (aceitas.indexOf(bloqueado.dataset.consentimento) < 0 || bloqueado.dataset.ativado) return;
      var s = document.createElement("script");
      if (bloqueado.src) s.src = bloqueado.src; else s.textContent = bloqueado.textContent;
      bloqueado.dataset.ativado = "1";
      bloqueado.after(s);
    });
  }

  function painel(escolha) {
    var antigo = document.getElementById("consentimento");
    if (antigo) antigo.remove();
    var categorias = Object.keys(OPCIONAIS);
    var aceitas = (escolha && escolha.aceitas) || [];
    var caixa = document.createElement("section");
    caixa.id = "consentimento";
    caixa.setAttribute("role", "dialog");
    caixa.setAttribute("aria-label", "Preferências de cookies");
    var html = "<p><b>Cookies</b>: usamos só o necessário para o site funcionar.";
    if (!categorias.length) {
      html += " Hoje não há nenhum cookie opcional, então não há nada para aceitar. <a href=\"cookies.html\">Saiba mais</a></p>" +
              "<div class=\"botoes\"><button data-acao=\"fechar\">Entendi</button></div>";
    } else {
      html += " Os itens abaixo são opcionais e ficam desligados até você escolher. <a href=\"cookies.html\">Saiba mais</a></p>";
      categorias.forEach(function (c) {
        html += "<label><input type=\"checkbox\" value=\"" + c + "\"" + (aceitas.indexOf(c) >= 0 ? " checked" : "") +
                "> " + OPCIONAIS[c] + "</label>";
      });
      html += "<div class=\"botoes\"><button data-acao=\"recusar\">Só os necessários</button>" +
              "<button data-acao=\"salvar\">Salvar escolha</button><button data-acao=\"aceitar\">Aceitar todos</button></div>";
    }
    caixa.innerHTML = html;
    caixa.addEventListener("click", function (ev) {
      var acao = ev.target.dataset && ev.target.dataset.acao;
      if (!acao) return;
      if (acao === "aceitar") escolha = gravar(categorias);
      if (acao === "recusar") escolha = gravar([]);
      if (acao === "salvar") {
        escolha = gravar(Array.prototype.map.call(caixa.querySelectorAll("input:checked"), function (i) { return i.value; }));
      }
      ativar(escolha);
      caixa.remove();
    });
    document.body.appendChild(caixa);
  }

  window.preferenciasDeCookies = function () { painel(ler()); };

  document.addEventListener("DOMContentLoaded", function () {
    var escolha = ler();
    // o sinal "Global Privacy Control" do navegador vale como recusa dos opcionais
    if (!escolha && navigator.globalPrivacyControl) escolha = gravar([]);
    ativar(escolha);
    if (!escolha && Object.keys(OPCIONAIS).length) painel(null);
    document.querySelectorAll("[data-preferencias-cookies]").forEach(function (b) {
      b.addEventListener("click", function (ev) { ev.preventDefault(); window.preferenciasDeCookies(); });
    });
  });
})();
