const { createBot } = require('mineflayer-viaproxy');
const readline = require('readline');

let bot = null;
let spamTimer = null;
let config = null;

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function stopSpam() {
  if (spamTimer) { clearInterval(spamTimer); spamTimer = null; }
}

async function startBot(cfg) {
  config = cfg;

  bot = await createBot({
    host: cfg.host,
    port: cfg.port,
    username: cfg.nick,
    auth: cfg.auth || 'offline',
    // version НЕ указываем — mineflayer-viaproxy сам определит
    forceViaProxy: true,                 // ← КЛЮЧЕВОЙ ФЛАГ
    viaProxyOpts: {
      javaPath: 'java',
      autoUpdate: true,
      // viaProxyLocation: 'C:\\path\\to\\ViaProxy.jar',  // если jar уже скачан
    },
  });

  bot.once('spawn', () => {
    send({ event: 'spawn', nick: cfg.nick });
    stopSpam();
    spamTimer = setInterval(() => {
      try { bot.chat(cfg.message); }
      catch (e) { send({ event: 'error', nick: cfg.nick, msg: e.message }); }
    }, cfg.interval);
  });

  bot.on('error', (err) => {
    send({ event: 'error', nick: cfg.nick, msg: err.message });
  });

  bot.on('kicked', (reason) => {
    send({ event: 'kicked', nick: cfg.nick, reason: String(reason) });
  });

  bot.on('end', (reason) => {
    stopSpam();
    send({ event: 'end', nick: cfg.nick, reason: String(reason) });
  });
}

const rl = readline.createInterface({ input: process.stdin });

rl.on('line', async (line) => {
  let cmd;
  try { cmd = JSON.parse(line); }
  catch { send({ event: 'error', msg: 'bad json' }); return; }

  switch (cmd.cmd) {
    case 'start':
      await startBot(cmd);
      break;
    case 'stop':
      stopSpam();
      if (bot) bot.quit('orchestrator stop');
      setTimeout(() => process.exit(0), 500);
      break;
    case 'restart':
      stopSpam();
      if (bot) bot.quit('restart');
      setTimeout(() => startBot(config), 2000);
      break;
    default:
      send({ event: 'error', msg: 'unknown cmd: ' + cmd.cmd });
  }
});

process.on('SIGTERM', () => { stopSpam(); process.exit(0); });
