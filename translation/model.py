"""The model client: the one place this repository asks a language model, over its own HTTP, and only
from a process of the world at a run-time edge — never from an agent.

**ONE CALL, TWO SHAPES OF ANSWER.** `ask` sends a system prompt and one message to the Messages API
and reads the content back: text, where the model was asked to write prose, and tool calls, where it
was handed tools — each a name and the input it filled. The translator hands it the sayables as tools
and reads the one it chose; a rendering is asked with no tool and read as text.

**NO LIBRARY.** The request is `urllib`, as the HTTP transport's is: a JSON body, three headers, one
endpoint. A library would be a dependency the image never carries for one POST; and a test hands
`post` of its own and sees exactly what would be sent.

**WHICH MODEL AND WHERE IS ENVIRONMENT**, a deployment fact and no belief anyone holds (rule 5):
`MODEL_API_KEY`, `MODEL_NAME`, and `MODEL_URL` where the endpoint is not the default. The key lives
in `infra/secrets/`, beside the admin token, and reaches the translator alone.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass, field

log = logging.getLogger("model")

DEFAULT_URL = "https://api.anthropic.com"
VERSION = "2023-06-01"
#  HOW LONG ONE CALL MAY TAKE, in real seconds.
TIMEOUT_S = 60.0


@dataclass
class Answer:
    """What the model answered: the text it wrote, and each tool it called with the input it filled."""
    text: str = ""
    calls: list[tuple[str, dict]] = field(default_factory=list)


def _post(url: str, headers: dict, body: bytes) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:          # noqa: S310 — the installation's endpoint
        return json.loads(response.read())


class Model:
    """A language model reached over the Messages API: which, where, and with what key."""

    def __init__(self, name: str, key: str, url: str = DEFAULT_URL, post=None, max_tokens: int = 1024):
        self.name, self.key, self.url = name, key, url.rstrip("/")
        self.post = post or _post
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

    def ask(self, system: str, text: str, tools=(), tool_choice: str | None = None) -> Answer:
        """One call: `system` as the system prompt, `text` as the one user message, `tools` offered
        where given — the model then MUST call one (`tool_choice` names which, or any) — and the
        answer read as text and calls."""
        body: dict = {"model": self.name, "max_tokens": self.max_tokens, "system": system,
                      "messages": [{"role": "user", "content": text}]}
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = {"type": "any"} if tool_choice is None else {"type": "tool", "name": tool_choice}
        headers = {"x-api-key": self.key, "anthropic-version": VERSION, "content-type": "application/json"}
        reply = self.post(self.url + "/v1/messages", headers, json.dumps(body).encode())
        answer = Answer()
        for block in reply.get("content", []):
            if block.get("type") == "text":
                answer.text += block.get("text", "")
            elif block.get("type") == "tool_use":
                answer.calls.append((block.get("name", ""), dict(block.get("input") or {})))
        return answer
