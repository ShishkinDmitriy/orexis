"""The model client: what one call hands the SDK, how an answer is read back, and how a failure is said."""

from __future__ import annotations

from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest

from agent.translation.model import DEFAULT_URL, RETRIES, TIMEOUT_S, Answer, Model, why_not


class Client:
    """The SDK's client as the model calls it: `messages.create` keeps what it was handed and answers `blocks`."""

    def __init__(self, *blocks):
        self.sent: list[dict] = []
        self.messages = SimpleNamespace(create=lambda **body: self.sent.append(body) or SimpleNamespace(content=list(blocks)))


def test_a_call_sends_the_prompt_the_message_and_the_tools_and_reads_the_calls_back():
    client = Client(SimpleNamespace(type="text", text="ok"),
                    SimpleNamespace(type="tool_use", name="ViewingOffer", input={"listing": "the flat", "at": "2026-11-02T18:00:00+00:00"}))
    model = Model("claude-x", "k3y", client=client)
    answer = model.ask("system", "hello", tools=[{"name": "ViewingOffer", "input_schema": {"type": "object"}}])
    assert client.sent == [{"model": "claude-x", "max_tokens": 1024, "system": "system",
                            "messages": [{"role": "user", "content": "hello"}],
                            "tools": [{"name": "ViewingOffer", "input_schema": {"type": "object"}}],
                            "tool_choice": {"type": "auto"}}]
    assert answer == Answer("ok", [("ViewingOffer", {"listing": "the flat", "at": "2026-11-02T18:00:00+00:00"})])


def test_a_call_with_no_tool_offers_none_and_reads_the_text():
    client = Client(SimpleNamespace(type="text", text="Dear Anna"))
    model = Model("m", "k", url="https://proxy.example/", client=client)
    assert model.ask("s", "t") == Answer("Dear Anna", [])
    assert "tools" not in client.sent[0] and "tool_choice" not in client.sent[0]
    assert model.url == "https://proxy.example"


def test_the_sdks_client_is_told_the_key_the_endpoint_the_timeout_and_the_retries():
    client = Model("m", "k3y", url="https://proxy.example/").client
    assert (client.api_key, str(client.base_url).rstrip("/"), client.timeout, client.max_retries) == \
        ("k3y", "https://proxy.example", TIMEOUT_S, RETRIES)


def test_the_environment_names_the_model_or_there_is_none():
    assert Model.from_environ({}) is None
    assert Model.from_environ({"MODEL_API_KEY": "k"}) is None
    model = Model.from_environ({"MODEL_API_KEY": "k", "MODEL_NAME": "claude-x", "MODEL_URL": "https://a.example"})
    assert (model.name, model.key, model.url) == ("claude-x", "k", "https://a.example")
    assert Model.from_environ({"MODEL_API_KEY": "k", "MODEL_NAME": "m"}).url == DEFAULT_URL


def _status(cls, code):
    request = httpx.Request("POST", DEFAULT_URL + "/v1/messages")
    return cls("refused", response=httpx.Response(code, request=request), body=None)


@pytest.mark.parametrize(("failure", "said"), [
    (_status(anthropic.AuthenticationError, 401), "its model refused its key"),
    (_status(anthropic.RateLimitError, 429), "its model is asked too often just now; try again in a minute"),
    (_status(anthropic.InternalServerError, 529), "its model is overloaded just now; try again in a minute"),
    (anthropic.APIConnectionError(request=httpx.Request("POST", DEFAULT_URL)), "its model could not be reached"),
    (OSError("boom"), "its model would not answer (boom)"),
])
def test_a_failure_is_said_by_its_class_in_a_persons_terms(failure, said):
    assert why_not(failure) == said
