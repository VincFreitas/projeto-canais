// Cena 3D da geladeira (Three.js + GSAP), desenhada na grade de pixels: pixel art em 3D low-poly.
// Mesmos nomes de peças e ações do roteiro 2D: caixa, gelo, entregador, bolha, evaporador, compressor,
// condensador, termometro, capilar, termostato, vedacao; ações entregar, derreter, calor_sai, alcool,
// evapora, termometro, fechar, pronto.

export const SERIE = "PULGA DO SABER · GELADEIRA";
export const PECAS = {
  caixa: { titulo: "Caixa", conta: true },
  gelo: { titulo: "Gelo", conta: false },
  entregador: { titulo: "Entregador", conta: false },
  bolha: { titulo: "Álcool", conta: false },
  evaporador: { titulo: "Evaporador", conta: true },
  compressor: { titulo: "Compressor", conta: true },
  condensador: { titulo: "Condensador", conta: true },
  termometro: { titulo: "Termômetro", conta: false },
  capilar: { titulo: "Tubo capilar", conta: true },
  termostato: { titulo: "Termostato", conta: true },
  vedacao: { titulo: "Vedação", conta: true },
};

// enquadramentos da câmera: posição e para onde olha
const VISTAS = {
  tudo: [[2.3, 1.75, 3.9], [0.25, 0.95, 0]],
  caixa: [[1.5, 1.45, 3.0], [0, 0.95, 0]],
  gelo: [[0.55, 1.55, 1.55], [0, 1.28, 0]],
  entregador: [[2.6, 1.5, 3.4], [0.9, 0.85, 0.3]],
  bolha: [[1.7, 1.7, 2.7], [1.2, 1.5, 0.6]],
  evaporador: [[0.45, 1.7, 1.6], [0, 1.5, -0.2]],
  compressor: [[1.9, 0.75, -1.9], [0.15, 0.3, -0.55]],
  condensador: [[1.4, 1.3, -2.6], [0, 1.0, -0.45]],
  termometro: [[1.9, 1.6, -1.5], [0.95, 1.35, -0.55]],
  capilar: [[1.5, 2.4, 1.4], [0, 1.85, -0.3]],
  termostato: [[-0.3, 1.12, 0.85], [0.42, 1.0, 0]],
  vedacao: [[1.6, 1.3, 2.6], [0.1, 0.95, 0.35]],
};

