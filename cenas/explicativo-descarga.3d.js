// Cena 3D da descarga: vaso e caixa translúcidos, tampa de borracha, sifão em S, água parada e boia.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · DESCARGA";
export const PECAS = {
  vaso: { titulo: "Vaso", conta: false },
  caixa: { titulo: "Caixa acoplada", conta: true },
  sifao: { titulo: "Sifão", conta: true },
  boia: { titulo: "Boia", conta: true },
};
const VISTAS = {
  tudo: [[1.3, 1.05, 1.5], [0, 0.5, -0.1]],
  vaso: [[0.9, 0.9, 1.0], [0, 0.4, 0]],
  caixa: [[0.95, 1.05, 0.75], [0, 0.78, -0.32]],
  sifao: [[1.45, 0.55, 0.35], [0, 0.26, -0.1]],
  boia: [[0.75, 1.0, 0.45], [-0.08, 0.78, -0.32]],
};
const SIFAO = [[0, 0.3, 0.03], [0, 0.18, 0.08], [0, 0.1, 0.0], [0, 0.18, -0.1], [0, 0.26, -0.17], [0, 0.12, -0.26],
  [0, 0.02, -0.3]];

export function criar(args) {
  const k = kit(args, { ceu: 0x22383a });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#d8dce2", "#b8bec8", [14, 14]), parede: k.azulejo("#96d6b4", "#b4e6c8", [16, 8]), janela: false });

  const louca = k.vidro(0xf8f8fc, 0.5);
  const vaso = k.grupo([0, 0, 0]);
  const bacia = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.13, 0.22, 24, 1, true), louca);
  bacia.position.y = 0.42;
  vaso.add(bacia);
  k.cilindro(0.13, 0.25, 0, [0, 0.13, -0.02], vaso, 20, louca);
  const assento = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.03, 8, 28), k.toon(0xf4f4f8));
  assento.rotation.x = Math.PI / 2;
  assento.position.y = 0.54;
  vaso.add(assento);
  const aguaBacia = k.cilindro(0.18, 0.02, 0, [0, 0.36, 0], vaso, 24, k.brilho(0x5aaaf0, { transparent: true, opacity: 0.85 }));

  // caixa acoplada translúcida, com água, tampa de borracha e boia
  const caixa = k.grupo([0, 0, -0.32]);
  k.caixa(0.5, 0.42, 0.2, 0, [0, 0.78, 0], caixa, k.vidro(0xe8f0ff, 0.3));
  const aguaCaixa = k.caixa(0.46, 0.36, 0.16, 0, [0, 0.76, 0], caixa, k.brilho(0x5aaaf0, { transparent: true, opacity: 0.6 }));
  const botao = k.cilindro(0.04, 0.03, 0xd2d2dc, [0.12, 1.0, 0], caixa, 16);
  const dobra = k.grupo([0.02, 0.585, 0], caixa);
  const tampa = k.cilindro(0.05, 0.015, 0x282830, [0.04, 0, 0], dobra, 16);
  const corrente = k.caixa(0.005, 0.38, 0.005, 0x60606a, [0.07, 0.79, 0], caixa);
  const cano = k.tubo([[0, 0.57, -0.32], [0, 0.5, -0.2], [0, 0.52, -0.05]], 0.03, 0xaab0ba);

  const boia = k.grupo([0, 0, 0], caixa);
  k.cilindro(0.015, 0.36, 0xaab0ba, [-0.18, 0.76, 0], boia, 10);  // cano da torneirinha
  const valvula = k.caixa(0.05, 0.04, 0.05, 0x60606a, [-0.18, 0.95, 0], boia);
  const haste = k.caixa(0.2, 0.012, 0.012, 0x60606a, [-0.08, 0.9, 0], boia);
  const bola = k.esfera(0.05, 0xf07a3c, [0.03, 0.9, 0], boia);

  const sifao = k.tubo(SIFAO, 0.045, 0xe6e8ee);
  sifao.mat.transparent = true; sifao.mat.opacity = 0.55;
  const selo = k.tubo(SIFAO.slice(0, 4), 0.032, 0x5aaaf0, true);
  const cheio = k.tubo(SIFAO, 0.032, 0x5aaaf0, true);

  const balde = k.grupo([0.55, 0.8, 0.1]);
  k.cilindro(0.13, 0.25, 0x50a0dc, [0, 0, 0], balde, 16);

  const agua = k.pontos(120, 0.03), bolhas = k.pontos(40, 0.035), extras = k.pontos(60, 0.05);
  const curvaSifao = new THREE.CatmullRomCurve3(SIFAO.map((p) => k.V(...p)));
  const ANC = { vaso: k.V(0, 0.56, 0.2), caixa: k.V(0, 1.0, -0.22), tampa: k.V(0.06, 0.6, -0.22),
    sifao: k.V(0, 0.2, -0.12), ar: k.V(0, 0.24, -0.17), selo: k.V(0, 0.12, 0.04),
    boia: bola, torneira: valvula };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    let nivelCaixa = 0, levantada = 0, bacia = 0.35, girando = false;
    if (c === 3) nivelCaixa = 1;
    else if (c === 4) {
      const d = A("descarga");
      const f = d !== null ? k.suave(k.cl(d / 1.6)) : 0;
      nivelCaixa = 1 - f; levantada = d !== null && f < 1 ? 1 : 0; bacia = 0.35 + 0.5 * f; girando = d !== null;
    } else if (c === 5) { bacia = 0.8 - 0.5 * k.cl((A("puxa") ?? 0) / 2.5); girando = true; }
    else if (c === 9) nivelCaixa = 0.4 * k.cl((A("enche") ?? 0) / 2.5);
    else if (c === 10) nivelCaixa = 0.4 + 0.6 * k.suave(k.cl((A("fecha") ?? 0) / 2));
    else if (c >= 11) nivelCaixa = 1;
    const despeja = c === 1 && A("balde") !== null ? k.cl(A("balde") / 0.8) : 0;
    if (despeja) { bacia = 0.35 + 0.4 * despeja; girando = true; }
    balde.visible = c <= 2;
    balde.rotation.z = despeja * 1.6;
    balde.position.set(c === 2 ? 0.6 : 0.42, c === 2 ? 0.13 : 0.8, 0.1);

    const pc = P("caixa");
    caixa.visible = pc > 0;
    caixa.position.y = (1 - k.pop(k.cl(pc))) * 1.0;
    cano.m.visible = pc > 0;
    aguaCaixa.visible = nivelCaixa > 0.01;
    aguaCaixa.scale.y = Math.max(nivelCaixa, 0.01);
    aguaCaixa.position.y = 0.58 + 0.18 * nivelCaixa;
    dobra.rotation.z = levantada * 1.1;
    aguaBacia.scale.set(0.6 + bacia * 0.5, 1, 0.6 + bacia * 0.5);
    aguaBacia.position.y = 0.3 + bacia * 0.15;
    aguaBacia.rotation.y = girando ? T * 6 : 0;

    const ps = P("sifao");
    k.crescer(sifao, ps);
    k.crescer(selo, ps >= 1 ? 1 : 0);
    k.crescer(cheio, c === 5 && ps >= 1 ? 1 : 0);
    k.encaixar(boia, P("boia"));
    const byB = 0.6 + 0.32 * nivelCaixa;
    bola.position.y = byB;
    haste.position.y = (0.95 + byB) / 2;
    haste.rotation.z = Math.atan2(byB - 0.95, 0.21);
    const abrindo = c === 9 || (c === 10 && nivelCaixa < 0.97);

    k.nuvem(agua, (i, s) => {
      const fase = (T * 1.6 + s[0]) % 1;
      if (despeja > 0.3 && i < 50) return [0.35 - fase * 0.3, 0.75 - fase * 0.35, 0.08, 0.6, 0.82, 1];
      if (c === 4 && levantada && i < 50) {  // água descendo da caixa para a bacia
        const p = new THREE.Vector3().lerpVectors(k.V(0, 0.56, -0.32), k.V(0, 0.5, -0.02), fase);
        return [p.x + (s[1] - 0.5) * 0.04, p.y, p.z, 0.6, 0.82, 1];
      }
      if (girando && i >= 50 && i < 90) {  // redemoinho
        const a = T * 6 + s[1] * 6.3, r = 0.05 + s[2] * 0.12;
        return [Math.cos(a) * r, 0.36 + bacia * 0.15 + 0.01, Math.sin(a) * r, 0.8, 0.92, 1];
      }
      if (abrindo && i >= 90) return [-0.18, 0.95 - fase * 0.35, -0.32, 0.7, 0.88, 1];  // torneirinha
      return null;
    });
    k.correr(bolhas, curvaSifao, T, 0.6, 0x9ed2ff, 0xffffff, 18, c === 5 && ps >= 1);
    k.nuvem(extras, (i, s) => {
      const fase = (T * 1.2 + s[0]) % 1;
      if (c === 6 && i < 14) return [Math.sin(i) * 0.02, 0.2 + fase * 0.1, -0.15 - s[1] * 0.04, 1, 1, 1];  // bolhas de ar
      if (c === 7 && A("selo") !== null && i < 16) {  // cheiro do esgoto barrado
        return [(s[1] - 0.5) * 0.1, -0.02 + fase * 0.12, -0.32 + s[2] * 0.06, 0.6, 0.65, 0.25];
      }
      if (c === 11 && k.pisca(T, s) > 0.15) return [-0.5 + s[0], 0.2 + s[1] * 0.9, 0.2, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
