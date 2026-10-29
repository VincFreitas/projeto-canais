// Cena 3D do micro-ondas: do fogo às moléculas de água girando, e o forno montado em volta do prato.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · MICRO-ONDAS";
export const PECAS = {
  fogao: { titulo: "Fogão", conta: false },
  comida: { titulo: "Comida", conta: false },
  molecula: { titulo: "Molécula", conta: false },
  magnetron: { titulo: "Magnetron", conta: true },
  caixa: { titulo: "Caixa de metal", conta: true },
  porta: { titulo: "Porta com grade", conta: true },
  prato: { titulo: "Prato giratório", conta: true },
};
const VISTAS = {
  tudo: [[0.8, 1.75, 2.3], [-0.35, 1.05, 0]],
  fogao: [[-0.3, 1.75, 1.5], [-0.95, 1.0, 0]],
  comida: [[0.4, 1.4, 1.2], [0, 1.0, 0]],
  molecula: [[0.35, 1.75, 1.7], [0, 1.65, 0.2]],
  magnetron: [[1.35, 1.4, 1.1], [0.53, 1.15, 0]],
  caixa: [[1.1, 1.55, 1.6], [0.08, 1.15, 0]],
  porta: [[0.7, 1.35, 1.4], [0, 1.15, 0.3]],
  prato: [[0.9, 1.65, 1.7], [0, 1.05, 0]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x3a2c22 });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#a06a44", "#8a5a38", [10, 10]), parede: k.azulejo("#ecc890", "#f6dcaa", [12, 6]), janela: false });
  k.caixa(3.2, 0.9, 0.9, 0x96603c, [0, 0.45, 0]);           // bancada
  k.caixa(3.2, 0.04, 0.92, 0xe8e2d6, [0, 0.92, 0]);

  // fogão com frigideira (cenas 1 e 2)
  const fogao = k.grupo([-0.95, 0.94, 0]);
  k.caixa(0.6, 0.04, 0.5, 0x2a2a30, [0, 0, 0], fogao);
  const chamas = [0, 1, 2, 3, 4, 5].map((i) => k.esfera(0.03, 0, [Math.cos(i) * 0.12, 0.04, Math.sin(i) * 0.12], fogao, k.brilho(0x5096ff)));
  const frigideira = k.cilindro(0.2, 0.05, 0x3c3c44, [0, 0.1, 0], fogao, 20);
  k.caixa(0.3, 0.03, 0.04, 0x3c3c44, [0.33, 0.1, 0], fogao);
  const relogio = k.grupo([-0.95, 1.9, -0.44]);
  k.cilindro(0.16, 0.03, 0xf4f4f8, [0, 0, 0], relogio, 24).rotation.x = Math.PI / 2;
  const ponteiro = k.caixa(0.015, 0.12, 0.01, 0x202028, [0, 0.05, 0.02], relogio);
  ponteiro.geometry.translate(0, 0.04, 0);

  // prato e comida
  const prato = k.cilindro(0.26, 0.02, 0xdce6f0, [0, 0.96, 0], k.scene, 28);
  const marca = k.esfera(0.025, 0, [0.22, 0.98, 0], k.scene, k.brilho(0xdc3c3c));
  const comida = k.grupo([0, 0.97, 0]);
  k.caixa(0.3, 0.08, 0.2, 0xc86e3c, [0, 0.04, 0], comida);
  k.caixa(0.22, 0.04, 0.14, 0xe6a050, [0, 0.1, 0], comida);

  // bolha com moléculas de água
  const bolha = k.grupo([0, 1.65, 0.2]);
  const fundo = new THREE.Mesh(new THREE.CircleGeometry(0.42, 32), k.brilho(0xe6f4ff));
  bolha.add(fundo);
  const molecula = (raio) => {
    const g = k.grupo([0, 0, 0.05], bolha);
    const o = k.esfera(raio, 0xdc3c3c, [0, 0, 0], g);
    const h1 = k.esfera(raio * 0.6, 0xf4f4f8, [Math.cos(0.9) * raio * 1.3, Math.sin(0.9) * raio * 1.3, 0], g);
    const h2 = k.esfera(raio * 0.6, 0xf4f4f8, [Math.cos(Math.PI - 0.9) * raio * 1.3, Math.sin(Math.PI - 0.9) * raio * 1.3, 0], g);
    return { g, o, h1, h2 };
  };
  const gotas = Array.from({ length: 9 }, (_, i) =>
    k.esfera(0.035, 0, [-0.25 + (i * 0.29) % 0.5, -0.22 + (i * 0.17) % 0.42, 0.05], bolha, k.brilho(0x5aa0f0)));
  const grande = molecula(0.1);
  const pequenas = Array.from({ length: 7 }, (_, i) => {
    const m = molecula(0.04);
    m.g.position.set(-0.25 + (i * 0.37) % 0.5, -0.2 + (i * 0.23) % 0.4, 0.05);
    return m;
  });

  // magnetron, caixa de metal, porta com grade
  const magnetron = k.grupo([0.54, 1.15, 0]);
  k.caixa(0.14, 0.2, 0.2, 0x5a5a64, [0, 0, 0], magnetron);
  for (let i = 0; i < 5; i++) k.caixa(0.18, 0.012, 0.24, 0x8c8c96, [0, -0.08 + i * 0.04, 0], magnetron);
  k.esfera(0.05, 0xc8783c, [0, 0, 0.11], magnetron);
  const guia = k.caixa(0.1, 0.06, 0.08, 0x8c8c96, [-0.12, 0, 0], magnetron);
  const metal = k.toon(0xc8ccd6);
  const paredes = k.grupo([0, 0, 0]);
  const pedaco = (w, h, d, x, y, z) => k.caixa(w, h, d, 0, [x, y, z], paredes, metal);
  const lados = [pedaco(0.92, 0.03, 0.62, 0, 1.47, 0), pedaco(0.03, 0.52, 0.62, -0.46, 1.2, 0),
    pedaco(0.92, 0.52, 0.03, 0, 1.2, -0.31), pedaco(0.03, 0.52, 0.62, 0.46, 1.2, 0)];
  const painel = k.caixa(0.18, 0.52, 0.62, 0x3c4048, [0.56, 1.2, 0], paredes);
  for (let i = 0; i < 6; i++) k.caixa(0.05, 0.05, 0.01, 0xd2d2dc, [0.52 + (i % 2) * 0.08, 1.3 - Math.floor(i / 2) * 0.08, 0.315], paredes);
  const visor = k.caixa(0.13, 0.05, 0.01, 0x1ec878, [0.56, 1.4, 0.315], paredes, k.brilho(0x1ec878));
  const grade = k.textura((g, w, h) => {
    g.fillStyle = "rgba(30,34,44,0.92)"; g.fillRect(0, 0, w, h);
    for (let y = 1; y < h; y += 4) for (let x = 1; x < w; x += 4) g.clearRect(x, y, 2, 2);  // furinhos
  }, 256, 160, [1, 1]);
  const dobradica = k.grupo([-0.46, 1.2, 0.31]);
  const porta = new THREE.Mesh(new THREE.BoxGeometry(0.92, 0.52, 0.02),
    new THREE.MeshToonMaterial({ map: grade, transparent: true, color: 0xffffff }));
  porta.position.x = 0.46;
  dobradica.add(porta);
  const luz = new THREE.PointLight(0xffe6a0, 0, 1.4);
  luz.position.set(0, 1.4, 0);
  k.scene.add(luz);

  const ondas = k.pontos(120, 0.03), extras = k.pontos(80, 0.05);
  const ANC = { fogao: k.V(-0.95, 1.1, 0), comida: k.V(0, 1.1, 0.1), molecula: k.V(0, 2.0, 0.25),
    positivo: grande.h1, negativo: grande.o, guia: guia, magnetron: k.V(0.54, 1.32, 0.12),
    caixa: k.V(0, 1.48, 0.3), porta: k.V(0.1, 1.2, 0.33), prato: marca };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const fogo = c <= 2;
    fogao.visible = fogo;
    chamas.forEach((f, i) => f.scale.setScalar(0.7 + 0.5 * Math.abs(Math.sin(T * 12 + i))));
    relogio.visible = c === 2 && A("espera") !== null;
    ponteiro.rotation.z = -T * 5;
    comida.visible = !fogo;
    prato.visible = marca.visible = !fogo;
    const giro = P("prato") > 0 ? T * 1.5 : 0;
    comida.rotation.y = giro;
    marca.position.set(Math.cos(giro) * 0.22, 0.98, -Math.sin(giro) * 0.22);

    // bolha das moléculas
    const chave = { 3: "agua", 4: "molecula", 5: "onda", 6: "giram" }[c];
    const abre = chave ? A(chave) : null;
    bolha.visible = [3, 4, 5, 6].includes(c) && (c !== 3 || abre !== null);
    bolha.scale.setScalar(Math.max(c === 3 ? k.pop(k.cl((abre ?? 0) / 0.4)) : 1, 0.001));
    bolha.lookAt(k.cam.position);
    gotas.forEach((g, i) => { g.visible = c === 3; g.position.y = -0.22 + (i * 0.17) % 0.42 + Math.sin(T * 2 + i) * 0.02; });
    grande.g.visible = c === 4;
    grande.g.rotation.z = Math.sin(T * 1.5) * 0.15;
    pequenas.forEach((m, i) => {
      m.g.visible = c === 5 || c === 6;
      if (c === 5) m.g.rotation.z = Math.sin(T * 18) > 0 ? 0 : Math.PI;
      if (c === 6) {
        m.g.rotation.z = T * (6 + i) + i;
        const calor = k.cl((abre ?? 0) / 3);
        m.o.material.color.setRGB(0.86 + 0.14 * calor, 0.24 + 0.31 * calor, 0.24 - 0.08 * calor);
      }
    });

    // forno montando em volta
    k.encaixar(magnetron, P("magnetron"));
    const pc = P("caixa");
    paredes.visible = pc > 0;
    lados.forEach((l, i) => (l.visible = pc * 4 > i));
    painel.visible = pc >= 1;
    dobradica.visible = P("porta") > 0;
    dobradica.rotation.y = -1.6 * (1 - k.suave(k.cl(P("porta"))));
    const ligado = c >= 7;
    luz.intensity = c >= 10 ? 1.6 : 0;
    visor.material.color.setHSL(0.42, 0.75, 0.35 + (ligado ? 0.15 * Math.sin(T * 4) : 0));

    k.nuvem(ondas, (i, s) => {
      if (!ligado || P("magnetron") < 1) return null;
      const fase = (T * 0.9 + s[0]) % 1;
      if (c === 8 && pc >= 1) {  // ondas batendo nas paredes e voltando
        const x = 0.4 - Math.abs(((fase * 2.4) % 2) - 1) * 0.8;
        return [x, 1.0 + s[1] * 0.42, -0.25 + s[2] * 0.5, 0.6, 1, 0.78];
      }
      return [0.42 - fase * 0.9, 1.15 + Math.sin(fase * 20 + s[1] * 6) * 0.06, -0.15 + s[2] * 0.3, 0.6, 1, 0.78];
    });
    k.nuvem(extras, (i, s) => {
      const fase = (T * 0.5 + s[0]) % 1;
      if (fogo && i < 30) return [-0.95 + (s[1] - 0.5) * 0.3, 1.1 + fase * 0.5, (s[2] - 0.5) * 0.2, 1, 0.55, 0.15];
      if (c >= 10 && i < 40) return [(s[1] - 0.5) * 0.25, 1.1 + fase * 0.3, (s[2] - 0.5) * 0.2, 1, 1, 1];
      if (c === 11 && i >= 40 && i < 46) {  // pontos quentes e frios espalhados pelo giro
        const a = giro + i;
        return [Math.cos(a) * 0.18, 1.08, Math.sin(a) * 0.18, ...(i % 2 ? [1, 0.5, 0.15] : [0.35, 0.65, 1])];
      }
      if (c === 12 && k.pisca(T, s) > 0.15) return [-0.6 + s[0] * 1.3, 0.95 + s[1] * 0.7, 0.35, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