export function criar({ THREE, gsap, largura: W, altura: H }) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1d2a52);
  const camera = new THREE.PerspectiveCamera(48, 216 / 384, 0.05, 40);

  // luz de "videogame": hemisfério + sol com sombra, materiais toon com 3 tons
  scene.add(new THREE.HemisphereLight(0xfff2d6, 0x30304a, 1.4));
  const sol = new THREE.DirectionalLight(0xffffff, 2.2);
  sol.position.set(2.5, 4, 3);
  scene.add(sol);
  const tons = new THREE.DataTexture(new Uint8Array([70, 70, 70, 255, 160, 160, 160, 255, 255, 255, 255, 255]), 3, 1);
  tons.minFilter = tons.magFilter = THREE.NearestFilter;
  tons.needsUpdate = true;
  const toon = (cor, extra = {}) => new THREE.MeshToonMaterial({ color: cor, gradientMap: tons, ...extra });
  const brilho = (cor) => new THREE.MeshBasicMaterial({ color: cor });

  const pop = gsap.parseEase("back.out(2.2)");
  const suave = gsap.parseEase("power2.inOut");
  const mola = gsap.parseEase("elastic.out(1, 0.45)");
  const lerp = THREE.MathUtils.lerp;
  const clamp = THREE.MathUtils.clamp;

  // ---------- cenário: cozinha ----------
  const textura = (desenho, w, h, rep) => {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    desenho(cv.getContext("2d"), w, h);
    const tx = new THREE.CanvasTexture(cv);
    tx.magFilter = tx.minFilter = THREE.NearestFilter;
    tx.wrapS = tx.wrapT = THREE.RepeatWrapping;
    tx.repeat.set(rep[0], rep[1]);
    tx.colorSpace = THREE.SRGBColorSpace;
    return tx;
  };
  const azulejo = textura((g, w, h) => {
    g.fillStyle = "#2e5696"; g.fillRect(0, 0, w, h);
    g.fillStyle = "#4470b8"; g.fillRect(0, 0, w, 2); g.fillRect(0, 0, 2, h);
  }, 16, 16, [14, 8]);
  const tabua = textura((g, w, h) => {
    g.fillStyle = "#946038"; g.fillRect(0, 0, w, h);
    g.fillStyle = "#7a4c2c"; g.fillRect(0, 0, w, 2);
  }, 16, 16, [10, 30]);
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), toon(0xffffff, { map: tabua }));
  chao.rotation.x = -Math.PI / 2;
  scene.add(chao);
  for (const [x, z, ry] of [[0, -3, 0], [-3, 0, Math.PI / 2]]) {
    const parede = new THREE.Mesh(new THREE.PlaneGeometry(10, 4), toon(0xffffff, { map: azulejo }));
    parede.position.set(x, 2, z);
    parede.rotation.y = ry;
    scene.add(parede);
  }
  const janela = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.7), brilho(0x101a44));
  janela.position.set(-1.6, 1.9, -2.98);
  scene.add(janela);
  const lua = new THREE.Mesh(new THREE.CircleGeometry(0.09, 10), brilho(0xfff2c0));
  lua.position.set(-1.35, 2.05, -2.97);
  scene.add(lua);
  const lampada = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), brilho(0xffe6a0));
  lampada.position.set(0.3, 2.9, 0.6);
  scene.add(lampada);

  // ---------- a caixa (vira geladeira) ----------
  const caixa = new THREE.Group();
  scene.add(caixa);
  const corMadeira = new THREE.Color(0xa86c3c), corCreme = new THREE.Color(0xece2c4);
  const matCasca = toon(0xa86c3c), matDentro = toon(0x6e4626);
  const painel = (w, h, d, x, y, z, mat) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.position.set(x, y, z);
    caixa.add(m);
    return m;
  };
  painel(1.0, 1.8, 0.05, 0, 0.95, -0.325, matCasca);       // fundo
  painel(0.05, 1.8, 0.7, -0.475, 0.95, 0, matCasca);       // lados
  painel(0.05, 1.8, 0.7, 0.475, 0.95, 0, matCasca);
  painel(1.0, 0.05, 0.7, 0, 1.825, 0, matCasca);           // topo
  painel(1.0, 0.05, 0.7, 0, 0.075, 0, matCasca);           // base
  painel(0.9, 1.7, 0.02, 0, 0.95, -0.29, matDentro);       // interior escuro
  const prateleiras = [0.62, 1.1].map((y) => painel(0.9, 0.03, 0.6, 0, y, 0, toon(0xcfd2da)));
  for (const x of [-0.4, 0.4]) painel(0.1, 0.05, 0.1, x, 0.025, 0.25, toon(0x222228));  // pés

  const comida = new THREE.Group();
  caixa.add(comida);
  const leite = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.28, 8), toon(0xf6f6fa));
  leite.position.set(-0.3, 0.24, 0.05);
  const tampa = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.05, 8), toon(0x3c78dc));
  tampa.position.set(-0.3, 0.405, 0.05);
  const maca = new THREE.Mesh(new THREE.IcosahedronGeometry(0.07, 0), toon(0xdc3240));
  maca.position.set(-0.05, 0.17, 0.08);
  const queijo = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.1, 0.15), toon(0xfad23c));
  queijo.position.set(0.22, 0.15, 0.05);
  const verdura = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.12, 0.2), toon(0x78c85a));
  verdura.position.set(-0.2, 0.7, 0.0);
  const cenoura = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.3, 6), toon(0xf08c46));
  cenoura.rotation.z = Math.PI / 2;
  cenoura.position.set(0.2, 0.68, 0.05);
  comida.add(leite, tampa, maca, queijo, verdura, cenoura);

  const luzDentro = new THREE.PointLight(0xfff0c0, 0, 2.5);
  luzDentro.position.set(0, 1.5, 0.1);
  caixa.add(luzDentro);

  // porta: gira na dobradiça da esquerda
  const dobradica = new THREE.Group();
  dobradica.position.set(-0.5, 0, 0.36);
  caixa.add(dobradica);
  const porta = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.8, 0.05), toon(0xa86c3c));
  porta.position.set(0.5, 0.95, 0);
  dobradica.add(porta);
  const puxador = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.4, 0.05), toon(0x9a9aa4));
  puxador.position.set(0.88, 1.0, 0.05);
  dobradica.add(puxador);
  const vedacao = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.8, 0.02),
    new THREE.MeshBasicMaterial({ color: 0xe65adc, wireframe: true }));
  vedacao.position.set(0.5, 0.95, -0.035);
  dobradica.add(vedacao);

  // ---------- gelo e poça ----------
  const gelo = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.36, 0.32),
    new THREE.MeshToonMaterial({ color: 0x9ad2f5, gradientMap: tons, transparent: true, opacity: 0.85 }));
  gelo.position.set(0.05, 1.3, 0);
  caixa.add(gelo);
  const poca = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.01, 16), brilho(0x6eb4e6));
  poca.position.set(0.1, 0.006, 0.6);
  scene.add(poca);

  // ---------- entregador ----------
  const homem = new THREE.Group();
  scene.add(homem);
  const parte = (w, h, d, x, y, z, cor, pai = homem) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), toon(cor));
    m.position.set(x, y, z);
    pai.add(m);
    return m;
  };
  parte(0.3, 0.42, 0.2, 0, 1.05, 0, 0x3c6ed2);   // camisa
  parte(0.2, 0.2, 0.2, 0, 1.38, 0, 0xf0c496);     // cabeça
  parte(0.24, 0.07, 0.24, 0, 1.5, 0, 0x2850b4);   // boné
  const pernas = [-0.08, 0.08].map((x) => {
    const g = new THREE.Group();
    g.position.set(x, 0.84, 0);
    homem.add(g);
    parte(0.11, 0.8, 0.12, 0, -0.4, 0, 0x282838, g);
    return g;
  });
  const blocoHomem = parte(0.36, 0.26, 0.26, -0.3, 1.05, 0.05, 0x9ad2f5);

  // ---------- bolha do álcool na mão ----------
  const bolha = new THREE.Group();
  bolha.position.set(1.2, 1.5, 0.6);
  scene.add(bolha);
  const disco = new THREE.Mesh(new THREE.CircleGeometry(0.5, 20), brilho(0xf4f8ff));
  bolha.add(disco);
  const mao = new THREE.Group();
  mao.position.set(0, -0.08, 0.02);
  bolha.add(mao);
  parte(0.42, 0.22, 0.04, 0, 0, 0, 0xf0c496, mao);
  for (let k = 0; k < 4; k++) parte(0.07, 0.2, 0.04, -0.15 + k * 0.1, 0.2, 0, 0xf0c496, mao);
  const gotas = [];
  for (let k = 0; k < 4; k++) {
    const g = new THREE.Mesh(new THREE.SphereGeometry(0.035, 6, 4), brilho(0x8cc8ff));
    bolha.add(g);
    gotas.push(g);
  }

  // ---------- canos (tubos que crescem) ----------
  const tubo = (pontos, raio, cor, emissiva = false) => {
    const curva = new THREE.CatmullRomCurve3(pontos.map((p) => new THREE.Vector3(...p)), false, "catmullrom", 0.05);
    const geo = new THREE.TubeGeometry(curva, Math.max(pontos.length * 16, 40), raio, 6, false);
    const mat = emissiva ? new THREE.MeshBasicMaterial({ color: cor }) : toon(cor);
    const m = new THREE.Mesh(geo, mat);
    m.userData.total = geo.index.count;
    scene.add(m);
    return { m, curva, mat };
  };
  const crescer = (t, p) => { t.m.visible = p > 0; t.m.geometry.setDrawRange(0, Math.floor(t.m.userData.total * p / 6) * 6); };

  const zig = [];
  for (let k = 0; k < 5; k++) {
    const y = 1.76 - k * 0.09;
    zig.push(k % 2 ? [0.4, y, -0.27] : [-0.4, y, -0.27], k % 2 ? [-0.4, y, -0.27] : [0.4, y, -0.27]);
  }
  const evap = tubo(zig, 0.022, 0xc87034);
  const saida = tubo([[0.4, 1.4, -0.27], [0.43, 1.4, -0.38], [0.43, 1.2, -0.45], [0.3, 0.55, -0.5], [0.2, 0.42, -0.58]], 0.022, 0xc87034);
  const grade = [];
  for (let k = 0; k < 9; k++) {
    const y = 0.55 + k * 0.13;
    grade.push(k % 2 ? [0.38, y, -0.43] : [-0.38, y, -0.43], k % 2 ? [-0.38, y, -0.43] : [0.38, y, -0.43]);
  }
  const compCond = tubo([[0.3, 0.32, -0.62], [0.42, 0.42, -0.6], [0.4, 0.55, -0.43]], 0.022, 0xc87034);
  const cond = tubo(grade, 0.02, 0x2a2a32);
  const condQuente = tubo(grade, 0.024, 0xff7a28, true);
  const capilar = tubo([[-0.38, 1.59, -0.43], [-0.2, 1.88, -0.43], [0, 1.9, -0.25], [-0.2, 1.85, -0.2], [-0.4, 1.76, -0.27]], 0.012, 0xf0aa64);

  // compressor: cápsula preta atrás, embaixo
  const compressor = new THREE.Group();
  compressor.position.set(0.2, 0, -0.62);
  scene.add(compressor);
  const corpo = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.19, 0.3, 10), toon(0x26262e));
  corpo.position.y = 0.17;
  const cupula = new THREE.Mesh(new THREE.SphereGeometry(0.17, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), toon(0x26262e));
  cupula.position.y = 0.32;
  const placa = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.06, 0.01), toon(0xd2d23c));
  placa.position.set(0, 0.2, 0.185);
  compressor.add(corpo, cupula, placa);

  // termômetro na parede de trás
  const termo = new THREE.Group();
  termo.position.set(0.95, 1.1, -0.55);
  scene.add(termo);
  const vidro = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.6, 8), toon(0xf4f4f8));
  vidro.position.y = 0.3;
  const bulbo = new THREE.Mesh(new THREE.SphereGeometry(0.055, 8, 6), brilho(0xdc2828));
  const mercurio = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 1, 6), brilho(0xdc2828));
  termo.add(vidro, bulbo, mercurio);

  // termostato: mostrador na lateral de dentro
  const termostato = new THREE.Group();
  termostato.position.set(0.44, 1.0, 0.0);
  termostato.rotation.y = -Math.PI / 2;
  caixa.add(termostato);
  const mostrador = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.03, 14), toon(0xf4f4f8));
  mostrador.rotation.x = Math.PI / 2;
  const ponteiro = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.07, 0.01), brilho(0xdc2828));
  ponteiro.geometry.translate(0, 0.035, 0);
  ponteiro.position.z = 0.02;
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 4), brilho(0x50e66e));
  led.position.set(0, 0.14, 0.02);
  termostato.add(mostrador, ponteiro, led);

  // ---------- partículas ----------
  const pontos = (n, tam, cor) => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    geo.setAttribute("color", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const m = new THREE.Points(geo, new THREE.PointsMaterial({ size: tam, vertexColors: true, sizeAttenuation: true }));
    m.userData.cor = new THREE.Color(cor);
    scene.add(m);
    return m;
  };
  const sementes = Array.from({ length: 400 }, (_, k) => [Math.sin(k * 12.9898) * 43758.5453 % 1, Math.sin(k * 78.233) * 12345.678 % 1, Math.sin(k * 3.1) * 999.1 % 1].map((v) => Math.abs(v)));
  const fluxos = Array.from({ length: 6 }, () => pontos(40, 0.05, 0xffffff));
  const poeira = pontos(60, 0.025, 0xfff0c8);
  const extra = pontos(120, 0.045, 0xffffff);

  const corA = new THREE.Color(), corB = new THREE.Color();
  const correr = (pts, curva, T, vel, a, b, n = 14, visivel = true) => {
    pts.visible = visivel;
    if (!visivel) return;
    const pos = pts.geometry.attributes.position, cor = pts.geometry.attributes.color;
    corA.set(a); corB.set(b ?? a);
    for (let k = 0; k < 40; k++) {
      if (k >= n) { pos.setXYZ(k, 0, -10, 0); continue; }
      const u = ((k / n) + T * vel) % 1;
      const p = curva.getPointAt(u);
      pos.setXYZ(k, p.x, p.y, p.z);
      const c = corA.clone().lerp(corB, u);
      cor.setXYZ(k, c.r, c.g, c.b);
    }
    pos.needsUpdate = cor.needsUpdate = true;
  };
  const nuvem = (pts, n, f) => {  // f(k, semente) -> [x, y, z, r, g, b] ou null
    const pos = pts.geometry.attributes.position, cor = pts.geometry.attributes.color;
    const max = pos.count;
    for (let k = 0; k < max; k++) {
      const v = k < n ? f(k, sementes[k % sementes.length]) : null;
      if (!v) { pos.setXYZ(k, 0, -10, 0); continue; }
      pos.setXYZ(k, v[0], v[1], v[2]);
      cor.setXYZ(k, v[3], v[4], v[5]);
    }
    pos.needsUpdate = cor.needsUpdate = true;
  };

  const ancoras3d = {
    caixa: new THREE.Vector3(0, 1.85, 0.3), gelo: new THREE.Vector3(0.05, 1.45, 0.1),
    entregador: new THREE.Vector3(1.2, 1.5, 0.4), bolha: new THREE.Vector3(1.2, 1.85, 0.6),
    evaporador: new THREE.Vector3(0, 1.62, -0.25), compressor: new THREE.Vector3(0.2, 0.42, -0.5),
    condensador: new THREE.Vector3(0, 1.1, -0.45), termometro: new THREE.Vector3(0.95, 1.5, -0.55),
    capilar: new THREE.Vector3(0, 1.9, -0.25), termostato: new THREE.Vector3(0.42, 1.0, 0.0),
    vedacao: new THREE.Vector3(0.45, 1.2, 0.38),
  };
  const v = new THREE.Vector3(), alvo = new THREE.Vector3();

  function quadro(e) {
    const { t, T, cena } = e;
    const P = (n) => e.pecas[n] ?? 0;
    const A = (n) => (e.acoes[n] === undefined ? null : e.acoes[n]);

    // câmera: viaja entre enquadramentos com curva do GSAP, respira e treme no impacto
    const [pa, aa] = VISTAS[e.camera.de] || VISTAS.tudo, [pb, ab] = VISTAS[e.camera.para] || VISTAS.tudo;
    const f = suave(clamp(e.camera.f, 0, 1));
    const orbita = Math.sin(T * 0.25) * 0.12;
    camera.position.set(lerp(pa[0], pb[0], f) + orbita, lerp(pa[1], pb[1], f) + Math.sin(T * 0.4) * 0.03,
      lerp(pa[2], pb[2], f) - orbita * 0.5);
    alvo.set(lerp(aa[0], ab[0], f), lerp(aa[1], ab[1], f), lerp(aa[2], ab[2], f));
    if (e.impacto > 0) camera.position.x += Math.sin(t * 90) * 0.02 * e.impacto;
    camera.fov = 48 * (1 - 0.1 * e.impacto);
    camera.updateProjectionMatrix();
    camera.lookAt(alvo);
    camera.updateMatrixWorld();  // as etiquetas projetam com a câmera deste quadro, não a do anterior

    // caixa: cai e encaixa; vira geladeira creme quando chega o evaporador
    const pc = P("caixa");
    caixa.visible = pc > 0;
    caixa.position.y = (1 - pop(pc)) * 1.2;
    const moderna = P("evaporador");
    matCasca.color.copy(corMadeira).lerp(corCreme, moderna);
    matDentro.color.set(0x6e4626).lerp(new THREE.Color(0xd4cab0), moderna);
    porta.material.color.copy(matCasca.color);
    const fechar = A("fechar"), reabrir = A("pronto");
    let abertura = 1;
    if (fechar !== null) abertura = 1 - suave(clamp(fechar / 1.2, 0, 1));
    if (reabrir !== null) abertura = mola(clamp(reabrir / 1.4, 0, 1));
    dobradica.rotation.y = -2.0 * abertura;
    vedacao.visible = P("vedacao") > 0 && abertura < 0.1;
    vedacao.material.color.setHSL(0.85, 0.8, 0.55 + 0.15 * Math.sin(T * 6));
    luzDentro.intensity = cena >= 14 ? 2.5 : 0;

    // gelo derretendo e poça crescendo
    const der = A("derreter");
    const m = der !== null ? clamp(der / 4, 0, 1) : 0;
    gelo.visible = cena <= 3;
    gelo.scale.y = 1 - 0.85 * m;
    gelo.position.y = 1.12 + 0.18 * gelo.scale.y;
    poca.visible = cena === 3 && m > 0;
    poca.scale.set(0.05 + 0.5 * m, 1, 0.05 + 0.35 * m);

    // entregador andando com o bloco de gelo
    const ent = A("entregar");
    homem.visible = cena === 2 && ent !== null;
    if (homem.visible) {
      const ida = clamp(ent / 2.4, 0, 1);
      homem.position.set(lerp(3.2, 1.05, suave(ida)), 0, 0.6);
      homem.rotation.y = -Math.PI / 2;
      const passo = ida < 1 ? Math.sin(T * 10) * 0.5 : 0;
      pernas[0].rotation.x = passo; pernas[1].rotation.x = -passo;
      blocoHomem.position.y = 1.05 + Math.abs(Math.sin(T * 10)) * 0.02;
    }

    // bolha do álcool
    const alc = A("alcool");
    bolha.visible = cena === 5 && alc !== null;
    if (bolha.visible) {
      const s = pop(clamp(alc / 0.4, 0, 1));
      bolha.scale.setScalar(Math.max(s, 0.01));
      bolha.lookAt(camera.position);
      gotas.forEach((g, k) => {
        const fase = (T * 0.8 + k * 0.25) % 1;
        g.visible = fase < 0.45;
        g.position.set(-0.15 + k * 0.1, 0.18 + fase * 0.05, 0.05);
      });
    }

    // canos e peças montando
    crescer(evap, P("evaporador"));
    crescer(saida, P("compressor"));
    crescer(compCond, P("condensador"));
    crescer(cond, P("condensador"));
    crescer(capilar, P("capilar"));
    const pcomp = P("compressor");
    compressor.visible = pcomp > 0;
    compressor.scale.setScalar(Math.max(pop(pcomp), 0.01));
    const pterm = P("termostato");
    termostato.visible = pterm > 0;
    termostato.scale.setScalar(Math.max(pop(pterm), 0.01));
    const ciclo = cena === 12 ? Math.floor(T / 1.6) % 2 === 0 : true;
    const ligado = cena >= 8 && (pterm <= 0 || ciclo);
    ponteiro.rotation.z = ligado ? -0.9 : 0.6;
    led.material.color.set(ligado ? 0x50e66e : 0xe63c3c);
    compressor.position.x = 0.2 + (ligado ? Math.sin(T * 120) * 0.006 : 0);

    // condensador em brasa quando o motor está ligado
    condQuente.m.visible = ligado && P("condensador") >= 1;
    condQuente.mat.color.setHSL(0.07, 1, 0.45 + 0.1 * Math.sin(T * 4));
    termo.visible = cena >= 10;
    const sobe = A("termometro") !== null ? suave(clamp(A("termometro") / 2, 0, 1)) : (cena > 10 ? 1 : 0.2);
    mercurio.scale.y = 0.1 + 0.45 * sobe;
    mercurio.position.y = mercurio.scale.y / 2;

    // fluxos de gás e de calor
    const evapora = cena >= 7;
    correr(fluxos[0], evap.curva, T, 0.18, 0xd2f0ff, 0x8cd2ff, 16, evapora && P("evaporador") >= 1);
    correr(fluxos[1], saida.curva, T, 0.3, 0x96dcff, 0xb4e6ff, 10, ligado && pcomp >= 1);
    correr(fluxos[2], cond.curva, T, 0.08, 0xff5a3c, 0xffc85a, 30, ligado && P("condensador") >= 1);
    correr(fluxos[3], capilar.curva, T, 0.35, 0xffaa50, 0x96e6ff, 10, ligado && P("capilar") >= 1);
    correr(fluxos[4], compCond.curva, T, 0.4, 0xff6a3c, 0xff6a3c, 6, ligado && P("condensador") >= 1);
    fluxos[5].visible = false;

    // partículas extras de cada passo
    nuvem(poeira, 60, (k, s) => [-2.5 + s[0] * 5, (s[1] * 3 + T * 0.05 * (1 + s[2])) % 3, -2.5 + s[2] * 4, 1, 0.94, 0.78]);
    nuvem(extra, 120, (k, s) => {
      if (cena === 1 && k < 30) {  // gelinho brilhando
        const pisca = Math.max(0, Math.sin(T * (2 + 3 * s[2]) + s[0] * 6)) ** 4;
        return pisca > 0.1 ? [-0.2 + s[0] * 0.5, 1.12 + s[1] * 0.45, 0.2 + s[2] * 0.1, 0.85, 0.95, 1] : null;
      }
      if (cena === 3 && m > 0 && k < 20) {  // pingos
        const fase = (T * 1.4 + s[0]) % 1;
        return [-0.15 + s[1] * 0.4, 1.1 - fase * 1.1, 0.25, 0.47, 0.75, 0.94];
      }
      if (cena === 4 && A("calor_sai") !== null && k < 60) {  // calor saindo da caixa
        const fase = (T * 0.5 + s[0]) % 1;
        return [lerp(-0.3 + s[1] * 0.6, -1.4, fase * fase), 0.5 + fase * 1.8, lerp(0, -2.6, fase), 1, 0.5, 0.16];
      }
      if (cena === 5 && bolha.visible && k < 30) {  // vapor do álcool
        const fase = (T * 0.6 + s[0]) % 1;
        return [1.05 + s[1] * 0.3, 1.6 + fase * 0.35, 0.7, 0.86, 0.94, 1];
      }
      if (cena === 7 && k < 40) {  // calor da comida entrando no cano
        const fase = (T * 0.5 + s[0]) % 1;
        c3.set(0xff8228).lerp(new THREE.Color(0x96dcff), fase);
        return [-0.3 + s[1] * 0.6, 0.3 + fase * 1.35, 0.1 - fase * 0.35, c3.r, c3.g, c3.b];
      }
      if (cena >= 7 && P("evaporador") >= 1 && k >= 60 && k < 80) {  // gelo no cano
        const pisca = Math.max(0, Math.sin(T * 3 + s[0] * 9)) ** 3;
        return pisca > 0.2 ? [-0.4 + s[1] * 0.8, 1.38 + s[2] * 0.4, -0.25, 0.92, 0.97, 1] : null;
      }
      if (ligado && P("condensador") >= 1 && k >= 80 && k < 110) {  // ondas de calor atrás
        const fase = (T * 0.6 + s[0]) % 1;
        return [-0.4 + s[1] * 0.8 + Math.sin(fase * 8 + k) * 0.03, 0.6 + fase * 1.4, -0.55 - fase * 0.2, 1, 0.55, 0.2];
      }
      if (cena === 13 && vedacao.visible && k < 30) {  // brilho do ímã
        const pisca = Math.max(0, Math.sin(T * 5 + s[0] * 9)) ** 3;
        return pisca > 0.2 ? [-0.5 + s[1], 0.05 + s[2] * 1.8, 0.39, 1, 0.66, 1] : null;
      }
      if (cena >= 14 && k < 50) {  // brilhos do fim
        const pisca = Math.max(0, Math.sin(T * (2 + 3 * s[2]) + s[0] * 6)) ** 4;
        return pisca > 0.1 ? [-1 + s[0] * 2.2, 0.2 + s[1] * 2.2, -0.3 + s[2], 1, 1, 0.85] : null;
      }
      return null;
    });

    // onde cada peça está na tela (para as etiquetas)
    const ancoras = {};
    for (const [nome, p] of Object.entries(ancoras3d)) {
      v.copy(p);
      if (["caixa", "gelo", "termostato", "vedacao"].includes(nome)) v.y += caixa.position.y;
      v.project(camera);
      if (v.z < 1) ancoras[nome] = [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H];
    }
    return ancoras;
  }
  const c3 = new THREE.Color();

  return { scene, camera, quadro };
}
