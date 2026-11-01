"""The email transport's part: brought up from the environment, then started — attached, held, and polling."""

from __future__ import annotations

import pytest

from agent.transport.email import create as creating
from agent.transport.email.driver import Email

TEST = "http://example.org/test#"
MAILBOX = {"MAIL_ADDRESS": "keeper@example.org", "MAIL_PASSWORD": "p", "MAIL_IMAP_HOST": "imap.example.org",
           "MAIL_SMTP_HOST": "smtp.example.org", "MAIL_POLL_S": "45"}


class Runtime:
    me, beliefs = TEST + "keeper", None

    def __init__(self):
        self.timers, self.attached, self.held = [], [], []

    def every(self, seconds, job):
        self.timers.append((seconds, job))

    def submit(self, job):
        pass

    def attach(self, member):
        self.attached.append(member)

    def hold(self, who):
        self.held.append(who)


def test_create_brings_the_mailbox_up_and_start_polls_it(monkeypatch):
    for name, value in MAILBOX.items():
        monkeypatch.setenv(name, value)
    runtime = Runtime()
    part = creating.create(runtime)
    assert isinstance(part, Email) and part.box.address == "keeper@example.org"
    part.start(runtime)
    assert runtime.timers == [(45.0, part.poll)] and runtime.attached == [part] and runtime.held == [part]


def test_create_refuses_where_the_environment_names_no_mailbox(monkeypatch):
    for name in MAILBOX:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="no mailbox in the environment"):
        creating.create(Runtime())
