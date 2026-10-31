"""The Telegram carrier over a stand-in for the Bot API: what it polls, how it confirms what it saw, and
what it sends; and that it is none without a token."""

from __future__ import annotations

from translation.carrier import Telegram


class Api:
    """A Bot API that answers what the test says and keeps every call."""

    def __init__(self, updates=()):
        self.updates, self.calls = list(updates), []

    def __call__(self, url, body):
        self.calls.append((url, body))
        if url.endswith("/getUpdates"):
            since = body.get("offset", 0)
            return {"ok": True, "result": [u for u in self.updates if u["update_id"] >= since]}
        return {"ok": True, "result": {"message_id": 1}}


def _message(update_id, chat, text=None, **more):
    message = {"chat": {"id": chat}, **more}
    if text is not None:
        message["text"] = text
    return {"update_id": update_id, "message": message}


def test_a_poll_answers_each_text_message_by_its_chat_and_confirms_what_it_saw():
    api = Api([_message(10, 4815162342, "Sorry, it went to another applicant."), _message(11, 4815162342, photo=[{}]),
               _message(12, 777, "  any evening  "), {"update_id": 13, "edited_message": {"chat": {"id": 777}, "text": "x"}}])
    bot = Telegram("123:abc", "https://api.telegram.org/", api)
    assert bot.poll() == [("4815162342", "Sorry, it went to another applicant."), ("777", "any evening")]
    assert api.calls[0] == ("https://api.telegram.org/bot123:abc/getUpdates", {"timeout": 0, "allowed_updates": ["message"]})
    assert bot.offset == 14, "every update seen, text or not, is confirmed by the next offset"
    assert bot.poll() == [] and api.calls[-1][1]["offset"] == 14


def test_a_message_is_sent_to_the_chat_by_its_id():
    api = Api()
    Telegram("123:abc", call=api).send("4815162342", "Dear Clara, could I view the studio?")
    assert api.calls == [("https://api.telegram.org/bot123:abc/sendMessage", {"chat_id": "4815162342", "text": "Dear Clara, could I view the studio?"})]


def test_no_token_is_no_bot(caplog):
    assert Telegram.from_environ({}) is None and "TELEGRAM_BOT_TOKEN" in caplog.text
    bot = Telegram.from_environ({"TELEGRAM_BOT_TOKEN": "123:abc"}, url="https://tg.example/")
    assert bot is not None and bot.url == "https://tg.example"
