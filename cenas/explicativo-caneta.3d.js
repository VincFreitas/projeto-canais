// Cena 3D da caneta esferográfica: pena e tinteiro, tubo de tinta, esfera na ponta, escrita, jornal e patente.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · CANETA";
export const PECAS = {
  tubo: { titulo: "Tubo de tinta", conta: true },
  ponta: { titulo: "Ponta", conta: false },
  esfera: { titulo: "Esfera", conta: true },
  jornal: { titulo: "Jornal", conta: false },
  tinta: { titulo: "Tinta grossa", conta: true },
  corpo: { titulo: "Caneta", conta: true },
};
const VISTAS = {
  tudo: [[0.85, 1.3, 1.1], [0.12, 0.88, -0.05]],
  tubo: [[0.5, 1.15, 0.8], [0, 0.97, 0]],
  tinta: [[0.5, 1.15, 0.8], [0, 0.97, 0]],
  ponta: [[0.2, 0.87, 0.32], [0, 0.785, 0]],
  esfera: [[0.2, 0.87, 0.32], [0, 0.785, 0]],
  jornal: [[0.0, 1.15, 0.95], [-0.32, 0.92, 0]],
  corpo: [[0.55, 1.2, 0.95], [0, 0.98, 0]],
};
const MESA = 0.75;

