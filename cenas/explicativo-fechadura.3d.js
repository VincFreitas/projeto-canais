// Cena 3D da fechadura: diagrama em corte na frente da porta, com cilindro, colunas de pinos, molas, lingueta e chave.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · FECHADURA";
export const PECAS = {
  porta: { titulo: "Porta", conta: false },
  lingueta: { titulo: "Lingueta e cilindro", conta: true },
  pinos: { titulo: "Pinos", conta: true },
  chave: { titulo: "Chave", conta: true },
};
const VISTAS = {
  tudo: [[0.7, 1.55, 2.5], [0, 1.15, 0]],
  porta: [[0.7, 1.45, 2.7], [0, 1.1, 0]],
  lingueta: [[1.05, 1.4, 1.6], [0.3, 1.15, 0.15]],
  pinos: [[0.2, 1.4, 1.75], [0, 1.2, 0.15]],
  chave: [[-0.3, 1.4, 1.8], [-0.15, 1.12, 0.15]],
};
const COLUNAS = [-0.3, -0.15, 0, 0.15, 0.3];
const DENTES = [0.04, 0.07, 0.05, 0.08, 0.06];  // tamanho de cada pino de baixo
const LINHA = 1.18, FUNDO = 1.04, TOPO = 1.38, Z = 0.17;

