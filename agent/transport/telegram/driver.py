"""The Telegram driver: an agent's own bot, answering the transport family's contract over the Bot API.

**THE BOT IS THE AGENT'S.** It is the account the agent speaks through on Telegram (`telegram:hasBot`), its token
`TELEGRAM_BOT_TOKEN` and where the API answers `TELEGRAM_URL`, both environment, the standard library alone between
them. A group with several agents holds several bots, each its agent's, so each speaks in its own name.

**IT POLLS.** `start` asks the runtime to ask `getUpdates` every `TELEGRAM_POLL_S` real seconds, from the offset after
the last update seen, on a thread of its own; every text message is handed to the runtime as a job, its channel the
chat's id. `handle` finds the `telegram:Chat` the world names by that id, the person by the user id they wrote as
where the world states it, and says `prose`; a chat the world names none of is nobody's, dropped and said once.

**IT SAYS WHOM A GROUP'S WORDS WERE FOR**, as Telegram tells it: words that tag the bot (`@its_username`, or a
command sent `/status@its_username`) or reply to one of its messages are addressed to this agent; words that tag or
reply to someone else and not the bot are addressed to them. Which account is the bot's own is asked of the API
(`getMe`) before the first poll, since the interpreter can know it and no document need say it. In a chat with
one person every word is the agent's, and nothing is said.

**IT SENDS.** `say_to` posts `sendMessage` to a chat the world names by its id, as a reply to the message it names
where it names one, and is False for any other channel; `writing_in` posts `sendChatAction` with
`typing` there, which Telegram shows for five seconds or until the message.
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
        self.bot: tuple[str, str] | None = None                # the bot's own user id and username, by `getMe`

    @classmethod
    def connect(cls, me: str, deliver=None, *, environ=None, client=None) -> "Telegram":
        env = os.environ if environ is None else environ
        token = env.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("no TELEGRAM_BOT_TOKEN in the environment — this agent speaks through a bot and holds "
                               "no token for it; write secrets/<agent>/telegram.env and regenerate the compose file")
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

    def whoami(self) -> tuple[str, str]:
        """The bot's own user id and username, asked of the API once."""
        if self.bot is None:
            reply = self.call(self._method("getMe"), {})
            found = (reply.get("result") or {}) if reply.get("ok", True) else {}
            if "id" not in found:
                raise RuntimeError(f"getMe told nothing of the bot: {reply.get('description', reply)}")
            self.bot = (str(found["id"]), str(found.get("username") or "").lower())
        return self.bot

    def updates(self) -> list[tuple[str, bytes]]:
        """Every text message since the last poll, as its chat's id and `{"from": user id, "text": …, "addressed": …,
        "message": its id}`; an update that is no text message is passed over, and every update seen is confirmed by
        the next poll's offset."""
        self.whoami()
        body = {"timeout": 0, "allowed_updates": ["message"]}
        if self.offset is not None:
            body["offset"] = self.offset
        reply = self.call(self._method("getUpdates"), body)
        out = []
        for update in reply.get("result", []) if reply.get("ok", True) else []:
            self.offset = max(self.offset or 0, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or {}
            text, chat = message.get("text"), message.get("chat") or {}
            if text and chat.get("id") is not None:
                sender, number = (message.get("from") or {}).get("id"), message.get("message_id")
                out.append((str(chat["id"]), json.dumps({
                    "from": str(sender) if sender is not None else None, "text": text.strip(),
                    "addressed": None if chat.get("type") == "private" else self.addressed(message),
                    "message": str(number) if number is not None else None}).encode()))
        return out

    def addressed(self, message: dict) -> bool | None:
        """Whom a group's message was for: True where it tags the bot or replies to it, False where it tags or replies
        to someone else and not the bot, None where it does neither. An entity's offset and length are in UTF-16 code
        units, as the Bot API counts them."""
        me, username = self.whoami()
        units = (message.get("text") or "").encode("utf-16-le")
        mine = other = False
        for entity in message.get("entities") or []:
            start, length = int(entity.get("offset", 0)), int(entity.get("length", 0))
            piece = units[2 * start:2 * (start + length)].decode("utf-16-le", errors="replace")
            if entity.get("type") == "text_mention":
                tagged = str((entity.get("user") or {}).get("id")) == me
            elif entity.get("type") == "mention":
                tagged = piece.lstrip("@").lower() == username
            elif entity.get("type") == "bot_command" and "@" in piece:
                tagged = piece.split("@", 1)[1].lower() == username
            else:
                continue
            mine, other = mine or tagged, other or not tagged
        replied = (message.get("reply_to_message") or {}).get("from") or {}
        if "id" in replied:
            to_me = str(replied["id"]) == me
            mine, other = mine or to_me, other or not to_me
        return True if mine else False if other else None

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
        prose = Prose(chats[0], people[0] if people else None, said.get("text") or "", at,
                      addressed=said.get("addressed"), message=said.get("message"))
        return [(None, graph) for graph in self.prose.emit(prose)]

    def say_to(self, store, channel: str, text: str, *, reply: str | None = None) -> bool:
        body = {"text": text}
        if reply is not None:
            body["reply_parameters"] = {"message_id": int(reply), "allow_sending_without_reply": True}
        return self._post(store, channel, "sendMessage", body)

    def writing_in(self, store, channel: str) -> bool:
        return self._post(store, channel, "sendChatAction", {"action": "typing"})

    def _post(self, store, channel: str, method: str, body: dict) -> bool:
        """`method` posted to the chat the world names `channel` by its id; False where it names none, or the API
        refuses or fails."""
        found = rows(store, _ID_Q, graphs_of(store, BELIEF, common=True), chat=channel)
        if not found:
            return False
        try:
            answer = self.call(self._method(method), {"chat_id": found[0]["id"], **body})
        except Exception as exc:                                         # noqa: BLE001 — the api fails
            log.warning("%s: the bot would not answer %s: %s", local_of(self.me), method, exc)
            return False
        if not answer.get("ok", True):
            log.warning("telegram would not take a %s for %s: %s", method, local_of(channel), answer.get("description", answer))
            return False
        return True
