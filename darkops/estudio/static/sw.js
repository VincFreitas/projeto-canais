// Service worker do Estúdio: deixa instalar como aplicativo (PC ou celular) e mostra um aviso quando o
// Estúdio está fechado. Só guarda arquivos estáticos (CSS, ícones); páginas e ações sempre vão ao Estúdio,
// para nunca mostrar fila, aprovação ou estado velhos. Servido em /sw.js (escopo: o Estúdio inteiro).
const VERSAO = new URL(self.location).searchParams.get("v") || "0";
const CACHE = "estudio-estatico-" + VERSAO;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (ev) => {
  ev.waitUntil((async () => {
    for (const nome of await caches.keys()) if (nome !== CACHE) await caches.delete(nome);  // versão nova: limpa a velha
    await self.clients.claim();
  })());
});

const FECHADO = `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estúdio fechado · Projeto Canais</title>
<body style="font:17px/1.6 system-ui,sans-serif;background:#111;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center">
<div><div style="font-size:48px;color:#f5c518">✦</div><h1>O Estúdio está fechado</h1>
<p>Abra pelo atalho <b>Projeto Canais</b> no PC e recarregue esta página.</p></div></body></html>`;

self.addEventListener("fetch", (ev) => {
  const pedido = ev.request;
  if (pedido.method !== "GET") return;  // ações (POST) nunca passam por aqui
  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/static/")) {
    // rede primeiro (o CSS muda sem trocar de versão durante o desenvolvimento); a cópia só serve com o Estúdio fechado
    ev.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const resposta = await fetch(pedido);
        if (resposta.ok) cache.put(pedido, resposta.clone());
        return resposta;
      } catch (erro) {
        return (await cache.match(pedido)) || Response.error();
      }
    })());
  } else if (pedido.mode === "navigate") {
    ev.respondWith(fetch(pedido).catch(() =>
      new Response(FECHADO, { headers: { "Content-Type": "text/html; charset=utf-8" } })));
  }
});
