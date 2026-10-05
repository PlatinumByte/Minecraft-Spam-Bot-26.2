# Minecraft Spam Bot

Мультибот для **Minecraft Java 26.2**, который заходит на сервер и спамит в чат.
Оркестратор на Python + воркеры на Node.js через `mineflayer-viaproxy`.
Работает с версиями, которые `mineflayer` напрямую не держит (26.2+), через прослойку ViaProxy.

---

## Как это устроено

```
orchestrator.py  ──spawn──>  bot_worker.js  ──>  ViaProxy (JVM)  ──>  MC-сервер
   (Python)                     (Node.js)          (Java, per-bot)
```

- **`orchestrator.py`** — плодит N воркеров, каждому даёт свой ник, следит за событиями (`spawn` / `kicked` / `end` / `error`), реконнектит упавших.
- **`bot_worker.js`** — один процесс = один бот. Поднимает ViaProxy, коннектится к MC-серверу, спамит в чат с заданным интервалом.
- **ViaProxy** — Java-прокси, транслирует протокол клиента в 26.2. Каждый бот запускает свой экземпляр (см. [ограничения](#ограничения-и-грабли)).
- Общение оркестратора с воркерами — JSON-строки через `stdin`/`stdout`.

---

## Требования

| Компонент | Версия | Обязательно |
|---|---|---|
| Python | 3.10+ | ✅ |
| Node.js | 18+ | ✅ |
| Java (JRE) | 17+ | ✅ (для ViaProxy) |
| ОС | Windows / Linux / macOS | — |

Проверка:

```bash
python --version
node --version
java -version
```

Если Java нет — ставь [Temurin 17+](https://adoptium.net).

---

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/<твой-юзер>/<репо>.git
cd <репо>
```

### 2. Python-окружение

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

> Внешних питон-зависимостей нет — только стандартная библиотека.
> Виртуалка нужна чисто для изоляции.

### 3. Node-зависимости

```bash
npm install mineflayer-viaproxy
```

При первом запуске `mineflayer-viaproxy` сам скачает `ViaProxy.jar`
в папку `viaproxy/` рядом с воркером.

---

## Настройка

Все параметры — в `orchestrator.py`:

| Параметр | Описание | Пример |
|---|---|---|
| `HOST` | Адрес MC-сервера | `"127.0.0.1"` |
| `PORT` | Порт сервера | `25565` |
| `NUM_BOTS` | Сколько ботов запускать | `10` |
| `SPAM_MESSAGE` | Что спамить | `"..."` |
| `SPAM_INTERVAL_MS` | Интервал между сообщениями, мс | `1000` |
| `AUTH` | `offline` для пиратки, `microsoft` для online-mode | `"offline"` |
| `RECONNECT_DELAY` | Базовая задержка реконнекта, сек | `12` |
| `SPAWN_STAGGER` | Разнос стартов ботов, сек | `6.0` |

Ники генерируются автоматически из списка `PREFIXES` + 5 случайных символов.

---

## Запуск

```bash
python orchestrator.py
```

Остановка — **Ctrl+C**. Оркестратор погасит всех воркеров.

### Что увидишь в логе

```
[+] BotBKQSb spawned
[+] xX_1sNIm spawned
[!] PlayerZvvSD kicked: {"translate":"multiplayer.disconnect.server_full"}
[-] Noob99AkZ end: socketClosed
[x] UsergVtPv error: connect ECONNREFUSED 127.0.0.1:50089
```

| Префикс | Значение |
|---|---|
| `[+]` | Бот успешно зашёл в мир |
| `[!]` | Сервер кикнул (throttle, server_full, бан и т.д.) |
| `[-]` | Соединение закрыто |
| `[x]` | Ошибка внутри воркера |

---

## Ограничения и грабли

### 1. `Connection throttled!`

Сервер душит коннекты с одного IP. Дефолтное окно на Paper/Spigot — **4000 мс**.
Если `SPAWN_STAGGER` меньше — половина ботов отвалится сразу после старта.

**Что делать:** `SPAWN_STAGGER = 6.0` или больше. Если сервер жёстче — 12–15 сек.

### 2. `multiplayer.disconnect.server_full`

Сервер забит. Ты занимаешь больше слотов, чем `max-players`.
Уменьшай `NUM_BOTS` или ставь паузу на реконнект после `server_full`.

### 3. `ViaProxy failed to start. Exit code: 3221225794`

`0xC0000142` = `STATUS_DLL_INIT_FAILED`. **Windows не тянет много параллельных JVM.**
Практический предел — **3–5 ботов** с per-bot ViaProxy.

**Что делать:**
- Уменьшить `NUM_BOTS` до 3–5.
- Или поднять **один общий ViaProxy** и направить всех ботов в него (см. [раздел ниже](#один-viaproxy-на-всех-для-10-ботов)).

### 4. `bot._client.chat is not a function`

`mineflayer-viaproxy` иногда не привязывает `bot._client.chat` до первого тика.
В `bot_worker.js` есть фоллбэк на прямой `write('chat_message', ...)`.

### 5. `MaxListenersExceededWarning`

Каждый реконнект плодит listener'ы на `process.beforeExit` и не снимает.
После ~10 реконнектов на воркер — warning, после ~20 — утечка.
Косметика, но лучше не давать ботам реконнектиться слишком часто.

---

## Один ViaProxy на всех (для 10+ ботов)

Если 3–5 ботов мало, а 10+ с per-bot ViaProxy крашится — делаем так.

### 1. Скачать `ViaProxy.jar`

[github.com/ViaVersion/ViaProxy/releases/latest](https://github.com/ViaVersion/ViaProxy/releases/latest)

Положить в `viaproxy/ViaProxy.jar`.

### 2. Запустить ViaProxy отдельно

```bash
cd viaproxy
java -jar ViaProxy.jar
```

В меню:

| Поле | Значение |
|---|---|
| target | `<адрес твоего MC-сервера>:25565` |
| bind | `127.0.0.1:25568` |
| target version | `26.2` |

Проверить что слушает:

```bash
# Windows
netstat -an | findstr 25568

# Linux / macOS
ss -tlnp | grep 25568
```

### 3. Поправить `bot_worker.js`

```js
bot = await createBot({
  host: '127.0.0.1',
  port: 25568,                 // порт ViaProxy
  username: cfg.nick,
  auth: cfg.auth || 'offline',
  version: '26.2',
  forceViaProxy: false,        // свой ViaProxy не поднимаем
  // viaProxyOpts: { ... }     // убрать
});
```

Теперь 10–20 ботов коннектятся в одну JVM, ресурсы не улетают в космос.

---

## Правовая хуйня

Код выложен «как есть», для образовательных целей.
Автор не несёт ответственности за то, как ты его используешь.
Спам в чужих серверах — это твои проблемы с админами, а не мои.

---

## Лицензия

[MIT](LICENSE)
