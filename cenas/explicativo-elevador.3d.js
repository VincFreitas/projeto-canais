// Cena 3D do elevador: poço em corte, polia e motor, contrapeso, freio de segurança, limitador e a plataforma de Otis.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · ELEVADOR";
export const PECAS = {
  cabine: { titulo: "Cabine", conta: false },
  motor: { titulo: "Motor", conta: true },
  contrapeso: { titulo: "Contrapeso", conta: true },
  freio: { titulo: "Freio de segurança", conta: true },
  limitador: { titulo: "Limitador de velocidade", conta: true },
};
const VISTAS = {
  tudo: [[2.0, 2.1, 4.2], [0, 1.75, 0]],
  cabine: [[1.3, 1.6, 2.4], [0, 1.3, 0]],
  motor: [[1.1, 3.45, 1.8], [0.15, 3.15, 0]],
  contrapeso: [[1.5, 2.0, 2.8], [0.25, 1.6, -0.2]],
  freio: [[1.0, 1.55, 1.8], [-0.45, 1.3, 0]],
  limitador: [[-0.1, 3.35, 1.7], [-0.35, 3.1, 0]],
};
const TOPO = 3.15;

export function criar(args) {
  const k = kit(args, { ceu: 0x1a1c40 });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#46464e", "#3a3a42", [10, 10]), parede: k.azulejo("#d27878", "#b46060", [12, 8]), janela: false,
    fundoZ: -0.6 });
  // poço: paredes laterais em corte, andares e trilhos
  for (const x of [-0.55, 0.55]) k.caixa(0.05, 3.4, 1.0, 0x6a6474, [x, 1.7, -0.1]).userData.semSombra = true;
  for (let i = 0; i < 4; i++) k.caixa(1.15, 0.03, 0.1, 0x8a8494, [0, 0.8 * i + 0.05, 0.4]);
  for (const x of [-0.5, 0.5]) k.caixa(0.03, 3.3, 0.04, 0xa0a6b4, [x, 1.65, 0]);
  const casaMaquinas = k.caixa(1.3, 0.05, 1.0, 0x5a5464, [0, 2.95, -0.1]);

  // polia e motor
  const polia = k.grupo([0.1, TOPO, 0]);
  const roda = new THREE.Mesh(new THREE.TorusGeometry(0.14, 0.025, 8, 28), k.toon(0x60606a));
  polia.add(roda);
  for (let i = 0; i < 4; i++) { const r = k.caixa(0.02, 0.26, 0.02, 0x46464e, [0, 0, 0], polia); r.rotation.z = i * Math.PI / 4; }
  const motor = k.grupo([0.42, TOPO, 0]);
  k.cilindro(0.11, 0.22, 0x3c5ab4, [0, 0, 0], motor, 16).rotation.x = Math.PI / 2;
  k.caixa(0.08, 0.04, 0.04, 0x60606a, [-0.15, 0, 0], motor);

  // cabine com gente, plataforma antiga, contrapeso, cabos
  const cabine = k.grupo([0, 1, 0]);
  k.caixa(0.8, 0.9, 0.7, 0, [0, 0.45, 0], cabine, k.vidro(0xf4ead2, 0.35));
  k.caixa(0.8, 0.04, 0.7, 0xc8b48c, [0, 0.02, 0], cabine);
  k.caixa(0.8, 0.04, 0.7, 0xc8b48c, [0, 0.88, 0], cabine);
  const luzCabine = k.caixa(0.5, 0.02, 0.2, 0, [0, 0.85, 0], cabine, k.brilho(0xfff0b4));
  const gente = [0x3c6ed2, 0xd24660, 0x46aa6e].map((cor, i) => {
    const g = k.grupo([-0.22 + i * 0.22, 0.04, 0], cabine);
    k.cilindro(0.07, 0.42, cor, [0, 0.25, 0], g, 10);
    k.esfera(0.07, 0xf0c496, [0, 0.55, 0], g);
    return g;
  });
  const plataforma = k.grupo([0, 1, 0]);
  k.caixa(0.85, 0.05, 0.7, 0x8c6440, [0, 0, 0], plataforma);
  const otis = k.grupo([0, 0.03, 0], plataforma);
  k.cilindro(0.08, 0.45, 0x282838, [0, 0.25, 0], otis, 10);
  k.esfera(0.07, 0xf0c496, [0, 0.55, 0], otis);
  k.cilindro(0.06, 0.12, 0x141418, [0, 0.66, 0], otis, 12);
  k.cilindro(0.1, 0.01, 0x141418, [0, 0.61, 0], otis, 16);
  const contrapeso = k.caixa(0.22, 0.45, 0.14, 0x5a5a64, [0.24, 1.5, -0.3]);
  const cabo1 = k.cilindro(0.008, 1, 0x26262c, [0, 0, 0], k.scene, 6);
  const cabo2 = k.cilindro(0.008, 1, 0x26262c, [0, 0, 0], k.scene, 6);
  const esticar = (cabo, a, b) => {
    cabo.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
    const d = new THREE.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    cabo.scale.set(1, d.length(), 1);
    cabo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  };

  // freio de segurança (garras) e limitador
  const garras = [-1, 1].map((s) => k.caixa(0.06, 0.12, 0.1, 0xd23c3c, [s * 0.46, 1.4, 0]));
  const limitador = k.grupo([-0.35, TOPO, 0]);
  const rodinha = new THREE.Mesh(new THREE.TorusGeometry(0.08, 0.02, 8, 20), k.toon(0xe6c83c));
  limitador.add(rodinha);
  const pesinhos = [-1, 1].map((s) => k.esfera(0.02, 0x26262c, [s * 0.05, 0, 0], limitador));
  const caboLim = k.cilindro(0.006, 1, 0x60606a, [0, 0, 0], k.scene, 6);

  const placa = k.grupo([-1.0, 2.2, 0.3]);
  k.caixa(0.45, 0.25, 0.02, 0xf0c83c, [0, 0, 0], placa);
  const faiscas = k.pontos(60, 0.03), extras = k.pontos(50, 0.04);
  const pontaCabo = k.grupo([0.1, 2.6, 0]);
  const ANC = { cabine: k.V(0, 2.0, 0.35), motor: motor, contrapeso: contrapeso, freio: garras[0], limitador: limitador,
    cabo: pontaCabo, trilho: k.V(-0.5, 1.3, 0.03), otis: k.V(0, 1.75, 0.1) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const ciclo = 0.5 - 0.5 * Math.cos(T * 0.5);
    let carY = 0.3 + 1.6 * ciclo, girando = 1, cortado = false, caindo = 0;
    if (c === 1) carY = A("corda") !== null ? 0.3 + 1.2 * k.suave(k.cl(A("corda") / 3)) : 0.3;
    if (c === 2 && A("pesado") !== null) { carY = 0.6 + Math.sin(T * 6) * 0.02; girando = 0.1; }
    if (c === 4 && A("esforco") !== null) { carY = 0.6 + 0.2 * k.suave(k.cl(A("esforco") / 3)); girando = 0.3; }
    if (c === 7 && A("arrebenta") !== null) { cortado = true; caindo = Math.min(A("arrebenta") ** 2 * 0.4, 0.8); carY = 1.6 - caindo; }
    if (c === 8) { cortado = true; carY = 0.9; }
    if (c === 9) carY = 1.3;
    if (c === 10 && A("otis") !== null) { cortado = A("otis") > 0.6; carY = 1.2 - (cortado ? Math.min((A("otis") - 0.6) * 0.3, 0.12) : 0); }
    if (c === 11) { cortado = true; carY = 1.08; }
    const antiga = c === 10 || c === 11;
    cabine.visible = !antiga;
    plataforma.visible = antiga;
    cabine.position.y = plataforma.position.y = carY;
    gente.forEach((g) => (g.visible = c >= 2));
    roda.rotation.z = -T * 3 * girando;
    polia.children.forEach((ch, i) => { if (i > 0) ch.rotation.z = i * Math.PI / 4 - T * 3 * girando; });
    k.encaixar(motor, P("motor"));
    motor.position.x = 0.42 + (c === 4 ? Math.sin(T * 50) * 0.004 : 0);
    const topoCarro = carY + (antiga ? 0.05 : 0.9);
    if (!cortado) esticar(cabo1, [0, topoCarro, 0], [-0.04, TOPO, 0]);
    else esticar(cabo1, [-0.04, TOPO, 0], [-0.04 + Math.sin(T * 6) * 0.04, 2.5, 0]);
    pontaCabo.position.set(-0.04, (topoCarro + TOPO) / 2, 0);
    const cp = P("contrapeso");
    contrapeso.visible = cabo2.visible = cp > 0 && !cortado;
    const cwY = Math.max(0.3, 2.6 - (carY - 0.3));
    contrapeso.position.y = cwY;
    contrapeso.scale.setScalar(Math.max(k.pop(k.cl(cp)), 0.001));
    esticar(cabo2, [0.24, cwY + 0.22, -0.3], [0.24, TOPO, -0.05]);
    const fr = P("freio");
    garras.forEach((g, i) => {
      g.visible = fr > 0;
      g.scale.setScalar(Math.max(k.pop(k.cl(fr)), 0.001));
      g.position.set((i ? 1 : -1) * (cortado && [8, 11].includes(c) ? 0.475 : 0.44), carY + 0.4, 0);
    });
    k.encaixar(limitador, P("limitador"));
    rodinha.rotation.z = T * 4;
    pesinhos.forEach((p, i) => p.position.set(Math.cos(T * 4 + i * Math.PI) * 0.05, Math.sin(T * 4 + i * Math.PI) * 0.05, 0));
    caboLim.visible = P("limitador") > 0 && !antiga;
    esticar(caboLim, [-0.43, TOPO, 0], [-0.43, carY + 0.5, 0]);
    placa.visible = c === 2 && A("pesado") !== null;
    luzCabine.visible = !antiga;

    k.nuvem(faiscas, (i, s) => {
      const fase = (T * 2 + s[0]) % 1;
      if ((c === 8 || c === 11) && cortado) return [(i % 2 ? 0.47 : -0.47), carY + 0.35 - fase * 0.3, (s[1] - 0.5) * 0.08, 1, 0.85 - fase * 0.4, 0.3];
      if (c === 7 && A("arrebenta") !== null && A("arrebenta") < 0.6 && i < 20) return [-0.04 + (s[1] - 0.5) * 0.2, 2.5 + (s[2] - 0.5) * 0.2, 0.05, 1, 1, 0.5];
      return null;
    });
    k.nuvem(extras, (i, s) => {
      if (c === 4 && A("esforco") !== null && i < 10) return [0.42 + (s[0] - 0.5) * 0.2, TOPO + 0.15 + ((T + s[1]) % 1) * 0.2, 0.1, 0.6, 0.8, 1];
      if (c === 12 && k.pisca(T, s) > 0.15) return [-0.5 + s[0], 0.3 + s[1] * 2.8, 0.4, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
