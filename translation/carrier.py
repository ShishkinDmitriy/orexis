"""A carrier: what reaches a person — their address polled for what they wrote, and their address sent what
an agent says. The translator knows no carrier: it is handed one with `poll` and `send`.

**EMAIL, OVER THE STANDARD LIBRARY.** `Email` reads unseen messages over IMAP and sends over SMTP, the
account's address and credential in this process's own variables — `MAIL_ADDRESS`, `MAIL_PASSWORD`,
`MAIL_IMAP_HOST` and `MAIL_SMTP_HOST`, `MAIL_IMAP_PORT` and `MAIL_SMTP_PORT` where not the defaults —
and no library beyond `imaplib`, `smtplib` and `email`. A message is its sender's address and its
plain text; one that carries no plain text is dropped, said in the log.

**A MEMORY CARRIER FOR A TEST**: what it was handed is what it polls, and what it sent is kept.
"""

from __future__ import annotations

import email
import email.utils
import imaplib
import logging
import os
import smtplib
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
