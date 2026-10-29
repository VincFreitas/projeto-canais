// Cena 3D do freio: roda girando, disco e pastilhas, pedal, cilindro mestre, fluido no cano, pistão largo e pinça.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · FREIO";
export const PECAS = {
  roda: { titulo: "Roda", conta: false },
  disco: { titulo: "Disco e pastilhas", conta: true },
  pedal: { titulo: "Pedal", conta: false },
  fluido: { titulo: "Fluido de freio", conta: true },
  cilindro: { titulo: "Cilindro mestre", conta: true },
  pistao_roda: { titulo: "Pistão largo", conta: true },
  pinca: { titulo: "Pinça", conta: true },
};
const VISTAS = {
  tudo: [[-0.15, 1.25, 3.1], [-0.25, 0.6, 0]],
  roda: [[0.75, 0.75, 1.4], [0.4, 0.52, 0]],
  disco: [[0.7, 0.8, 1.0], [0.4, 0.55, 0]],
  pinca: [[0.75, 1.0, 0.8], [0.4, 0.74, 0]],
  pistao_roda: [[0.75, 1.0, 0.8], [0.4, 0.74, 0]],
  fluido: [[-0.1, 1.1, 1.6], [-0.2, 0.65, 0]],
  cilindro: [[-0.45, 0.95, 1.0], [-0.75, 0.6, 0]],
  pedal: [[-0.35, 0.85, 1.3], [-0.85, 0.45, 0]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x262838 });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#5a5a64", "#4a4a54", [10, 10]), parede: k.azulejo("#4a4e66", "#5a5e78", [20, 10]), janela: false });
  for (let i = 0; i < 6; i++) k.caixa(0.3, 0.005, 0.05, 0xdcc83c, [-1.5 + i * 0.6, 0.003, 0.6]);

  // roda: pneu, aro com raios, disco e pinça
  const CX = 0.4, CY = 0.52;
  const roda = k.grupo([CX, CY, 0]);
  const pneu = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.1, 12, 36), k.toon(0x222228));
  roda.add(pneu);
  const aro = k.grupo([0, 0, 0], roda);
  k.cilindro(0.06, 0.08, 0x8a8e9a, [0, 0, 0], aro, 16).rotation.x = Math.PI / 2;
  for (let i = 0; i < 5; i++) {
    const r = k.caixa(0.03, 0.32, 0.02, 0xb4b8c4, [0, 0, -0.06], aro);
    r.geometry.translate(0, 0.17, 0);
    r.rotation.z = i * Math.PI * 2 / 5;
  }
  const discoG = k.grupo([0, 0, 0.02], roda);
  const disco = k.cilindro(0.26, 0.025, 0xc8ccd6, [0, 0, 0], discoG, 32);
  disco.rotation.x = Math.PI / 2;
  const furos = k.grupo([0, 0, 0.014], discoG);
  for (let i = 0; i < 6; i++) k.cilindro(0.018, 0.005, 0x50505a, [Math.cos(i) * 0.18, Math.sin(i) * 0.18, 0], furos, 10).rotation.x = Math.PI / 2;
  const pinca = k.grupo([CX, CY + 0.25, 0]);
  k.caixa(0.2, 0.12, 0.16, 0xd23c3c, [0, 0, 0], pinca);
  const pastilhas = [-1, 1].map((s) => k.caixa(0.14, 0.06, 0.02, 0x463c3c, [CX, CY + 0.235, s * 0.045]));
  const pistao = k.cilindro(0.028, 0.04, 0xb4b4be, [CX, CY + 0.29, 0.09], k.scene, 16);
  pistao.rotation.x = Math.PI / 2;

  // para-lama do carro
  const paralama = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.12, 8, 24, Math.PI), k.toon(0xc8283c));
  paralama.position.set(CX, CY, -0.05);
  k.scene.add(paralama);
  const lataria = k.caixa(2.0, 0.5, 0.3, 0xc8283c, [CX - 0.3, 1.35, -0.3]);

  // pedal, cilindro mestre e cano com fluido
  const pedal = k.grupo([-0.85, 0.75, 0]);
  const haste = k.caixa(0.03, 0.5, 0.03, 0x60606a, [0, -0.25, 0], pedal);
  const sapata = k.caixa(0.14, 0.04, 0.12, 0x3c3c44, [0, -0.5, 0.03], pedal);
  const pe = k.caixa(0.12, 0.08, 0.28, 0x2a2a30, [0, -0.5, 0.2], pedal);
  const cilindro = k.grupo([-0.62, 0.68, 0]);
  k.caixa(0.32, 0.08, 0.08, 0x9a9eaa, [0, 0, 0], cilindro, k.vidro(0xc8ccd6, 0.55));
  const embolo = k.caixa(0.05, 0.07, 0.07, 0x50505a, [-0.12, 0, 0], cilindro);
  k.caixa(0.1, 0.07, 0.07, 0xf0d23c, [0.05, 0.08, 0], cilindro);  // reservatório
  const caminho = [[-0.45, 0.68, 0], [-0.1, 0.68, 0.14], [0.05, 0.95, 0.14], [CX, 0.98, 0.14], [CX, 0.84, 0.06]];
  const cano = k.tubo(caminho, 0.022, 0x9a9eaa);
  cano.mat.transparent = true; cano.mat.opacity = 0.5;
  const fluido = k.tubo(caminho, 0.014, 0xf0d23c, true);
  const pressao = k.pontos(30, 0.03), faiscas = k.pontos(60, 0.035), extras = k.pontos(40, 0.05);
  const curva = fluido.curva;

  const placa = k.grupo([-1.0, 1.7, 0]);
  k.caixa(0.5, 0.25, 0.02, 0xf0c83c, [0, 0, 0], placa);
  const seta = (x, tam) => k.caixa(0.04 * tam, 0.15 * tam, 0.02, 0x64dc78, [x, 0, 0.1]);
  const setaPe = seta(-0.85, 1), setaRoda = seta(CX, 2.4);

  const ANC = { roda: k.V(CX, CY + 0.52, 0), disco: k.V(CX, CY + 0.1, 0.02), pedal: sapata, fluido: k.V(0.05, 0.95, 0),
    cilindro: k.V(-0.62, 0.74, 0.05), pistao_roda: pistao, pinca: k.V(CX, CY + 0.32, 0.05), calor: k.V(CX + 0.12, CY + 0.2, 0.03) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    let freando = 0;
    if (c === 4 && A("atrito") !== null) freando = k.suave(k.cl(A("atrito") / 2));
    else if ([7, 8, 9, 10].includes(c) && (A("pressao") !== null || c > 7)) freando = 0.6 + 0.4 * Math.sin(T * 2) ** 2;
    else if (c === 11) freando = 0.2;
    else if (c === 12) freando = k.suave(k.cl((A("pronto") ?? 0) / 2));
    const giro = T * 6 * (1 - freando);
    aro.rotation.z = -giro; discoG.rotation.z = -giro;
    paralama.visible = lataria.visible = c >= 2;
    k.encaixar(discoG, P("disco"));
    const calor = c === 4 || c === 12 ? freando : 0.35 * freando;
    disco.material.color.setRGB(0.78 + 0.22 * calor, 0.8 - 0.35 * calor, 0.84 - 0.65 * calor);
    pastilhas.forEach((p, i) => { p.visible = P("disco") > 0; p.position.z = (i ? 1 : -1) * (0.045 - 0.012 * freando); });
    k.encaixar(pinca, P("pinca"));
    pistao.visible = P("pistao_roda") > 0;
    pistao.scale.set(1, 1, 1 + freando);
    const pisado = [7, 8, 9, 10, 12].includes(c) ? 1 : c === 5 ? 0.5 + 0.5 * Math.sin(T * 3) : 0;
    pedal.visible = c >= 5;
    pedal.rotation.z = -(c === 11 ? 0.5 : 0.25) * pisado - (c === 11 ? 0.3 : 0);
    k.encaixar(cilindro, P("cilindro"));
    embolo.position.x = -0.12 + 0.1 * pisado;
    k.crescer(cano, P("fluido"));
    k.crescer(fluido, P("fluido"));
    k.correr(pressao, curva, T, 0.8, 0xffffc8, 0xffffff, 16, c >= 7 && pisado > 0 && P("fluido") >= 1);
    placa.visible = c === 2 && A("carro") !== null;
    setaPe.visible = setaRoda.visible = c === 9 && A("forca") !== null;
    if (setaRoda.visible) setaRoda.position.set(CX, CY + 0.55, 0.15);

    k.nuvem(faiscas, (i, s) => {
      if (!(freando > 0.3 && [4, 10, 12].includes(c))) return null;
      const fase = (T * 2 + s[0]) % 1, a = -0.6 + s[1] * 1.2;
      return [CX + 0.12 + Math.cos(a) * fase * 0.35, CY + 0.25 + Math.sin(a) * fase * 0.3 - fase * fase * 0.3, 0.08, 1, 0.85 - 0.4 * fase, 0.25];
    });
    k.nuvem(extras, (i, s) => {
      const fase = (T * 0.7 + s[0]) % 1;
      if (c === 11 && i < 8) return [-0.1 + (i % 3) * 0.02, 0.68 + 0.02 * Math.sin(T * 4 + i), 0.14, 1, 1, 1];  // bolhas de ar no cano
      if (c === 5 && i < 12) return [-0.85 + i * 0.1, 0.4 + i * 0.03, 0.05, 1, 1, 1];  // caminho pontilhado
      if (calor > 0.5 && i >= 12 && i < 30) return [CX + (s[1] - 0.5) * 0.3, CY + 0.3 + fase * 0.3, 0.05, 1, 0.55, 0.2];
      if (c === 12 && k.pisca(T, s) > 0.15) return [-0.6 + s[0] * 1.6, 0.2 + s[1] * 1.2, 0.3, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
