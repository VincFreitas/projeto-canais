// Cena 3D do chuveiro elétrico: carcaça transparente para ver o diafragma, o contato, a resistência e a chave.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · CHUVEIRO";
export const PECAS = {
  panela: { titulo: "Panela", conta: false },
  chuveiro: { titulo: "Chuveiro", conta: true },
  resistencia: { titulo: "Resistência", conta: true },
  diafragma: { titulo: "Diafragma", conta: true },
  chave: { titulo: "Chave verão/inverno", conta: true },
};
const VISTAS = {
  tudo: [[1.8, 2.0, 2.4], [-0.15, 1.25, -2.0]],
  panela: [[0.9, 1.7, 1.2], [-0.8, 0.8, -1.5]],
  chuveiro: [[1.3, 2.2, -0.2], [0, 1.9, -2.6]],
  resistencia: [[0.95, 2.0, -0.9], [0, 1.85, -2.6]],
  diafragma: [[0.95, 2.35, -0.9], [0, 2.15, -2.6]],
  chave: [[1.5, 2.15, -1.1], [0.3, 2.0, -2.6]],
};

export function criar(args) {
  const k = kit(args);
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#e6ecf0", "#c4ccd4", [12, 12]), parede: k.azulejo("#6cc4c0", "#8ed8d4"), janela: false });
  k.cilindro(0.08, 0.02, 0x9aa0aa, [0.6, 0.011, -1.6]);  // ralo

  // panela no fogão e balde (cenas 1 e 2)
  const cozinha = k.grupo([-0.8, 0, -1.5]);
  k.caixa(0.7, 0.8, 0.5, 0xe6e6ea, [0, 0.4, 0], cozinha);  // fogão branco com tampo preto e boca
  k.caixa(0.72, 0.03, 0.52, 0x26262c, [0, 0.815, 0], cozinha);
  k.caixa(0.5, 0.25, 0.02, 0x3c3c46, [0, 0.45, 0.26], cozinha);
  k.cilindro(0.12, 0.02, 0x1c1c22, [0, 0.83, 0], cozinha);
  const panela = k.cilindro(0.18, 0.2, 0xdcdfe6, [0, 0.92, 0], cozinha);
  const chamas = [0, 1, 2, 3, 4].map((i) => k.esfera(0.035, 0, [-0.12 + i * 0.06, 0.82, 0.05], cozinha, k.brilho(0x5096ff)));
  const balde = k.cilindro(0.17, 0.32, 0x50a0dc, [1.6, 0.16, 0], cozinha);

  // chuveiro
  const ch = k.grupo([0, 0, -2.6]);
  const cano = k.cilindro(0.04, 0.6, 0x9aa0aa, [0, 2.7, 0], ch);
  const carcaca = k.caixa(0.62, 0.8, 0.42, 0, [0, 2.0, 0], ch, k.vidro(0xe8f0ff, 0.28));
  const crivo = k.cilindro(0.3, 0.06, 0xdcdfe6, [0, 1.56, 0], ch, 24);
  const diafragma = k.cilindro(0.2, 0.025, 0x3c3c46, [0, 2.15, 0], ch, 24);
  const contato = k.caixa(0.12, 0.03, 0.08, 0xe6b43c, [0, 2.3, 0], ch);
  const helice = [];
  for (let i = 0; i <= 60; i++) {
    const a = i / 60 * Math.PI * 14;
    helice.push([-0.22 + i / 60 * 0.44, 1.82 + Math.cos(a) * 0.05, Math.sin(a) * 0.05]);
  }
  const resist = k.tubo(helice, 0.012, 0x6e5a50, false, ch);
  const resistQuente = k.tubo(helice, 0.014, 0xffb43c, true, ch);
  const resistPartida = k.tubo(helice.slice(0, 26), 0.012, 0x3c2828, false, ch);
  const resistPartida2 = k.tubo(helice.slice(34), 0.012, 0x3c2828, false, ch);
  const chave = k.grupo([0.36, 2.0, 0], ch);
  k.cilindro(0.09, 0.05, 0xf4f4f8, [0, 0, 0], chave, 20).rotation.z = Math.PI / 2;
  const ponteiro = k.caixa(0.02, 0.1, 0.02, 0x282830, [0.03, 0, 0], chave);
  const sol = k.esfera(0.035, 0, [0.03, 0.13, -0.08], chave, k.brilho(0xffc828));
  const floco = k.esfera(0.035, 0, [0.03, 0.13, 0.08], chave, k.brilho(0x78c8ff));

  const agua = k.pontos(160, 0.03), vapor = k.pontos(80, 0.06), extra = k.pontos(80, 0.04);
  const fluxoCano = k.pontos(20, 0.03), corrente = k.pontos(30, 0.035);
  const caminhoCano = new THREE.LineCurve3(k.V(0, 3.0, -2.6), k.V(0, 2.4, -2.6));
  const caminhoCorrente = new THREE.CatmullRomCurve3([k.V(0.36, 2.0, -2.6), k.V(0.1, 2.3, -2.6), k.V(0.05, 2.0, -2.6),
    k.V(-0.22, 1.82, -2.6)]);

  const ANC = { panela: k.V(-0.8, 1.05, -1.5), agua_quente: k.V(-0.8, 1.15, -1.5), chuveiro: k.V(0, 2.42, -2.6),
    resistencia: k.V(0, 1.82, -2.4), diafragma: k.V(0, 2.15, -2.4), contato: k.V(0, 2.3, -2.4),
    chave: k.V(0.4, 2.0, -2.5), verao: sol, inverno: floco };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, t, cena: c } = e;
    k.camera(e, VISTAS);
    cozinha.visible = c <= 2;
    const esfria = A("esfria");
    chamas.forEach((f, i) => { f.visible = esfria === null; f.scale.setScalar(0.8 + 0.4 * Math.sin(T * 20 + i)); });
    const pc = P("chuveiro");
    k.encaixar(ch, pc);
    ch.position.y = (1 - k.pop(k.cl(pc))) * 1.5;
    const rompe = A("romper"), ligar = A("ligar");
    const pouca = c === 8;
    let empurrado = 0;
    if (c === 7 && ligar !== null) empurrado = k.suave(k.cl(ligar / 0.6));
    else if (c >= 9) empurrado = 1;
    else if (pouca) empurrado = 0.3;
    const aguaLigada = [3, 4, 9, 10, 11].includes(c) || (c === 7 && ligar !== null) || pouca;
    let estado = 0;
    if (c === 3 || c === 4) estado = 2;
    else if (c === 5) estado = rompe !== null && rompe > 1.5 ? 3 : 2;
    else if (empurrado >= 0.95) estado = 2;
    k.crescer(resist, pc >= 1 && estado === 0 ? 1 : 0);
    k.crescer(resistQuente, estado === 2 ? 1 : 0);
    resistQuente.mat.color.setHSL(0.09 - (c === 5 ? 0.06 * k.cl(rompe / 1.5) : 0), 1, 0.55 + 0.08 * Math.sin(T * 8));
    k.crescer(resistPartida, estado === 3 ? 1 : 0);
    k.crescer(resistPartida2, estado === 3 ? 1 : 0);
    diafragma.visible = P("diafragma") > 0;
    diafragma.scale.set(1, 1 + 3 * empurrado, 1);
    diafragma.position.y = 2.15 + 0.07 * empurrado;
    contato.visible = P("diafragma") > 0;
    k.encaixar(chave, P("chave"));
    const inverno = A("inverno") !== null;
    ponteiro.rotation.x = inverno ? 0.8 : -0.8;

    k.correr(fluxoCano, caminhoCano, T, 1.2, 0xbee6ff, 0xbee6ff, 12, aguaLigada && pc >= 1);
    k.correr(corrente, caminhoCorrente, T, 1.4, 0xffffa0, 0xffffff, 16, (c === 7 && empurrado > 0.95) || c === 10);
    const quente = estado === 2 && !pouca;
    k.nuvem(agua, (i, s) => {
      if (!aguaLigada || pc < 1 || (pouca && i > 12)) return null;
      const fase = (T * 1.6 + s[0]) % 1;
      const a = s[1] * Math.PI * 2, r = s[2] * 0.25;
      return [Math.cos(a) * r, 1.52 - fase * 1.5, -2.6 + Math.sin(a) * r, ...(quente ? [1, 0.82, 0.55] : [0.55, 0.78, 1])];
    });
    k.nuvem(vapor, (i, s) => {
      const fase = (T * 0.4 + s[0]) % 1;
      if (c <= 2 && esfria === null && i < 30) return [-0.8 + (s[1] - 0.5) * 0.3, 1.05 + fase * 0.8, -1.5, 1, 1, 1];
      if (quente && aguaLigada && i >= 30) return [(s[1] - 0.5) * 1.2, 0.3 + fase * 1.6, -2.4 + s[2] * 0.6, 1, 1, 1];
      return null;
    });
    k.nuvem(extra, (i, s) => {
      if (c === 5 && rompe !== null && rompe > 1.3 && rompe < 2.6 && i < 40) {  // faíscas quando rompe
        const r = (rompe - 1.3) * 0.6;
        return [Math.cos(s[0] * 6.3) * r, 1.82 + Math.sin(s[1] * 6.3) * r, -2.6 + s[2] * 0.2, 1, 0.8 - r, 0.3];
      }
      if (c === 2 && esfria !== null && i < 20 && k.pisca(T, s) > 0.2) return [-0.9 + s[0] * 0.3, 0.9 + s[1] * 0.3, -1.4, 0.7, 0.9, 1];
      if (c === 11 && k.pisca(T, s) > 0.15) return [-0.8 + s[0] * 1.6, 1.0 + s[1] * 1.6, -2.4 + s[2] * 0.5, 1, 1, 0.85];
      if (empurrado > 0.95 && c === 7 && i < 10 && k.pisca(T * 2, s) > 0.2) return [(s[0] - 0.5) * 0.1, 2.28, -2.55, 1, 1, 0.6];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
