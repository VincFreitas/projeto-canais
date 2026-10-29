// Kit comum das cenas 3D (Three.js + GSAP): sala, materiais, canos que crescem, partículas, câmera e etiquetas.
// Cada cena (cenas/<slug>.3d.js) cria o kit com kit(args, opções) e só descreve o seu objeto e o que se mexe.

export function kit({ THREE, gsap, largura: W, altura: H }, opcoes = {}) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(opcoes.ceu ?? 0x1d2a52);
  const cam = new THREE.PerspectiveCamera(opcoes.fov ?? 48, W / H, 0.05, 60);
  scene.add(new THREE.HemisphereLight(0xfff2d6, 0x30304a, opcoes.ambiente ?? 1.4));
  const sol = new THREE.DirectionalLight(0xffffff, opcoes.sol ?? 2.2);
  sol.position.set(1.2, 7, 2.2);  // luz bem de cima: a sombra cai no chão, não na parede
  scene.add(sol);

  const tons = new THREE.DataTexture(new Uint8Array([80, 80, 80, 255, 170, 170, 170, 255, 255, 255, 255, 255]), 3, 1);
  tons.minFilter = tons.magFilter = THREE.NearestFilter;
  tons.needsUpdate = true;
  const toon = (cor, extra = {}) => new THREE.MeshToonMaterial({ color: cor, gradientMap: tons, ...extra });
  const brilho = (cor, extra = {}) => new THREE.MeshBasicMaterial({ color: cor, ...extra });
  const vidro = (cor, opacidade = 0.35) => new THREE.MeshToonMaterial({ color: cor, gradientMap: tons, transparent: true,
    opacity: opacidade, depthWrite: false });

  const pop = gsap.parseEase("back.out(2.2)");
  const suave = gsap.parseEase("power2.inOut");
  const mola = gsap.parseEase("elastic.out(1, 0.45)");
  const lerp = THREE.MathUtils.lerp, clamp = THREE.MathUtils.clamp;
  const cl = (x) => clamp(x, 0, 1);

  const textura = (desenho, w, h, rep) => {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    desenho(cv.getContext("2d"), w, h);
    const tx = new THREE.CanvasTexture(cv);
    tx.wrapS = tx.wrapT = THREE.RepeatWrapping;
    tx.repeat.set(rep[0], rep[1]);
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 4;
    return tx;
  };
  const azulejo = (fundo, linha, rep = [14, 8]) => textura((g, w, h) => {
    g.fillStyle = fundo; g.fillRect(0, 0, w, h);
    g.fillStyle = linha; g.fillRect(0, 0, w, 3); g.fillRect(0, 0, 3, h);
  }, 64, 64, rep);
  const tabua = (fundo = "#946038", linha = "#7a4c2c") => textura((g, w, h) => {
    g.fillStyle = fundo; g.fillRect(0, 0, w, h);
    g.fillStyle = linha; g.fillRect(0, 0, w, 4);
  }, 64, 64, [10, 30]);

  // sala: chão e duas paredes (fundo e esquerda), com janela e lua opcionais
  const sala = ({ piso = tabua(), parede = azulejo("#2e5696", "#4470b8"), janela = true, fundoZ = -3, ladoX = -3 } = {}) => {
    const chao = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), toon(0xffffff, { map: piso }));
    chao.rotation.x = -Math.PI / 2;
    scene.add(chao);
    for (const [x, z, ry] of [[0, fundoZ, 0], [ladoX, 0, Math.PI / 2]]) {
      const p = new THREE.Mesh(new THREE.PlaneGeometry(14, 5), toon(0xffffff, { map: parede }));
      p.position.set(x, 2.5, z);
      p.rotation.y = ry;
      scene.add(p);
    }
    if (janela) {
      const j = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.7), brilho(0x101a44));
      j.position.set(-1.6, 1.9, fundoZ + 0.02);
      const lua = new THREE.Mesh(new THREE.CircleGeometry(0.09, 16), brilho(0xfff2c0));
      lua.position.set(-1.35, 2.05, fundoZ + 0.03);
      scene.add(j, lua);
    }
    return chao;
  };

  const caixa = (w, h, d, cor, pos, pai = scene, mat = null) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat ?? toon(cor));
    m.position.set(...pos);
    pai.add(m);
    return m;
  };
  const cilindro = (r, h, cor, pos, pai = scene, lados = 16, mat = null) => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, lados), mat ?? toon(cor));
    m.position.set(...pos);
    pai.add(m);
    return m;
  };
  const esfera = (r, cor, pos, pai = scene, mat = null) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), mat ?? toon(cor));
    m.position.set(...pos);
    pai.add(m);
    return m;
  };
  const grupo = (pos = [0, 0, 0], pai = scene) => {
    const g = new THREE.Group();
    g.position.set(...pos);
    pai.add(g);
    return g;
  };

  // cano que cresce ao longo do caminho (peça sendo montada)
  const tubo = (pontos, raio, cor, emissiva = false, pai = scene) => {
    const curva = new THREE.CatmullRomCurve3(pontos.map((p) => new THREE.Vector3(...p)), false, "catmullrom", 0.05);
    const geo = new THREE.TubeGeometry(curva, Math.max(pontos.length * 20, 48), raio, 10, false);
    const mat = emissiva ? brilho(cor) : toon(cor);
    const m = new THREE.Mesh(geo, mat);
    m.userData.total = geo.index.count;
    pai.add(m);
    return { m, curva, mat };
  };
  const crescer = (t, p) => {
    t.m.visible = p > 0;
    t.m.geometry.setDrawRange(0, Math.floor(t.m.userData.total * cl(p) / 6) * 6);
  };

  // partículas
  const sementes = Array.from({ length: 500 }, (_, k) =>
    [Math.abs(Math.sin(k * 12.9898) * 43758.5453 % 1), Math.abs(Math.sin(k * 78.233) * 12345.678 % 1),
     Math.abs(Math.sin(k * 3.1) * 999.1 % 1)]);
  const pontos = (n, tam) => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    geo.setAttribute("color", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const m = new THREE.Points(geo, new THREE.PointsMaterial({ size: tam, vertexColors: true, sizeAttenuation: true }));
    scene.add(m);
    return m;
  };
  const cA = new THREE.Color(), cB = new THREE.Color(), cC = new THREE.Color();
  const correr = (pts, curva, T, vel, a, b, n = 14, visivel = true) => {
    pts.visible = visivel;
    if (!visivel) return;
    const pos = pts.geometry.attributes.position, cor = pts.geometry.attributes.color;
    cA.set(a); cB.set(b ?? a);
    for (let k = 0; k < pos.count; k++) {
      if (k >= n) { pos.setXYZ(k, 0, -10, 0); continue; }
      const u = ((k / n) + T * vel) % 1;
      const p = curva.getPointAt(u);
      pos.setXYZ(k, p.x, p.y, p.z);
      cC.copy(cA).lerp(cB, u);
      cor.setXYZ(k, cC.r, cC.g, cC.b);
    }
    pos.needsUpdate = cor.needsUpdate = true;
  };
  const nuvem = (pts, f) => {  // f(k, semente) -> [x, y, z, r, g, b] ou null
    const pos = pts.geometry.attributes.position, cor = pts.geometry.attributes.color;
    for (let k = 0; k < pos.count; k++) {
      const v = f(k, sementes[k % sementes.length]);
      if (!v) { pos.setXYZ(k, 0, -10, 0); continue; }
      pos.setXYZ(k, v[0], v[1], v[2]);
      cor.setXYZ(k, v[3], v[4], v[5]);
    }
    pos.needsUpdate = cor.needsUpdate = true;
  };
  const rgb = (hex) => { cC.set(hex); return [cC.r, cC.g, cC.b]; };
  const pisca = (T, s) => Math.max(0, Math.sin(T * (2 + 3 * s[2]) + s[0] * 6)) ** 4;
  const poeira = pontos(70, 0.022);

  // câmera: viaja entre enquadramentos com curva do GSAP, orbita de leve e treme no impacto
  const alvo = new THREE.Vector3();
  const camera = (e, VISTAS) => {
    const [pa, aa] = VISTAS[e.camera.de] || VISTAS.tudo, [pb, ab] = VISTAS[e.camera.para] || VISTAS.tudo;
    const f = suave(cl(e.camera.f));
    const orbita = Math.sin(e.T * 0.25) * 0.12;
    cam.position.set(lerp(pa[0], pb[0], f) + orbita, lerp(pa[1], pb[1], f) + Math.sin(e.T * 0.4) * 0.03,
      lerp(pa[2], pb[2], f) - orbita * 0.5);
    alvo.set(lerp(aa[0], ab[0], f), lerp(aa[1], ab[1], f), lerp(aa[2], ab[2], f));
    if (e.impacto > 0) cam.position.x += Math.sin(e.t * 90) * 0.02 * e.impacto;
    cam.fov = (opcoes.fov ?? 48) * (1 - 0.1 * e.impacto);
    cam.updateProjectionMatrix();
    cam.lookAt(alvo);
    cam.updateMatrixWorld();
    nuvem(poeira, (k, s) => [-3 + s[0] * 6, (s[1] * 3.2 + e.T * 0.05 * (1 + s[2])) % 3.2, -2.8 + s[2] * 5, 1, 0.94, 0.8]);
  };

  // onde cada âncora 3D está na tela, para as etiquetas (âncora pode ser Vector3 ou um objeto 3D)
  const v = new THREE.Vector3();
  const ancoras = (mapa) => {
    const r = {};
    for (const [nome, a] of Object.entries(mapa)) {
      if (a.isObject3D) { if (!a.visible) continue; a.getWorldPosition(v); } else v.copy(a);
      v.project(cam);
      if (v.z < 1 && Math.abs(v.x) < 1.2 && Math.abs(v.y) < 1.2) r[nome] = [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H];
    }
    return r;
  };
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const P = (e) => (n) => e.pecas[n] ?? 0;
  const A = (e) => (n) => (e.acoes[n] === undefined ? null : e.acoes[n]);
  const encaixar = (obj, p, base = 1) => { obj.visible = p > 0; obj.scale.setScalar(Math.max(pop(cl(p)), 0.001) * base); };

  return { THREE, scene, cam, sol, toon, brilho, vidro, pop, suave, mola, lerp, clamp, cl, textura, azulejo, tabua, sala,
    caixa, cilindro, esfera, grupo, tubo, crescer, pontos, correr, nuvem, rgb, pisca, camera, ancoras, V, P, A, encaixar };
}
