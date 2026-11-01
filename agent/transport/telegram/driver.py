"""The Telegram driver: an agent's own bot, answering the transport family's contract over the Bot API.

**THE BOT IS THE AGENT'S.** It is the account the agent speaks through on Telegram (`telegram:hasBot`), its token
`TELEGRAM_BOT_TOKEN` and where the API answers `TELEGRAM_URL`, both environment, the standard library alone between
them. A group with several agents holds several bots, each its agent's, so each speaks in its own name.

**IT POLLS.** `start` asks the runtime to ask `getUpdates` every `TELEGRAM_POLL_S` real seconds, from the offset after
the last update seen, on a thread of its own; every text message is handed to the runtime as a job, its channel the
chat's id. `handle` finds the `telegram:Chat` the world names by that id, the person by the user id they wrote as
where the world states it, and says `prose`; a chat the world names none of is nobody's, dropped and said once.

**IT SENDS.** `say_to` posts `sendMessage` to a chat the world names by its id, and is False for any other channel.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request

import pyoxigraph as ox

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import BELIEF, local_of
from agent.store import graphs_of, rows
from agent.transport.transport import Prose, Transport

log = logging.getLogger("telegram")

TELEGRAM_URL = "https://api.telegram.org"
POLL_S = 3.0
TIMEOUT_S = 30.0

#  WHICH CHAT A MESSAGE IS ON, and which person wrote it: the chat by the id the API names it, the person by theirs.
_CHAT_Q = "SELECT ?chat WHERE { ?chat a telegram:Chat ; telegram:chatId ?id FILTER (STR(?id) = $id) }"
_USER_Q = "SELECT ?person WHERE { ?person telegram:userId ?id FILTER (STR(?id) = $id) }"
_ID_Q = "SELECT ?id WHERE { $chat a telegram:Chat ; telegram:chatId ?id }"


def _call(url: str, body: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json"},
                                     method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:            # noqa: S310 — the bot's api
        return json.loads(response.read())


class Telegram(Transport):
    """One agent's bot: polled for what is written to it, told what the agent says, over `call(url, body)`."""

    def __init__(self, me: str, token: str, url: str = TELEGRAM_URL, call=None, spawn=None, deliver=None,
                 every: float = POLL_S):
        self.me, self.token, self.url = me, token, url.rstrip("/")
        self.call = call or _call
        self.spawn = spawn or (lambda work: threading.Thread(target=work, daemon=True).start())
        self.deliver = deliver or (lambda *message: None)
        self.every = every
        self.offset: int | None = None
        self.prose = Signal("prose")
        self._unknown: set[str] = set()
        self._polling = threading.Lock()

    @classmethod
    def connect(cls, me: str, deliver=None, *, environ=None, client=None) -> "Telegram":
        env = os.environ if environ is None else environ
        token = env.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("no TELEGRAM_BOT_TOKEN in the environment — this agent speaks through a bot and holds "
                               "no token for it; write secrets/telegram-<agent>.env and regenerate the compose file")
        return cls(me, token, env.get("TELEGRAM_URL") or TELEGRAM_URL, call=client, deliver=deliver,
                   every=float(env.get("TELEGRAM_POLL_S") or POLL_S))

    def _method(self, name: str) -> str:
        return f"{self.url}/bot{self.token}/{name}"

    def start(self, runtime) -> None:
        super().start(runtime)
        runtime.every(self.every, self.poll)

    def poll(self) -> list[str]:
        """Ask for what was written since the last poll, on a thread of its own, one poll at a time."""
        def ask():
            if not self._polling.acquire(blocking=False):
                return
            try:
                for channel, payload in self.updates():
                    self.deliver(channel, payload, clock.now())
            except Exception as exc:                                     # noqa: BLE001 — the api fails
                log.warning("%s: the bot would not answer: %s", local_of(self.me), exc)
            finally:
                self._polling.release()
        self.spawn(ask)
        return []

    def updates(self) -> list[tuple[str, bytes]]:
        """Every text message since the last poll, as its chat's id and `{"from": user id, "text": …}`; an update that
        is no text message is passed over, and every update seen is confirmed by the next poll's offset."""
        body = {"timeout": 0, "allowed_updates": ["message"]}
        if self.offset is not None:
            body["offset"] = self.offset
        reply = self.call(self._method("getUpdates"), body)
        out = []
        for update in reply.get("result", []) if reply.get("ok", True) else []:
            self.offset = max(self.offset or 0, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or {}
            text, chat = message.get("text"), (message.get("chat") or {}).get("id")
            if text and chat is not None:
                sender = (message.get("from") or {}).get("id")
                out.append((str(chat), json.dumps({"from": str(sender) if sender is not None else None,
                                                   "text": text.strip()}).encode()))
        return out

    def handle(self, store, channel: str, payload: bytes, at, *, memo=None) -> list[tuple[str | None, str]]:
        stated = graphs_of(store, BELIEF, common=True)
        chats = [r["chat"] for r in rows(store, _CHAT_Q, stated, id=ox.Literal(channel))]
        if not chats:
            if channel not in self._unknown:
                self._unknown.add(channel)
                log.warning("%s: a message in Telegram chat %s, which the world names in no chat: dropped", local_of(self.me), channel)
            return []
        said = json.loads(payload)
        people = [r["person"] for r in rows(store, _USER_Q, stated, id=ox.Literal(said["from"]))] if said.get("from") else []
        prose = Prose(chats[0], people[0] if people else None, said.get("text") or "", at)
        return [(None, graph) for graph in self.prose.emit(prose)]

    def say_to(self, store, channel: str, text: str) -> bool:
        found = rows(store, _ID_Q, graphs_of(store, BELIEF, common=True), chat=channel)
        if not found:
            return False
        reply = self.call(self._method("sendMessage"), {"chat_id": found[0]["id"], "text": text})
        if not reply.get("ok", True):
            log.warning("telegram would not take a message for %s: %s", local_of(channel), reply.get("description", reply))
            return False
        return True
