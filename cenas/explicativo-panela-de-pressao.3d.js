// Cena 3D da panela de pressão: corpo translúcido com feijão, tampa presa, borracha, peso, válvula de segurança e trava.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · PANELA DE PRESSÃO";
export const PECAS = {
  panela: { titulo: "Panela", conta: false },
  tampa: { titulo: "Tampa presa", conta: true },
  borracha: { titulo: "Borracha de vedação", conta: true },
  valvula: { titulo: "Peso (válvula)", conta: true },
  seguranca: { titulo: "Válvula de segurança", conta: true },
  trava: { titulo: "Trava", conta: true },
};
const VISTAS = {
  tudo: [[0.95, 1.55, 1.45], [0, 1.02, 0]],
  panela: [[0.65, 1.35, 1.05], [0, 1.0, 0]],
  tampa: [[0.65, 1.5, 0.95], [0, 1.2, 0]],
  borracha: [[0.55, 1.3, 0.65], [-0.18, 1.18, 0]],
  valvula: [[0.38, 1.55, 0.65], [0, 1.32, 0]],
  seguranca: [[0.45, 1.5, 0.6], [0.12, 1.26, 0.04]],
  trava: [[0.7, 1.4, 0.65], [0.36, 1.22, 0]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x3a2e22 });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#7a5a44", "#6a4c38", [10, 10]), parede: k.azulejo("#f0d8b0", "#f8e6c8", [12, 6]), janela: false });
  k.caixa(1.6, 0.85, 0.8, 0x3a3a44, [0, 0.425, 0]);            // fogão
  k.caixa(1.62, 0.03, 0.82, 0x24242a, [0, 0.865, 0]);
  const chamas = Array.from({ length: 10 }, (_, i) =>
    k.esfera(0.025, 0, [Math.cos(i * 0.63) * 0.13, 0.9, Math.sin(i * 0.63) * 0.13], k.scene, k.brilho(0x5096ff)));

  // corpo em vidro (em corte), com água, feijão e bolhas
  const corpo = k.grupo([0, 0.88, 0]);
  k.cilindro(0.26, 0.3, 0, [0, 0.15, 0], corpo, 32, k.vidro(0xd8dce6, 0.38));
  k.cilindro(0.26, 0.015, 0xb4b8c4, [0, 0.008, 0], corpo, 32);
  const agua = k.cilindro(0.245, 0.17, 0, [0, 0.1, 0], corpo, 32, k.brilho(0x6eaae6, { transparent: true, opacity: 0.55 }));
  const feijoes = new THREE.InstancedMesh(new THREE.BoxGeometry(0.03, 0.018, 0.02), k.toon(0x6e2e28), 40);
  corpo.add(feijoes);
  const boneco = new THREE.Object3D();
  k.caixa(0.22, 0.03, 0.04, 0x26262c, [-0.36, 0.25, 0], corpo);  // cabo do corpo

  // tampa, borracha, peso, válvula de segurança e trava
  const tampa = k.grupo([0, 1.19, 0]);
  k.cilindro(0.27, 0.03, 0xb4b8c4, [0, 0, 0], tampa, 32);
  k.cilindro(0.2, 0.02, 0xc8ccd6, [0, 0.025, 0], tampa, 32);
  k.caixa(0.3, 0.03, 0.05, 0x26262c, [0.4, 0.02, 0], tampa);
  const borracha = new THREE.Mesh(new THREE.TorusGeometry(0.255, 0.012, 8, 40), k.toon(0x202024));
  borracha.rotation.x = Math.PI / 2;
  borracha.position.y = 1.175;
  k.scene.add(borracha);
  const pino = k.cilindro(0.012, 0.05, 0x60606a, [0, 1.24, 0], k.scene, 10);
  const peso = k.grupo([0, 1.27, 0]);
  k.cilindro(0.04, 0.05, 0x3c3c44, [0, 0, 0], peso, 16);
  k.cilindro(0.015, 0.03, 0x3c3c44, [0, 0.04, 0], peso, 10);
  const seguranca = k.cilindro(0.02, 0.025, 0xd23c3c, [0.12, 1.225, 0.04], k.scene, 12);
  const trava = k.caixa(0.03, 0.03, 0.03, 0xf0b428, [0.3, 1.235, 0]);
  const mao = k.grupo([0.55, 1.25, 0]);
  k.caixa(0.15, 0.06, 0.08, 0xf0c496, [0, 0, 0], mao);

  // termômetro e relógio (cena 2)
  const termometro = k.grupo([-0.45, 1.0, 0.15]);
  k.cilindro(0.015, 0.35, 0xf4f4f8, [0, 0.17, 0], termometro, 10);
  k.esfera(0.03, 0, [0, 0, 0], termometro, k.brilho(0xdc2828));
  k.cilindro(0.009, 0.2, 0, [0, 0.1, 0], termometro, 8, k.brilho(0xdc2828));
  const relogio = k.grupo([0.55, 1.6, -0.39]);
  k.cilindro(0.13, 0.02, 0xf4f4f8, [0, 0, 0], relogio, 24).rotation.x = Math.PI / 2;
  const ponteiro = k.caixa(0.012, 0.1, 0.01, 0x202028, [0, 0, 0.02], relogio);
  ponteiro.geometry.translate(0, 0.04, 0);

  const bolhas = k.pontos(60, 0.015), vapor = k.pontos(140, 0.035), jatos = k.pontos(80, 0.03);
  const ANC = { panela: k.V(0, 1.18, 0.27), tampa: k.V(0.2, 1.22, 0.1), borracha: k.V(-0.25, 1.175, 0.05),
    valvula: peso, seguranca: seguranca, trava: trava, vapor: k.V(0, 1.08, 0.1) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    chamas.forEach((f, i) => f.scale.setScalar(0.7 + 0.5 * Math.abs(Math.sin(T * 14 + i))));
    let pressao = 0;
    if (c === 3 && A("pressao") !== null) pressao = k.suave(k.cl(A("pressao") / 2));
    else if (c >= 4) pressao = 1;
    const tremor = c === 6 && A("treme") !== null ? 0.008 * k.cl(A("treme")) : 0;
    corpo.position.x = Math.sin(T * 40) * tremor;
    agua.material.color.setHSL(0.58 - 0.05 * pressao, 0.65, 0.65);
    let i = 0;
    for (let j = 0; j < 40; j++) {  // feijões balançando na água
      const a = j * 2.4, r = 0.05 + (j % 7) * 0.025;
      boneco.position.set(Math.cos(a) * r, 0.04 + (j % 5) * 0.025 + Math.sin(T * 3 + j) * 0.005 * (1 + pressao), Math.sin(a) * r);
      boneco.rotation.set(j, T * (1 + pressao) + j, 0);
      boneco.updateMatrix();
      feijoes.setMatrixAt(i++, boneco.matrix);
    }
    feijoes.instanceMatrix.needsUpdate = true;

    const pt = P("tampa");
    tampa.visible = pt > 0;
    tampa.position.y = 1.19 + (1 - k.pop(k.cl(pt))) * 0.5;
    tampa.position.x = corpo.position.x;
    tampa.rotation.y = pt < 1 ? (1 - pt) * 0.8 : 0;  // gira para travar
    k.encaixar(borracha, P("borracha"));
    borracha.rotation.x = Math.PI / 2;
    pino.visible = P("valvula") > 0;
    let levanta = 0;
    if (c === 7 && A("levanta") !== null) levanta = k.suave(k.cl(A("levanta") / 0.4));
    else if (c === 8 || c === 12) levanta = 1;
    k.encaixar(peso, P("valvula"));
    peso.position.y = 1.27 + 0.03 * levanta + (levanta > 0.5 ? Math.sin(T * 30) * 0.006 : 0);
    peso.rotation.z = levanta > 0.5 ? Math.sin(T * 25) * 0.15 : 0;
    const pula = c === 9 && A("emergencia") !== null;
    seguranca.visible = P("seguranca") > 0;
    seguranca.position.y = 1.225 + (pula ? 0.12 * k.cl(A("emergencia") / 0.3) : 0);
    k.encaixar(trava, P("trava"));
    mao.visible = c === 10;
    mao.position.x = 0.55 + Math.sin(T * 6) * 0.02;
    termometro.visible = relogio.visible = c === 2 && A("ferve") !== null;
    ponteiro.rotation.z = -T * 5;

    k.nuvem(bolhas, (j, s) => {
      const fase = (T * (1 + pressao) + s[0]) % 1;
      return [Math.cos(s[1] * 6.3) * s[2] * 0.22 + corpo.position.x, 0.9 + fase * 0.17, Math.sin(s[1] * 6.3) * s[2] * 0.22, 0.85, 0.94, 1];
    });
    k.nuvem(vapor, (j, s) => {
      const fase = (T * 0.4 + s[0]) % 1;
      if (pt <= 0 && j < 50) return [(s[1] - 0.5) * 0.4, 1.1 + fase * 0.6, (s[2] - 0.5) * 0.3, 1, 1, 1];  // sem tampa: vapor escapa
      if (pressao > 0 && j >= 50 && j < 50 + 90 * pressao) {  // vapor preso, cada vez mais denso
        return [Math.cos(s[1] * 6.3) * s[2] * 0.23, 1.07 + s[0] * 0.1 + Math.sin(T * 3 + j) * 0.01, Math.sin(s[1] * 6.3) * s[2] * 0.23, 1, 1, 1];
      }
      return null;
    });
    k.nuvem(jatos, (j, s) => {
      const fase = (T * 3 + s[0]) % 1;
      if (levanta > 0.3 && j < 30) return [(s[1] - 0.5) * 0.04 * fase, 1.3 + fase * 0.5, (s[2] - 0.5) * 0.04, 1, 1, 1];
      if (pula && j >= 30 && j < 55) return [0.12 + (s[1] - 0.5) * 0.03, 1.25 + fase * 0.4, 0.04, 1, 1, 1];
      if (c === 5 && A("escapa") !== null && P("borracha") < 1 && j >= 55) {  // vapor pela beirada da tampa
        const a = s[1] * 6.3;
        return [Math.cos(a) * (0.27 + fase * 0.15), 1.19 + fase * 0.05, Math.sin(a) * (0.27 + fase * 0.15), 1, 1, 1];
      }
      if (c === 6 && tremor > 0 && j >= 55) return [(s[1] - 0.5) * 0.6, 0.95 + s[2] * 0.4, 0.3, 1, 0.35, 0.25];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
