// Cena 3D do airbag: boneco de teste no banco, volante com o saco dobrado, sensor, cápsula, enchimento e furinhos.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · AIRBAG";
export const PECAS = {
  boneco: { titulo: "Motorista", conta: false },
  saco: { titulo: "Saco dobrado", conta: true },
  sensor: { titulo: "Sensor", conta: true },
  capsula: { titulo: "Cápsula", conta: true },
  furos: { titulo: "Furinhos", conta: true },
};
const VISTAS = {
  tudo: [[1.5, 1.45, 1.9], [0.25, 0.95, 0]],
  boneco: [[1.4, 1.25, 1.2], [0.15, 1.0, 0]],
  saco: [[1.0, 1.2, 0.75], [0.48, 1.05, 0]],
  sensor: [[0.75, 0.8, 1.05], [0.28, 0.4, 0.3]],
  capsula: [[0.9, 1.15, 0.5], [0.5, 1.05, 0]],
  furos: [[1.1, 1.25, 0.95], [0.38, 1.05, 0]],
};

export function criar(args) {
  const k = kit(args, { ceu: 0x283c6e });
  const { THREE } = k;
  k.sala({ piso: k.azulejo("#4a4a56", "#3c3c46", [10, 10]), parede: k.azulejo("#3a5a96", "#4a6aa8", [12, 8]), janela: false,
    fundoZ: -1.2 });
  const carro = k.grupo([0, 0, 0]);
  k.caixa(0.5, 0.12, 0.5, 0x3c3c46, [0, 0.5, 0], carro);          // banco
  k.caixa(0.12, 0.65, 0.5, 0x3c3c46, [-0.24, 0.85, 0], carro);
  k.caixa(0.6, 0.35, 0.9, 0x50546a, [1.0, 0.8, 0], carro);        // painel
  k.caixa(0.04, 0.5, 0.9, 0x96b4dc, [1.05, 1.25, 0], carro, k.vidro(0xb4d2ff, 0.25));  // para-brisa
  k.caixa(2.0, 0.04, 1.0, 0x30303a, [0.3, 0.32, 0], carro);       // assoalho
  const coluna = k.tubo([[0.9, 0.85, 0], [0.55, 1.02, 0]], 0.035, 0x46464e, false, carro);
  const volante = k.grupo([0.52, 1.04, 0], carro);
  volante.rotation.z = 0.5;
  const aro = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.025, 8, 28), k.toon(0x26262c));
  aro.rotation.y = Math.PI / 2;
  volante.add(aro);
  const cubo = k.cilindro(0.075, 0.06, 0, [0, 0, 0], volante, 18, k.vidro(0x46464e, 0.45));
  cubo.rotation.z = Math.PI / 2;
  const dobrado = Array.from({ length: 4 }, (_, i) => k.caixa(0.02, 0.1 - i * 0.012, 0.1, 0xf4f4fa, [-0.02 + i * 0.008, 0, 0], volante));

  // boneco de teste
  const boneco = k.grupo([0, 0.58, 0]);
  const amarelo = 0xf0c828;
  const quadril = k.caixa(0.3, 0.15, 0.32, amarelo, [0, 0.05, 0], boneco);
  for (const z of [-0.09, 0.09]) k.tubo([[0.1, 0.05, z], [0.42, 0.08, z], [0.48, -0.22, z]], 0.05, amarelo, false, boneco);
  const tronco = k.grupo([-0.02, 0.1, 0], boneco);
  k.cilindro(0.13, 0.45, amarelo, [0, 0.24, 0], tronco, 14);
  const cabeca = k.grupo([0, 0.6, 0], tronco);
  k.esfera(0.12, amarelo, [0, 0, 0], cabeca);
  for (const z of [-0.06, 0.06]) k.esfera(0.025, 0x1e1e24, [0.1, 0.02, z], cabeca);
  const bracos = [-0.15, 0.15].map((z) => k.tubo([[0, 0.4, z], [0.3, 0.32, z * 1.2], [0.48, 0.42, z * 0.9]], 0.035, amarelo, false, tronco));
  const cinto = k.tubo([[-0.12, 0.88, 0.17], [0.1, 0.55, 0.17], [0.15, 0.15, 0.17]], 0.03, 0x50505a);

  // airbag e furinhos
  const bolsa = k.grupo([0.48, 1.05, 0]);
  const saco = k.esfera(1, 0xf8f8fc, [0, 0, 0], bolsa);
  const furos = Array.from({ length: 6 }, (_, i) => {
    const a = i * 1.05;
    return k.esfera(0.06, 0x50505a, [-0.6, Math.cos(a) * 0.75, Math.sin(a) * 0.75], bolsa);
  });

  // sensor e cápsula
  const sensor = k.grupo([0.28, 0.36, 0.32]);
  k.caixa(0.22, 0.04, 0.16, 0x288c50, [0, 0, 0], sensor);
  const mostrador = k.cilindro(0.05, 0.01, 0xf4f4f8, [0, 0.03, 0], sensor, 16);
  const agulha = k.caixa(0.005, 0.005, 0.045, 0xdc2828, [0, 0.04, 0.02], sensor);
  agulha.geometry.translate(0, 0, 0.02);
  const capsula = k.cilindro(0.03, 0.04, 0xd2503c, [0.5, 1.05, 0], k.scene, 12);
  capsula.rotation.z = Math.PI / 2;
  const olho = k.grupo([0.3, 1.75, 0.2]);
  k.esfera(0.16, 0xf8f8fc, [0, 0, 0], olho);
  k.esfera(0.07, 0x3c78c8, [0.12, 0, 0], olho);
  const palpebra = k.esfera(0.165, 0xf0c496, [0, 0, 0], olho);

  const fluxoSinal = k.pontos(20, 0.025), fogo = k.pontos(60, 0.03), puffs = k.pontos(90, 0.05);
  const sinal = new THREE.CatmullRomCurve3([k.V(0.28, 0.4, 0.32), k.V(0.75, 0.8, 0.15), k.V(0.5, 1.05, 0)]);
  const ANC = { boneco: k.V(0.05, 1.5, 0.1), saco: k.V(0.5, 1.12, 0.12), sensor: sensor, capsula: capsula,
    furos: furos[1], cinto: k.V(0.0, 0.75, 0.17) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const bate = A("bate");
    carro.position.x = c === 1 && bate !== null ? Math.sin(bate * 60) * 0.02 * Math.max(0, 1 - bate / 0.5) : 0;
    let inclina = 0, cab = 0;
    if (c === 1 && bate !== null) inclina = k.suave(k.cl(bate / 0.4)) * 0.6;
    else if (c === 2 && A("cabeca") !== null) { inclina = 0.3; cab = k.suave(k.cl(A("cabeca") / 0.5)) * 0.6; }
    else if (c === 8 && A("duro") !== null) { inclina = 0.3; cab = 0.45 - Math.abs(Math.sin(Math.min(A("duro"), 1.2) * 5)) * 0.35; }
    else if (c === 9 || c === 11) { inclina = 0.3; cab = 0.3; }
    tronco.rotation.z = -inclina;
    cabeca.rotation.z = -cab;
    cinto.m.visible = c >= 2;
    cinto.mat.color.set(c === 11 ? 0xff7a3c : 0x50505a);
    dobrado.forEach((d) => (d.visible = P("saco") > 0 && P("saco") >= 0 && !(c >= 7)));
    let cheio = 0;
    if (c === 7 && A("enche") !== null) cheio = k.suave(k.cl(A("enche") / 0.15));
    else if (c === 8) cheio = 1;
    else if (c === 9) cheio = 1 - 0.55 * k.cl((A("murcha") ?? 0) / 2.5);
    else if (c >= 10) cheio = 0.5;
    bolsa.visible = cheio > 0.02;
    bolsa.scale.set(0.2 * cheio, 0.26 * cheio, 0.26 * cheio);
    bolsa.position.x = 0.48 - 0.12 * cheio;
    furos.forEach((f) => (f.visible = P("furos") > 0));
    k.encaixar(sensor, P("sensor"));
    agulha.rotation.y = [1, 6, 7].includes(c) ? -1.6 : -0.4 + 0.15 * Math.sin(T * 2);
    capsula.visible = P("capsula") > 0;
    capsula.material.color.set(c === 7 && cheio < 1 ? 0xffc83c : 0xd2503c);
    olho.visible = c === 4 && A("piscar") !== null;
    palpebra.scale.set(1, Math.abs(Math.sin(T * 4)) > 0.85 ? 1 : 0.05, 1);
    palpebra.visible = olho.visible && Math.abs(Math.sin(T * 4)) > 0.85;

    k.correr(fluxoSinal, sinal, T, 1.2, 0xffffa0, 0xffffff, 12, c === 6 && P("capsula") >= 1);
    k.nuvem(fogo, (i, s) => {
      if (!(c === 7 && cheio < 1 && A("enche") !== null)) return null;
      const a = s[0] * 6.3, r = ((T * 4 + s[1]) % 1) * 0.12;
      return [0.5 - r * 0.3, 1.05 + Math.cos(a) * r, Math.sin(a) * r, 1, 0.8, 0.3];
    });
    k.nuvem(puffs, (i, s) => {
      const fase = (T * 1.2 + s[0]) % 1;
      if (c === 9 && P("furos") > 0 && i < 60) {
        const a = (i % 6) * 1.05;
        return [0.48 - 0.12 * cheio - 0.12 * cheio * (1 + fase), 1.05 + Math.cos(a) * 0.2 * cheio * (1 + fase * 0.6), Math.sin(a) * 0.2 * cheio * (1 + fase * 0.6), 1, 1, 1];
      }
      if (c === 1 && bate !== null && i < 40) return [0.2 + fase * 0.8, 0.6 + s[1] * 0.9, 0.5, 1, 1, 1];  // linhas de impacto
      if ((c === 10 || c === 12) && k.pisca(T, s) > 0.15) return [-0.2 + s[0] * 1.2, 0.6 + s[1] * 1.0, 0.4, 1, 1, 0.85];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
