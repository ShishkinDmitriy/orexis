"""What translation says happened — the event its part's signal carries, and what of it is reported.

`Translated` only metrics hears, so it is made only where heard: one use of the model, a person's message answered
over a conversation's requests or an agent's statement rendered in one, with what it spent by the API's own names —
which is how an admin sees what an agent's chats cost, on the dashboard drawn from this class.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.metrics import Tag, Value


@dataclass(frozen=True)
class Translated:
    """One use of the model: a person's message answered (`answer`) or an agent's statement rendered (`render`),
    whether it ended in words, in silence, in no words or in the model failing; the requests it made, the tokens
    they spent by the API's own names, and its real seconds."""
    metric = "translated"
    act: Tag = None
    outcome: Tag = None
    model: Tag = None
    requests: Value = None
    input_tokens: Value = None
    cache_creation_input_tokens: Value = None
    cache_read_input_tokens: Value = None
    output_tokens: Value = None
    duration_s: Value = None
