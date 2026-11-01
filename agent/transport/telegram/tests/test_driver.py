"""The Telegram driver over a stand-in Bot API: what `getUpdates` answers becomes a chat's id and the words with the
user who wrote them, the offset moving past every update seen; a message is said as `prose` in the chat the world
names by that id, by the person who writes as that user; a chat the world names none of is dropped and said once;
in a group, words that tag the bot or reply to it are addressed to the agent and words that tag or reply to someone
else are not, the bot's own account asked of `getMe` once; and what the agent says goes to `sendMessage` with the
chat's id, replying to the message it answers."""

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
        if url.endswith("/getMe"):
            return {"ok": True, "result": {"id": BOT_ID, "is_bot": True, "username": "Keeper_Home_bot"}}
        return {"ok": True, "result": {}}


BOT_ID = 900


def _message(update_id, chat, text, user=111, kind=None, number=None, **more):
    kind = kind or ("private" if chat > 0 else "group")
    return {"update_id": update_id, "message": {"message_id": number or update_id, "chat": {"id": chat, "type": kind},
                                                "from": {"id": user}, "text": text, **more}}


def _said(user, text, addressed=None, message=None):
    return json.dumps({"from": user, "text": text, "addressed": addressed, "message": message}).encode()


def _tag(text, piece, kind="mention", **more):
    """An entity over the first `piece` in `text`, its offset and length in UTF-16 code units as the Bot API counts."""
    start = len(text[:text.index(piece)].encode("utf-16-le")) // 2
    return {"type": kind, "offset": start, "length": len(piece.encode("utf-16-le")) // 2, **more}


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
    assert driver.updates() == [("4242", _said("111", "hello", None, "10")), ("-100", _said("222", "hi all", None, "12"))]
    assert driver.updates() == []
    assert [body.get("offset") for name, body in api.calls if name == "getUpdates"] == [None, 13], \
        "every update seen is confirmed by the next poll"
    assert [name for name, _ in api.calls] == ["getMe", "getUpdates", "getUpdates"], "the bot's own account, asked once"


def test_in_a_group_words_that_tag_the_bot_or_reply_to_it_are_addressed_to_it_and_to_someone_else_not(bot):
    _, driver, api, _ = bot
    tagged = "🌿 @keeper_home_bot is the door locked?"
    other = "@anna_k what do you think?"
    both = "@anna_k and @Keeper_Home_bot, look"
    command = "/status@Keeper_Home_bot"
    api.updates = [
        _message(1, -100, tagged, entities=[_tag(tagged, "@keeper_home_bot")]),
        _message(2, -100, other, entities=[_tag(other, "@anna_k")]),
        _message(3, -100, both, entities=[_tag(both, "@anna_k"), _tag(both, "@Keeper_Home_bot")]),
        _message(4, -100, "is it?", reply_to_message={"message_id": 70, "from": {"id": BOT_ID, "is_bot": True}}),
        _message(5, -100, "is it?", reply_to_message={"message_id": 71, "from": {"id": 222}}),
        _message(6, -100, command, entities=[_tag(command, command, "bot_command")]),
        _message(7, -100, "/status@other_bot", entities=[_tag("/status@other_bot", "/status@other_bot", "bot_command")]),
        _message(8, -100, "Kim, look", entities=[_tag("Kim, look", "Kim", "text_mention", user={"id": BOT_ID})]),
        _message(9, -100, "nobody tagged"),
        _message(10, 4242, "@anna_k said so", entities=[_tag("@anna_k said so", "@anna_k")]),
    ]
    assert [json.loads(payload)["addressed"] for _, payload in driver.updates()] == \
        [True, False, True, True, False, True, False, True, None, None], \
        "a tag of the bot, by any case, or a reply to it is its; one of someone else is theirs; a chat with one person tells nothing"


def test_a_poll_delivers_each_message_to_the_container(bot):
    _, driver, api, _ = bot
    delivered = []
    driver.deliver = lambda *message: delivered.append(message[:2])
    api.updates = [_message(1, 4242, "hello")]
    assert driver.poll() == []
    assert delivered == [("4242", _said("111", "hello", None, "1"))]


def test_a_poll_the_api_will_not_tell_the_bot_to_is_said_and_asked_again(bot, caplog):
    _, driver, api, _ = bot
    driver.call = lambda url, body: {"ok": False, "description": "Unauthorized"}
    assert driver.poll() == [] and driver.bot is None and "Unauthorized" in caplog.text
    driver.call = api
    driver.poll()
    assert driver.bot == (str(BOT_ID), "keeper_home_bot")


def test_a_message_is_prose_in_the_chat_the_world_names_by_its_id_by_the_person_writing_as_the_user(bot, snapshots):
    store, driver, _, heard = bot
    before = len(store)
    assert driver.handle(store, "4242", _said("111", "hello", None, "5"), snapshots.NOW) == []
    assert driver.handle(store, "-100", _said("999", "who am I", True, "6"), snapshots.NOW) == []
    assert [(p.channel, p.sender, p.text, p.addressed, p.message) for p in heard] == [
        (TEST + "anna_telegram", TEST + "anna", "hello", None, "5"),
        (TEST + "household_telegram", None, "who am I", True, "6")], \
        "a user the world names nobody by is no sender, and whom the words were for travels with them"
    assert len(store) == before


def test_a_chat_the_world_names_none_of_is_dropped_and_said_once(bot, snapshots, caplog):
    store, driver, _, heard = bot
    for _ in range(2):
        assert driver.handle(store, "777", _said("111", "hi"), snapshots.NOW) == []
    assert heard == [] and caplog.text.count("Telegram chat 777") == 1


def test_what_the_agent_says_goes_to_send_message_with_the_chats_id(bot):
    store, driver, api, _ = bot
    assert driver.say_to(store, TEST + "anna_telegram", "the fern is dry") is True
    assert driver.say_to(store, TEST + "household_telegram", "it is", reply="42") is True
    assert api.calls == [("sendMessage", {"chat_id": "4242", "text": "the fern is dry"}),
                         ("sendMessage", {"chat_id": "-100", "text": "it is",
                                          "reply_parameters": {"message_id": 42, "allow_sending_without_reply": True}})], \
        "an answer replies to the message it answers, and is sent though that message is gone"
    assert driver.say_to(store, TEST + "anna_mail", "x") is False, "a channel that is no Telegram chat is not this member's"


def test_connect_refuses_an_agent_with_no_token():
    with pytest.raises(RuntimeError, match="no TELEGRAM_BOT_TOKEN"):
        Telegram.connect(TEST + "keeper", environ={})
    driver = Telegram.connect(TEST + "keeper", environ={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_URL": "https://bots.example/",
                                                       "TELEGRAM_POLL_S": "5"})
    assert (driver.url, driver.every) == ("https://bots.example", 5.0)