export function criar(args) {
  const k = kit(args, { ceu: 0x2e2420 });
  const { THREE } = k;
  k.sala({ piso: k.tabua("#8a6444", "#6e4c30"), parede: k.azulejo("#e6c8a0", "#d4b48a", [12, 6]), janela: false });
  const porta = k.caixa(1.3, 2.3, 0.08, 0x5a3a22, [0, 1.15, 0]);
  porta.userData.semSombra = true;
  for (let i = 0; i < 5; i++) k.caixa(0.01, 2.2, 0.085, 0x46301c, [-0.52 + i * 0.26, 1.15, 0]).userData.semSombra = true;
  k.caixa(0.12, 2.4, 0.2, 0x5a3c26, [0.72, 1.2, 0]);  // batente

  // tranca de madeira (cenas 1 e 2)
  const tranca = k.caixa(1.2, 0.1, 0.06, 0x6e4626, [0, 1.15, 0.1]);
  const suportes = [-0.5, 0.5].map((x) => k.caixa(0.08, 0.16, 0.06, 0x3c3c46, [x, 1.15, 0.07]));
  const duvida = k.grupo([0, 1.75, 0.2]);
  k.esfera(0.12, 0xf4f4f8, [0, 0, 0], duvida);
  k.caixa(0.03, 0.09, 0.03, 0x282830, [0, 0.03, 0.11], duvida);
  k.caixa(0.03, 0.03, 0.03, 0x282830, [0, -0.06, 0.11], duvida);

  // mecanismo em corte
  const mec = k.grupo([0, 0, 0]);
  k.caixa(1.0, 0.42, 0.24, 0, [0, 1.2, Z], mec, k.vidro(0xf4f4ff, 0.14));
  const miolo = k.grupo([0, 1.1, Z], mec);
  const cil = k.cilindro(0.08, 0.86, 0, [0, 0, 0], miolo, 24, k.vidro(0xe6b45a, 0.55));
  cil.rotation.z = Math.PI / 2;
  const listra = k.caixa(0.86, 0.012, 0.012, 0x7a5420, [0, 0.07, 0.04], miolo);
  const lingueta = k.caixa(0.28, 0.08, 0.08, 0xc8ccd6, [0.6, 1.1, Z], mec);
  const furo = (x) => k.caixa(0.06, TOPO - FUNDO, 0.06, 0, [x, (TOPO + FUNDO) / 2, Z], mec, k.vidro(0x202028, 0.25));
  COLUNAS.forEach(furo);
  const linha = k.caixa(0.86, 0.004, 0.25, 0, [0, LINHA, Z], mec, k.brilho(0xff3c3c, { transparent: true, opacity: 0.7 }));

  const colunas = COLUNAS.map((x, j) => {
    const g = k.grupo([x, 0, Z], mec);
    const baixo = k.cilindro(0.022, DENTES[j], 0xffd23c, [0, 0, 0], g, 12);
    const cima = k.cilindro(0.022, 0.12, 0x7ab4ff, [0, 0, 0], g, 12);
    const helice = [];
    for (let i = 0; i <= 40; i++) { const a = i / 40 * Math.PI * 12; helice.push([Math.cos(a) * 0.02, i / 40, Math.sin(a) * 0.02]); }
    const mola = k.tubo(helice, 0.004, 0x8c96aa, false, g);
    return { g, baixo, cima, mola };
  });

  // chave
  const chave = k.grupo([0, 0, Z]);
  const corChave = k.toon(0xc8ccd6);
  k.caixa(0.86, 0.035, 0.03, 0, [-0.43, 1.06, 0], chave, corChave);
  const dentes = COLUNAS.map((x, j) => k.caixa(0.06, 1, 0.03, 0, [x - 0.43 + 0.43, 0, 0], chave, corChave));
  const argola = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.03, 8, 20), corChave);
  argola.position.set(-0.98, 1.06, 0);
  chave.add(argola);
  const fenda = k.grupo([-0.65, 1.1, Z]);
  k.caixa(0.4, 0.025, 0.025, 0x50505a, [0.2, 0, 0], fenda);
  k.caixa(0.18, 0.06, 0.06, 0xdc3c3c, [-0.05, 0, 0], fenda);

  const brilhos = k.pontos(60, 0.03);
  const ANC = { porta: k.V(0, 1.9, 0.05), lingueta: lingueta, pinos: k.V(0, 1.38, Z), chave: argola,
    cilindro: k.V(-0.2, 1.1, Z + 0.08), mola: colunas[0].mola.m, pino_cima: colunas[0].cima, linha: k.V(0.2, LINHA, Z + 0.1),
    tamanhos: colunas[3].baixo };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    const t1 = A("tranca") !== null ? k.suave(k.cl(A("tranca") / 0.8)) : 0;
    tranca.visible = c <= 2;
    tranca.position.x = 1.2 * (1 - t1);
    suportes.forEach((s) => (s.visible = c <= 2));
    duvida.visible = c === 2 && A("fora") !== null;
    mec.visible = P("lingueta") > 0;
    mec.scale.setScalar(Math.max(k.pop(k.cl(P("lingueta"))), 0.001));
    let levanta = 0, gira = 0, entra = 0, errada = false;
    if (c === 4 && A("chave_fenda") !== null) gira = k.suave(k.cl(A("chave_fenda") / 1));
    if (c === 8) { entra = k.suave(k.cl(P("chave"))); levanta = A("alinha") !== null ? k.suave(k.cl(A("alinha") / 1)) : 0; }
    else if (c === 9) { entra = levanta = 1; gira = k.suave(k.cl((A("gira") ?? 0) / 1)); }
    else if (c === 10) { entra = levanta = 1; errada = A("errada") !== null; }
    else if (c >= 11) { entra = levanta = 1; gira = c === 12 ? 1 : 0; }
    fenda.visible = c === 4;
    fenda.rotation.x = gira * 1.4;
    miolo.rotation.x = gira * 1.4;
    lingueta.position.x = 0.6 - 0.2 * gira;
    linha.visible = [6, 8, 9, 10].includes(c) && P("pinos") >= 1;
    linha.material.color.set(levanta >= 1 && !errada ? 0xffffff : 0xff3c3c);
    const pp = P("pinos");
    colunas.forEach((col, j) => {
      col.g.visible = pp > 0;
      col.g.scale.setScalar(Math.max(k.pop(k.cl(pp)), 0.001));
      const L = DENTES[j];
      let sobe = (LINHA - L - FUNDO) * levanta;  // a chave empurra até a emenda ficar na linha
      if (errada && j === 2) sobe -= 0.035;
      const base = FUNDO + sobe;
      col.baixo.position.y = base + L / 2;
      col.cima.position.y = base + L + 0.06;
      const topoMola = base + L + 0.12;
      col.mola.m.position.y = topoMola;
      col.mola.m.scale.y = TOPO - topoMola;
      const destaque = c === 7 ? 0.5 + 0.5 * Math.sin(T * 6) : 0;
      col.baixo.material.emissive?.setRGB(destaque * 0.5, destaque * 0.35, 0);
    });
    chave.visible = (P("chave") > 0 && c >= 8) || c > 8;
    chave.position.x = -0.9 * (1 - entra);
    dentes.forEach((d, j) => {
      const topo = LINHA - DENTES[j] + (errada && j === 2 ? -0.035 : 0);
      const alto = topo - 1.075;
      d.scale.y = Math.max(alto, 0.001);
      d.position.set(COLUNAS[j], 1.075 + alto / 2, 0);
    });
    k.nuvem(brilhos, (j, s) => {
      if (c === 9 && gira > 0 && j < 20) return [Math.cos(s[0] * 6.3) * 0.12, 1.1 + Math.sin(s[0] * 6.3) * 0.12, Z + 0.1, 1, 0.95, 0.6];
      if ((c === 11 || c === 12) && k.pisca(T, s) > 0.15) return [-0.5 + s[0], 0.95 + s[1] * 0.5, Z + 0.15, 1, 1, 0.85];
      if (c === 10 && errada && j < 10) return [COLUNAS[2] + (s[0] - 0.5) * 0.1, LINHA + (s[1] - 0.5) * 0.06, Z + 0.14, 1, 0.2, 0.2];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
