// Abre o n8n mais rápido no Windows (o n8n.ps1 carrega com NODE_OPTIONS --require).
// Ao abrir, o Node procura cada módulo em várias pastas e extensões (dezenas de consultas ao disco por
// require, num node_modules de ~290 mil arquivos), e o antivírus confere cada consulta. Este arquivo guarda
// onde cada módulo foi achado e, na próxima abertura, usa esse caminho direto.
// O nome do cache (DARKOPS_CACHE_N8N) muda com a versão do n8n e com a data do node_modules/.package-lock.json,
// que o npm reescreve em toda instalação: qualquer mudança nos pacotes começa um cache novo. Se mesmo assim
// o n8n cair logo ao abrir, o cache é apagado e o n8n.ps1 abre de novo sem ele.
const Module = require('node:module');
const fs = require('node:fs');
const path = require('node:path');

const arquivo = process.env.DARKOPS_CACHE_N8N;
const eh_n8n = /[\\/]n8n[\\/]bin[\\/]n8n$/.test(process.argv[1] || '');
// os comandos que o n8n abre (Execute Command: Python, Claude Code...) não herdam nada disto
delete process.env.NODE_OPTIONS;
delete process.env.DARKOPS_CACHE_N8N;
if (arquivo && eh_n8n && typeof Module._findPath === 'function') {
  let cache = {};
  try { cache = JSON.parse(fs.readFileSync(arquivo, 'utf8')); } catch { cache = {}; }
  let novos = 0;
  const original = Module._findPath;
  Module._findPath = function (pedido, pastas, principal) {
    const chave = pedido + '\n' + (pastas && pastas.length ? pastas[0] : '');
    const achado = cache[chave];
    if (achado) return achado;
    const caminho = original.apply(this, arguments);
    if (caminho) { cache[chave] = caminho; novos++; }
    return caminho;
  };
  const gravar = () => {
    if (!novos) return;
    novos = 0;
    try {
      fs.mkdirSync(path.dirname(arquivo), { recursive: true });
      fs.writeFileSync(arquivo + '.tmp', JSON.stringify(cache));
      fs.renameSync(arquivo + '.tmp', arquivo);
    } catch { /* sem cache: o n8n só abre no tempo normal */ }
  };
  // o n8n nunca sai sozinho: grava depois de abrir (e de novo mais tarde, para os módulos carregados no uso)
  for (const s of [90, 600]) setTimeout(gravar, s * 1000).unref();
  process.on('exit', (codigo) => {
    if (codigo !== 0 && process.uptime() < 180) {
      try { fs.unlinkSync(arquivo); } catch { /* já não existe */ }
    }
  });
}
