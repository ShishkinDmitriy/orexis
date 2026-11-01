"""The Telegram transport's part: brought up from the environment, then started — attached, held, and polling."""

from __future__ import annotations

import pytest

from agent.transport.telegram import create as creating
from agent.transport.telegram.driver import Telegram

TEST = "http://example.org/test#"


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


def test_create_brings_the_bot_up_and_start_polls_it(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_POLL_S", "4")
    runtime = Runtime()
    part = creating.create(runtime)
    assert isinstance(part, Telegram) and part.me == runtime.me
    part.start(runtime)
    assert runtime.timers == [(4.0, part.poll)] and runtime.attached == [part] and runtime.held == [part]


def test_create_refuses_where_the_environment_holds_no_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="no TELEGRAM_BOT_TOKEN"):
        creating.create(Runtime())
