"""A carrier: what reaches a person through a chat's channel — polled for what they wrote, and sent what an
agent says. The translator knows no carrier by name: it is handed each with `poll` and `send`, and picks
one by the channel's type (knowledge/domain/speech/chat.md).

**EMAIL, OVER THE STANDARD LIBRARY.** `Email` reads unseen messages over IMAP and sends over SMTP, the
account's address and credential in this process's own variables — `MAIL_ADDRESS`, `MAIL_PASSWORD`,
`MAIL_IMAP_HOST` and `MAIL_SMTP_HOST`, `MAIL_IMAP_PORT` and `MAIL_SMTP_PORT` where not the defaults —
and no library beyond `imaplib`, `smtplib` and `email`. A message is its sender's address and its
plain text; one that carries no plain text is dropped, said in the log.

**TELEGRAM, OVER THE BOT API.** `Telegram` is the translator's bot: `poll` asks `getUpdates` from the
offset after the last update it saw and answers each text message as its chat's id and its text, `send`
posts `sendMessage` to a chat. The token is `TELEGRAM_BOT_TOKEN`, the one secret, and where the API
answers is `TELEGRAM_URL`, the bot's `schema:url` in the world's deployment graph as `orexis-compose`
tells it (`translation/telegram.ttl`); the HTTP call is injected as the model's is, so a test hands a
stand-in.

**A MEMORY CARRIER FOR A TEST**: what it was handed is what it polls, and what it sent is kept.
"""

from __future__ import annotations

import email
import email.utils
import imaplib
import json
import logging
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

log = logging.getLogger("carrier")


class Memory:
    """A carrier a test fills: `inbox` is polled once, `sent` holds what was sent."""

    def __init__(self, inbox=()):
        self.inbox: list[tuple[str, str]] = list(inbox)
        self.sent: list[tuple[str, str]] = []

    def poll(self) -> list[tuple[str, str]]:
        out, self.inbox = list(self.inbox), []
        return out

    def send(self, address: str, text: str) -> None:
        self.sent.append((address, text))


def _text_of(message) -> str | None:
    """The plain text of a message, or None where it carries none."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition", "").startswith("attachment"):
                return part.get_content().strip()
        return None
    if message.get_content_type() == "text/plain":
        return message.get_content().strip()
    return None


class Email:
    """A mailbox read over IMAP and written over SMTP, as the environment names it."""

    def __init__(self, address: str, password: str, imap_host: str, smtp_host: str,
                 imap_port: int = 993, smtp_port: int = 465):
        self.address, self.password = address, password
        self.imap_host, self.imap_port, self.smtp_host, self.smtp_port = imap_host, imap_port, smtp_host, smtp_port

    @classmethod
    def from_environ(cls, environ=None) -> "Email | None":
        env = os.environ if environ is None else environ
        needed = ("MAIL_ADDRESS", "MAIL_PASSWORD", "MAIL_IMAP_HOST", "MAIL_SMTP_HOST")
        if not all(env.get(k) for k in needed):
            log.warning("no mailbox: %s are not all set", ", ".join(needed))
            return None
        return cls(env["MAIL_ADDRESS"], env["MAIL_PASSWORD"], env["MAIL_IMAP_HOST"], env["MAIL_SMTP_HOST"],
                   int(env.get("MAIL_IMAP_PORT", "993")), int(env.get("MAIL_SMTP_PORT", "465")))

    def poll(self) -> list[tuple[str, str]]:
        """Every unseen message, as its sender's address and its plain text, each marked seen."""
        out: list[tuple[str, str]] = []
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as box:
            box.login(self.address, self.password)
            box.select("INBOX")
            status, found = box.search(None, "UNSEEN")
            for number in (found[0].split() if status == "OK" and found and found[0] else []):
                status, data = box.fetch(number, "(RFC822)")
                if status != "OK" or not data or not isinstance(data[0], tuple):
                    continue
                message = email.message_from_bytes(data[0][1], policy=email.policy.default)
                sender = email.utils.parseaddr(message.get("From", ""))[1]
                text = _text_of(message)
                if sender and text:
                    out.append((sender, text))
                else:
                    log.warning("a message from %r carries no plain text: dropped", sender or "nobody")
                box.store(number, "+FLAGS", "\\Seen")
        return out

    def send(self, address: str, text: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.address, address, "From your agent"
        message.set_content(text)
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as mail:
            mail.login(self.address, self.password)
            mail.send_message(message)


TELEGRAM_URL = "https://api.telegram.org"
TIMEOUT_S = 30.0


def _call(url: str, body: dict | None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers={"content-type": "application/json"}, method="POST" if data else "GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:          # noqa: S310 — the bot's api
        return json.loads(response.read())


class Telegram:
    """The translator's bot on Telegram: polled for what the people wrote, told what the agents say.
    `call(url, body)` is the HTTP call, injected for a test."""

    def __init__(self, token: str, url: str = TELEGRAM_URL, call=None):
        self.token, self.url, self.call = token, url.rstrip("/"), call or _call
        self.offset: int | None = None

    @classmethod
    def from_environ(cls, environ=None) -> "Telegram | None":
        """The bot the environment names: its token, and where the API answers — `TELEGRAM_URL`, the world's
        deployment fact as `orexis-compose` tells it, or Telegram's own where none is told."""
        env = os.environ if environ is None else environ
        if not env.get("TELEGRAM_BOT_TOKEN"):
            log.warning("no telegram bot: TELEGRAM_BOT_TOKEN is not set")
            return None
        return cls(env["TELEGRAM_BOT_TOKEN"], env.get("TELEGRAM_URL") or TELEGRAM_URL)

    def _method(self, name: str) -> str:
        return f"{self.url}/bot{self.token}/{name}"

    def poll(self) -> list[tuple[str, str]]:
        """Every text message since the last poll, as its chat's id and its text; an update that is no text
        message is passed over, and every update seen is confirmed by the next poll's offset."""
        body = {"timeout": 0, "allowed_updates": ["message"]}
        if self.offset is not None:
            body["offset"] = self.offset
        reply = self.call(self._method("getUpdates"), body)
        out: list[tuple[str, str]] = []
        for update in reply.get("result", []) if reply.get("ok", True) else []:
            self.offset = max(self.offset or 0, int(update.get("update_id", 0)) + 1)
            message = update.get("message") or {}
            text, chat = message.get("text"), (message.get("chat") or {}).get("id")
            if text and chat is not None:
                out.append((str(chat), text.strip()))
            else:
                log.info("an update from chat %r carries no text: passed over", chat)
        return out

    def send(self, chat: str, text: str) -> None:
        reply = self.call(self._method("sendMessage"), {"chat_id": chat, "text": text})
        if not reply.get("ok", True):
            log.warning("telegram would not take a message for chat %s: %s", chat, reply.get("description", reply))
