"""The model client: the one place this repository asks a language model, through Anthropic's SDK, and only
from an agent's translation part, off its pass, at a run-time edge.

**A CONVERSATION, AND ONE CALL.** `converse` sends a system prompt in blocks, all but the last cached, and the
messages so far, with tools the model may call: the translator answers a person's words over as many turns
as the model's tool calls need, handing back each call's result, until it answers in text
(knowledge/domain/translation/briefing.md). `ask` is one call of one message, read as text — a statement
rendered for a person.

**THE SDK, FOR WHAT ONE POST DOES NOT DO.** It was one `urllib` POST, and a person in a chat met every
overloaded or rate-limited moment of the API as "could not answer". The client retries those and a
dropped connection with backoff, `RETRIES` times, and names each failure by its class, which `why_not`
says in the chat in the person's terms; the library is translation's own extra, so only a translating
agent's image carries it. A test hands a `client` of its own and sees exactly what would be sent.

**WHICH MODEL AND WHERE IS ENVIRONMENT**, a deployment fact and no belief anyone holds (rule 5):
`MODEL_API_KEY`, `MODEL_NAME`, and `MODEL_URL` where the endpoint is not the default. The key lives
in `infra/secrets/`, beside the admin token, and reaches each translating agent's container alone.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import anthropic

log = logging.getLogger("model")

DEFAULT_URL = "https://api.anthropic.com"
#  HOW LONG ONE CALL MAY TAKE, in real seconds, and how often an overloaded, rate-limited or unreachable API is
#  asked again, with the SDK's backoff between.
TIMEOUT_S = 60.0
RETRIES = 3


@dataclass
class Answer:
    """What the model answered: the text it wrote, and each tool it called with the input it filled."""
    text: str = ""
    calls: list[tuple[str, dict]] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)


#  WHAT A TURN SPENT, by the API's own names: fresh input, input written to and read from the cache, and output.
TOKENS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


@dataclass
class Turn:
    """One turn of a conversation: the text the model wrote, each tool it called as its id, name and input, and
    the content to hand back as the assistant's message when the calls are answered, and why the model stopped."""
    text: str = ""
    calls: list[tuple[str, str, dict]] = field(default_factory=list)
    content: list[dict] = field(default_factory=list)
    stop: str = ""
    tokens: dict[str, int] = field(default_factory=dict)


class Model:
    """A language model reached over the Messages API: which, where, and with what key."""

    def __init__(self, name: str, key: str, url: str = DEFAULT_URL, client=None, max_tokens: int = 1024):
        self.name, self.key, self.url = name, key, url.rstrip("/")
        self.client = client or anthropic.Anthropic(api_key=key, base_url=self.url, timeout=TIMEOUT_S, max_retries=RETRIES)
        self.max_tokens = max_tokens

    @classmethod
    def from_environ(cls, environ=None) -> "Model | None":
        """The model the environment names, or None where it names none: a translator with no model
        hears nothing and says nothing, and says so once."""
        env = os.environ if environ is None else environ
        key, name = env.get("MODEL_API_KEY"), env.get("MODEL_NAME")
        if not key or not name:
            log.warning("no model: MODEL_API_KEY and MODEL_NAME are not both set")
            return None
        return cls(name, key, env.get("MODEL_URL", DEFAULT_URL))

    def ask(self, system: str, text: str, tools=()) -> Answer:
        """One call: `system` as the system prompt, `text` as the one user message, `tools` offered
        where given — the model chooses whether to call one, since a model that thinks refuses to be
        made to, and the system prompt asks it to — and the answer read as text and calls."""
        body: dict = {"model": self.name, "max_tokens": self.max_tokens, "system": system,
                      "messages": [{"role": "user", "content": text}]}
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = {"type": "auto"}
        reply = self.client.messages.create(**body)
        answer = Answer(tokens=_tokens(reply))
        for block in reply.content:
            if block.type == "text":
                answer.text += block.text
            elif block.type == "tool_use":
                answer.calls.append((block.name, dict(block.input or {})))
        return answer


    def converse(self, system: list[str], messages: list[dict], tools=(), *, last: bool = False) -> Turn:
        """One turn: `system` as blocks, every one but the last cached — the instructions and the briefing's world
        change when a document does, its status with every reading — `messages` so far, and `tools` the model may
        call, none where this is the `last` turn, so it answers in text."""
        blocks = [{"type": "text", "text": text} for text in system if text]
        if len(blocks) > 1:
            blocks[-2]["cache_control"] = {"type": "ephemeral"}
        body: dict = {"model": self.name, "max_tokens": self.max_tokens, "system": blocks, "messages": _cached(messages)}
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = {"type": "none" if last else "auto"}
        reply = self.client.messages.create(**body)
        turn = Turn(stop=str(getattr(reply, "stop_reason", "") or ""), tokens=_tokens(reply))
        for block in reply.content:
            if block.type == "text":
                turn.text += block.text
                turn.content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                turn.calls.append((block.id, block.name, dict(block.input or {})))
                turn.content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": dict(block.input or {})})
        return turn


def _tokens(reply) -> dict[str, int]:
    """What one request spent, by the API's own names; nought for a name its reply does not carry."""
    usage = getattr(reply, "usage", None)
    return {k: int(getattr(usage, k, 0) or 0) for k in TOKENS}


def _cached(messages: list[dict]) -> list[dict]:
    """The conversation with its last block marked for the cache, so the next turn reads all of it from there and
    pays in full only for what it adds — a copy, since a mark left behind on every turn would pass the API's four."""
    if not messages:
        return messages
    last = dict(messages[-1])
    content = last["content"]
    blocks = [{"type": "text", "text": content}] if isinstance(content, str) else [dict(b) for b in content]
    blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return [*messages[:-1], {**last, "content": blocks}]


def why_not(exc: Exception) -> str:
    """Why the model would not answer, in a person's terms: by the SDK's class of the failure, its retries spent."""
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return "its model refused its key"
    if isinstance(exc, anthropic.RateLimitError):
        return "its model is asked too often just now; try again in a minute"
    if isinstance(exc, anthropic.InternalServerError):
        return "its model is overloaded just now; try again in a minute"
    if isinstance(exc, anthropic.APIConnectionError):
        return "its model could not be reached"
    return f"its model would not answer ({exc})"
