// Cena 3D do para-raios: tempestade, igreja com torre, captor no alto, cabo de descida e chão em corte com as hastes.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · PARA-RAIOS";
export const PECAS = {
  predio: { titulo: "Prédio", conta: false },
  captor: { titulo: "Captor (ponta)", conta: true },
  cabo: { titulo: "Cabo de descida", conta: true },
  aterramento: { titulo: "Aterramento", conta: true },
};
const VISTAS = {
  tudo: [[1.7, 1.7, 4.3], [0, 1.0, 0]],
  predio: [[1.3, 1.4, 3.0], [0, 0.9, 0]],
  captor: [[0.7, 2.5, 1.5], [0, 2.28, 0]],
  cabo: [[1.7, 1.3, 2.4], [0.5, 0.9, 0.3]],
  aterramento: [[1.2, 0.1, 2.9], [0.55, -0.3, 0.95]],
};
const PONTA = [0, 2.47, 0];

export function criar(args) {
  const k = kit(args, { ceu: 0x14162e, ambiente: 1.0, sol: 1.2 });
  const { THREE } = k;
  const chao = k.caixa(8, 0.8, 4, 0x6e4a32, [0, -0.4, -1]);         // terra (frente em corte)
  k.caixa(8, 0.04, 4, 0x46823c, [0, 0.0, -1]);                       // grama
  for (let i = 0; i < 6; i++) k.caixa(8, 0.008, 0.01, 0x5a3c28, [0, -0.1 - i * 0.12, 1.005]);

  // igreja com torre
  const predio = k.grupo([0, 0, 0]);
  k.caixa(1.0, 1.1, 0.8, 0xc8966e, [0, 0.55, 0], predio);
  k.caixa(0.42, 0.75, 0.42, 0xc8966e, [0, 1.47, 0], predio);
  const telhado = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.4, 4), k.toon(0x963c32));
  telhado.position.set(0, 2.05, 0);
  telhado.rotation.y = Math.PI / 4;
  predio.add(telhado);
  const janelas = [[-0.25, 0.75], [0.25, 0.75], [-0.25, 0.35], [0.25, 0.35], [0, 1.55]].map(([x, y]) =>
    k.caixa(0.14, 0.2, 0.01, 0, [x, y, 0.41 + (y > 1 ? -0.19 : 0)], predio, k.brilho(0xffdc78)));
  k.caixa(0.2, 0.32, 0.01, 0x5a3c28, [0, 0.16, 0.405], predio);

  // nuvens e Franklin
  const nuvens = k.grupo([0, 3.2, -0.6]);
  for (let i = 0; i < 9; i++) k.esfera(0.35 + (i % 3) * 0.1, i % 2 ? 0x4a4c62 : 0x5a5c74, [-2 + i * 0.5, (i % 2) * 0.15, (i % 3) * 0.2], nuvens);
  const franklin = k.grupo([-0.75, 0, 1.25]);
  k.cilindro(0.06, 0.3, 0x3c3c50, [0, 0.15, 0], franklin, 10);
  k.esfera(0.06, 0xf0c496, [0, 0.36, 0], franklin);
  const pipa = k.caixa(0.14, 0.14, 0.01, 0xdc3c3c, [0.4, 1.6, -0.2], franklin);
  pipa.rotation.z = Math.PI / 4;
  k.tubo([[0.05, 0.3, 0], [0.2, 0.9, -0.1], [0.4, 1.55, -0.2]], 0.004, 0xe6e6e6, false, franklin);

  // captor, cabo de descida e hastes
  const captor = k.cilindro(0.012, 0.25, 0xd2d6e0, [0, 2.35, 0], k.scene, 8);
  const brilhoPonta = k.esfera(0.03, 0, PONTA, k.scene, k.brilho(0xffffff));
  const caminhoCabo = [[0, 2.36, 0.02], [0.18, 1.85, 0.22], [0.52, 1.1, 0.42], [0.52, 0.02, 0.42], [0.55, -0.05, 0.9],
    [0.6, -0.15, 1.0]];
  const cabo = k.tubo(caminhoCabo, 0.015, 0xb4783c);
  const hastes = [0.42, 0.6, 0.78].map((x) => k.cilindro(0.012, 0.55, 0xc8ccd6, [x, -0.42, 1.01], k.scene, 8));
  const ligacao = k.tubo([[0.42, -0.15, 1.01], [0.78, -0.15, 1.01]], 0.012, 0xb4783c);

  const chuva = k.pontos(300, 0.018), raio = k.pontos(300, 0.05), energia = k.pontos(120, 0.04), fogo = k.pontos(80, 0.05);
  const curvaCabo = cabo.curva;
  const ANC = { predio: k.V(0.4, 1.1, 0.4), captor: brilhoPonta, cabo: k.V(0.52, 0.8, 0.42), aterramento: hastes[1],
    franklin: k.V(-0.75, 0.5, 1.25) };

  // relâmpago: zigue-zague sorteado a cada décimo de segundo, desenhado com pontos bem juntos
  const desenharRaio = (T, alvo, semente, ativo) => {
    let r = Math.floor(T * 10) * 7919 + semente;
    const rnd = () => ((r = (r * 16807) % 2147483647) / 2147483647);
    const pts = [[alvo[0] + (rnd() - 0.5) * 1.4, 3.2, alvo[2] - 0.4]];
    for (let i = 1; i < 8; i++) {
      const f = i / 8;
      pts.push([pts[0][0] + (alvo[0] - pts[0][0]) * f + (rnd() - 0.5) * 0.25, 3.2 + (alvo[1] - 3.2) * f, pts[0][2] + (alvo[2] - pts[0][2]) * f]);
    }
    pts.push(alvo);
    k.nuvem(raio, (i) => {
      if (!ativo) return null;
      const u = i / 300 * (pts.length - 1), j = Math.min(Math.floor(u), pts.length - 2), f = u - j;
      const a = pts[j], b = pts[j + 1];
      return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, 0.92, 0.95, 1];
    });
  };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const pisca = (T * 2.2) % 1 < 0.18;
    const comRaio = pisca && [1, 5, 6, 9, 10, 11].includes(c);
    k.scene.background.setHex(comRaio ? 0x5a64a0 : 0x14162e);
    const pc = P("captor"), pcab = P("cabo"), pat = P("aterramento");
    captor.visible = brilhoPonta.visible = pc > 0;
    captor.position.y = 2.35 + (1 - k.pop(k.cl(pc))) * 0.5;
    k.crescer(cabo, pcab);
    hastes.forEach((h) => { h.visible = pat > 0; h.scale.y = Math.max(k.cl(pat), 0.01); h.position.y = -0.15 - 0.275 * k.cl(pat); });
    ligacao.m.visible = pat > 0;
    const quebrado = c === 10 && A("ruim") !== null;
    if (quebrado) k.crescer(cabo, 0.55);
    franklin.visible = c === 4 && A("franklin") !== null;
    pipa.position.y = 1.6 + Math.sin(T * 2) * 0.05;
    janelas.forEach((j, i) => j.material.color.setHSL(0.12, 1, 0.65 + 0.1 * Math.sin(T * 3 + i)));

    let alvo = null;
    if (c === 1) alvo = [0, 2.25, 0];
    else if ([5, 6, 9, 11].includes(c) || quebrado) alvo = PONTA;
    desenharRaio(T, alvo || PONTA, c, comRaio && alvo !== null);
    k.nuvem(chuva, (i, s) => {
      const fase = (T * 1.6 + s[0]) % 1;
      return [-2.5 + s[1] * 5, 3.0 - fase * 3.1, -1.5 + s[2] * 3, 0.55, 0.62, 0.85];
    });
    k.nuvem(energia, (i, s) => {
      const fase = (T * 1.5 + s[0]) % 1;
      if ((c === 9 || c === 11) && pcab >= 1 && pat >= 1) {
        if (i < 40) { const p = curvaCabo.getPointAt((T * 1.2 + i / 40) % 1); return [p.x, p.y, p.z, 1, 1, 0.6]; }
        const a = Math.PI * (0.05 + 0.9 * s[1]);
        return [0.6 + Math.cos(a) * fase * 0.7, -0.2 - Math.sin(a) * fase * 0.5, 1.01, 1, 0.9, 0.5];
      }
      if (c === 1 && comRaio && i < 50) {  // sem para-raios: a descarga entra pelo prédio
        return [(s[1] - 0.5) * 0.5, 2.2 - fase * 2.1, 0.42, 1, 1, 0.7];
      }
      if (quebrado && comRaio && i < 30) return [0.52 - fase * 0.4, 1.1 - fase * 0.2, 0.42, 1, 1, 0.7];
      if (c === 4 && franklin.visible && i < 30) return [(s[1] - 0.5) * 0.4, 2.5 + fase * 0.6, -0.3, 0.7, 0.8, 1];
      return null;
    });
    k.nuvem(fogo, (i, s) => {
      const queimando = c === 2 || quebrado;
      if (!queimando) return null;
      const fase = (T * 2.5 + s[0]) % 1, foco = [[-0.3, 0.9], [0.3, 0.5], [0, 1.6]][i % 3];
      return [foco[0] + (s[1] - 0.5) * 0.15, foco[1] + fase * 0.3, 0.42, 1, 0.85 - 0.6 * fase, 0.2];
    });
    if (c === 11) k.nuvem(fogo, (i, s) => (k.pisca(T, s) > 0.15 ? [-1 + s[0] * 2, 0.2 + s[1] * 2.3, 0.6, 1, 1, 0.85] : null));
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
