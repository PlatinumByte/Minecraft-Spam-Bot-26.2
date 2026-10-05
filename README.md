MinecraftNET Scanner — Bot Spammer

Мультибот для Minecraft Java 26.2, который заходит на сервер и спамит в чат.
Оркестратор на Python + воркеры на Node.js через mineflayer-viaproxy.
Работает с версиями, которые mineflayer напрямую не держит (26.2 и выше),
через прослойку ViaProxy.

Как это устроено

orchestrator.py плодит N воркеров, каждому даёт свой ник, следит за событиями
(spawn / kicked / end / error), реконнектит упавших.
bot_worker.js — один процесс = один бот. Поднимает ViaProxy, коннектится к
MC-серверу, спамит в чат с заданным интервалом.
ViaProxy — Java-прокси, который транслирует протокол клиента в 26.2.
Каждый бот запускает свой экземпляр (см. ограничения ниже).
Общение оркестратора с воркерами — JSON-строки через stdin/stdout.

Схема:

orchestrator.py  --spawn-->  bot_worker.js  -->  ViaProxy (JVM)  -->  MC-сервер
   (Python)                     (Node.js)          (Java, per-bot)

Требования

- Python 3.10+
- Node.js 18+
- Java 17+ (JRE достаточно) — обязательна для ViaProxy
- Windows / Linux / macOS

Проверить:

python --version
node --version
java -version

Если Java нет — ставь Temurin 17+ с https://adoptium.net

Установка

1. Клонировать репозиторий

git clone https://github.com/<твой-юзер>/<репо>.git
cd <репо>

2. Python-окружение

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

Внешних питон-зависимостей нет — только стандартная библиотека.
Виртуалка нужна чисто для изоляции.

3. Node-зависимости

npm install mineflayer-viaproxy

При первом запуске mineflayer-viaproxy сам скачает ViaProxy.jar
в папку viaproxy/ рядом с воркером.

Настройка

Все параметры — в orchestrator.py:

HOST = "127.0.0.1"                    # адрес MC-сервера
PORT = 25565                          # порт
NUM_BOTS = 10                         # сколько ботов запускать
SPAM_MESSAGE = "..."                  # что спамить
SPAM_INTERVAL_MS = 1000               # интервал между сообщениями, мс
AUTH = "offline"                      # 'offline' для пиратки, 'microsoft' для online-mode
RECONNECT_DELAY = 12                  # базовая задержка реконнекта, сек
SPAWN_STAGGER = 6.0                   # разнос стартов ботов, сек

Ники генерируются автоматически из списка PREFIXES + 5 случайных символов.

Запуск

python orchestrator.py

Остановка — Ctrl+C. Оркестратор погасит всех воркеров.

Что увидишь в логе:

[+] BotBKQSb spawned
[+] xX_1sNIm spawned
[!] PlayerZvvSD kicked: {"translate":"multiplayer.disconnect.server_full"}
[-] Noob99AkZ end: socketClosed
[x] UsergVtPv error: connect ECONNREFUSED 127.0.0.1:50089

- [+] — бот успешно зашёл в мир.
- [!] — сервер кикнул (throttle, server_full, бан и т.д.).
- [-] — соединение закрыто.
- [x] — ошибка внутри воркера.

Ограничения и грабли

1. Connection throttled!

Сервер душит коннекты с одного IP. Дефолтное окно на Paper/Spigot —
4000 мс. Если SPAWN_STAGGER меньше — половина ботов отвалится сразу
после старта.

Что делать: SPAWN_STAGGER = 6.0 или больше. Если сервер жёстче —
12–15 сек.

2. multiplayer.disconnect.server_full

Сервер забит. Ты занимаешь больше слотов, чем max-players.
Уменьшай NUM_BOTS или ставь паузу на реконнект после server_full.

3. ViaProxy failed to start. Exit code: 3221225794

0xC0000142 = STATUS_DLL_INIT_FAILED. Windows не тянет много
параллельных JVM. Практический предел — 3–5 ботов с per-bot ViaProxy.

Что делать:
- Уменьшить NUM_BOTS до 3–5.
- Или поднять один общий ViaProxy и направить всех ботов в него
  (см. раздел «Один ViaProxy на всех»).

4. bot._client.chat is not a function

mineflayer-viaproxy иногда не привязывает bot._client.chat до первого
тика. В bot_worker.js есть фоллбэк на прямой write('chat_message', ...).

5. MaxListenersExceededWarning

Каждый реконнект плодит listener'ы на process.beforeExit и не снимает.
После ~10 реконнектов на воркер — warning, после ~20 — утечка.
Косметика, но лучше не давать ботам реконнектиться слишком часто.

Один ViaProxy на всех (для 10+ ботов)

Если 3–5 ботов мало, а 10+ с per-bot ViaProxy крашится — делаем так:

1. Скачать ViaProxy.jar

https://github.com/ViaVersion/ViaProxy/releases/latest

Положить в viaproxy/ViaProxy.jar.

2. Запустить ViaProxy отдельно

cd viaproxy
java -jar ViaProxy.jar

В меню:
- target: <адрес твоего MC-сервера>:25565
- bind: 127.0.0.1:25568
- target version: 26.2

Проверить что слушает:

# Windows
netstat -an | findstr 25568

# Linux / macOS
ss -tlnp | grep 25568

3. Поправить bot_worker.js

bot = await createBot({
  host: '127.0.0.1',
  port: 25568,                 // порт ViaProxy
  username: cfg.nick,
  auth: cfg.auth || 'offline',
  version: '26.2',
  forceViaProxy: false,        // свой ViaProxy не поднимаем
  // viaProxyOpts: { ... }     // убрать
});

Теперь 10–20 ботов коннектятся в одну JVM, ресурсы не улетают в космос.

Правовая хуйня

Код выложен «как есть», для образовательных целей. Автор не несёт
ответственности за то, как ты его используешь. Спам в чужих серверах —
это твои проблемы с админами, а не мои.

Лицензия

НЕТ
