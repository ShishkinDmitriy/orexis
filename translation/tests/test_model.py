"""The model client: what one call sends to the Messages API, and how an answer is read back."""

from __future__ import annotations

import json

from translation.model import DEFAULT_URL, VERSION, Answer, Model


def _reply(*blocks):
    return {"content": list(blocks)}


def test_a_call_sends_the_prompt_the_message_and_the_tools_and_reads_the_calls_back():
    sent = {}

    def post(url, headers, body):
        sent.update(url=url, headers=headers, body=json.loads(body))
        return _reply({"type": "text", "text": "ok"},
                      {"type": "tool_use", "name": "ViewingOffer", "input": {"listing": "the flat", "at": "2026-11-02T18:00:00+00:00"}})

    model = Model("claude-x", "k3y", post=post)
    answer = model.ask("system", "hello", tools=[{"name": "ViewingOffer", "input_schema": {"type": "object"}}])
    assert sent["url"] == DEFAULT_URL + "/v1/messages"
    assert sent["headers"] == {"x-api-key": "k3y", "anthropic-version": VERSION, "content-type": "application/json"}
    assert sent["body"] == {"model": "claude-x", "max_tokens": 1024, "system": "system",
                            "messages": [{"role": "user", "content": "hello"}],
                            "tools": [{"name": "ViewingOffer", "input_schema": {"type": "object"}}],
                            "tool_choice": {"type": "any"}}
    assert answer == Answer("ok", [("ViewingOffer", {"listing": "the flat", "at": "2026-11-02T18:00:00+00:00"})])


def test_a_call_with_no_tool_offers_none_and_reads_the_text():
    seen = []
    model = Model("m", "k", url="https://proxy.example/", post=lambda u, h, b: seen.append(json.loads(b)) or _reply({"type": "text", "text": "Dear Anna"}))
    assert model.ask("s", "t") == Answer("Dear Anna", [])
    assert "tools" not in seen[0] and "tool_choice" not in seen[0]
    assert model.url == "https://proxy.example"


def test_the_environment_names_the_model_or_there_is_none():
    assert Model.from_environ({}) is None
    assert Model.from_environ({"MODEL_API_KEY": "k"}) is None
    model = Model.from_environ({"MODEL_API_KEY": "k", "MODEL_NAME": "claude-x", "MODEL_URL": "https://a.example"})
    assert (model.name, model.key, model.url) == ("claude-x", "k", "https://a.example")
