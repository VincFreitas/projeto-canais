// Cena 3D do zíper: jaqueta no cabide, fileiras de dentes que encaixam atrás do cursor e a cunha que separa.
import { kit } from "./comum3d.js";

export const SERIE = "PULGA DO SABER · ZÍPER";
export const PECAS = {
  jaqueta: { titulo: "Jaqueta", conta: false },
  dentes: { titulo: "Dentes", conta: true },
  dente: { titulo: "Dente", conta: false },
  cursor: { titulo: "Cursor", conta: true },
  cunha: { titulo: "Cunha", conta: true },
};
const VISTAS = {
  tudo: [[1.0, 1.5, 2.8], [0, 1.1, 0]],
  jaqueta: [[0.7, 1.3, 2.1], [0, 1.15, 0]],
  dentes: [[0.45, 1.25, 1.25], [0, 1.1, 0]],
  dente: [[1.7, 1.55, 1.3], [1.15, 1.35, 0]],
  cursor: [[0.4, 0.95, 0.95], [0, 0.75, 0]],
  cunha: [[0.4, 1.05, 0.9], [0, 0.95, 0]],
};
const Y0 = 0.45, Y1 = 1.75;  // começo e fim do zíper

export function criar(args) {
  const k = kit(args, { ceu: 0x3a2a2a });
  const { THREE } = k;
  k.sala({ piso: k.tabua("#8a5a36", "#704628"), parede: k.azulejo("#c89670", "#b48460", [10, 6]), janela: false });

  // cabide e jaqueta
  k.cilindro(0.025, 1.9, 0x5a4636, [0, 0.95, -0.15]);
  k.cilindro(0.25, 0.04, 0x5a4636, [0, 0.02, -0.15]);
  const jeans = 0x3c6ebe, jeansEsc = 0x2c5296;
  const esq = k.caixa(0.58, 1.4, 0.06, jeans, [-0.32, 1.1, 0]);
  const dir = k.caixa(0.58, 1.4, 0.06, jeans, [0.32, 1.1, 0]);
  k.caixa(0.5, 0.16, 0.12, jeansEsc, [0, 1.86, -0.02]);  // gola
  for (const x of [-0.75, 0.75]) k.caixa(0.22, 1.25, 0.12, jeansEsc, [x, 1.15, -0.02]);  // mangas
  for (const x of [-0.36, 0.36]) k.caixa(0.2, 0.18, 0.01, jeansEsc, [x, 1.3, 0.035]);   // bolsos
  const botoes = [];
  for (let i = 0; i < 5; i++) botoes.push(k.cilindro(0.04, 0.02, 0xc8aa78, [0.08, 0.6 + i * 0.27, 0.04], k.scene, 12));
  botoes.forEach((b) => (b.rotation.x = Math.PI / 2));

  // dentes: duas fileiras (instanciadas), espaçados ou densos
  const metal = k.toon(0xdcdce4);
  const fazerFileira = (n) => new THREE.InstancedMesh(new THREE.BoxGeometry(0.045, 0.6 * (Y1 - Y0) / n, 0.035), metal, n * 2);
  const esparsa = fazerFileira(26), densa = fazerFileira(40);
  k.scene.add(esparsa, densa);
  const boneco = new THREE.Object3D();
  const posicionar = (malha, n, fechadoAte, prog) => {
    let i = 0;
    for (let j = 0; j < n; j++) {
      const y = Y0 + (j + 0.5) * (Y1 - Y0) / n;
      const aparece = y <= Y0 + (Y1 - Y0) * prog;
      const abre = fechadoAte === null ? 1 : k.cl((y - fechadoAte) / 0.9);
      for (const lado of [-1, 1]) {
        const alterna = (j % 2 === (lado > 0 ? 0 : 1)) ? 0.012 : 0;
        boneco.position.set(lado * (0.018 + 0.07 * abre) - lado * alterna * (1 - abre), y, 0.05);
        boneco.scale.setScalar(aparece ? 1 : 0.0001);
        boneco.updateMatrix();
        malha.setMatrixAt(i++, boneco.matrix);
      }
    }
    malha.instanceMatrix.needsUpdate = true;
  };

  // cursor com a cunha
  const cursor = k.grupo([0, 0.6, 0.08]);
  k.caixa(0.13, 0.1, 0.05, 0xc8c8d2, [0, 0, 0], cursor);
  k.caixa(0.06, 0.05, 0.05, 0xc8c8d2, [0, -0.07, 0], cursor);
  const puxador = k.caixa(0.035, 0.13, 0.015, 0x9696a0, [0, -0.15, 0.03], cursor);
  const cunha = new THREE.Mesh(new THREE.ConeGeometry(0.035, 0.09, 3), k.toon(0xdc3c3c));
  cunha.rotation.z = Math.PI;
  cunha.position.set(0, 0.02, 0.03);
  cursor.add(cunha);

  // dente gigante (cenas 4 e 5)
  const gigante = k.grupo([1.15, 1.3, 0]);
  k.caixa(0.36, 0.3, 0.2, 0xdcdce4, [0, 0, 0], gigante);
  k.caixa(0.16, 0.1, 0.12, 0xdcdce4, [0, 0.2, 0], gigante);                  // calombo
  const buraco = k.caixa(0.16, 0.1, 0.13, 0x50505a, [0, -0.11, 0.04], gigante);  // buraco
  const dedo = k.grupo([1.55, 1.1, 0.15]);
  k.caixa(0.35, 0.08, 0.08, 0xf0c496, [0, 0, 0], dedo);
  k.caixa(0.12, 0.08, 0.08, 0xf0c496, [-0.2, 0.06, 0], dedo);

  const vento = k.pontos(80, 0.03), brilhos = k.pontos(60, 0.04);
  const ANC = { jaqueta: k.V(0, 1.85, 0.1), dentes: k.V(0, 1.2, 0.08), dente: k.V(1.15, 1.45, 0.1),
    calombo: k.V(1.15, 1.52, 0.1), buraco: k.V(1.15, 1.18, 0.15), trava: k.V(0, 0.95, 0.08),
    cursor: cursor, cunha: k.V(0, 0.95, 0.12) };

  function quadro(e) {
    const P = k.P(e), A = k.A(e), { T, cena: c } = e;
    k.camera(e, VISTAS);
    botoes.forEach((b) => (b.visible = c <= 2));
    let yCursor = 0.55, fechado = null;
    if (c === 6 || c === 7) {
      const s = A("subir");
      yCursor = 0.55 + (s !== null ? 1.0 * k.suave(k.cl(s / 2.5)) : 0);
      fechado = yCursor;
    } else if (c === 8) {
      const d = A("descer");
      yCursor = 1.55 - (d !== null ? 1.0 * k.suave(k.cl(d / 2.5)) : 0);
      fechado = yCursor;
    } else if (c === 9) { yCursor = 1.0; fechado = yCursor; }
    else if (c >= 10) {
      const f = c === 10 ? A("fechar2") ?? 0 : 99;
      yCursor = 0.55 + 1.15 * k.suave(k.cl(f / 1.6));
      fechado = yCursor;
    }
    const densa1 = c > 9 || (c === 9 && A("densa") !== null);
    const pd = P("dentes");
    esparsa.visible = pd > 0 && !densa1;
    densa.visible = pd > 0 && densa1;
    posicionar(densa1 ? densa : esparsa, densa1 ? 40 : 26, fechado, pd);
    // painéis se afastam em cima quando o zíper está aberto (V)
    const abertura = fechado === null ? 1 : k.cl((1.75 - fechado) / 1.2);
    esq.rotation.z = 0.06 * abertura; dir.rotation.z = -0.06 * abertura;
    k.encaixar(cursor, P("cursor"));
    cursor.position.y = yCursor;
    puxador.rotation.x = Math.sin(T * 3) * 0.2;
    cunha.visible = P("cunha") > 0;
    cunha.scale.setScalar(Math.max(k.pop(k.cl(P("cunha"))), 0.001) * 1.4);
    const zoom = A("zoom_dente");
    gigante.visible = (c === 4 || c === 5) && zoom !== null;
    gigante.scale.setScalar(Math.max(k.pop(k.cl((zoom ?? 0) / 0.4)), 0.001));
    gigante.rotation.y = Math.sin(T * 0.6) * 0.4;
    dedo.visible = c === 5 && A("mao") !== null;
    dedo.position.x = 1.55 + Math.sin(T * 25) * 0.015;
    k.nuvem(vento, (i, s) => {
      if (c !== 2 || A("vento") === null) return null;
      const fase = (T * 0.8 + s[0]) % 1;
      return [-1.2 + fase * 2.4, 0.6 + (i % 5) * 0.27, 0.15 + s[2] * 0.1, 0.85, 0.92, 1];
    });
    k.nuvem(brilhos, (i, s) => {
      if ((c === 7 || c === 10) && fechado !== null && i < 12) {  // cliques de encaixe logo abaixo do cursor
        return k.pisca(T * 3, s) > 0.2 ? [(s[0] - 0.5) * 0.08, yCursor - 0.12 - s[1] * 0.05, 0.1, 1, 1, 0.7] : null;
      }
      if (c === 11 && k.pisca(T, s) > 0.15) return [-0.7 + s[0] * 1.4, 0.4 + s[1] * 1.5, 0.15, 1, 1, 0.85];
      if (c === 4 && gigante.visible && k.pisca(T, s) > 0.2) return [0.9 + s[0] * 0.5, 1.1 + s[1] * 0.5, 0.15, 1, 1, 1];
      return null;
    });
    return k.ancoras(ANC);
  }
  return { scene: k.scene, camera: k.cam, quadro };
}