export function criar(args) {
  const k = kit(args, { ceu: 0x283050 });
  const { THREE } = k;
  k.sala({ piso: k.tabua(), parede: k.azulejo("#5a6ea0", "#6a80b4", [14, 8]) });
  k.caixa(1.8, 0.05, 1.0, 0xa06e46, [0, MESA - 0.025, 0]);
  for (const x of [-0.8, 0.8]) for (const z of [-0.4, 0.4]) k.caixa(0.06, MESA - 0.05, 0.06, 0x7a5032, [x, (MESA - 0.05) / 2, z]);
  const folha = k.caixa(0.6, 0.004, 0.42, 0xfaf8f0, [0, MESA + 0.002, 0.05]);
  for (let i = 0; i < 6; i++) k.caixa(0.58, 0.001, 0.004, 0xbed2f0, [0, MESA + 0.0045, -0.1 + i * 0.06]);

  // pena e tinteiro (cenas 1 e 2)
  const tinteiro = k.cilindro(0.05, 0.07, 0x282830, [0.42, MESA + 0.035, -0.2], k.scene, 16);
  const pena = k.grupo([0.3, MESA + 0.05, -0.1]);
  const pluma = k.caixa(0.03, 0.35, 0.005, 0xf4f4fa, [0, 0.17, 0], pena);
  const mancha = k.cilindro(1, 0.002, 0x2850c8, [-0.1, MESA + 0.005, 0.15], k.scene, 20);

  // a caneta: tubo transparente, tinta, cone, esfera e corpo
  const caneta = k.grupo([0, MESA + 0.03, 0]);
  const tubo = k.cilindro(0.012, 0.3, 0, [0, 0.19, 0], caneta, 14, k.vidro(0xf0f4ff, 0.45));
  const tinta = k.cilindro(0.009, 0.2, 0x7aa0f0, [0, 0.14, 0], caneta, 12);
  const cone = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.035, 14), k.toon(0xc8ccd6));
  cone.rotation.x = Math.PI;
  cone.position.y = 0.025;
  caneta.add(cone);
  const esfera = k.esfera(0.005, 0xe6e6f0, [0, 0.006, 0], caneta);
  const corpo = k.grupo([0, 0, 0], caneta);
  k.cilindro(0.02, 0.28, 0, [0, 0.2, 0], corpo, 6, k.vidro(0xdce6ff, 0.3));
  k.cilindro(0.022, 0.06, 0x2850c8, [0, 0.37, 0], corpo, 12);
  k.caixa(0.008, 0.07, 0.006, 0xb4b4be, [0.024, 0.34, 0], corpo);
  const ancoraPonta = k.grupo([0, 0.01, 0], caneta);

  // linha escrita no papel (segmentos que aparecem atrás da ponta)
  const segmentos = Array.from({ length: 70 }, (_, i) => {
    const x = -0.25 + i * 0.0072;
    return k.caixa(0.008, 0.001, 0.005, 0x2850c8, [x, MESA + 0.0055, 0.12 + Math.sin(i * 0.5) * 0.01]);
  });

  // jornal e carimbo da patente
  const jornal = k.grupo([-0.35, MESA + 0.12, -0.05]);
  const papel = k.textura((g, w, h) => {
    g.fillStyle = "#ece6d6"; g.fillRect(0, 0, w, h);
    g.fillStyle = "#1e1e1e"; g.fillRect(8, 8, w - 16, 18);
    g.fillStyle = "#6e6e6e";
    for (let y = 36; y < h - 6; y += 8) { g.fillRect(8, y, w / 2 - 14, 3); g.fillRect(w / 2 + 4, y, w / 2 - 14, 3); }
  }, 128, 160, [1, 1]);
  const pagina = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.32, 0.004), k.toon(0xffffff, { map: papel }));
  jornal.add(pagina);
  const carimbo = k.grupo([0.13, MESA + 0.2, 0.05]);
  k.caixa(0.2, 0.09, 0.01, 0xc83232, [0, 0, 0], carimbo);
  k.caixa(0.16, 0.05, 0.012, 0xf4dede, [0, 0, 0.002], carimbo);

  const gotas = k.pontos(40, 0.012), extras = k.pontos(60, 0.02);
  const ANC = { tubo: k.V(0, MESA + 0.3, 0.02), ponta: ancoraPonta, esfera: ancoraPonta, jornal: k.V(-0.35, MESA + 0.3, 0),
    tinta: k.V(0, MESA + 0.25, 0.02), corpo: k.V(0, MESA + 0.42, 0.03), patente: k.V(0.13, MESA + 0.25, 0.06) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    tinteiro.visible = pena.visible = c <= 2;
    const molha = A("pena") !== null ? 0.5 + 0.5 * Math.sin(T * 2.4) : 0;
    pena.position.set(0.3 + 0.12 * molha, MESA + 0.05 + 0.15 * (1 - molha), -0.1 - 0.1 * molha);
    pena.rotation.z = -0.5;
    const m = c === 2 && A("mancha") !== null ? k.cl(A("mancha") / 2) : 0;
    mancha.visible = m > 0;
    mancha.scale.set(0.02 + 0.08 * m, 1, 0.02 + 0.06 * m);

    const pt = P("tubo");
    caneta.visible = pt > 0;
    caneta.position.y = MESA + 0.03 + (1 - k.pop(k.cl(pt))) * 0.5;
    esfera.visible = P("esfera") > 0;
    esfera.scale.setScalar(Math.max(k.pop(k.cl(P("esfera"))), 0.001));
    const grossa = P("tinta");
    tinta.material.color.setRGB(0.48 - 0.32 * grossa, 0.63 - 0.32 * grossa, 0.94 - 0.16 * grossa);
    corpo.visible = P("corpo") > 0;
    corpo.scale.setScalar(Math.max(k.pop(k.cl(P("corpo"))), 0.001));

    // escrevendo: a caneta anda e a linha aparece atrás dela
    let px = 0, escrito = c >= 11 ? 70 : 0;
    if (c === 5 && A("escreve") !== null) {
      const f = k.suave(k.cl(A("escreve") / 3));
      px = -0.25 + 0.5 * f;
      escrito = Math.floor(70 * f);
    }
    caneta.position.x = px;
    caneta.position.z = c === 5 || c >= 11 ? 0.12 : 0;
    caneta.rotation.z = c === 5 ? -0.25 : 0;
    const vira = c === 10 && A("virar") !== null ? k.suave(k.cl(A("virar") / 0.8)) : 0;
    caneta.rotation.x = vira * Math.PI;
    if (vira > 0) caneta.position.y = MESA + 0.03 + 0.42 * vira;
    tinta.position.y = 0.14 + 0.1 * vira;  // de cabeça para baixo, a tinta escorre para longe da ponta
    segmentos.forEach((s, i) => (s.visible = i < escrito || (c === 10 && i < 70 && Math.sin(i * 0.7 + T) > 0.3 && i < 70 * (1 - 0.6 * vira))));
    esfera.rotation.x = c === 5 ? T * 12 : 0;

    jornal.visible = c === 7 || c === 8;
    const j = c === 7 ? A("jornal") : 99;
    jornal.position.y = MESA + 0.18 + (1 - k.pop(k.cl((j ?? 0) / 0.5))) * 0.4;
    jornal.rotation.y = 0.3;
    carimbo.visible = c === 8 && grossa >= 1;

    k.nuvem(gotas, (i, s) => {
      const fase = (T * 2 + s[0]) % 1;
      if (c === 3 && A("vaza") !== null && P("esfera") <= 0) {  // sem bolinha: vaza tudo
        return [(s[1] - 0.5) * 0.01, MESA + 0.02 - fase * 0.02, (s[2] - 0.5) * 0.01, 0.16, 0.31, 0.78];
      }
      if (c === 6 && A("rala") !== null && A("rala") < 2.4) return [(s[1] - 0.5) * 0.03, MESA + 0.03 - fase * 0.03, 0.01, 0.48, 0.63, 0.94];
      return null;
    });
    if (c === 3 && A("vaza") !== null) { mancha.visible = true; mancha.position.set(0, MESA + 0.005, 0); mancha.scale.set(0.02 + 0.05 * k.cl(A("vaza") / 2), 1, 0.02 + 0.05 * k.cl(A("vaza") / 2)); }
    else mancha.position.set(-0.1, MESA + 0.005, 0.15);
    k.nuvem(extras, (i, s) => {
      if (c === 4 && i < 10 && k.pisca(T, s) > 0.2) return [(s[0] - 0.5) * 0.05, MESA + 0.01 + s[1] * 0.04, 0.02, 1, 1, 1];
      if (c === 7 && k.pisca(T, s) > 0.2) return [-0.48 + s[0] * 0.26, MESA + 0.05 + s[1] * 0.32, 0, 1, 1, 0.85];
      if (c === 11 && k.pisca(T, s) > 0.15) return [-0.4 + s[0] * 0.8, MESA + 0.05 + s[1] * 0.5, 0.15, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
