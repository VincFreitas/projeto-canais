// SPDX-License-Identifier: LicenseRef-PolyForm-Shield-1.0.0
// Projeto Canais · Vinicius Freitas · github.com/VincFreitas/projeto-canais
/* Prancha de Campo: monta o vídeo inteiro numa timeline GSAP pausada a partir de window.__PRANCHA (JSON).
   O roteiro só escreve componentes e a palavra da fala em que cada coisa acontece ("em"); este arquivo cuida de
   moldura, legenda, tempos, traço e movimento. Tudo é função do tempo da timeline e de sementes: nada de
   Math.random, Date ou relógio, para o HyperFrames poder pular para qualquer quadro e a imagem sair igual. */
(() => {
  "use strict";
  const D = window.__PRANCHA;
  const NS = "http://www.w3.org/2000/svg";
  gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin);

  // docs/movimento.md: tempos e curvas fixos
  const T = { rapido: .14, medio: .28, lento: .5, desenha: 1.1 };
  const C = { entra: "back.out(1.8)", bate: "power4.in", assenta: "elastic.out(1, .5)", sai: "power2.in",
    respira: "sine.inOut", desenha: "power1.inOut", suave: "power2.out", linear: "none" };
  const curva = n => C[n] || n || C.respira;

  const tl = gsap.timeline({ paused: true });
  const avisos = [];
  const eventos = [];  // [segundo, som] para a trilha de efeitos (darkops/sincronia.py)
  const som = (t, nome) => { if (nome && t >= 0) eventos.push([+t.toFixed(3), nome]); };
  let uid = 0;

  // ---------- utilitários
  function sorteio(txt) {  // mulberry32 com semente tirada do texto
    let a = 2166136261;
    for (const ch of String(txt)) a = Math.imul(a ^ ch.charCodeAt(0), 16777619) >>> 0;
    return () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const norm = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
  function el(tag, attrs = {}, pai = null, svg = true) {
    const e = svg ? document.createElementNS(NS, tag) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null) continue;
      if (k === "texto") e.textContent = v;
      else if (k === "html") e.innerHTML = v;
      else e.setAttribute(k, v);
    }
    if (pai) pai.appendChild(e);
    return e;
  }
  const div = (attrs, pai) => el("div", attrs, pai, false);
  const fmt = (v, casas = 0) => v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

  // "em" = palavra da fala (começo da palavra), "palavra#2" = 2ª vez, "palavra+0.4" = 0,4 s depois, número = segundos
  function quando(cena, em, padrao = 0) {
    if (em == null) return cena.ini + padrao;
    if (typeof em === "number") return cena.ini + em;
    let [alvo, desloc] = String(em).split("+");
    let n = 1;
    const m = alvo.match(/^(.*)#(\d+)$/);
    if (m) { alvo = m[1]; n = +m[2]; }
    const a = norm(alvo);
    let achou = 0;
    for (const p of cena.palavras) {
      if (norm(p.texto).startsWith(a) && ++achou === n) return cena.ini + p.inicio + (+desloc || 0);
    }
    avisos.push(`cena ${cena.i}: a palavra "${em}" não está na fala`);
    return cena.ini + padrao;
  }

  // curva suave (Catmull-Rom) por uma lista de pontos
  function suave(pts, fechado = false) {
    if (pts.length < 3) return "M" + pts.map(p => p.map(v => v.toFixed(1)).join(",")).join(" L");
    const P = fechado ? [pts[pts.length - 1], ...pts, pts[0], pts[1]] : [pts[0], ...pts, pts[pts.length - 1]];
    let d = `M${P[1][0].toFixed(1)},${P[1][1].toFixed(1)}`;
    for (let i = 1; i < P.length - 2; i++) {
      const [p0, p1, p2, p3] = [P[i - 1], P[i], P[i + 1], P[i + 2]];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ` C${c1.map(v => v.toFixed(1))} ${c2.map(v => v.toFixed(1))} ${p2.map(v => v.toFixed(1))}`;
    }
    return fechado ? d + " Z" : d;
  }

  // ---------- moldura
  const raiz = document.getElementById("root");
  const defs = el("svg", { width: 0, height: 0, style: "position:absolute" }, raiz);
  defs.innerHTML = `<defs><pattern id="hachura" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="16" stroke="rgba(92,242,224,.28)" stroke-width="3"/></pattern></defs>`;
  div({ id: "grade", class: "camada" }, raiz);
  const halos = {};
  for (const h of ["agua", "ambar", "osso"]) halos[h] = div({ id: `halo-${h}`, class: "camada halo" }, raiz);
  div({ id: "mesa" }, div({ id: "mesa-caixa" }, raiz));
  const poeira = div({ class: "camada" }, raiz);
  const palco = div({ class: "camada" }, raiz);
  div({ id: "vinheta", class: "camada" }, raiz);
  const barra = div({ id: "capitulos" }, raiz);
  const cab = div({ id: "cabecalho" }, raiz);
  const legenda = div({ id: "legenda" }, raiz);
  const ressalvaCx = div({ id: "ressalva" }, raiz);

  const cenas = D.cenas.map((c, i) => ({ ...c, i, fim: c.ini + c.dur }));
  const TOTAL = cenas[cenas.length - 1].fim;

  // halo por capítulo: a troca de cor marca a troca de assunto
  let haloAtual = null;
  for (const c of cenas) {
    const h = c.halo || "agua";
    if (h === haloAtual) continue;
    if (haloAtual) tl.to(halos[haloAtual], { opacity: 0, duration: .8, ease: C.respira }, c.ini);
    tl.fromTo(halos[h], { opacity: 0 }, { opacity: 1, duration: haloAtual ? .8 : .01, ease: C.respira, immediateRender: false }, c.ini);
    haloAtual = h;
  }

  // partículas: poucas, redondas, longe do centro, piscando devagar
  const rp = sorteio(`${D.semente}-poeira`);
  for (let k = 0; k < 16; k++) {
    let x, y;
    do { x = 40 + rp() * 1000; y = 260 + rp() * 1240; } while (x > 260 && x < 820 && y > 420 && y < 1120);
    const r = 1.5 + rp() * 2.5, o = .1 + rp() * .15;
    const p = div({ class: "particula", style: `left:${x.toFixed(0)}px;top:${y.toFixed(0)}px;width:${(2 * r).toFixed(1)}px;height:${(2 * r).toFixed(1)}px;opacity:${o.toFixed(2)}` }, poeira);
    const per = 2.5 + rp() * 2.5;
    tl.to(p, { opacity: o * .35, duration: per, ease: C.respira, yoyo: true, repeat: Math.max(1, Math.floor(TOTAL / per) - 1) }, rp() * 2);
    tl.to(p, { y: -(30 + rp() * 50), duration: TOTAL, ease: C.linear }, 0);
  }

  // barra de capítulos: cada segmento enche durante o seu capítulo
  for (const cap of D.capitulos || []) {
    const seg = div({ class: "cap" }, barra);
    const i = div({}, seg);
    const ini = cenas[cap.de].ini, fim = cenas[cap.ate].fim;
    tl.fromTo(i, { scaleX: 0 }, { scaleX: 1, duration: fim - ini, ease: C.linear }, ini);
  }

  // cabeçalho: ícone, título do tema, subtítulo, campo de estado (o termo técnico mora aqui) e a marca do olho
  el("svg", { id: "cab-icone", viewBox: "0 0 54 54", html: `<circle cx="27" cy="27" r="22" class="l" style="stroke-width:3"/>
    <path d="M27,9 L27,45 M9,27 L45,27" class="d" style="stroke-width:2"/><circle cx="27" cy="27" r="6" class="l" style="stroke-width:3"/>` }, cab);
  const txt = div({ id: "cab-textos" }, cab);
  div({ id: "cab-titulo", texto: D.titulo }, txt);
  div({ id: "cab-sub", texto: D.subtitulo }, txt);
  const estadoCx = div({ id: "cab-estado" }, cab);
  el("svg", { id: "cab-olho", viewBox: "0 0 40 40", html: `<path d="M3,20 Q20,5 37,20 Q20,35 3,20 Z" class="l" style="stroke-width:2.5"/>
    <circle cx="20" cy="20" r="5.5" fill="#5CF2E0"/>` }, cab);
  tl.fromTo(cab, { opacity: 0, y: -14 }, { opacity: 1, y: 0, duration: T.lento, ease: C.suave }, .05);
  tl.fromTo(barra, { opacity: 0 }, { opacity: 1, duration: T.lento }, .05);
  let estadoAnt = null;
  for (const c of cenas) {
    for (const e of c.estado || []) {
      const t = quando(c, e.em, .2);
      const caixa = div({ class: "estado", texto: String(e.texto).toUpperCase() }, estadoCx);
      if (estadoAnt) tl.to(estadoAnt, { clipPath: "inset(0 0 0 100%)", duration: T.medio, ease: C.sai }, t - .05);
      tl.fromTo(caixa, { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: .4, ease: C.suave, immediateRender: false }, t);
      estadoAnt = caixa;
    }
  }

  // ressalva: "reconstituição ilustrativa" ou a ressalva da cena (tradição, hipótese, escala exagerada)
  let resAnt = null, resTxt = null;
  for (const c of cenas) {
    const texto = c.ressalva || D.ressalva || "reconstituição ilustrativa";
    if (texto === resTxt) continue;
    const r = div({ class: "ressalva", texto }, ressalvaCx);
    if (resAnt) tl.to(resAnt, { opacity: 0, duration: T.medio }, c.ini);
    tl.fromTo(r, { opacity: 0 }, { opacity: 1, duration: T.lento, immediateRender: false }, c.ini + .1);
    resAnt = r; resTxt = texto;
  }

  // ---------- legenda: grupos curtos na faixa de baixo; a palavra futura fica a 30% e acende quando é dita
  const LIGA = new Set(["e", "de", "da", "do", "das", "dos", "a", "o", "as", "os", "um", "uma", "que", "pra", "para",
    "com", "sem", "no", "na", "em", "se", "por", "mais", "so", "nao", "num", "numa", "bem", "ao", "mil"]);
  function agrupar(pal) {
    const out = [];
    let g = [], n = 0;
    pal.forEach((p, i) => {
      g.push(i); n += p.texto.length + 1;
      const prox = pal[i + 1];
      const fecha = /[.,;:!?]$/.test(p.texto);
      if (!prox || fecha || (g.length >= 3 && !LIGA.has(norm(p.texto))) || n > 24) { out.push(g); g = []; n = 0; }
    });
    return out;
  }
  function indicesDestaque(c) {
    if (!c.destaque) return new Set();
    const alvo = String(c.destaque).split(/\s+/).map(norm).filter(Boolean);
    const P = c.palavras.map(p => norm(p.texto));
    for (let i = 0; i + alvo.length <= P.length; i++) {
      if (alvo.every((w, k) => P[i + k].startsWith(w))) return new Set(alvo.map((_, k) => i + k));
    }
    avisos.push(`cena ${c.i}: o destaque "${c.destaque}" não está na fala`);
    return new Set();
  }
  const todosGrupos = [];
  for (const c of cenas) {
    const dest = indicesDestaque(c);
    for (const g of agrupar(c.palavras)) todosGrupos.push({ c, g, dest });
  }
  todosGrupos.forEach((G, k) => {
    const { c, g, dest } = G;
    const caixa = div({ class: "grupo" }, legenda);
    let enf = null;
    for (const i of g) {
      const p = c.palavras[i];
      const pai = dest.has(i) ? (enf = enf || div({ class: "enfase" }, caixa)) : (enf = null, caixa);
      const s = el("span", { class: "p", texto: p.texto.replace(/[.,;:!?"“”«»]/g, "") }, pai, false);
      tl.fromTo(s, { opacity: .3 }, { opacity: 1, duration: .08, ease: C.linear, immediateRender: false }, c.ini + p.inicio);
    }
    const ini = c.ini + c.palavras[g[0]].inicio;
    const prox = todosGrupos[k + 1];
    const fim = prox ? prox.c.ini + prox.c.palavras[prox.g[0]].inicio : TOTAL;
    tl.fromTo(caixa, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, duration: T.medio, ease: C.suave, immediateRender: false }, ini);
    tl.to(caixa, { autoAlpha: 0, duration: .1, ease: C.sai }, Math.max(ini + .2, fim - .1));
  });

  // ---------- peças: SVG da biblioteca colocado no palco, com estado próprio (ângulo, pivô, deslocamento)
  function peca(ctx, nome, o) {
    const P = D.pecas[nome];
    if (!P) { avisos.push(`peça "${nome}" não existe`); return null; }
    const [vw, vh] = P.vb;
    const s = o.altura ? o.altura / vh : o.largura / vw;
    const ox = o.x - vw * s / 2, oy = o.base - vh * s;
    // w = embrulho sem transform (é ele que aparece/some: GSAP com x/y em <g> troca o transform do elemento)
    const w = el("g", {}, o.pai || ctx.svg);
    const g0 = el("g", { transform: `translate(${ox.toFixed(1)} ${oy.toFixed(1)})` }, w);
    const gm = el("g", {}, g0);
    const gs = el("g", { transform: o.espelhar ? `translate(${(vw * s).toFixed(1)} 0) scale(${-s} ${s})` : `scale(${s})` }, gm);
    const gr = el("g", {}, gs);
    gr.innerHTML = P.svg;
    g0.id = `pc${++uid}`;
    const h = { nome, P, s, vw, vh, ox, oy, w, g0, gm, gr, espelhar: !!o.espelhar, deps: [],
      st: { ang: o.ang || 0, px: 0, py: 0, pivx: 0, pivy: 0 } };
    if (o.pivo) [h.st.pivx, h.st.pivy] = P.pivos[o.pivo];
    h.st.px = o.px || 0; h.st.py = o.py || 0;
    aplicar(h);
    if (o.id) ctx.reg[o.id] = h;
    return h;
  }
  function aplicar(h) {
    h.gm.setAttribute("transform", `translate(${h.st.px.toFixed(2)} ${h.st.py.toFixed(2)})`);
    h.gr.setAttribute("transform", h.st.ang ? `rotate(${h.st.ang.toFixed(3)} ${h.st.pivx} ${h.st.pivy})` : "");
    for (const f of h.deps) f();
  }
  // ponto da peça (coordenada do desenho ou nome de pivô) em coordenada do palco, já com giro e deslocamento
  function ponto(h, local, st = h.st) {  // st = pose (padrão: a pose atual da peça)
    let [x, y] = typeof local === "string" ? h.P.pivos[local] : local;
    if (h.espelhar) x = h.vw - x;
    if (st.ang) {
      const a = st.ang * Math.PI / 180, dx = x - st.pivx, dy = y - st.pivy;
      x = st.pivx + dx * Math.cos(a) - dy * Math.sin(a);
      y = st.pivy + dx * Math.sin(a) + dy * Math.cos(a);
    }
    return [h.ox + st.px + x * h.s, h.oy + st.py + y * h.s];
  }
  const NEUTRA = { ang: 0, px: 0, py: 0, pivx: 0, pivy: 0 };
  // marcador que percorre um caminho: posição calculada pelo comprimento do traço (sem plugin, determinístico)
  function percorrer(marca, guia, t, dur, ease) {
    const L = guia.getTotalLength(), st = { u: 0 };
    const pos = () => { const q = guia.getPointAtLength(st.u * L); marca.setAttribute("transform", `translate(${q.x.toFixed(1)} ${q.y.toFixed(1)})`); };
    pos();
    tl.to(st, { u: 1, duration: dur, ease, onUpdate: pos }, t);
  }
  function tracos(raizEl) {
    const l = [...raizEl.querySelectorAll(".l,.d,.s,.a")];
    return l.sort((a, b) => (+a.dataset.ordem || 0) - (+b.dataset.ordem || 0));
  }
  // traço que se desenha na ordem do desenho, depois o preenchimento
  function desenhar(raizEl, t, dur = T.desenha) {
    const l = tracos(raizEl);
    if (!l.length) return;
    const cada = Math.max(.35, dur * .55);
    const passo = l.length > 1 ? (dur - cada) / (l.length - 1) : 0;
    tl.fromTo(l, { drawSVG: "0%" }, { drawSVG: "100%", duration: cada, ease: C.desenha, stagger: passo }, t);
    const massa = raizEl.querySelectorAll(".m,.sombra,.h");
    if (massa.length) tl.fromTo(massa, { opacity: 0 }, { opacity: 1, duration: T.lento, ease: C.suave }, t + dur * .6);
  }
  function aparecer(alvo, t, dur = T.medio, y = 10) {
    tl.fromTo(alvo, { opacity: 0, y }, { opacity: 1, y: 0, duration: dur, ease: C.suave }, t);
  }
  function pulso(h, t) {  // impacto = o traço engrossa e volta, e a peça dá um quique curto
    tl.to(tracos(h.gr), { strokeWidth: 9, duration: T.rapido, yoyo: true, repeat: 1, ease: C.suave }, t);
  }

  // ---------- componentes (o roteiro chama pelo nome em "c")
  const COMP = {};

  COMP.Peca = (ctx, o) => {
    const h = peca(ctx, o.peca, o);
    if (!h) return;
    if (o.desenhar !== false) desenhar(h.gr, quando(ctx.cena, o.em, .1), o.dur || T.desenha);
    else if (o.em != null) aparecer(h.w, quando(ctx.cena, o.em), T.medio, 0);
    if (o.cor === "alerta") tracos(h.gr).forEach(e => e.setAttribute("class", "a"));
    if (o.fantasma) {
      tracos(h.gr).forEach(e => e.setAttribute("class", "s tracejado"));
      h.gr.querySelectorAll(".m,.sombra").forEach(e => e.remove());
    }
  };

  // movimento de uma peça já colocada: giro em volta de um pivô e/ou deslocamento em px do palco
  COMP.Mover = (ctx, o) => {
    const h = ctx.reg[o.alvo];
    if (!h) { avisos.push(`cena ${ctx.cena.i}: Mover sem alvo "${o.alvo}"`); return; }
    for (const p of o.passos) {
      const t = quando(ctx.cena, p.em, p.t);
      if (p.pivo) {
        const [px, py] = h.P.pivos[p.pivo];
        tl.set(h.st, { pivx: px, pivy: py, onUpdate: () => aplicar(h) }, t);
      }
      const vars = { duration: p.dur || T.lento, ease: curva(p.curva), onUpdate: () => aplicar(h) };
      if (p.gira != null) vars.ang = p.gira;
      if (p.x != null) vars.px = p.x;
      if (p.y != null) vars.py = p.y;
      if (p.repete) { vars.yoyo = true; vars.repeat = p.repete; }
      tl.to(h.st, vars, t);
      if (p.pulso) pulso(h, t + vars.duration * .9);
    }
  };

  // fantasma tracejado âmbar: mostra o que aconteceria (tombar) sem a estátua real cair
  COMP.Fantasma = (ctx, o) => {
    const b = ctx.reg[o.alvo];
    const h = peca(ctx, b.nome, { x: b.ox + b.vw * b.s / 2, base: b.oy + b.vh * b.s, altura: b.vh * b.s, pivo: o.pivo });
    tracos(h.gr).forEach(e => e.setAttribute("class", "a tracejado"));
    h.gr.querySelectorAll(".m,.sombra").forEach(e => e.remove());
    const t = quando(ctx.cena, o.em);
    const ang0 = o.de != null ? o.de : b.st.ang;
    h.st.ang = ang0; aplicar(h);
    tl.fromTo(h.w, { opacity: 0 }, { opacity: .9, duration: T.rapido }, t);
    som(t + (o.dur || .9) * .95, "thud");
    tl.fromTo(h.st, { ang: ang0 }, { ang: o.gira, duration: o.dur || .9, ease: "power2.in", onUpdate: () => aplicar(h), immediateRender: false }, t);
    tl.to(h.w, { opacity: 0, duration: T.lento, ease: C.sai }, quando(ctx.cena, o.some_em, (t - ctx.cena.ini) + (o.dur || .9) + .5));
  };

  // prumo: linha vertical do centro de massa até o chão; fica âmbar quando passa da base de apoio
  COMP.Prumo = (ctx, o) => {
    const h = ctx.reg[o.alvo];
    const g = el("g", { opacity: 0 }, ctx.svg);
    const base = el("path", { class: "l", style: "stroke-width:7" }, g);
    const fio = el("path", { class: "d tracejado" }, g);
    const bola = el("circle", { r: 11, class: "l", style: "fill:#0B0F14" }, g);
    const [pa, pb] = o.apoio || ["tras", "frente"];
    const desenhaPrumo = () => {
      const [cx, cy] = ponto(h, "cm");
      const A = ponto(h, pa), B = ponto(h, pb);
      const chao = Math.max(A[1], B[1]);
      const fora = cx < Math.min(A[0], B[0]) - 2 || cx > Math.max(A[0], B[0]) + 2;
      base.setAttribute("d", `M${A[0].toFixed(1)},${A[1].toFixed(1)} L${B[0].toFixed(1)},${B[1].toFixed(1)}`);
      fio.setAttribute("d", `M${cx.toFixed(1)},${cy.toFixed(1)} L${cx.toFixed(1)},${(chao + 40).toFixed(1)}`);
      bola.setAttribute("cx", cx.toFixed(1)); bola.setAttribute("cy", cy.toFixed(1));
      const cor = fora ? "#F2B33D" : "#5CF2E0";
      for (const e of [base, fio, bola]) e.style.stroke = cor;
    };
    h.deps.push(desenhaPrumo);
    desenhaPrumo();
    aparecer(g, quando(ctx.cena, o.em, .3), T.medio, 0);
  };

  // seta de força (0° = direita, 90° = para baixo)
  COMP.Forca = (ctx, o) => {
    const g = el("g", { opacity: 0 }, ctx.svg);
    const [x, y] = o.de || ponto(ctx.reg[o.alvo], o.ponto);
    const a = (o.angulo || 0) * Math.PI / 180, L = o.tamanho || 160;
    const x2 = x + Math.cos(a) * L, y2 = y + Math.sin(a) * L;
    const cls = o.cor === "alerta" ? "a" : "l";
    const haste = el("path", { class: cls, style: "stroke-width:8", d: `M${x},${y} L${x2.toFixed(1)},${y2.toFixed(1)}` }, g);
    const ab = 26, a1 = a + Math.PI * .82, a2 = a - Math.PI * .82;
    const ponta = el("path", { class: cls, style: "stroke-width:8",
      d: `M${(x2 + Math.cos(a1) * ab).toFixed(1)},${(y2 + Math.sin(a1) * ab).toFixed(1)} L${x2.toFixed(1)},${y2.toFixed(1)} L${(x2 + Math.cos(a2) * ab).toFixed(1)},${(y2 + Math.sin(a2) * ab).toFixed(1)}` }, g);
    const t = quando(ctx.cena, o.em);
    tl.set(g, { opacity: 1 }, t);
    tl.fromTo(haste, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento, ease: C.suave }, t);
    tl.fromTo(ponta, { opacity: 0 }, { opacity: 1, duration: T.rapido }, t + T.lento * .8);
    if (o.rotulo) {
      const r = el("text", { class: o.cor === "alerta" ? "rot" : "rot-linha", x: (x2 + (o.rx || 16)).toFixed(0), y: (y2 + (o.ry || 10)).toFixed(0), texto: o.rotulo.toUpperCase() }, g);
      if (o.cor === "alerta") r.style.fill = "#F2B33D";
      aparecer(r, t + T.lento, T.medio, 0);
    }
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
  };

  // corda presa numa peça: frouxa (catenária) ou esticada; se desenha a partir da peça
  COMP.Corda = (ctx, o) => {
    const path = el("path", { class: "l", style: "stroke-width:6" }, ctx.svg);
    const st = { r: 0, tensao: o.tensa ? 1 : 0 };
    const pegar = ref => Array.isArray(ref) ? ref : ponto(ctx.reg[ref.alvo], ref.ponto);
    const desenha = () => {
      const A = pegar(o.de), B = pegar(o.para);
      const folga = (o.folga ?? 90) * (1 - st.tensao);
      const M = [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2 + folga];
      const n = 24, k = Math.max(1, Math.round(n * st.r));
      let d = "";
      for (let i = 0; i <= k; i++) {
        const u = (i / n) * (st.r * n / k);
        const x = (1 - u) ** 2 * A[0] + 2 * (1 - u) * u * M[0] + u * u * B[0];
        const y = (1 - u) ** 2 * A[1] + 2 * (1 - u) * u * M[1] + u * u * B[1];
        d += (i ? " L" : "M") + x.toFixed(1) + "," + y.toFixed(1);
      }
      path.setAttribute("d", st.r > 0 ? d : "");
      path.style.strokeWidth = (4 + 3 * st.tensao).toFixed(1);
      path.style.opacity = (.65 + .35 * st.tensao).toFixed(2);
    };
    for (const ref of [o.de, o.para]) if (!Array.isArray(ref)) ctx.reg[ref.alvo].deps.push(desenha);
    desenha();
    const t = quando(ctx.cena, o.em, .2);
    tl.to(st, { r: 1, duration: o.dur_desenho || .7, ease: C.desenha, onUpdate: desenha }, t);
    if (o.tensa_em) tl.to(st, { tensao: 1, duration: T.medio, ease: C.suave, onUpdate: desenha }, quando(ctx.cena, o.tensa_em));
    if (o.solta_em) tl.to(st, { tensao: 0, duration: T.lento, ease: C.respira, onUpdate: desenha }, quando(ctx.cena, o.solta_em));
    if (o.id) ctx.reg[o.id] = { st, path };
  };

  COMP.Pessoas = (ctx, o) => {  // um grupo de pessoas lado a lado, na mesma pose
    const n = o.n || 3, passo = o.passo || 70;
    const t = quando(ctx.cena, o.em, .2);
    for (let k = 0; k < n; k++) {
      const h = peca(ctx, `pessoa-${o.pose || "parado"}`, { x: o.x + (o.espelhar ? k : -k) * passo, base: o.base,
        altura: o.altura || 220, espelhar: o.espelhar, id: o.id ? `${o.id}${k}` : null });
      if (!h) return;
      desenhar(h.gr, t + k * .08, .6);
    }
  };

  // multidão: n pontos que acendem em cascata (semente fixa); "grupos" junta em montinhos
  COMP.Multidao = (ctx, o) => {
    const r = sorteio(`${D.semente}-${ctx.cena.i}-${o.semente || "m"}`);
    const [ax, ay, aw, ah] = o.area;
    const g = el("g", {}, ctx.svg);
    const pts = [];
    const nG = o.grupos || 0;
    for (let k = 0; k < o.n; k++) {
      if (nG) {
        const gi = k % nG, cx = ax + aw * (gi + .5) / nG, cy = ay + ah / 2;
        const ang = r() * Math.PI * 2, rad = Math.sqrt(r()) * Math.min(aw / nG, ah) * .32;
        pts.push([cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad]);
      } else pts.push([ax + r() * aw, ay + r() * ah]);
    }
    const raio = o.raio || 7;
    const bolas = pts.map(([x, y]) => el("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: raio, fill: o.cor === "linha" ? "#5CF2E0" : "rgba(232,226,212,.75)" }, g));
    const ordem = bolas.map((b, k) => [r(), b]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
    const t = quando(ctx.cena, o.em, .2);
    tl.fromTo(ordem, { opacity: 0, scale: 0, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: T.medio, ease: C.entra,
      stagger: (o.cascata_s || 1.2) / Math.max(1, o.n) }, t);
    if (o.rotulo) {
      const rt = el("text", { class: "rot", x: ax, y: ay - 18, texto: o.rotulo.toUpperCase() }, g);
      aparecer(rt, t + .2, T.medio, 0);
    }
  };

  // várias cópias de uma peça em grade, acendendo em cascata (10 elefantes, 6 semanas...)
  COMP.Cascata = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const col = o.colunas || o.n;
    const t = quando(ctx.cena, o.em, .2);
    const itens = [];
    for (let k = 0; k < o.n; k++) {
      const cx = o.x + (k % col) * o.passo_x, base = o.y + Math.floor(k / col) * o.passo_y;
      const h = peca(ctx, o.peca, { x: cx, base, largura: o.largura, pai: g });
      itens.push(h.w);
    }
    tl.fromTo(itens, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: T.medio, ease: C.entra, stagger: o.cascata || .1 }, t);
    if (o.rotulo) {
      const rt = el("text", { class: "rot", x: o.x - o.largura / 2, y: o.y - o.passo_y * 0 - (o.rotulo_dy || 150), texto: o.rotulo.toUpperCase() }, g);
      aparecer(rt, t, T.medio, 0);
    }
  };

  // calendário: colunas que vão sendo riscadas (tempo de trabalho)
  COMP.Calendario = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const lado = o.lado || 64, n = o.n || 6, t = quando(ctx.cena, o.em, .2);
    const caixas = [], riscos = [];
    for (let k = 0; k < n; k++) {
      const x = o.x + k * (lado + 14), y = o.y;
      caixas.push(el("rect", { class: "s", x, y, width: lado, height: lado, rx: 6 }, g));
      riscos.push(el("path", { class: "a", d: `M${x + 14},${y + 14} L${x + lado - 14},${y + lado - 14} M${x + lado - 14},${y + 14} L${x + 14},${y + lado - 14}` }, g));
    }
    tl.fromTo(caixas, { opacity: 0 }, { opacity: 1, duration: T.rapido, stagger: .05 }, t);
    tl.fromTo(riscos, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio, stagger: .16, ease: C.suave }, t + .3);
    if (o.rotulo) aparecer(el("text", { class: "rot", x: o.x, y: o.y - 18, texto: o.rotulo.toUpperCase() }, g), t, T.medio, 0);
  };

  COMP.Carimbo = (ctx, o) => {
    const cor = o.cor === "linha" ? "#5CF2E0" : o.cor === "erro" ? "#E5484D" : "#F2B33D";
    const g = el("g", { transform: `translate(${o.x} ${o.y}) rotate(${o.rot ?? -6})` }, ctx.svg);
    const larg = o.texto.length * 40 + 70;
    el("rect", { x: -larg / 2, y: -50, width: larg, height: 100, rx: 10, fill: "rgba(11,15,20,.82)", stroke: cor, "stroke-width": 6 }, g);
    el("text", { class: "carimbo-txt", x: 0, y: 23, "text-anchor": "middle", fill: cor, texto: o.texto.toUpperCase() }, g);
    const dentro = el("g", {}, ctx.svg);
    dentro.appendChild(g);
    const t = quando(ctx.cena, o.em);
    som(t + T.rapido * 1.2, "impacto");
    tl.fromTo(dentro, { opacity: 0, scale: 1.6, svgOrigin: `${o.x} ${o.y}` }, { opacity: 1, scale: 1, duration: T.rapido * 1.4, ease: C.bate }, t);
    tl.fromTo(dentro, { scale: 1.12 }, { scale: 1, duration: T.lento, ease: C.assenta, svgOrigin: `${o.x} ${o.y}`, immediateRender: false }, t + T.rapido * 1.4);
  };

  // etiqueta: pino no ponto, conector traçado e rótulo em vidro (Consolas)
  COMP.Etiqueta = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const P = o.ponta || ponto(ctx.reg[o.alvo], o.ponto);
    const larg = o.texto.length * 14.3 + 30;
    const dir = o.x >= P[0] ? 1 : -1;
    const lx = dir > 0 ? o.x : o.x - larg;
    const linha = el("path", { class: "d", d: `M${P[0].toFixed(1)},${P[1].toFixed(1)} L${o.x},${o.y}` }, g);
    const pino = el("circle", { cx: P[0].toFixed(1), cy: P[1].toFixed(1), r: 9, fill: "#5CF2E0" }, g);
    const caixa = el("g", {}, g);
    el("rect", { x: lx, y: o.y - 26, width: larg, height: 52, rx: 8, fill: "rgba(11,15,20,.85)", stroke: "rgba(92,242,224,.55)", "stroke-width": 2 }, caixa);
    el("text", { class: "rot-linha", x: lx + 15, y: o.y + 9, texto: o.texto.toUpperCase() }, caixa);
    const t = quando(ctx.cena, o.em);
    tl.fromTo(pino, { scale: 0, transformOrigin: "50% 50%" }, { scale: 1, duration: T.rapido, ease: C.entra }, t);
    tl.fromTo(linha, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio, ease: C.suave }, t + .08);
    tl.fromTo(caixa, { opacity: 0, x: -14 * dir }, { opacity: 1, x: 0, duration: T.medio, ease: C.entra }, t + .25);
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
  };

  // destaca uma parte da peça (traço engrossa e acende) — ex.: a base curva
  COMP.Destacar = (ctx, o) => {
    const h = ctx.reg[o.alvo];
    const partes = [...h.gr.querySelectorAll("[data-parte]")].filter(e => e.dataset.parte === o.parte);
    const t = quando(ctx.cena, o.em);
    tl.to(partes, { strokeWidth: 11, duration: T.medio, ease: C.entra }, t);
    tl.set(partes, { attr: { class: "l brilho" } }, t);
  };

  // lupa: círculo no ponto da peça, conector e a ampliação ao lado (cópia viva do desenho)
  COMP.Lupa = (ctx, o) => {
    const h = ctx.reg[o.alvo];
    const g = el("g", {}, ctx.svg);
    const F = ponto(h, o.foco, o.pose || NEUTRA), L = o.liga_a, r = o.raio || 60, z = o.zoom || 2.6, R = r * z;
    const id = `lupa${++uid}`;
    el("clipPath", { id, html: `<circle cx="${L[0]}" cy="${L[1]}" r="${R}"/>` }, g);
    el("circle", { cx: L[0], cy: L[1], r: R, fill: "#0B0F14" }, g);
    const zoom = el("g", { "clip-path": `url(#${id})` }, g);
    el("use", { href: `#${h.g0.id}`, transform: `translate(${L[0]} ${L[1]}) scale(${z}) translate(${-F[0]} ${-F[1]})` }, zoom);
    const aro = el("circle", { cx: L[0], cy: L[1], r: R, class: "l" }, g);
    const peq = el("circle", { cx: F[0].toFixed(1), cy: F[1].toFixed(1), r, class: "l" }, g);
    const ang = Math.atan2(L[1] - F[1], L[0] - F[0]);
    const con = el("path", { class: "d", d: `M${(F[0] + Math.cos(ang) * r).toFixed(1)},${(F[1] + Math.sin(ang) * r).toFixed(1)} L${(L[0] - Math.cos(ang) * R).toFixed(1)},${(L[1] - Math.sin(ang) * R).toFixed(1)}` }, g);
    const t = quando(ctx.cena, o.em);
    tl.fromTo(peq, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio }, t);
    tl.fromTo(con, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio }, t + .2);
    tl.fromTo(aro, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento }, t + .35);
    tl.fromTo([zoom, g.children[1]], { opacity: 0 }, { opacity: 1, duration: T.lento }, t + .45);
    if (o.rotulo) {
      const rt = el("text", { class: "rot-linha", x: L[0], y: L[1] + R + 46, "text-anchor": "middle", texto: o.rotulo.toUpperCase() }, g);
      aparecer(rt, t + .7, T.medio, 0);
    }
  };

  // corte: a silhueta ganha hachura (vista em corte)
  COMP.Corte = (ctx, o) => {
    const h = ctx.reg[o.alvo];
    const m = h.gr.querySelector(".m");
    const hx = m.cloneNode(); hx.setAttribute("class", "h");
    m.after(hx);
    tl.fromTo(hx, { opacity: 0 }, { opacity: 1, duration: T.lento }, quando(ctx.cena, o.em, .1));
  };

  COMP.Contador = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const tam = o.tam || 190;
    const num = el("text", { class: "num", x: o.x, y: o.y, "text-anchor": "middle", style: `font-size:${tam}px`, texto: fmt(o.de || 0, o.casas) }, g);
    const un = el("text", { class: "unid", x: o.x, y: o.y + tam * .32 + 18, "text-anchor": "middle", texto: (o.unidade || "").toUpperCase() }, g);
    let anel = null;
    if (o.anel) anel = el("circle", { cx: o.x, cy: o.y - tam * .3, r: tam * .78, class: "d", transform: `rotate(-90 ${o.x} ${o.y - tam * .3})` }, g);
    if (o.rotulo) el("text", { class: "rot", x: o.x, y: o.y - tam * .86, "text-anchor": "middle", texto: o.rotulo.toUpperCase() }, g);
    const t = quando(ctx.cena, o.em);
    const st = { v: o.de || 0 };
    som(t, "riser");
    tl.fromTo(g, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: T.medio, ease: C.suave }, t - .05);
    tl.to(st, { v: o.ate, duration: o.dur || 1.0, ease: "power2.out", onUpdate: () => { num.textContent = fmt(st.v, o.casas); } }, t);
    if (anel) tl.fromTo(anel, { drawSVG: "0%" }, { drawSVG: "100%", duration: o.dur || 1.0, ease: "power2.out" }, t);
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
    void un;
  };

  // medidor horizontal com zona de alerta; o ponteiro anda nos passos
  COMP.Medidor = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const L = o.largura || 640, x = o.x, y = o.y;
    const esc = v => x + (v - o.de) / (o.ate - o.de) * L;
    el("text", { class: "rot", x, y: y - 34, texto: o.rotulo.toUpperCase() }, g);
    el("rect", { x, y: y - 14, width: L, height: 28, rx: 14, fill: "rgba(232,226,212,.06)", stroke: "rgba(232,226,212,.35)", "stroke-width": 2 }, g);
    if (o.zona) el("rect", { x: esc(o.zona[0]), y: y - 14, width: esc(o.zona[1]) - esc(o.zona[0]), height: 28, rx: 14, fill: "rgba(242,179,61,.22)" }, g);
    const enche = el("rect", { x, y: y - 9, height: 18, rx: 9, fill: "#5CF2E0" }, g);
    const valor = el("text", { class: "rot-linha", x: x + L, y: y - 34, "text-anchor": "end" }, g);
    const st = { v: o.valor ?? o.de };
    const desenha = () => {
      const w = Math.max(18, esc(st.v) - x);
      enche.setAttribute("width", w.toFixed(1));
      const alerta = o.zona && st.v >= o.zona[0];
      enche.setAttribute("fill", alerta ? "#F2B33D" : "#5CF2E0");
      valor.style.fill = alerta ? "#F2B33D" : "#5CF2E0";
      valor.textContent = `${fmt(st.v, o.casas || 0)} ${o.unidade || ""}`.trim().toUpperCase();
    };
    desenha();
    const t0 = quando(ctx.cena, o.em, .2);
    aparecer(g, t0, T.medio, 0);
    for (const p of o.passos || []) {
      const vars = { v: p.valor, duration: p.dur || T.lento, ease: curva(p.curva || "suave"), onUpdate: desenha };
      if (p.repete) { vars.yoyo = true; vars.repeat = p.repete; }
      tl.to(st, vars, quando(ctx.cena, p.em));
    }
  };

  // ficha de dossiê: os campos são "datilografados" (Consolas, revelado em degraus)
  COMP.Ficha = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const L = o.largura || 640, x = o.x, y = o.y, alt = 120 + o.campos.length * 96;
    el("rect", { x, y, width: L, height: alt, rx: 18, fill: "rgba(11,15,20,.88)", stroke: "rgba(92,242,224,.45)", "stroke-width": 2 }, g);
    el("path", { class: "d", d: `M${x + 30},${y + 86} L${x + L - 30},${y + 86}` }, g);
    const tit = el("text", { class: "rot-linha", x: x + 30, y: y + 60, style: "font-size:32px", texto: o.titulo.toUpperCase() }, g);
    const t0 = quando(ctx.cena, o.em, .2);
    tl.fromTo(g, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: T.medio, ease: C.suave }, t0);
    void tit;
    o.campos.forEach((c, k) => {
      const yy = y + 150 + k * 96;
      el("text", { class: "rot", x: x + 30, y: yy - 4, style: "font-size:22px;opacity:.7", texto: c.rotulo.toUpperCase() }, g);
      const id = `fc${++uid}`;
      const clip = el("clipPath", { id }, g);
      const r = el("rect", { x: x + 28, y: yy, width: 0, height: 64 }, clip);
      el("text", { class: "item", x: x + 30, y: yy + 50, "clip-path": `url(#${id})`, style: "font-family:Consolas,monospace;font-weight:700", texto: c.valor }, g);
      const w = c.valor.length * 24.3 + 6;
      tl.to(r, { attr: { width: w }, duration: c.valor.length * .055, ease: `steps(${c.valor.length})` }, quando(ctx.cena, c.em, (t0 - ctx.cena.ini) + .3 + k * .4));
    });
  };

  // resumo final: itens que acendem com um "check" e um item riscado em âmbar
  COMP.Resumo = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    o.itens.forEach((it, k) => {
      const y = o.y + k * 110;
      const caixa = el("rect", { class: "l", x: o.x, y: y - 40, width: 56, height: 56, rx: 10, style: "stroke-width:4" }, g);
      const ok = el("path", { class: "l", d: `M${o.x + 12},${y - 12} L${o.x + 25},${y + 2} L${o.x + 46},${y - 26}`, style: "stroke-width:6" }, g);
      const tx = el("text", { class: "item", x: o.x + 86, y: y + 2, texto: it.texto }, g);
      const t = quando(ctx.cena, it.em, .2 + k * .35);
      tl.fromTo(caixa, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio }, t);
      tl.fromTo(tx, { opacity: 0, x: -12 }, { opacity: 1, x: 0, duration: T.medio, ease: C.suave }, t + .05);
      tl.fromTo(ok, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio, ease: C.suave }, t + .2);
      som(t + .2, "pop");
    });
    if (o.risco) {
      const h = peca(ctx, o.risco.peca, { x: o.risco.x, base: o.risco.base, altura: o.risco.altura || 220 });
      const t = quando(ctx.cena, o.risco.em);
      desenhar(h.gr, t - .6, .6);
      const [x0, y0] = [o.risco.x - 130, o.risco.base - (o.risco.altura || 220) - 20];
      const x1 = o.risco.x + 130, y1 = o.risco.base + 20;
      const corte = el("path", { class: "a", style: "stroke-width:12", d: `M${x0},${y1} L${x1},${y0}` }, ctx.svg);
      tl.fromTo(corte, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio, ease: C.bate }, t);
      tl.to(tracos(h.gr), { stroke: "rgba(232,226,212,.45)", duration: T.medio }, t);
    }
  };

  COMP.Texto = (ctx, o) => {
    const tx = el("text", { class: o.classe || "rot-linha", x: o.x, y: o.y, "text-anchor": o.ancora || "middle", style: o.estilo || "", texto: o.texto }, ctx.svg);
    const t = quando(ctx.cena, o.em, .2);
    aparecer(tx, t, T.medio, 0);
    if (o.pulso) tl.to(tx, { opacity: .35, duration: 1.1, ease: C.respira, yoyo: true, repeat: o.pulso }, t + T.medio);
    if (o.some_em) tl.to(tx, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
  };

  COMP.Linha = (ctx, o) => {  // chão, régua, guia
    const p = el("path", { class: o.classe || "s", d: o.d }, ctx.svg);
    tl.fromTo(p, { drawSVG: "0%" }, { drawSVG: "100%", duration: o.dur || T.lento, ease: C.desenha }, quando(ctx.cena, o.em, 0));
    if (o.rotulo) aparecer(el("text", { class: "rot", x: o.rx, y: o.ry, texto: o.rotulo.toUpperCase() }, ctx.svg), quando(ctx.cena, o.em, 0) + .3, T.medio, 0);
  };

  // mapa de uma região (contorno próprio, curvas de nível, pinos e rota com marcador)
  COMP.Mapa = (ctx, o) => {
    const base = o.dados || D.regioes[o.regiao] || {};
    const R = { ...base, lugares: { ...(base.lugares || {}), ...(o.lugares || {}) } };
    const polis = R.poligonos || [R.contorno];
    const g = el("g", {}, ctx.svg);
    const todos = polis.flat();
    const caixaLL = o.bbox || [Math.min(...todos.map(p => p[0])), Math.min(...todos.map(p => p[1])),
      Math.max(...todos.map(p => p[0])), Math.max(...todos.map(p => p[1]))];
    const lat0 = (caixaLL[1] + caixaLL[3]) / 2;
    const kx = Math.cos(lat0 * Math.PI / 180) * 111.32, ky = 110.57;
    const km = ([lon, lat]) => [lon * kx, -lat * ky];
    const [x0, y1] = km([caixaLL[0], caixaLL[1]]), [x1, y0] = km([caixaLL[2], caixaLL[3]]);
    const esc = Math.min(o.largura / (x1 - x0), o.altura / (y1 - y0));
    const cx = o.x - (x0 + x1) / 2 * esc, cy = o.y - (y0 + y1) / 2 * esc;
    const proj = ll => { const [a, b] = km(ll); return [cx + a * esc, cy + b * esc]; };
    const lugar = n => proj(R.lugares[n] || n);
    const corte = `mc${++uid}`;
    el("clipPath", { id: corte, html: `<rect x="${o.x - o.largura / 2 - 30}" y="${o.y - o.altura / 2 - 30}" width="${o.largura + 60}" height="${o.altura + 60}" rx="24"/>` }, g);
    const terra = el("g", { "clip-path": `url(#${corte})` }, g);
    const contornos = [], massas = [];
    for (const poli of polis) {
      if (poli.length < 3) continue;
      const d = R.poligonos ? "M" + poli.map(proj).map(p => p.map(v => v.toFixed(1)).join(",")).join(" L") + " Z" : suave(poli.map(proj), true);
      massas.push(el("path", { class: "m", d }, terra));
      contornos.push(el("path", { class: "l", d, style: R.poligonos ? "stroke-width:3" : "" }, terra));
    }
    const t0 = quando(ctx.cena, o.em, .1);
    tl.fromTo(contornos, { drawSVG: "0%" }, { drawSVG: "100%", duration: 1.6, ease: C.desenha, stagger: .4 / Math.max(1, contornos.length) }, t0);
    tl.fromTo(massas, { opacity: 0 }, { opacity: 1, duration: T.lento }, t0 + 1.2);
    for (const r of o.rios || []) {  // rio, estrada ou linha qualquer em lon/lat
      const rio = el("path", { class: r.classe || "d", d: suave(r.pontos.map(proj)) }, terra);
      tl.fromTo(rio, { drawSVG: "0%" }, { drawSVG: "100%", duration: 1.2, ease: C.desenha }, quando(ctx.cena, r.em, (t0 - ctx.cena.ini) + .8));
      if (r.rotulo) {
        const [lx, ly] = proj(r.rotulo_em || r.pontos[Math.floor(r.pontos.length / 2)]);
        aparecer(el("text", { class: "rot", x: lx.toFixed(0), y: ly.toFixed(0), texto: r.rotulo.toUpperCase() }, g), quando(ctx.cena, r.em, (t0 - ctx.cena.ini) + 1.2), T.medio, 0);
      }
    }
    // curvas de nível dos vulcões
    const aneis = [];
    for (const v of R.relevo || []) {
      const [vx, vy] = proj(v.centro);
      v.raios_km.forEach((rk, k) => {
        const rr = rk * esc;
        aneis.push(el("ellipse", { class: "d", cx: vx.toFixed(1), cy: vy.toFixed(1), rx: (rr * (v.alongar || 1)).toFixed(1), ry: rr.toFixed(1), style: `opacity:${(.75 - k * .15).toFixed(2)}` }, g));
      });
    }
    if (aneis.length) tl.fromTo(aneis, { drawSVG: "0%" }, { drawSVG: "100%", duration: .8, stagger: .06, ease: C.desenha }, quando(ctx.cena, o.relevo_em, (t0 - ctx.cena.ini) + .8));
    // escala gráfica
    if (o.escala_km) {
      const L = o.escala_km * esc, ex = o.x - o.largura / 2 + 10, ey = o.y + o.altura / 2 + 40;
      const reg = el("g", {}, g);
      el("path", { class: "s", d: `M${ex},${ey} L${(ex + L).toFixed(1)},${ey} M${ex},${ey - 10} L${ex},${ey + 10} M${(ex + L).toFixed(1)},${ey - 10} L${(ex + L).toFixed(1)},${ey + 10}` }, reg);
      el("text", { class: "rot", x: (ex + L + 18).toFixed(1), y: ey + 9, texto: `${o.escala_km} KM` }, reg);
      aparecer(reg, t0 + 1.2, T.medio, 0);
    }
    for (const p of o.pinos || []) {
      const [px, py] = lugar(p.lugar);
      const pg = el("g", {}, g);
      const anel = el("circle", { cx: px.toFixed(1), cy: py.toFixed(1), r: 26, class: "l", style: "stroke-width:3" }, pg);
      el("circle", { cx: px.toFixed(1), cy: py.toFixed(1), r: 10, fill: p.cor === "alerta" ? "#F2B33D" : "#5CF2E0" }, pg);
      const dx = p.lado === "esq" ? -1 : 1, lx = px + dx * 56, ly = py + (p.dy || -54);
      el("path", { class: "d", d: `M${(px + dx * 22).toFixed(1)},${(py - 14).toFixed(1)} L${lx.toFixed(1)},${(ly + 10).toFixed(1)}` }, pg);
      el("text", { class: "rot-linha", x: (lx + dx * 8).toFixed(1), y: ly.toFixed(1), "text-anchor": dx > 0 ? "start" : "end", texto: p.rotulo.toUpperCase() }, pg);
      const t = quando(ctx.cena, p.em, (t0 - ctx.cena.ini) + 1);
      tl.fromTo(pg, { opacity: 0 }, { opacity: 1, duration: T.rapido }, t);
      som(t, "pop");
      tl.fromTo(anel, { scale: 2.2, transformOrigin: "50% 50%" }, { scale: 1, duration: T.lento, ease: C.entra }, t);
    }
    if (o.rota) {
      const pts = o.rota.lugares.map(lugar);
      const d = suave(pts);
      const id = `m${++uid}`;
      const mask = el("mask", { id, maskUnits: "userSpaceOnUse", x: -2000, y: -2000, width: 5000, height: 5000 }, g);
      const revela = el("path", { d, fill: "none", stroke: "#fff", "stroke-width": 20, "stroke-linecap": "round" }, mask);
      el("path", { d, class: "l tracejado", mask: `url(#${id})`, style: "stroke-width:6" }, g);
      const guia = el("path", { d, fill: "none", stroke: "none" }, g);
      const marca = el("g", {}, g);
      if (o.rota.marcador) {
        const h = peca(ctx, o.rota.marcador, { x: 0, base: 0, altura: o.rota.marcador_altura || 70, pai: marca });
        h.g0.setAttribute("transform", `translate(${(-h.vw * h.s / 2).toFixed(1)} ${(-h.vh * h.s).toFixed(1)})`);
      } else el("circle", { r: 14, fill: "#5CF2E0" }, marca);
      const t = quando(ctx.cena, o.rota.em, (t0 - ctx.cena.ini) + 1.4);
      const dur = o.rota.dur || 2.2;
      tl.fromTo(revela, { drawSVG: "0%" }, { drawSVG: "100%", duration: dur, ease: C.desenha }, t);
      tl.fromTo(marca, { opacity: 0 }, { opacity: 1, duration: T.rapido }, t);
      percorrer(marca, guia, t, dur, C.desenha);
      if (o.rota.km) {
        const fimP = o.rota.km_no_meio ? pts[Math.floor(pts.length / 2)] : pts[pts.length - 1];
        const rk = el("text", { class: "rot-linha", x: (fimP[0] + (o.rota.km_dx || 0)).toFixed(1), y: (fimP[1] + (o.rota.km_dy || 64)).toFixed(1), "text-anchor": "middle", texto: o.rota.km }, g);
        aparecer(rk, t + dur * .8, T.medio, 0);
      }
    }
  };

  // ---------- mais componentes (mecanismos e dados)

  // trem de engrenagens com dentes de verdade; cada uma gira na razão certa (sentidos alternados)
  function rodaDentada(n, r) {
    const m = 2 * r / n, ra = r + m, rd = r - 1.25 * m, s = 2 * Math.PI / n, pts = [];
    for (let k = 0; k < n; k++) {
      const a = k * s;
      for (const [rr, f] of [[rd, 0], [ra, .28], [ra, .5], [rd, .78]]) pts.push([rr * Math.cos(a + f * s), rr * Math.sin(a + f * s)]);
    }
    return "M" + pts.map(p => p.map(v => v.toFixed(1)).join(",")).join(" L") + " Z";
  }
  COMP.Engrenagens = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const t = quando(ctx.cena, o.em, .2);
    const fim = o.para_em != null ? quando(ctx.cena, o.para_em) : ctx.cena.fim;
    const voltas0 = (o.rps || .25) * Math.max(.5, fim - t);
    o.trem.forEach((e, k) => {
      const gg = el("g", { transform: `translate(${e.x} ${e.y})` }, g);
      const roda = el("g", {}, gg);
      el("path", { class: "m", d: rodaDentada(e.dentes, e.raio) }, roda);
      const contorno = el("path", { class: e.cor === "alerta" ? "a" : "l", d: rodaDentada(e.dentes, e.raio), style: "stroke-width:3" }, roda);
      const miolo = el("circle", { class: "d", r: Math.max(10, e.raio * .18) }, roda);
      const raios = el("path", { class: "d", d: [0, 1, 2, 3].map(q => { const a = q * Math.PI / 2 + Math.PI / 4;
        return `M${(Math.cos(a) * e.raio * .2).toFixed(1)},${(Math.sin(a) * e.raio * .2).toFixed(1)} L${(Math.cos(a) * e.raio * .72).toFixed(1)},${(Math.sin(a) * e.raio * .72).toFixed(1)}`; }).join(" ") }, roda);
      tl.fromTo([contorno, miolo, raios], { drawSVG: "0%" }, { drawSVG: "100%", duration: .8, ease: C.desenha }, Math.max(ctx.cena.ini + .05, t - 1 + k * .12));
      const sentido = (o.sentidos || [])[k] ?? (k % 2 ? -1 : 1);
      const razao = o.trem[0].dentes / e.dentes;
      tl.fromTo(roda, { rotation: e.fase || 0, svgOrigin: "0 0" }, { rotation: (e.fase || 0) + sentido * razao * voltas0 * 360, svgOrigin: "0 0", duration: fim - t, ease: C.linear, immediateRender: false }, t);
      if (e.rotulo) aparecer(el("text", { class: "rot-linha", x: e.x, y: e.y + e.raio + 50, "text-anchor": "middle", texto: e.rotulo.toUpperCase() }, g), t, T.medio, 0);
    });
  };

  // ondas que se espalham (som, eco, tremor)
  COMP.Onda = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const [x, y] = o.origem, R = o.raio || 380, n = o.n || 3, t = quando(ctx.cena, o.em, .2);
    const cls = o.cor === "alerta" ? "a" : "l";
    for (let k = 0; k < n; k++) {
      const c = el("circle", { cx: x, cy: y, r: 10, class: cls, style: "stroke-width:4", "data-livre": 1 }, g);
      if (o.arco) c.setAttribute("style", `stroke-width:4;stroke-dasharray:${o.arco}`);
      const tk = t + k * (o.atraso || .35);
      tl.fromTo(c, { attr: { r: 10 }, opacity: .95 }, { attr: { r: R }, opacity: 0, duration: o.dur || 1.4, ease: "power1.out" }, tk);
      if (k === 0) som(tk, "pop");
    }
  };

  // feixe de luz que entra e acende o alvo
  COMP.Feixe = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const [x0, y0] = o.de, [x1, y1] = o.para, L = o.largura || 26;
    const brilho = el("path", { d: `M${x0},${y0} L${x1},${y1}`, stroke: "rgba(242,179,61,.28)", "stroke-width": L * 2.4, "stroke-linecap": "round", fill: "none" }, g);
    const nucleo = el("path", { d: `M${x0},${y0} L${x1},${y1}`, stroke: "#F2B33D", "stroke-width": L, "stroke-linecap": "round", fill: "none", class: "brilho-ambar" }, g);
    const t = quando(ctx.cena, o.em, .2), dur = o.dur || 1.6;
    tl.fromTo([brilho, nucleo], { drawSVG: "0%" }, { drawSVG: "100%", duration: dur, ease: C.desenha }, t);
    if (o.alvo_acende) {
      const [ax, ay] = o.alvo_acende;
      const luz = el("circle", { cx: ax, cy: ay, r: o.raio_alvo || 70, fill: "rgba(242,179,61,.35)", class: "brilho-ambar" }, g);
      tl.fromTo(luz, { opacity: 0, scale: .3, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: T.lento, ease: C.entra }, t + dur * .95);
      som(t + dur, "ding");
    }
  };

  // sol âmbar percorrendo um arco no céu
  COMP.Sol = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const [x0, y0, x1, y1, xc, yc] = o.arco;
    const guia = el("path", { d: `M${x0},${y0} Q${xc},${yc} ${x1},${y1}`, fill: "none", stroke: "rgba(242,179,61,.35)", "stroke-width": 3, "stroke-dasharray": "6 10", "data-livre": 1 }, g);
    const sol = el("g", {}, g);
    el("circle", { r: 46, fill: "#F2B33D", class: "brilho-ambar" }, sol);
    for (let k = 0; k < 12; k++) {
      const a = k * Math.PI / 6;
      el("path", { d: `M${(Math.cos(a) * 60).toFixed(1)},${(Math.sin(a) * 60).toFixed(1)} L${(Math.cos(a) * 80).toFixed(1)},${(Math.sin(a) * 80).toFixed(1)}`, class: "a", style: "stroke-width:4" }, sol);
    }
    const t = quando(ctx.cena, o.em, .2);
    tl.fromTo(guia, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento }, Math.max(ctx.cena.ini, t - .3));
    tl.fromTo(sol, { opacity: 0 }, { opacity: 1, duration: T.medio }, t);
    percorrer(sol, guia, t, o.dur || 2.4, C.respira);
    if (o.rotulo) aparecer(el("text", { class: "rot", x: x1, y: y1 + 120, "text-anchor": "middle", style: "fill:#F2B33D", texto: o.rotulo.toUpperCase() }, g), t + .5, T.medio, 0);
  };

  // muro poligonal (células de Voronoi com semente): pedras encaixadas sem fresta
  COMP.Voronoi = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const r = sorteio(`${D.semente}-${o.semente || "voronoi"}`);
    const [X, Y, W, H] = [o.x, o.y, o.largura, o.altura], n = o.n || 18;
    let s = Array.from({ length: n }, () => [X + r() * W, Y + r() * H]);
    const recorta = (poli, a, b) => {  // mantém o lado de a no bissetor entre a e b
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1], out = [];
      const f = p => (p[0] - mx) * dx + (p[1] - my) * dy;
      for (let i = 0; i < poli.length; i++) {
        const p = poli[i], q = poli[(i + 1) % poli.length], fp = f(p), fq = f(q);
        if (fp <= 0) out.push(p);
        if ((fp < 0) !== (fq < 0)) { const u = fp / (fp - fq); out.push([p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u]); }
      }
      return out;
    };
    const celulas = () => s.map((a, i) => s.reduce((poli, b, j) => i === j ? poli : recorta(poli, a, b), [[X, Y], [X + W, Y], [X + W, Y + H], [X, Y + H]]));
    for (let it = 0; it < 2; it++) s = celulas().map(c => [c.reduce((v, p) => v + p[0], 0) / c.length, c.reduce((v, p) => v + p[1], 0) / c.length]);
    const cs = celulas(), folga = o.juntas ?? 0;
    const pedras = cs.map(c => {
      const cx = c.reduce((v, p) => v + p[0], 0) / c.length, cy = c.reduce((v, p) => v + p[1], 0) / c.length;
      const d = "M" + c.map(p => [cx + (p[0] - cx) * (1 - folga), cy + (p[1] - cy) * (1 - folga)].map(v => v.toFixed(1)).join(",")).join(" L") + " Z";
      el("path", { class: "m", d }, g);
      return el("path", { class: "l", d, style: "stroke-width:4" }, g);
    });
    const ordem = pedras.map(p => [r(), p]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
    const t = quando(ctx.cena, o.em, .2);
    tl.fromTo(ordem, { drawSVG: "0%" }, { drawSVG: "100%", duration: .5, ease: C.desenha, stagger: (o.dur || 1.6) / n }, t);
    if (o.id) ctx.reg[o.id] = { g, celulas: cs };
  };

  // linha do tempo com marcos que aparecem na palavra; anos negativos viram "a.C."
  COMP.LinhaDoTempo = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const x = o.x ?? 80, y = o.y ?? 520, L = o.largura ?? 800;
    const anos = o.marcos.map(m => m.ano), de = o.de ?? Math.min(...anos), ate = o.ate ?? Math.max(...anos);
    const esc = a => x + (a - de) / ((ate - de) || 1) * L;
    const eixo = el("path", { class: "s", d: `M${x - 20},${y} L${x + L + 20},${y}`, style: "stroke-width:4" }, g);
    const t0 = quando(ctx.cena, o.em, .1);
    tl.fromTo(eixo, { drawSVG: "0%" }, { drawSVG: "100%", duration: .8, ease: C.desenha }, t0);
    o.marcos.forEach((m, k) => {
      const mx = esc(m.ano), cima = m.lado ? m.lado === "cima" : k % 2 === 0, mg = el("g", {}, g);
      el("path", { class: m.destaque ? "l" : "d", d: `M${mx},${y - 18} L${mx},${y + 18}` }, mg);
      el("circle", { cx: mx, cy: y, r: m.destaque ? 13 : 9, fill: m.destaque ? "#5CF2E0" : "rgba(232,226,212,.75)" }, mg);
      const ano = m.ano < 0 ? `${fmt(-m.ano)} a.C.` : String(m.ano);
      el("text", { class: "num", x: mx, y: cima ? y - 46 : y + 84, "text-anchor": "middle", style: `font-size:${m.destaque ? 54 : 42}px;fill:${m.destaque ? "#5CF2E0" : "#F4F1EA"}`, texto: m.texto_ano || ano }, mg);
      el("text", { class: "rot", x: mx, y: cima ? y - 104 : y + 124, "text-anchor": "middle", texto: m.rotulo.toUpperCase() }, mg);
      const tm = quando(ctx.cena, m.em, (t0 - ctx.cena.ini) + .6 + k * .45);
      aparecer(mg, tm, T.medio, cima ? 10 : -10);
      som(tm, "pop");
    });
  };

  // tela dividida: dois lados com títulos e o símbolo no meio; cada lado tem os próprios itens em 0..440 de largura
  COMP.TelaDividida = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const t = quando(ctx.cena, o.em, .1);
    const meio = el("path", { class: "s", d: "M480,80 L480,900", style: "stroke-dasharray:10 12" }, g);
    tl.fromTo(meio, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento }, t);
    const fundo = el("circle", { cx: 480, cy: 466, r: 60, fill: "#0B0F14" }, g);
    const simb = el("text", { class: "num", x: 480, y: 500, "text-anchor": "middle", style: "font-size:96px;fill:#F2B33D", texto: o.simbolo || "≠" }, g);
    aparecer([fundo, simb], quando(ctx.cena, o.simbolo_em, (t - ctx.cena.ini) + .5), T.medio, 0);
    [["esq", 20], ["dir", 500]].forEach(([lado, dx]) => {
      const L = o[lado];
      if (!L) return;
      const sub = el("g", { transform: `translate(${dx} 0)` }, g);
      g.insertBefore(sub, fundo);
      if (L.titulo) aparecer(el("text", { class: lado === "esq" ? "rot" : "rot-linha", x: 220, y: 70, "text-anchor": "middle", style: `font-size:30px${L.cor === "alerta" ? ";fill:#F2B33D" : ""}`, texto: L.titulo.toUpperCase() }, sub), t, T.medio, 0);
      for (const it of L.itens || []) montar({ ...ctx, svg: sub }, it);
    });
  };

  // seta por um caminho qualquer, com ponta calculada no fim
  COMP.Seta = (ctx, o) => {
    const g = el("g", { opacity: 0 }, ctx.svg);
    const cls = o.cor === "alerta" ? "a" : "l";
    const p = el("path", { class: cls, d: o.d, style: "stroke-width:6" }, g);
    const L = p.getTotalLength(), a = p.getPointAtLength(Math.max(0, L - 14)), b = p.getPointAtLength(L);
    const ang = Math.atan2(b.y - a.y, b.x - a.x), ab = 24;
    const ponta = el("path", { class: cls, style: "stroke-width:6", d: `M${(b.x + Math.cos(ang + 2.6) * ab).toFixed(1)},${(b.y + Math.sin(ang + 2.6) * ab).toFixed(1)} L${b.x.toFixed(1)},${b.y.toFixed(1)} L${(b.x + Math.cos(ang - 2.6) * ab).toFixed(1)},${(b.y + Math.sin(ang - 2.6) * ab).toFixed(1)}` }, g);
    const t = quando(ctx.cena, o.em, .2);
    tl.set(g, { opacity: 1 }, t);
    tl.fromTo(p, { drawSVG: "0%" }, { drawSVG: "100%", duration: o.dur || T.lento, ease: C.desenha }, t);
    tl.fromTo(ponta, { opacity: 0 }, { opacity: 1, duration: T.rapido }, t + (o.dur || T.lento) * .9);
    if (o.rotulo) aparecer(el("text", { class: o.cor === "alerta" ? "rot" : "rot-linha", x: o.rx ?? b.x, y: o.ry ?? b.y - 24, "text-anchor": "middle", style: o.cor === "alerta" ? "fill:#F2B33D" : "", texto: o.rotulo.toUpperCase() }, g), t + .3, T.medio, 0);
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
  };

  // cota: medida com traços nas pontas e o valor no meio
  COMP.Cota = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const [x0, y0] = o.de, [x1, y1] = o.para, a = Math.atan2(y1 - y0, x1 - x0), nx = -Math.sin(a) * 14, ny = Math.cos(a) * 14;
    const linha = el("path", { class: "d", d: `M${x0},${y0} L${x1},${y1} M${x0 + nx},${y0 + ny} L${x0 - nx},${y0 - ny} M${x1 + nx},${y1 + ny} L${x1 - nx},${y1 - ny}` }, g);
    const tx = el("text", { class: "rot-linha", x: ((x0 + x1) / 2 + (o.tx || 0)).toFixed(0), y: ((y0 + y1) / 2 + (o.ty ?? -18)).toFixed(0), "text-anchor": "middle", texto: o.texto.toUpperCase() }, g);
    const t = quando(ctx.cena, o.em, .2);
    tl.fromTo(linha, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento, ease: C.desenha }, t);
    aparecer(tx, t + .3, T.medio, 0);
  };

  // retângulo, elipse ou caminho com preenchimento (corte de terreno, câmara, bloco)
  COMP.Forma = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const d = o.d || (o.elipse ? `M${o.x - o.rx},${o.y} a${o.rx},${o.ry} 0 1,0 ${2 * o.rx},0 a${o.rx},${o.ry} 0 1,0 ${-2 * o.rx},0 Z` :
      `M${o.x},${o.y} L${o.x + o.largura},${o.y} L${o.x + o.largura},${o.y + o.altura} L${o.x},${o.y + o.altura} Z`);
    if (o.preencher !== false) el("path", { class: o.hachura ? "h" : "m", d }, g);
    const tr = el("path", { class: o.classe || "l", d }, g);
    const t = quando(ctx.cena, o.em, .1);
    tl.fromTo(tr, { drawSVG: "0%" }, { drawSVG: "100%", duration: o.dur || T.desenha, ease: C.desenha }, t);
    const cheios = g.querySelectorAll(".m,.h");
    if (cheios.length) tl.fromTo(cheios, { opacity: 0 }, { opacity: 1, duration: T.lento }, t + .5);
    if (o.rotulo) aparecer(el("text", { class: "rot", x: o.rx_rotulo ?? (o.x ?? 0), y: o.ry_rotulo ?? ((o.y ?? 0) - 18), texto: o.rotulo.toUpperCase() }, g), t + .4, T.medio, 0);
    if (o.id) ctx.reg[o.id] = { g };
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
  };

  // trajeto com pegadas e marcador (planta): o objeto anda de verdade pelo caminho
  COMP.Trajeto = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const d = suave(o.pontos);
    const id = `m${++uid}`;
    const mask = el("mask", { id, maskUnits: "userSpaceOnUse", x: -2000, y: -2000, width: 5000, height: 5000 }, g);
    const revela = el("path", { d, fill: "none", stroke: "#fff", "stroke-width": 16, "stroke-linecap": "round" }, mask);
    el("path", { d, class: "d tracejado", mask: `url(#${id})` }, g);
    const guia = el("path", { d, fill: "none", stroke: "none" }, g);
    const t = quando(ctx.cena, o.em, .2), dur = o.dur || 2.4;
    tl.fromTo(revela, { drawSVG: "0%" }, { drawSVG: "100%", duration: dur, ease: C.linear }, t);
    if (o.pegadas) {
      o.pontos.forEach((p, k) => {
        const pe = el("ellipse", { cx: p[0], cy: p[1], rx: 16, ry: 9, fill: "rgba(92,242,224,.35)", stroke: "#5CF2E0", "stroke-width": 2 }, g);
        tl.fromTo(pe, { opacity: 0, scale: .4, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: T.rapido, ease: C.entra }, t + dur * k / (o.pontos.length - 1));
      });
    }
    const marca = el("g", {}, g);
    const h = peca(ctx, o.marcador || "moai-topo", { x: 0, base: 0, altura: o.marcador_altura || 110, pai: marca });
    h.g0.setAttribute("transform", `translate(${(-h.vw * h.s / 2).toFixed(1)} ${(-h.vh * h.s / 2).toFixed(1)})`);
    desenhar(h.gr, t - .5, .45);
    percorrer(marca, guia, t, dur, C.linear);
    if (o.balanco) tl.fromTo(h.gr, { rotation: -o.balanco, svgOrigin: `${h.vw / 2} ${h.vh / 2}` },
      { rotation: o.balanco, duration: dur / (o.passos || 6), ease: C.respira, yoyo: true, repeat: (o.passos || 6) - 1, svgOrigin: `${h.vw / 2} ${h.vh / 2}`, immediateRender: false }, t);
  };

  // plano 2.5D (vista de cima inclinada): os componentes dentro dele são desenhados num SVG deitado
  COMP.Planta = (ctx, o) => {
    const cx = div({ class: "plano-caixa" }, ctx.wrap);
    const pl = div({ class: "plano" }, cx);
    const svg = el("svg", { viewBox: "0 0 960 980" }, pl);
    const grade = el("g", {}, svg);
    for (let x = 80; x <= 880; x += 80) el("path", { class: "s", style: "opacity:.25;stroke-width:2", d: `M${x},140 L${x},900` }, grade);
    for (let y = 140; y <= 900; y += 80) el("path", { class: "s", style: "opacity:.25;stroke-width:2", d: `M80,${y} L880,${y}` }, grade);
    const sub = { ...ctx, svg: el("g", {}, svg) };
    const t = quando(ctx.cena, o.em, 0);
    const esc = o.escala ?? .86;  // o plano deitado cresce para a frente na perspectiva: um pouco menor cabe no palco
    tl.fromTo(pl, { rotationX: o.inclinacao ?? 52, scale: esc, opacity: 0, y: 40 }, { rotationX: o.inclinacao ?? 52, scale: esc, opacity: 1, y: 0, duration: T.lento, ease: C.suave }, t);
    if (o.em_sobe) tl.to(pl, { rotationX: 0, duration: 1.2, ease: C.respira }, quando(ctx.cena, o.em_sobe));
    if (o.some_em) tl.to(pl, { opacity: 0, duration: T.medio }, quando(ctx.cena, o.some_em));
    for (const it of o.itens) montar(sub, it);
  };

  // ---------- texto medido por tabela (Georgia do Windows, medida em 2026-11-12): determinístico, não depende de a
  // fonte já ter carregado quando o roteiro é montado. Acento conta como a letra sem acento.
  const LETRAS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,:;!?-'";
  const LARG = Object.fromEntries(Object.entries({
    negrito: "60 65 53 66 57 39 58 68 35 35 63 34 102 69 64 66 65 52 51 40 68 57 86 59 56 53 76 76 72 83 72 67 81 91 45 60 82 69 102 84 82 70 82 80 65 68 83 76 113 81 73 69 70 49 63 62 65 60 65 55 68 65 25 33 33 37 37 38 55 38 27",
    italico: "57 55 45 58 47 33 57 56 30 29 53 29 88 59 54 58 56 46 43 35 58 54 82 50 56 44 67 65 64 75 65 60 73 81 39 52 69 60 93 77 73 61 73 70 56 62 76 67 98 71 62 60 61 43 56 55 56 53 57 50 60 57 24 27 27 38 38 33 48 37 22",
  }).map(([f, s]) => [f, Object.fromEntries(s.split(" ").map((v, i) => [LETRAS[i], v / 100]))]));
  const largura = (s, tam, fam = "negrito") => [...String(s)].reduce((a, c) => a + (LARG[fam][c.normalize("NFD")[0]] ?? .6), 0) * tam;
  // quebra em linhas que cabem em "max" px
  function quebrar(texto, tam, max, fam = "negrito") {
    const linhas = [];
    let atual = "";
    for (const p of String(texto).split(/\s+/).filter(Boolean)) {
      const tenta = atual ? `${atual} ${p}` : p;
      if (atual && largura(tenta, tam, fam) > max) { linhas.push(atual); atual = p; } else atual = tenta;
    }
    if (atual) linhas.push(atual);
    return linhas;
  }
  // maior tamanho (de "tam" para baixo) em que o texto cabe em até "maxLinhas" linhas
  function caber(texto, tam, max, maxLinhas, fam = "negrito", minimo = 30) {
    for (let s = tam; s >= minimo; s -= 2) {
      const l = quebrar(texto, s, max, fam);
      if (l.length <= maxLinhas && l.every(x => largura(x, s, fam) <= max)) return { tam: s, linhas: l };
    }
    return { tam: minimo, linhas: quebrar(texto, minimo, max, fam) };
  }
  // contorno "feito à mão" em volta de uma caixa (para circular uma palavra), com semente
  function circulo(cx, cy, rx, ry, semente) {
    const r = sorteio(semente), pts = [];
    for (let k = 0; k <= 14; k++) {
      const a = -2.5 + k / 13 * Math.PI * 2.1, f = 1 + (r() - .5) * .08;
      pts.push([cx + Math.cos(a) * rx * f, cy + Math.sin(a) * ry * f]);
    }
    return suave(pts);
  }

  // manchete de jornal: a folha entra girando, a manchete se imprime palavra a palavra e as colunas se desenham.
  // O nome do jornal é sempre inventado (nunca o de um jornal de verdade) e a manchete é texto próprio.
  COMP.Manchete = (ctx, o) => {
    const Wd = o.largura || 760, Hd = o.altura || (o.foto ? 820 : 720), x0 = (o.x ?? 480) - Wd / 2, y0 = o.y ?? (980 - Hd) / 2, pad = 34, aw = Wd - 2 * pad;
    const giro = el("g", {}, ctx.svg);
    const g = el("g", { transform: `translate(${x0} ${y0})` }, giro);
    el("rect", { class: "chapa", x: 0, y: 0, width: Wd, height: Hd, rx: 6 }, g);
    const borda = el("rect", { class: "l", x: 0, y: 0, width: Wd, height: Hd, rx: 6, style: "stroke-width:4" }, g);
    // cabeçalho do jornal: nome, data e fios
    const nomeJ = String(o.jornal || "O Diário").toUpperCase();
    const tj = Math.min(64, (aw - 2 * nomeJ.length) / Math.max(1, largura(nomeJ, 1)));  // + 2 px de espaço entre letras
    el("text", { class: "jornal", x: Wd / 2, y: pad + tj * .82, "text-anchor": "middle", style: `font-size:${tj.toFixed(1)}px`, texto: nomeJ }, g);
    let y = pad + tj + 14;
    el("path", { class: "s", d: `M${pad},${y} L${Wd - pad},${y}`, style: "stroke-width:2" }, g);
    el("text", { class: "rot", x: pad, y: y + 30, style: "font-size:20px;opacity:.8", texto: String(o.data || "").toUpperCase() }, g);
    el("text", { class: "rot", x: Wd - pad, y: y + 30, "text-anchor": "end", style: "font-size:20px;opacity:.8", texto: String(o.edicao || "edição extra").toUpperCase() }, g);
    y += 44;
    el("path", { class: "s", d: `M${pad},${y} L${Wd - pad},${y} M${pad},${y + 6} L${Wd - pad},${y + 6}`, style: "stroke-width:2" }, g);
    y += 30;
    // manchete: o maior tamanho que cabe em até 3 linhas
    const M = caber(o.titulo, o.tam || (o.foto ? 66 : 78), aw, o.max_linhas || 3, "negrito", 36);
    const palavras = [];
    const caixas = {};
    M.linhas.forEach((linha, k) => {
      const yy = y + M.tam * (.86 + k * 1.04);
      const tx = el("text", { class: "manchete", x: Wd / 2, y: yy.toFixed(1), "text-anchor": "middle", style: `font-size:${M.tam}px` }, g);
      let cx = Wd / 2 - largura(linha, M.tam) / 2;
      linha.split(" ").forEach((p, j) => {
        const sp = el("tspan", { texto: (j ? " " : "") + p }, tx);
        palavras.push(sp);
        if (j) cx += largura(" ", M.tam);
        const w = largura(p, M.tam);
        caixas[norm(p)] = caixas[norm(p)] || [cx + w / 2, yy - M.tam * .34, w / 2 + 16, M.tam * .62];
        cx += w;
      });
    });
    y += M.tam * (M.linhas.length * 1.04 + .3);
    let fina = null;
    if (o.linha_fina) {
      const F = caber(o.linha_fina, 30, aw, 2, "italico", 22);
      fina = el("g", {}, g);
      F.linhas.forEach((l, k) => el("text", { class: "linha-fina", x: Wd / 2, y: (y + F.tam * (.9 + k * 1.15)).toFixed(1), "text-anchor": "middle", style: `font-size:${F.tam}px`, texto: l }, fina));
      y += F.tam * (F.linhas.length * 1.15 + .4);
    }
    el("path", { class: "s", d: `M${pad},${y} L${Wd - pad},${y}`, style: "stroke-width:2" }, g);
    y += 22;
    // colunas de texto (traços), com foto opcional na primeira
    const nc = o.colunas || 3, gap = 24, cw = (aw - gap * (nc - 1)) / nc, rr = sorteio(`${D.semente}-manchete-${o.titulo}`);
    const corpo = [];
    let fotoG = null, fotoPeca = null;
    for (let c = 0; c < nc; c++) {
      const cx = pad + c * (cw + gap);
      let yy = y;
      if (c === 0 && o.foto) {
        const larg = nc >= 3 ? cw * 2 + gap : cw, alt = Math.min(280, (Hd - y - pad) * .78);
        fotoG = el("g", {}, g);
        el("rect", { class: o.foto.peca ? "m" : "h", x: cx, y: yy, width: larg, height: alt }, fotoG);
        el("rect", { class: "s", x: cx, y: yy, width: larg, height: alt, style: "stroke-width:2" }, fotoG);
        if (o.foto.peca) {
          fotoPeca = peca(ctx, o.foto.peca, { x: cx + larg / 2, base: yy + alt - 12, altura: alt - 30, pai: fotoG });
        }
        if (nc >= 3) { // a foto ocupa duas colunas: a segunda começa embaixo dela também
          corpo.push(...colunaTracos(g, cx + cw + gap, yy + alt + 24, cw, Hd - pad, rr));
          c++;
        }
        yy += alt + 24;
      }
      corpo.push(...colunaTracos(g, cx, yy, cw, Hd - pad, rr));
      if (c < nc - 1) el("path", { class: "s", d: `M${cx + cw + gap / 2},${y} L${cx + cw + gap / 2},${Hd - pad}`, style: "stroke-width:1.5;opacity:.5" }, g);
    }
    // tempo: entra (girando ou caindo), imprime a manchete, a linha fina e as colunas
    const t = quando(ctx.cena, o.em, .1), cx0 = x0 + Wd / 2, cy0 = y0 + Hd / 2, fim = o.gira ?? -2;
    som(t, "whoosh");
    if (o.giro === false) {
      tl.fromTo(giro, { opacity: 0, y: -40, rotation: fim, svgOrigin: `${cx0} ${cy0}` }, { opacity: 1, y: 0, rotation: fim, svgOrigin: `${cx0} ${cy0}`, duration: T.lento, ease: C.entra }, t);
      tl.fromTo(borda, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento, ease: C.desenha }, t);
    } else {
      tl.fromTo(giro, { opacity: 0, scale: .2, rotation: fim - 360, svgOrigin: `${cx0} ${cy0}` },
        { opacity: 1, scale: 1, rotation: fim, svgOrigin: `${cx0} ${cy0}`, duration: .75, ease: "power3.out" }, t);
    }
    const pousa = t + (o.giro === false ? T.lento : .75);
    som(pousa - .05, "thud");
    tl.fromTo(palavras, { attr: { "fill-opacity": 0 } }, { attr: { "fill-opacity": 1 }, duration: .06, ease: C.linear, stagger: .11 }, pousa);
    const depois = pousa + palavras.length * .11 + .1;
    if (fina) aparecer(fina, depois, T.medio, 6);
    tl.fromTo(corpo, { drawSVG: "0%" }, { drawSVG: "100%", duration: .25, ease: C.suave, stagger: Math.min(.02, 1.2 / Math.max(1, corpo.length)) }, depois);
    if (fotoG) {
      tl.fromTo(fotoG, { opacity: 0 }, { opacity: 1, duration: T.medio }, depois);
      if (fotoPeca) desenhar(fotoPeca.gr, depois + .1, .9);
    }
    // destaque: a palavra da manchete ganha um círculo âmbar, como caneta no papel
    if (o.destaque) {
      const b = caixas[norm(String(o.destaque).split(/\s+/)[0])];
      if (!b) avisos.push(`cena ${ctx.cena.i}: Manchete: a palavra "${o.destaque}" não está no título`);
      else {
        const ci = el("path", { class: "a", d: circulo(b[0], b[1], b[2], b[3], `${D.semente}-${o.destaque}`), style: "stroke-width:6" }, g);
        const td = quando(ctx.cena, o.destaque_em, (depois - ctx.cena.ini) + .4);
        tl.fromTo(ci, { drawSVG: "0%" }, { drawSVG: "100%", duration: .45, ease: C.suave }, td);
        som(td, "pop");
      }
    }
    if (o.id) ctx.reg[o.id] = { g: giro };
    if (o.some_em) tl.to(giro, { opacity: 0, duration: T.medio, ease: C.sai }, quando(ctx.cena, o.some_em));
  };
  function colunaTracos(g, x, y, w, ymax, r) {
    const out = [];
    for (let yy = y + 8; yy <= ymax; yy += 22) {
      const fimPar = r() < .16;
      const len = fimPar ? w * (.3 + .45 * r()) : w;
      out.push(el("path", { class: "s", d: `M${x.toFixed(1)},${yy.toFixed(1)} L${(x + len).toFixed(1)},${yy.toFixed(1)}`, style: "stroke-width:5;opacity:.38" }, g));
      if (fimPar) yy += 12;
    }
    return out;
  }

  // painel de aeroporto (split-flap): cada plaqueta gira pelo alfabeto, na ordem fixa, até a letra certa.
  // Bom para revelar um nome, uma data ou um número; "passos" troca o texto depois.
  const ALFABETO = " ABCDEFGHIJKLMNOPQRSTUVWXYZÁÂÃÉÊÍÓÔÕÚÇ0123456789.,:-/%+";
  COMP.Painel = (ctx, o) => {
    const linhasDe = p => (p.linhas || [p.texto ?? ""]).map(s => String(s).toUpperCase());
    const etapas = [{ em: o.em, linhas: linhasDe(o), cor: o.cor }, ...(o.passos || []).map(p => ({ em: p.em, linhas: linhasDe(p), cor: p.cor ?? o.cor }))];
    const rows = Math.max(...etapas.map(e => e.linhas.length));
    const cols = Math.max(o.celulas || 0, ...etapas.flatMap(e => e.linhas.map(l => [...l].length)));
    const alinha = (l, n) => {
      const c = [...l];
      const sobra = n - c.length, esq = o.alinhar === "esquerda" ? 0 : Math.floor(sobra / 2);
      return [...Array(esq).fill(" "), ...c, ...Array(sobra - esq).fill(" ")];
    };
    const grade = linhas => Array.from({ length: rows }, (_, r) => alinha(linhas[r] || "", cols));
    let alfabeto = ALFABETO;
    for (const e of etapas) for (const l of e.linhas) for (const ch of l) if (!alfabeto.includes(ch)) alfabeto += ch;
    const A = [...alfabeto];
    // tamanho: a altura da plaqueta encolhe até o painel caber em 840 px de largura
    const h = Math.min(o.tam || 130, 840 / (cols * .7 + (cols - 1) * .08)), w = h * .7, gap = h * .08, rg = h * .16;
    const W = cols * w + (cols - 1) * gap, H = rows * h + (rows - 1) * rg;
    const bx = (o.x ?? 480) - W / 2, by = (o.y ?? 470) - H / 2;
    const g = el("g", {}, ctx.svg);
    const moldura = el("rect", { class: "l", x: bx - 24, y: by - 24, width: W + 48, height: H + 48, rx: 16 }, g);
    if (o.rotulo) el("text", { class: "rot-linha", x: bx - 24, y: by - 44, texto: o.rotulo.toUpperCase() }, g);
    const tam = h * .74, cor0 = "#F4F1EA", corDe = c => c === "alerta" ? "#F2B33D" : c === "linha" ? "#5CF2E0" : cor0;
    const cel = [];
    const plaquetas = el("g", {}, g);
    for (let r = 0; r < rows; r++) {
      for (let k = 0; k < cols; k++) {
        const cx = bx + k * (w + gap), cy = by + r * (h + rg), ym = cy + h / 2;
        const cg = el("g", {}, plaquetas);
        const id = `pf${++uid}`;
        el("clipPath", { id: `${id}c`, html: `<rect x="${cx}" y="${cy}" width="${w}" height="${h / 2}"/>` }, cg);
        el("clipPath", { id: `${id}b`, html: `<rect x="${cx}" y="${ym}" width="${w}" height="${h / 2}"/>` }, cg);
        el("rect", { x: cx, y: cy, width: w, height: h, rx: 6, fill: "#141B23", stroke: "rgba(232,226,212,.2)", "stroke-width": 2 }, cg);
        const letra = (y, clip) => el("text", { class: "flap", x: cx + w / 2, y, "text-anchor": "middle", style: `font-size:${tam.toFixed(1)}px`, "clip-path": `url(#${clip})` }, cg);
        const by0 = ym + tam * .36;
        const cima = letra(by0, `${id}c`), baixo = letra(by0, `${id}b`);
        // plaquetas que caem: a de cima (letra velha) fecha até o meio; a de baixo (letra nova) abre do meio
        const fc = el("g", { "clip-path": `url(#${id}c)` }, cg), fci = el("g", {}, fc);
        el("rect", { x: cx, y: cy, width: w, height: h, rx: 6, fill: "#1B242E" }, fci);
        const fcT = el("text", { class: "flap", x: cx + w / 2, y: by0, "text-anchor": "middle", style: `font-size:${tam.toFixed(1)}px` }, fci);
        const fb = el("g", { "clip-path": `url(#${id}b)` }, cg), fbi = el("g", {}, fb);
        el("rect", { x: cx, y: cy, width: w, height: h, rx: 6, fill: "#1B242E" }, fbi);
        const fbT = el("text", { class: "flap", x: cx + w / 2, y: by0, "text-anchor": "middle", style: `font-size:${tam.toFixed(1)}px` }, fbi);
        el("path", { d: `M${cx},${ym} L${cx + w},${ym}`, stroke: "#05070A", "stroke-width": 3 }, cg);
        cel.push({ ym, cima, baixo, fci, fcT, fbi, fbT, r, k });
      }
    }
    const pinta = (c, atual, prox, fase, cor) => {
      const s1 = fase < .5 ? 1 - fase * 2 : 0, s2 = fase < .5 ? 0 : fase * 2 - 1;
      c.cima.textContent = prox; c.baixo.textContent = atual; c.fcT.textContent = atual; c.fbT.textContent = prox;
      for (const e of [c.cima, c.baixo, c.fcT, c.fbT]) e.style.fill = cor;
      c.fci.setAttribute("transform", `translate(0 ${c.ym}) scale(1 ${s1.toFixed(3)}) translate(0 ${-c.ym})`);
      c.fbi.setAttribute("transform", `translate(0 ${c.ym}) scale(1 ${s2.toFixed(3)}) translate(0 ${-c.ym})`);
      c.fci.style.opacity = (1 - .45 * fase).toFixed(3);
    };
    const passo = o.passo || .06, maximo = o.max || 12;
    let atual = grade(o.de ? [String(o.de).toUpperCase()] : []), corPassada = cor0;
    cel.forEach(c => pinta(c, atual[c.r][c.k], atual[c.r][c.k], 0, cor0));
    const t0 = quando(ctx.cena, o.em, .1);
    tl.fromTo(moldura, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.lento, ease: C.desenha }, t0 - .45);
    tl.fromTo(plaquetas, { opacity: 0 }, { opacity: 1, duration: T.medio, ease: C.suave }, t0 - .3);
    if (o.rotulo) aparecer(g.querySelector("text.rot-linha"), t0 - .3, T.medio, 0);
    etapas.forEach((e, n) => {
      const alvo = grade(e.linhas), cor = corDe(e.cor);
      // cada plaqueta: a sequência do alfabeto entre a letra atual e a nova (no máximo "max" giros)
      const seqs = cel.map(c => {
        const de = A.indexOf(atual[c.r][c.k]), para = A.indexOf(alvo[c.r][c.k]);
        if (de === para) return [A[para]];
        let dist = (para - de + A.length) % A.length;
        let ini = de;
        if (dist > maximo) { ini = (para - maximo + A.length) % A.length; dist = maximo; }
        const s = de === ini ? [] : [A[de]];
        for (let j = 0; j <= dist; j++) s.push(A[(ini + j) % A.length]);
        return s;
      });
      const atraso = cel.map(c => (c.k * .025 + c.r * .06) / passo);
      const K = Math.max(...cel.map((c, i) => atraso[i] + seqs[i].length - 1));
      if (K <= 0) return;
      const t = n ? quando(ctx.cena, e.em) : t0, st = { k: 0 }, corAnt = corPassada;
      const desenha = () => cel.forEach((c, i) => {
        const s = seqs[i], kc = Math.min(Math.max(st.k - atraso[i], 0), s.length - 1), j = Math.floor(kc);
        const pronto = j >= s.length - 1;
        pinta(c, s[j], s[Math.min(j + 1, s.length - 1)], pronto ? 0 : kc - j, pronto ? cor : kc === 0 ? corAnt : cor0);
      });
      tl.to(st, { k: K, duration: K * passo, ease: C.linear, onUpdate: desenha }, t);
      som(t, "tique");
      atual = alvo; corPassada = cor;
    });
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio, ease: C.sai }, quando(ctx.cena, o.some_em));
  };

  // celular em camadas (vista explodida): fecha como um aparelho só e abre em vidro, tela, placa, bateria e carcaça,
  // cada camada com o nome ao lado. Desenho próprio em perspectiva isométrica (nada de marca nem modelo de verdade).
  const CAMADAS_CEL = { vidro: "VIDRO", tela: "TELA", placa: "PLACA", bateria: "BATERIA", carcaca: "CARCAÇA" };
  COMP.Celular = (ctx, o) => {
    const e = o.escala || 1, W = 225 * e, L = 465 * e, x = o.x ?? 330, y = o.y ?? 650, gap = (o.gap || 80) * e;
    const c30 = .866;
    const P = (u, v, z = 0) => [x + (u - v) * c30, y + (u + v) * .5 - z];
    const caminho = (pts, z = 0, fechado = true) => "M" + pts.map(([u, v]) => P(u, v, z).map(n => n.toFixed(1)).join(",")).join(" L") + (fechado ? " Z" : "");
    const rr = (u0, v0, w, h, r, n = 5) => {
      const pts = [];
      const canto = (cu, cv, a0) => { for (let k = 0; k <= n; k++) { const a = a0 + k / n * Math.PI / 2; pts.push([cu + Math.cos(a) * r, cv + Math.sin(a) * r]); } };
      canto(u0 + w - r, v0 + r, -Math.PI / 2); canto(u0 + w - r, v0 + h - r, 0); canto(u0 + r, v0 + h - r, Math.PI / 2); canto(u0 + r, v0 + r, Math.PI);
      return pts;
    };
    const roda = (cu, cv, r, n = 20) => Array.from({ length: n }, (_, k) => [cu + Math.cos(k / n * Math.PI * 2) * r, cv + Math.sin(k / n * Math.PI * 2) * r]);
    const reta = (pts) => caminho(pts, 0, false);
    const u0 = -W / 2, v0 = -L / 2;
    // cada camada: contorno, chapa (esconde o que está embaixo), espessura e detalhes, no plano (u, v)
    const DESENHO = {
      carcaca: { esp: 18 * e, contorno: rr(u0, v0, W, L, 34 * e), det: [
        ["l", rr(u0 + 14 * e, v0 + 14 * e, 92 * e, 92 * e, 22 * e)], ["d", roda(u0 + 40 * e, v0 + 40 * e, 15 * e)], ["d", roda(u0 + 80 * e, v0 + 40 * e, 15 * e)],
        ["d", roda(u0 + 40 * e, v0 + 80 * e, 15 * e)], ...[0, 1, 2, 3, 4].map(k => ["s", roda(-36 * e + k * 18 * e, L / 2 - 16 * e, 4 * e, 8)])] },
      bateria: { esp: 10 * e, contorno: rr(u0 + 24 * e, v0 + 160 * e, W - 48 * e, L * .52, 14 * e), det: [
        ["d", [[-14 * e, v0 + 200 * e], [14 * e, v0 + 200 * e]], 1], ["d", [[0, v0 + 186 * e], [0, v0 + 214 * e]], 1],
        ...[0, 1, 2].map(k => ["s", [[u0 + 50 * e, v0 + 250 * e + k * 40 * e], [W / 2 - 50 * e, v0 + 250 * e + k * 40 * e]], 1])] },
      placa: { esp: 6 * e, contorno: [[u0 + 10 * e, v0 + 10 * e], [W / 2 - 10 * e, v0 + 10 * e], [W / 2 - 10 * e, L / 2 - 40 * e], [W / 2 - 62 * e, L / 2 - 40 * e],
        [W / 2 - 62 * e, v0 + 150 * e], [u0 + 10 * e, v0 + 150 * e]], det: [
        ["l", rr(-6 * e, v0 + 40 * e, 58 * e, 58 * e, 6 * e)], ["d", rr(6 * e, v0 + 52 * e, 34 * e, 34 * e, 4 * e)],
        ["d", rr(W / 2 - 52 * e, v0 + 160 * e, 32 * e, 64 * e, 4 * e)], ["d", rr(W / 2 - 52 * e, v0 + 250 * e, 32 * e, 40 * e, 4 * e)],
        ["d", roda(u0 + 42 * e, v0 + 46 * e, 15 * e)], ["d", roda(u0 + 42 * e, v0 + 92 * e, 15 * e)],
        ["s", [[52 * e, v0 + 70 * e], [W / 2 - 26 * e, v0 + 70 * e], [W / 2 - 26 * e, v0 + 120 * e]], 1],
        ["s", [[24 * e, v0 + 98 * e], [24 * e, v0 + 128 * e], [W / 2 - 36 * e, v0 + 128 * e], [W / 2 - 36 * e, v0 + 160 * e]], 1],
        ["s", [[-6 * e, v0 + 70 * e], [u0 + 70 * e, v0 + 70 * e], [u0 + 70 * e, v0 + 130 * e]], 1]] },
      tela: { esp: 5 * e, contorno: rr(u0 + 4 * e, v0 + 4 * e, W - 8 * e, L - 8 * e, 30 * e), det: [
        ["d", rr(u0 + 16 * e, v0 + 16 * e, W - 32 * e, L - 32 * e, 22 * e)],
        ...[1, 2, 3, 4, 5, 6].map(k => ["s", [[u0 + 16 * e, v0 + 16 * e + k * (L - 32 * e) / 7], [W / 2 - 16 * e, v0 + 16 * e + k * (L - 32 * e) / 7]], 1]),
        ...[1, 2].map(k => ["s", [[u0 + 16 * e + k * (W - 32 * e) / 3, v0 + 16 * e], [u0 + 16 * e + k * (W - 32 * e) / 3, L / 2 - 16 * e]], 1])] },
      vidro: { esp: 3 * e, contorno: rr(u0, v0, W, L, 34 * e), det: [
        ["d", roda(0, v0 + 22 * e, 7 * e, 12)], ["s", rr(-28 * e, v0 + 10 * e, 56 * e, 6 * e, 3 * e, 2)],
        ["d", [[u0 + 30 * e, v0 + 120 * e], [u0 + 120 * e, v0 + 30 * e]], 1], ["d", [[u0 + 30 * e, v0 + 170 * e], [u0 + 170 * e, v0 + 30 * e]], 1]] },
    };
    const nomes = (o.camadas || ["vidro", "tela", "placa", "bateria", "carcaca"]).filter(n => {
      if (!DESENHO[n]) avisos.push(`cena ${ctx.cena.i}: Celular: camada "${n}" não existe`);
      return DESENHO[n];
    });
    const g = el("g", {}, ctx.svg);
    const fundo = [...nomes].reverse();  // desenha de baixo (carcaça) para cima (vidro)
    const cam = {};
    let zFechado = 0;
    fundo.forEach((n, i) => {
      const d = DESENHO[n], gl = el("g", {}, g), z = zFechado;
      zFechado += d.esp + 2 * e;
      // espessura: o contorno de baixo aparece só onde a chapa de cima não cobre
      el("path", { class: "s", d: caminho(d.contorno, z - d.esp), style: "stroke-width:2.5" }, gl);
      const chapa = el("path", { class: "chapa", d: caminho(d.contorno, z) }, gl);
      const cont = el("path", { class: "l", d: caminho(d.contorno, z), "data-ordem": 1 }, gl);
      for (const [cls, pts, aberto] of d.det) el("path", { class: cls, d: caminho(pts, z, !aberto), "data-ordem": 2 }, gl);
      cam[n] = { gl, chapa, cont, i, zAberto: i * gap - z };
    });
    // nomes das camadas: fio do canto direito de cada camada (na posição aberta) até o texto
    const nomesG = el("g", {}, g), fios = {};
    const nomesTxt = { ...CAMADAS_CEL, ...(o.rotulos || {}) };
    // canto mais à direita de cada camada, já na altura aberta; os nomes ficam numa coluna só
    const canto = n => DESENHO[n].contorno.reduce((m, q) => (q[0] - q[1] > m[0] - m[1] ? q : m));
    const lx = Math.max(o.rotulo_x || 0, ...nomes.map(n => P(...canto(n), cam[n].i * gap)[0] + 50));
    for (const n of nomes) {
      const [cx, yy] = P(...canto(n), cam[n].i * gap);
      const fg = el("g", {}, nomesG);
      el("circle", { cx: cx.toFixed(1), cy: yy.toFixed(1), r: 6, fill: "#5CF2E0" }, fg);
      const fio = el("path", { class: "d", d: `M${(cx + 10).toFixed(1)},${yy.toFixed(1)} L${(lx - 12).toFixed(1)},${yy.toFixed(1)}` }, fg);
      const tx = el("text", { class: "rot-linha", x: lx.toFixed(1), y: (yy + 9).toFixed(1), texto: String(nomesTxt[n]).toUpperCase() }, fg);
      fios[n] = { fg, fio, tx };
    }
    const t = quando(ctx.cena, o.em, .1);
    fundo.forEach((n, i) => {
      desenhar(cam[n].gl, t + i * .14, .8);
      tl.fromTo(cam[n].chapa, { opacity: 0 }, { opacity: 1, duration: T.medio, ease: C.suave }, t + i * .14 + .3);
    });
    const ta = quando(ctx.cena, o.abre_em, (t - ctx.cena.ini) + 1.6);
    som(ta, "whoosh");
    nomes.forEach((n, k) => tl.to(cam[n].gl, { y: -cam[n].zAberto, duration: .9, ease: "power2.inOut" }, ta + k * .06));
    nomes.forEach((n, k) => {
      const f = fios[n], tn = ta + .75 + k * .14;
      tl.fromTo(f.fg, { opacity: 0 }, { opacity: 1, duration: T.rapido, immediateRender: false }, tn);
      tl.fromTo(f.fio, { drawSVG: "0%" }, { drawSVG: "100%", duration: T.medio, ease: C.suave }, tn);
      tl.fromTo(f.tx, { opacity: 0, x: -10 }, { opacity: 1, x: 0, duration: T.medio, ease: C.suave }, tn + .12);
      som(tn, "pop");
    });
    tl.set(nomesG, { opacity: 1 }, ta);
    // destaque: uma camada fica âmbar e as outras apagam
    if (o.destaque && cam[o.destaque]) {
      const td = quando(ctx.cena, o.destaque_em, (ta - ctx.cena.ini) + 1.6);
      for (const n of nomes) {
        if (n === o.destaque) continue;
        tl.to([cam[n].gl, fios[n].fg], { opacity: .3, duration: T.medio, ease: C.suave }, td);
      }
      tl.to(tracos(cam[o.destaque].gl), { stroke: "#F2B33D", duration: T.medio, ease: C.suave }, td);
      tl.to(fios[o.destaque].tx, { fill: "#F2B33D", duration: T.medio }, td);
      pulso({ gr: cam[o.destaque].gl }, td);
      som(td, "pop");
    } else if (o.destaque) avisos.push(`cena ${ctx.cena.i}: Celular: destaque "${o.destaque}" não é uma camada`);
    if (o.fecha_em) {
      const tf = quando(ctx.cena, o.fecha_em);
      tl.to(nomesG, { opacity: 0, duration: T.rapido }, tf);
      nomes.forEach(n => tl.to(cam[n].gl, { y: 0, opacity: 1, duration: .8, ease: "power2.inOut" }, tf + .1));
    }
    if (o.id) ctx.reg[o.id] = { g };
    if (o.some_em) tl.to(g, { opacity: 0, duration: T.medio, ease: C.sai }, quando(ctx.cena, o.some_em));
  };

  // sub-cena: agrupa itens e permite trocar de quadro no meio da cena (entra_em / some_em)
  COMP.Grupo = (ctx, o) => {
    const g = el("g", {}, ctx.svg);
    const sub = { ...ctx, svg: g };
    if (o.entra_em != null) tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: T.medio }, quando(ctx.cena, o.entra_em));
    if (o.some_em != null) tl.to(g, { opacity: 0, duration: T.medio, ease: C.sai }, quando(ctx.cena, o.some_em));
    for (const it of o.itens) montar(sub, it);
  };

  function montar(ctx, it) {
    const f = COMP[it.c];
    if (!f) { avisos.push(`cena ${ctx.cena.i}: componente "${it.c}" não existe`); return; }
    try { f(ctx, it); } catch (e) { avisos.push(`cena ${ctx.cena.i}: ${it.c} falhou: ${e.message}`); }
  }

  // ---------- cenas
  cenas.forEach((c, i) => {
    const wrap = div({ class: "cena", "data-cena": i }, palco);
    const svg = el("svg", { viewBox: "0 0 960 980" }, wrap);
    const cam = el("g", {}, svg);
    const ctx = { cena: c, wrap, svg: cam, reg: {} };
    for (const it of c.itens || []) montar(ctx, it);
    // entra e sai por opacidade; um respiro de câmera bem lento dá vida ao quadro parado
    if (i) som(c.ini, "whoosh");
    tl.fromTo(wrap, { autoAlpha: 0 }, { autoAlpha: 1, duration: i ? .3 : .01, ease: C.suave, immediateRender: false }, c.ini);
    if (i < cenas.length - 1) tl.to(wrap, { autoAlpha: 0, duration: .25, ease: C.sai }, c.fim - .1);
    const z = c.camera?.zoom || 1.035, [fx, fy] = c.camera?.foco || [480, 490];
    tl.fromTo(cam, { scale: 1, svgOrigin: `${fx} ${fy}` }, { scale: z, svgOrigin: `${fx} ${fy}`, duration: c.dur, ease: C.respira, immediateRender: false }, c.ini);
  });

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  window.__prancha = {
    tl, avisos, eventos, total: TOTAL,
    // caixas medidas no quadro t (para a conferência automática)
    medir(t) {
      tl.seek(t, false);
      const caixa = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(v => Math.round(v)); };
      const visivel = e => getComputedStyle(e).visibility !== "hidden" && +getComputedStyle(e).opacity > .05;
      const cena = [...document.querySelectorAll(".cena")].find(visivel);
      let assunto = null;
      if (cena) {
        // o que está recortado (mapa) conta só até o recorte; onda e guia decorativa (data-livre) não contam
        const caixaDe = e => {
          let r = e.getBoundingClientRect();
          const g = e.closest("[clip-path]");
          if (g) {
            const id = (g.getAttribute("clip-path").match(/#([^)]+)/) || [])[1];
            const forma = id && document.getElementById(id)?.firstElementChild;
            if (forma) {
              const c = forma.getBoundingClientRect();
              const x0 = Math.max(r.left, c.left), y0 = Math.max(r.top, c.top), x1 = Math.min(r.right, c.right), y1 = Math.min(r.bottom, c.bottom);
              r = { left: x0, top: y0, right: x1, bottom: y1, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0) };
            }
          }
          return r;
        };
        const r = [...cena.querySelectorAll(".l,.d")].filter(e => !e.closest("[data-livre]") && +getComputedStyle(e).opacity > .05)
          .map(caixaDe).filter(r => r.width + r.height > 0);
        if (r.length) assunto = [Math.min(...r.map(b => b.left)), Math.min(...r.map(b => b.top)), Math.max(...r.map(b => b.right)), Math.max(...r.map(b => b.bottom))].map(Math.round);
      }
      const leg = [...document.querySelectorAll(".grupo")].filter(visivel).map(caixa);
      return { t, cena: cena ? +cena.dataset.cena : null, assunto, legenda: leg, avisos };
    },
  };
  tl.seek(0);
})();
