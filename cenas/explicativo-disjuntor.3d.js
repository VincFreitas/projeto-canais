// Cena 3D do disjuntor: tomada sobrecarregada, fio, fusível, e o disjuntor em corte (lâmina, mola, eletroímã e alavanca).
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · DISJUNTOR";
export const PECAS = {
  tomada: { titulo: "Tomada", conta: false },
  fio: { titulo: "Fio", conta: false },
  fusivel: { titulo: "Fusível", conta: true },
  lamina: { titulo: "Lâmina bimetálica", conta: true },
  eletroima: { titulo: "Eletroímã", conta: true },
  disjuntor: { titulo: "Disjuntor", conta: true },
};
const VISTAS = {
  tudo: [[1.0, 1.65, 2.8], [-0.2, 1.3, 0]],
  tomada: [[0.1, 0.95, 1.5], [-0.7, 0.6, 0]],
  fio: [[0.3, 2.0, 1.5], [-0.6, 1.9, 0]],
  fusivel: [[-0.15, 2.0, 1.1], [-0.68, 2.0, 0]],
  lamina: [[0.45, 1.6, 1.1], [-0.08, 1.48, 0]],
  eletroima: [[0.65, 1.5, 1.1], [0.15, 1.4, 0]],
  disjuntor: [[0.7, 1.7, 1.6], [0, 1.5, 0]],
};
const CAMINHO = [[-0.7, 2.7, 0.06], [-0.7, 1.75, 0.06], [-0.12, 1.75, 0.08], [-0.12, 1.66, 0.08], [-0.08, 1.33, 0.08],
  [0.15, 1.3, 0.08], [0.15, 1.18, 0.08], [0.0, 1.0, 0.06], [-0.7, 0.9, 0.06], [-0.7, 0.62, 0.06]];

