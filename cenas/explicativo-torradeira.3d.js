// Cena 3D da torradeira: alavanca, mola, trava, eletroímã, temporizador e seletor de tempo num corte lateral.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · TORRADEIRA";
export const PECAS = {
  resistencias: { titulo: "Resistências", conta: false },
  mola: { titulo: "Mola", conta: false },
  trava: { titulo: "Trava", conta: true },
  eletroima: { titulo: "Eletroímã", conta: true },
  temporizador: { titulo: "Temporizador", conta: true },
  seletor: { titulo: "Seletor de tempo", conta: true },
};
const VISTAS = {  // [câmera, alvo] no mundo: o corpo começa em y 0,94 (tampo da bancada)
  tudo: [[0.2, 1.5, 1.9], [0.15, 1.18, 0]],
  resistencias: [[-0.1, 1.4, 0.95], [-0.1, 1.3, 0]],
  mola: [[0.5, 1.1, 0.6], [0.42, 1.02, 0]],
  trava: [[0.4, 1.3, 0.65], [0.33, 1.2, 0]],
  eletroima: [[0.52, 1.25, 0.65], [0.44, 1.15, 0]],
  temporizador: [[0.62, 1.45, 0.65], [0.58, 1.38, 0]],
  seletor: [[0.15, 1.45, 0.75], [0.1, 1.38, 0.15]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x3a2c22 });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#d8c8a0", "#c4b084", [10, 10]), parede: k.azulejo("#f6e4b0", "#f0d890", [12, 6]), janela: false });
  k.caixa(3.0, 0.9, 0.9, 0x8a5a38, [0, 0.45, 0]);           // bancada
  k.caixa(3.0, 0.04, 0.92, 0xe8e2d6, [0, 0.92, 0]);

  // corpo da torradeira (corte lateral, aberto para a câmera)
  const corpo = k.grupo([0, 0.94, 0]);
  k.caixa(0.62, 0.5, 0.42, 0xd2d2dc, [0, 0.25, -0.05], corpo, k.vidro(0x3c3c46, 0.22));
  k.caixa(0.66, 0.05, 0.46, 0xb8b8c2, [0, 0.015, -0.03], corpo);

  // fenda, pão e resistências
  const resistencias = k.grupo([-0.1, 0.42, -0.02], corpo);
  const fios = [];
  for (const x of [-0.14, 0.06]) {
    const helice = [];
    for (let i = 0; i <= 24; i++) helice.push([x + Math.sin(i * 0.9) * 0.012, 0.18 - i / 24 * 0.36, 0.01]);
    fios.push(k.tubo(helice, 0.006, 0xc89050, false, resistencias));
  }
  const pao = k.grupo([-0.1, 0.5, -0.02], corpo);
  k.caixa(0.16, 0.26, 0.16, 0xe8d4a0, [0, 0, 0], pao);
  const pao2 = k.caixa(0.16, 0.26, 0.16, 0xe8d4a0, [0.2, 0, 0], corpo);

  // alavanca, mola e trava do lado direito
  const alavanca = k.grupo([0.42, 0.55, 0], corpo);
  k.caixa(0.05, 0.3, 0.2, 0x3c3c44, [0, 0, 0], alavanca);
  const haste = k.caixa(0.03, 0.4, 0.03, 0x8c8c96, [0, -0.3, 0], alavanca);
  const heliceMola = [];
  for (let i = 0; i <= 30; i++) { const a = i / 30 * Math.PI * 8; heliceMola.push([0.42 + Math.cos(a) * 0.03, 0.08 + i / 30 * 0.22, Math.sin(a) * 0.03]); }
  const mola = k.tubo(heliceMola.map(([x, y, z]) => [x - 0.42, y - 0.08, z]), 0.006, 0x8c96aa, false, alavanca);
  mola.m.position.set(0, -0.62, 0);

  const trava = k.grupo([0.3, 0.28, 0], corpo);
  k.caixa(0.1, 0.03, 0.05, 0x5a5a64, [0, 0, 0], trava);
  const gancho = k.caixa(0.03, 0.06, 0.05, 0x5a5a64, [0.05, 0.03, 0], trava);
  const entalhe = k.caixa(0.04, 0.02, 0.05, 0x2a2a30, [0, 0.02, 0.03], alavanca);

  // eletroímã
  const eletroima = k.grupo([0.46, 0.2, 0], corpo);
  k.cilindro(0.02, 0.14, 0x5a5a64, [0, 0, 0], eletroima, 10).rotation.z = Math.PI / 2;
  const bobina = [];
  for (let i = 0; i <= 50; i++) { const a = i / 50 * Math.PI * 16; bobina.push([Math.cos(a) * 0.03, Math.sin(a) * 0.03, -0.06 + i / 50 * 0.12]); }
  k.tubo(bobina, 0.005, 0xc8783c, false, eletroima);
  const tab = k.caixa(0.03, 0.03, 0.04, 0x8c8c96, [-0.08, 0, 0], eletroima);
  const campo = k.esfera(0.08, 0, [0, 0, 0], eletroima, k.brilho(0x96c8ff, { transparent: true, opacity: 0.2 }));

  // temporizador (placa + capacitor)
  const temporizador = k.grupo([0.6, 0.45, -0.05], corpo);
  k.caixa(0.14, 0.1, 0.02, 0x2a5a3c, [0, 0, 0], temporizador);
  const capacitor = k.cilindro(0.025, 0.08, 0x3c3c44, [0.03, 0.08, 0.02], temporizador, 14);
  const nivel = k.cilindro(0.021, 0.001, 0x1ec878, [0.03, 0.045, 0.02], temporizador, 14, k.brilho(0x1ec878));

  // seletor de tempo
  const seletor = k.grupo([0.1, 0.42, 0.18], corpo);
  k.cilindro(0.045, 0.02, 0xe8e2d6, [0, 0, 0], seletor, 18).rotation.x = Math.PI / 2;
  const ponteiro = k.caixa(0.008, 0.03, 0.005, 0x3c3c44, [0, 0.02, 0.011], seletor);
  ponteiro.geometry.translate(0, 0.015, 0);

  const fumaca = k.pontos(60, 0.035), faiscas = k.pontos(50, 0.03), extras = k.pontos(60, 0.03);
  const ANC = { resistencias: resistencias, mola: k.V(0.42, 0.98, 0.03), trava: trava, eletroima: eletroima,
    temporizador: temporizador, seletor: seletor };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);

    const abaixa = c === 1 && A("abaixa") !== null ? k.suave(k.cl(A("abaixa") / 1.2)) : (c >= 2 && c <= 8 ? 1 : 0);
    const solta = c === 3 && A("solta") !== null ? k.suave(k.cl(A("solta") / 1.0)) : 0;
    const dispara = c === 9 && A("dispara") !== null ? k.suave(k.cl(A("dispara") / 1.0)) : (c >= 10 ? 1 : 0);
    const preso = abaixa > 0 && !(c === 3 && solta > 0.5) && dispara < 0.5;

    const alturaPao = preso ? 0.0 : (dispara > 0 ? dispara * 0.22 : (abaixa > 0 ? -abaixa * 0.0 : 0.22));
    pao.position.y = 0.5 + (preso ? 0 : (c === 3 ? solta * 0.22 : (dispara > 0 ? dispara * 0.22 : (c <= 1 ? -abaixa * 0 : 0.22))));
    alavanca.position.y = 0.55 + (preso ? -0.06 : (c === 3 ? -0.06 + solta * 0.06 : (dispara > 0 ? -0.06 + dispara * 0.06 : 0)));
    haste.scale.y = 1;

    pao2.visible = c <= 1 ? false : true;
    pao2.position.y = c >= 9 ? 0.5 + dispara * 0.22 : 0.5;

    const quente = c >= 2 && c <= 11 ? 1 : 0;
    fios.forEach((f) => f.m.material.color.setRGB(quente ? 1 : 0.78, quente ? 0.35 + 0.1 * Math.sin(T * 6) : 0.56, quente ? 0.1 : 0.31));

    const travaFechada = c >= 4 && c <= 8;
    trava.visible = P("trava") > 0;
    trava.scale.setScalar(Math.max(k.pop(k.cl(P("trava"))), 0.001));
    gancho.position.x = travaFechada || c === 3 ? 0.05 : -0.02;

    eletroima.visible = P("eletroima") > 0;
    eletroima.scale.setScalar(Math.max(k.pop(k.cl(P("eletroima"))), 0.001));
    campo.visible = c >= 6 && c <= 8;
    campo.scale.setScalar(1 + 0.1 * Math.sin(T * 10));
    tab.position.x = (c >= 6 && c <= 8) ? -0.03 : -0.08;

    temporizador.visible = P("temporizador") > 0;
    temporizador.scale.setScalar(Math.max(k.pop(k.cl(P("temporizador"))), 0.001));
    const enchendo = c === 8 ? k.cl((A("circuito") ?? 0) / 2) : (c >= 9 ? 1 : (c >= 8 ? 0.4 : 0));
    nivel.scale.y = Math.max(enchendo, 0.02) * 40;
    nivel.position.y = 0.045 + Math.max(enchendo, 0.02) * 0.018;

    seletor.visible = P("seletor") > 0;
    seletor.scale.setScalar(Math.max(k.pop(k.cl(P("seletor"))), 0.001));
    ponteiro.rotation.z = c === 10 ? Math.sin(T * 2) * 0.6 : 0;

    const queimado = c === 5 || c === 11;
    pao.children[0] && pao.children[0].material.color.setRGB(queimado ? 0.3 : (c >= 9 ? 0.72 : 0.91), queimado ? 0.18 : (c >= 9 ? 0.5 : 0.83), queimado ? 0.12 : 0.63);
    if (pao2.material) pao2.material.color.setRGB(c === 11 ? 0.3 : (c >= 9 ? 0.72 : 0.91), c === 11 ? 0.18 : (c >= 9 ? 0.5 : 0.83), c === 11 ? 0.12 : 0.63);

    const sensor = c === 12;

    k.nuvem(fumaca, (i, s) => {
      if (!queimado) return null;
      const fase = (T * 1.6 + s[0]) % 1;
      return [-0.1 + (s[1] - 0.5) * 0.1, 0.65 + fase * 0.4, -0.02 + s[2] * 0.1, 0.5, 0.5, 0.5];
    });
    k.nuvem(faiscas, (i, s) => {
      if (c === 7 && k.pisca(T, s) > 0.2) return [0.46 + (s[1] - 0.5) * 0.14, 0.2 + (s[2] - 0.5) * 0.14, 0.02, 0.6, 0.78, 1];
      return null;
    });
    k.nuvem(extras, (i, s) => {
      if (sensor && i < 20) {
        const fase = (T * 2 + s[0]) % 1;
        return [-0.1 + (s[1] - 0.5) * 0.02, 0.5 + (s[2] - 0.5) * 0.02, -0.02 + fase * 0.4, 1, 0.9, 0.4];
      }
      if (c === 13 && k.pisca(T, s) > 0.15) return [-0.3 + s[0] * 0.8, 0.6 + s[1] * 0.5, 0.2, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
