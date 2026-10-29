// Cena 3D do extintor: triângulo do fogo, água, óleo, cilindro em corte com pó e gás, pino, rótulo ABC, CO2 e uso.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · EXTINTOR";
export const PECAS = {
  fogo: { titulo: "Fogo", conta: false },
  cilindro: { titulo: "Cilindro com pó", conta: true },
  gas: { titulo: "Gás apertado", conta: true },
  pino: { titulo: "Pino de trava", conta: true },
  rotulo: { titulo: "Rótulo ABC", conta: true },
};
const VISTAS = {
  tudo: [[1.15, 1.35, 2.4], [-0.1, 0.6, 0]],
  fogo: [[0.1, 1.15, 1.9], [-0.6, 0.62, 0.2]],
  cilindro: [[1.15, 0.95, 1.35], [0.4, 0.45, 0]],
  gas: [[1.0, 1.1, 1.0], [0.4, 0.62, 0]],
  pino: [[0.95, 1.0, 0.75], [0.4, 0.72, 0]],
  rotulo: [[1.05, 0.7, 1.15], [0.4, 0.4, 0.1]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x2a2e3c });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#aab0c0", "#969cac", [12, 12]), parede: k.azulejo("#e2e6ee", "#ccd2de", [12, 6]), janela: false,
    fundoZ: -0.5 });
  const porta = k.caixa(0.6, 1.3, 0.04, 0x5a6478, [-1.2, 0.65, -0.48]);
  const saida = k.caixa(0.35, 0.14, 0.03, 0, [-1.2, 1.45, -0.46], k.scene, k.brilho(0x28aa5a));

  // lixeira com fogo, balde, frigideira com óleo
  const lixeira = k.cilindro(0.15, 0.32, 0x60606a, [-0.6, 0.16, 0.2], k.scene, 14);
  const chamas = Array.from({ length: 7 }, (_, i) => {
    const m = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.25, 6), k.brilho(i % 2 ? 0xffb428 : 0xff6428));
    m.position.set(-0.6 + Math.cos(i) * 0.07, 0.42, 0.2 + Math.sin(i) * 0.07);
    k.scene.add(m);
    return m;
  });
  const balde = k.grupo([-0.2, 0.7, 0.3]);
  k.cilindro(0.1, 0.18, 0x50a0dc, [0, 0, 0], balde, 14);
  const frigideira = k.grupo([-0.6, 0.52, 0.2]);
  k.cilindro(0.2, 0.05, 0x3c3c44, [0, 0, 0], frigideira, 20);
  k.caixa(0.3, 0.03, 0.04, 0x3c3c44, [0.32, 0, 0], frigideira);

  // triângulo do fogo
  const tri = k.grupo([-0.6, 0.95, 0.2]);
  const vertices = [[0, 0.22, 0], [-0.2, -0.12, 0], [0.2, -0.12, 0]];
  k.tubo([...vertices, vertices[0]], 0.012, 0xffa028, true, tri);
  const icones = [k.caixa(0.08, 0.08, 0.08, 0x8c5a32, vertices[1], tri), k.esfera(0.05, 0x78c8ff, vertices[2], tri),
    k.esfera(0.05, 0xff5a28, vertices[0], tri)];

  // extintor em corte
  const ext = k.grupo([0.4, 0, 0]);
  const casco = k.cilindro(0.11, 0.55, 0, [0, 0.3, 0], ext, 20, k.vidro(0xdc2828, 0.45));
  const po = k.cilindro(0.1, 0.36, 0xf0d23c, [0, 0.21, 0], ext, 20);
  k.cilindro(0.11, 0.03, 0xb41e1e, [0, 0.03, 0], ext, 20);
  const cabeca = k.grupo([0, 0.6, 0], ext);
  k.cilindro(0.045, 0.06, 0x26262c, [0, 0, 0], cabeca, 12);
  const gatilho = k.caixa(0.16, 0.025, 0.04, 0x26262c, [0.06, 0.06, 0], cabeca);
  k.caixa(0.16, 0.025, 0.04, 0x26262c, [0.06, 0.02, 0], cabeca);
  const mangueira = k.tubo([[0.44, 0.62, 0], [0.52, 0.5, -0.06], [0.5, 0.32, 0.04], [0.3, 0.44, 0.26]], 0.016, 0x26262c);
  const bico = k.cilindro(0.025, 0.08, 0x26262c, [0.22, 0.47, 0.28], k.scene, 10);
  bico.rotation.z = 1.2;
  const manometro = k.grupo([-0.05, 0.62, 0.05], ext);
  k.cilindro(0.035, 0.015, 0xf4f4f8, [0, 0, 0], manometro, 16).rotation.x = Math.PI / 2;
  k.caixa(0.004, 0.025, 0.004, 0x28a03c, [0, 0.008, 0.01], manometro);
  const pino = k.grupo([0.02, 0.645, 0.03], ext);
  const argola = new THREE.Mesh(new THREE.TorusGeometry(0.025, 0.006, 6, 16), k.toon(0xd2d2dc));
  argola.position.x = -0.05;
  pino.add(argola);
  k.cilindro(0.004, 0.08, 0xd2d2dc, [0, 0, 0], pino, 6).rotation.z = Math.PI / 2;
  k.caixa(0.012, 0.02, 0.01, 0xf0c828, [0.02, -0.01, 0], pino);
  const rotulo = k.grupo([0, 0.33, 0.112], ext);
  k.caixa(0.16, 0.12, 0.004, 0xfafafa, [0, 0, 0], rotulo);
  const letras = [0x3cb45a, 0xdc3c3c, 0x3c6edc].map((cor, i) => k.caixa(0.04, 0.04, 0.006, cor, [-0.05 + i * 0.05, 0, 0.003], rotulo));
  const co2 = k.grupo([0.72, 0, 0.3]);
  k.cilindro(0.09, 0.6, 0x26262c, [0, 0.3, 0], co2, 16);
  k.cilindro(0.04, 0.12, 0x46464e, [0.1, 0.55, 0.05], co2, 10).rotation.z = 1;

  const fogo = k.pontos(120, 0.04), poJato = k.pontos(160, 0.04), gas = k.pontos(40, 0.025), vapor = k.pontos(80, 0.06);
  const ANC = { fogo: k.V(-0.6, 0.65, 0.2), cilindro: k.V(0.4, 0.6, 0.12), gas: k.V(0.4, 0.5, 0.11), pino: argola,
    rotulo: k.V(0.4, 0.4, 0.12), combustivel: icones[0], oxigenio: icones[1], calor: icones[2], po: k.V(0.4, 0.2, 0.11),
    manometro: manometro, letra_a: letras[0], letra_b: letras[1], letra_c: letras[2], base: k.V(-0.6, 0.35, 0.35) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    let forca = 1;
    if (c === 2 && A("agua") !== null) forca = 1 - k.suave(k.cl(A("agua") / 1.2));
    if (c === 3 && A("oleo") !== null) forca = 1 + k.suave(k.cl(A("oleo") / 0.5));
    if (c === 10 && A("usar") !== null) forca = 1 - k.suave(k.cl((A("usar") - 1) / 2.5));
    if (c >= 11) forca = 0;
    chamas.forEach((ch, i) => {
      ch.visible = forca > 0.05;
      ch.scale.set(forca, forca * (0.7 + 0.5 * Math.abs(Math.sin(T * 9 + i))), forca);
      ch.position.y = (c === 3 ? 0.62 : 0.42) + 0.06 * forca;
    });
    lixeira.visible = c !== 3;
    frigideira.visible = c === 3;
    balde.visible = c === 2 && A("agua") !== null;
    balde.rotation.z = k.cl((A("agua") ?? 0) / 0.6) * 1.8;
    tri.visible = c === 1 && A("triangulo") !== null;
    tri.scale.setScalar(Math.max(k.pop(k.cl((A("triangulo") ?? 0) / 0.6)), 0.001));
    tri.lookAt(k.cam.position);
    icones.forEach((ic, i) => (ic.rotation.y = T * (1 + i)));

    const pc = P("cilindro");
    ext.visible = mangueira.m.visible = bico.visible = pc > 0;
    ext.scale.setScalar(Math.max(k.pop(k.cl(pc)), 0.001));
    manometro.visible = P("gas") > 0;
    const usando = c === 10 && A("usar") !== null;
    pino.visible = P("pino") > 0 && !(usando && A("usar") > 0.3);
    pino.position.x = 0.02 - (usando ? k.cl(A("usar") / 0.3) * 0.2 : 0);
    rotulo.visible = P("rotulo") > 0;
    rotulo.scale.setScalar(Math.max(k.pop(k.cl(P("rotulo"))), 0.001));
    gatilho.rotation.z = usando && A("usar") > 0.8 ? -0.25 : 0;
    co2.visible = c === 8 && A("co2") !== null;
    porta.visible = true;
    saida.material.color.setHSL(0.4, 0.6, c === 11 ? 0.35 + 0.15 * Math.sin(T * 5) : 0.35);

    k.nuvem(fogo, (i, s) => {
      if (forca <= 0.05) return null;
      const fase = (T * 2 + s[0]) % 1, base = c === 3 ? 0.55 : 0.34;
      return [-0.6 + (s[1] - 0.5) * 0.25 * forca, base + fase * 0.45 * forca, 0.2 + (s[2] - 0.5) * 0.25 * forca, 1, 0.85 - 0.55 * fase, 0.2];
    });
    k.nuvem(poJato, (i, s) => {
      const fase = (T * 2 + s[0]) % 1;
      if (usando && A("usar") > 0.8) {  // jato varrendo a base do fogo
        const ang = Math.sin(T * 3) * 0.25;
        return [0.2 - fase * 0.8, 0.46 - fase * 0.12, 0.28 + Math.sin(ang) * fase * 0.3 + (s[1] - 0.5) * fase * 0.15, 0.98, 0.84, 0.25];
      }
      if (c === 4 && i < 60 && k.pisca(T, s) > 0.1) return [0.4 + (s[1] - 0.5) * 0.18, 0.06 + s[2] * 0.3, 0.11, 0.98, 0.84, 0.25];
      return null;
    });
    k.nuvem(gas, (i, s) => {
      if (P("gas") <= 0) return null;
      const a = s[0] * 6.3, r = s[1] * 0.09;
      return [0.4 + Math.cos(a) * r + Math.sin(T * 9 + i) * 0.004, 0.42 + s[2] * 0.12, Math.sin(a) * r, 0.47, 0.75, 1];
    });
    k.nuvem(vapor, (i, s) => {
      const fase = (T * 0.6 + s[0]) % 1;
      if (c === 2 && forca < 0.6) return [-0.6 + (s[1] - 0.5) * 0.3, 0.4 + fase * 0.6, 0.2, 1, 1, 1];
      if (c === 8 && co2.visible) return [0.62 - fase * 0.6, 0.55 + (s[1] - 0.5) * 0.3 * fase, 0.35 + (s[2] - 0.5) * 0.3, 0.92, 0.97, 1];
      if (c === 12 && k.pisca(T, s) > 0.15) return [-0.8 + s[0] * 1.6, 0.2 + s[1] * 1.0, 0.4, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
