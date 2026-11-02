"""The email driver: an agent's own mailbox, answering the transport family's contract over IMAP and SMTP.

**THE MAILBOX IS THE AGENT'S**, named by `MAIL_ADDRESS`, `MAIL_PASSWORD`, `MAIL_IMAP_HOST` and `MAIL_SMTP_HOST`, with
`MAIL_IMAP_PORT` and `MAIL_SMTP_PORT` where not 993 and 465, and no library beyond `imaplib`, `smtplib` and
`email`. **IT POLLS** every `MAIL_POLL_S` real seconds on a thread of its own, every unseen message with a plain
text handed to the runtime as a job, its channel the sender's address; `handle` finds the contact point the world
names by that address and says `prose`. **IT SENDS** to a contact point's address by `say_to`.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import imaplib
import logging
import os
import smtplib
import threading
from email.message import EmailMessage

import pyoxigraph as ox

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import BELIEF, local_of
from agent.store import graphs_of, rows
from agent.transport.transport import Prose, Transport

log = logging.getLogger("email")

POLL_S = 30.0

_CONTACT_Q = "SELECT ?contact WHERE { ?contact schema:email ?address FILTER (LCASE(STR(?address)) = LCASE($address)) }"
_ADDRESS_Q = "SELECT ?address WHERE { $contact schema:email ?address }"


def _text_of(message) -> str | None:
    """The plain text of a message, or None where it carries none."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition", "").startswith("attachment"):
                return part.get_content().strip()
        return None
    return message.get_content().strip() if message.get_content_type() == "text/plain" else None


class Mailbox:
    """A mailbox over the standard library, as the environment names it: `fetch` the unseen, `send` one."""

    def __init__(self, address, password, imap_host, smtp_host, imap_port=993, smtp_port=465):
        self.address, self.password = address, password
        self.imap_host, self.imap_port, self.smtp_host, self.smtp_port = imap_host, imap_port, smtp_host, smtp_port

    def fetch(self) -> list[tuple[str, str]]:
        out = []
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as box:
            box.login(self.address, self.password)
            box.select("INBOX")
            status, found = box.search(None, "UNSEEN")
            for number in (found[0].split() if status == "OK" and found and found[0] else []):
                status, data = box.fetch(number, "(RFC822)")
                if status == "OK" and data and isinstance(data[0], tuple):
                    message = email.message_from_bytes(data[0][1], policy=email.policy.default)
                    sender, text = email.utils.parseaddr(message.get("From", ""))[1], _text_of(message)
                    if sender and text:
                        out.append((sender, text))
                box.store(number, "+FLAGS", "\\Seen")
        return out

    def send(self, to: str, text: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.address, to, "From your agent"
        message.set_content(text)
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as mail:
            mail.login(self.address, self.password)
            mail.send_message(message)


class Email(Transport):
    """One agent's mailbox: polled for what is written to it, told what the agent says, over a `box` with `fetch`
    and `send`."""

    def __init__(self, me: str, box, spawn=None, deliver=None, every: float = POLL_S):
        self.me, self.box = me, box
        self.spawn = spawn or (lambda work: threading.Thread(target=work, daemon=True).start())
        self.deliver = deliver or (lambda *message: None)
        self.every = every
        self.prose = Signal("prose")
        self._unknown: set[str] = set()

    @classmethod
    def connect(cls, me: str, deliver=None, *, environ=None, client=None) -> "Email":
        env = os.environ if environ is None else environ
        needed = ("MAIL_ADDRESS", "MAIL_PASSWORD", "MAIL_IMAP_HOST", "MAIL_SMTP_HOST")
        if client is None and not all(env.get(k) for k in needed):
            raise RuntimeError(f"no mailbox in the environment: {', '.join(needed)} — write secrets/<agent>/mail.env "
                               "and regenerate the compose file")
        box = client or Mailbox(env["MAIL_ADDRESS"], env["MAIL_PASSWORD"], env["MAIL_IMAP_HOST"], env["MAIL_SMTP_HOST"],
                                int(env.get("MAIL_IMAP_PORT") or 993), int(env.get("MAIL_SMTP_PORT") or 465))
        return cls(me, box, deliver=deliver, every=float(env.get("MAIL_POLL_S") or POLL_S))

    def start(self, runtime) -> None:
        super().start(runtime)
        runtime.every(self.every, self.poll)

    def poll(self) -> list[str]:
        def ask():
            try:
                for sender, text in self.box.fetch():
                    self.deliver(sender, text.encode(), clock.now())
            except Exception as exc:                                     # noqa: BLE001 — the mailbox fails
                log.warning("%s: the mailbox would not answer: %s", local_of(self.me), exc)
        self.spawn(ask)
        return []

    def handle(self, store, channel: str, payload: bytes, at, *, memo=None) -> list[tuple[str | None, str]]:
        found = [r["contact"] for r in rows(store, _CONTACT_Q, graphs_of(store, BELIEF, common=True), address=ox.Literal(channel))]
        if not found:
            if channel not in self._unknown:
                self._unknown.add(channel)
                log.warning("%s: mail from %s, whom the world names in no chat: dropped", local_of(self.me), channel)
            return []
        prose = Prose(found[0], None, payload.decode("utf-8", errors="replace"), at)
        return [(None, graph) for graph in self.prose.emit(prose)]

    def say_to(self, store, channel: str, text: str, *, reply: str | None = None) -> bool:
        found = rows(store, _ADDRESS_Q, graphs_of(store, BELIEF, common=True), contact=channel)
        if not found:
            return False
        self.box.send(found[0]["address"], text)
        return True
