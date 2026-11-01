"""The Telegram driver over a stand-in Bot API: what `getUpdates` answers becomes a chat's id and the words with the
user who wrote them, the offset moving past every update seen; a message is said as `prose` in the chat the world
names by that id, by the person who writes as that user; a chat the world names none of is dropped and said once;
and what the agent says goes to `sendMessage` with the chat's id."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.transport.telegram.driver import Telegram
from agent.transport.transport import Transport

WORLD = Path(__file__).parent / "worlds" / "a_chat_on_telegram.trig"
TEST = "http://example.org/test#"


class Api:
    """The Bot API as the driver calls it: `getUpdates` answers what is queued and forgets it, anything else is kept."""

    def __init__(self, *updates):
        self.updates, self.calls = list(updates), []

    def __call__(self, url, body):
        self.calls.append((url.rsplit("/", 1)[-1], body))
        if url.endswith("/getUpdates"):
            found, self.updates = self.updates, []
            return {"ok": True, "result": found}
        return {"ok": True, "result": {}}


def _message(update_id, chat, text, user=111):
    return {"update_id": update_id, "message": {"chat": {"id": chat}, "from": {"id": user}, "text": text}}


@pytest.fixture
def bot(snapshots):
    api = Api()
    driver = Telegram(TEST + "keeper", "123:abc", call=api, spawn=lambda work: work())
    heard = []
    driver.prose.connect(lambda prose: heard.append(prose) or [])
    return snapshots.stand_in(WORLD), driver, api, heard


def test_the_driver_answers_the_familys_contract(bot):
    _, driver, _, _ = bot
    assert isinstance(driver, Transport)


def test_updates_are_each_text_message_by_its_chats_id_and_the_offset_moves_past_them(bot):
    _, driver, api, _ = bot
    api.updates = [_message(10, 4242, " hello "), {"update_id": 11, "edited_message": {}}, _message(12, -100, "hi all", 222)]
    assert driver.updates() == [("4242", json.dumps({"from": "111", "text": "hello"}).encode()),
                                ("-100", json.dumps({"from": "222", "text": "hi all"}).encode())]
    assert driver.updates() == []
    assert [body.get("offset") for name, body in api.calls] == [None, 13], "every update seen is confirmed by the next poll"
    assert {name for name, _ in api.calls} == {"getUpdates"}


def test_a_poll_delivers_each_message_to_the_container(bot):
    _, driver, api, _ = bot
    delivered = []
    driver.deliver = lambda *message: delivered.append(message[:2])
    api.updates = [_message(1, 4242, "hello")]
    assert driver.poll() == []
    assert delivered == [("4242", json.dumps({"from": "111", "text": "hello"}).encode())]


def test_a_message_is_prose_in_the_chat_the_world_names_by_its_id_by_the_person_writing_as_the_user(bot, snapshots):
    store, driver, _, heard = bot
    before = len(store)
    assert driver.handle(store, "4242", json.dumps({"from": "111", "text": "hello"}).encode(), snapshots.NOW) == []
    assert driver.handle(store, "-100", json.dumps({"from": "999", "text": "who am I"}).encode(), snapshots.NOW) == []
    assert [(p.channel, p.sender, p.text) for p in heard] == [(TEST + "anna_telegram", TEST + "anna", "hello"),
                                                              (TEST + "household_telegram", None, "who am I")], \
        "a user the world names nobody by is no sender"
    assert len(store) == before


def test_a_chat_the_world_names_none_of_is_dropped_and_said_once(bot, snapshots, caplog):
    store, driver, _, heard = bot
    for _ in range(2):
        assert driver.handle(store, "777", json.dumps({"from": "111", "text": "hi"}).encode(), snapshots.NOW) == []
    assert heard == [] and caplog.text.count("Telegram chat 777") == 1


def test_what_the_agent_says_goes_to_send_message_with_the_chats_id(bot):
    store, driver, api, _ = bot
    assert driver.say_to(store, TEST + "anna_telegram", "the fern is dry") is True
    assert api.calls == [("sendMessage", {"chat_id": "4242", "text": "the fern is dry"})]
    assert driver.say_to(store, TEST + "anna_mail", "x") is False, "a channel that is no Telegram chat is not this member's"


def test_connect_refuses_an_agent_with_no_token():
    with pytest.raises(RuntimeError, match="no TELEGRAM_BOT_TOKEN"):
        Telegram.connect(TEST + "keeper", environ={})
    driver = Telegram.connect(TEST + "keeper", environ={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_URL": "https://bots.example/",
                                                       "TELEGRAM_POLL_S": "5"})
    assert (driver.url, driver.every) == ("https://bots.example", 5.0)