export function criar(args) {
  const k = kit(args, { ceu: 0x2a2440 });
  const { THREE } = k;
  k.sala({ piso: k.tabua("#8a7058", "#705a46"), parede: k.azulejo("#d6cce6", "#c4b8da", [12, 8]), janela: false, fundoZ: 0 });

  // tomada com um monte de plugues
  const tomada = k.grupo([-0.7, 0.55, 0.02]);
  k.caixa(0.22, 0.3, 0.03, 0xf4f4f8, [0, 0, 0], tomada);
  const plugues = Array.from({ length: 6 }, (_, i) => {
    const p = k.caixa(0.05, 0.06, 0.06, 0x2a2a30, [-0.06 + (i % 3) * 0.06, 0.06 - Math.floor(i / 3) * 0.1, 0.04], tomada);
    const cor = [0xdc3c3c, 0x3c78dc, 0x3cb45a, 0xe6b428, 0x9a50c8, 0x50c8c8][i];
    const t = k.tubo([[0, 0, 0.03], [0.1 + i * 0.05, -0.3, 0.2], [0.2 + i * 0.12, -0.55, 0.4]], 0.01, cor, false, p);
    return { p, t };
  });

  const fio = k.tubo(CAMINHO, 0.016, 0xc8783c);
  const fioQuente = k.tubo(CAMINHO.slice(0, 3), 0.02, 0xff5028, true);
  const curva = fio.curva;

  // fusível
  const fusivel = k.grupo([-0.7, 2.05, 0.06]);
  k.cilindro(0.04, 0.18, 0, [0, 0, 0], fusivel, 14, k.vidro(0xd2ecff, 0.4));
  for (const y of [-0.1, 0.1]) k.cilindro(0.042, 0.03, 0xb4b8c4, [0, y, 0], fusivel, 14);
  const filete = k.cilindro(0.004, 0.17, 0xc8783c, [0, 0, 0], fusivel, 6);
  const fileteRompido = k.grupo([0, 0, 0], fusivel);
  k.cilindro(0.004, 0.05, 0x3c3c3c, [0, 0.06, 0], fileteRompido, 6);
  k.cilindro(0.004, 0.05, 0x3c3c3c, [0, -0.06, 0], fileteRompido, 6);

  // disjuntor em corte
  const caixa = k.grupo([0, 1.45, 0.08]);
  k.caixa(0.6, 0.72, 0.22, 0, [0, 0, 0], caixa, k.vidro(0x3c3c46, 0.22));
  const alavanca = k.grupo([0, 0.37, 0], caixa);
  k.caixa(0.05, 0.16, 0.05, 0x2a2a30, [0, 0.08, 0], alavanca);
  const contatoFixo = k.caixa(0.08, 0.02, 0.05, 0xe6c83c, [-0.12, 0.22, 0], caixa);
  const contatoMovel = k.caixa(0.08, 0.02, 0.05, 0xe6c83c, [-0.05, 0.23, 0], caixa);
  const lamina = k.grupo([-0.1, 0.18, 0], caixa);
  const segmentos = [];  // cada pedaço preso ao de cima: a lâmina curva inteira
  let pai = lamina;
  for (let i = 0; i < 10; i++) {
    const g = k.grupo([0, i === 0 ? 0 : -0.032, 0], pai);
    k.caixa(0.018, 0.034, 0.05, 0xd2783c, [-0.01, -0.016, 0], g);
    k.caixa(0.018, 0.034, 0.05, 0xb4b8c8, [0.01, -0.016, 0], g);
    segmentos.push(g);
    pai = g;
  }
  const helice = [];
  for (let i = 0; i <= 40; i++) { const a = i / 40 * Math.PI * 10; helice.push([Math.cos(a) * 0.025, i / 40 * 0.15, Math.sin(a) * 0.025]); }
  const mola = k.tubo(helice.map(([x, y, z]) => [x + 0.08, y + 0.08, z]), 0.005, 0x8c96aa, false, caixa);
  const eletroima = k.grupo([0.15, -0.05, 0], caixa);
  k.cilindro(0.025, 0.24, 0x5a5a64, [0, 0, 0], eletroima, 10);
  const bobina = [];
  for (let i = 0; i <= 80; i++) { const a = i / 80 * Math.PI * 22; bobina.push([Math.cos(a) * 0.04, -0.1 + i / 80 * 0.2, Math.sin(a) * 0.04]); }
  k.tubo(bobina, 0.006, 0xc8783c, false, eletroima);
  const campo = k.esfera(0.12, 0, [0, 0, 0], eletroima, k.brilho(0x96c8ff, { transparent: true, opacity: 0.18 }));

  const aviso = k.grupo([0.55, 2.2, 0.05]);
  const tri = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.02, 3), k.brilho(0xf0c828));
  tri.rotation.x = Math.PI / 2;
  aviso.add(tri);
  const corrente = k.pontos(40, 0.03), fogo = k.pontos(80, 0.04), extras = k.pontos(60, 0.035);
  const ANC = { tomada: k.V(-0.7, 0.72, 0.05), fio: k.V(-0.7, 2.3, 0.06), fusivel: fusivel, lamina: k.V(-0.1, 1.5, 0.12),
    eletroima: eletroima, disjuntor: alavanca, mola: k.V(0.08, 1.6, 0.12) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const aparelhos = [1, 2, 11].includes(c) ? 6 : 2;
    plugues.forEach((p, i) => (p.p.visible = i < aparelhos));
    let aberto = false, entorta = 0, puxa = 0;
    if (c === 6 && A("entorta") !== null) { entorta = k.suave(k.cl(A("entorta") / 1.5)); aberto = entorta > 0.8; }
    if (c === 8 && A("puxa") !== null) { puxa = k.suave(k.cl(A("puxa") / 0.25)); aberto = puxa > 0.8; }
    if (c === 10) aberto = A("rearma") === null || A("rearma") < 0.6;
    if (c === 11) aberto = Math.floor(T * 1.2) % 2 === 0;
    const queimado = (c === 3 && A("derrete") !== null && A("derrete") > 0.8) || c === 4;
    const disj = P("lamina") > 0;
    caixa.visible = disj;
    caixa.scale.setScalar(Math.max(k.pop(k.cl(P("lamina"))), 0.001));
    alavanca.rotation.z = aberto ? 0.7 : -0.7;
    contatoMovel.position.set(-0.05 + (aberto ? 0.04 : 0), 0.23 + (aberto ? 0.05 : 0), 0);
    segmentos.forEach((s, i) => (s.rotation.z = i ? entorta * 0.09 : 0));
    mola.m.scale.y = aberto ? 0.6 : 1;
    eletroima.visible = P("eletroima") > 0;
    eletroima.scale.setScalar(Math.max(k.pop(k.cl(P("eletroima"))), 0.001));
    campo.visible = puxa > 0 || (c === 7 && A("curto") !== null);
    campo.scale.setScalar(1 + 0.15 * Math.sin(T * 20));
    fusivel.visible = P("fusivel") > 0 && (c === 3 || c === 4);
    const voa = c === 4 ? k.suave(k.cl((A("lixo") ?? 0) / 1)) : 0;
    fusivel.position.set(-0.7 + voa * 1.2, 2.05 + voa * 0.5, 0.06 + voa * 0.3);
    fusivel.rotation.z = voa * 3;
    filete.visible = !queimado;
    fileteRompido.visible = queimado;
    const fogoFio = c === 2 && A("fogo") !== null ? k.cl(A("fogo") / 2) : 0;
    k.crescer(fioQuente, fogoFio > 0 ? 1 : 0);
    fioQuente.mat.color.setRGB(1, 0.3 + 0.2 * Math.sin(T * 8), 0.15);
    aviso.visible = c === 11;
    aviso.scale.setScalar(0.8 + 0.3 * Math.abs(Math.sin(T * 6)));

    const corta = aberto || queimado;
    const forte = [1, 2, 7, 11].includes(c);
    k.correr(corrente, curva, T, forte ? 0.5 : 0.25, 0xffe65a, 0xfff0a0, forte ? 36 : 18, !corta);
    k.nuvem(fogo, (i, s) => {
      if (fogoFio <= 0.5) return null;
      const fase = (T * 2 + s[0]) % 1;
      return [-0.7 + (s[1] - 0.5) * 0.08, 2.1 + s[2] * 0.4 + fase * 0.15, 0.08, 1, 0.8 - 0.5 * fase, 0.15];
    });
    k.nuvem(extras, (i, s) => {
      if (c === 7 && A("curto") !== null && i < 40) {  // faísca do curto na tomada
        const r = ((T * 3 + s[0]) % 1) * 0.2;
        return [-0.7 + Math.cos(s[1] * 6.3) * r, 0.55 + Math.sin(s[1] * 6.3) * r, 0.1, 1, 1, 0.7];
      }
      if (c === 12 && k.pisca(T, s) > 0.15) return [-0.6 + s[0] * 1.2, 0.9 + s[1] * 1.3, 0.2, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
