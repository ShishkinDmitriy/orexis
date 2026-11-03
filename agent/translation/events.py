"""What translation says happened — the events its part's signals carry, and what of each is reported or journaled.

`Translated` only metrics hears, so it is made only where heard: one use of the model, a person's message answered
over a conversation's requests or an agent's statement rendered in one, with what it spent by the API's own names —
which is how an admin sees what an agent's chats cost, on the dashboard drawn from this class.

`Conversed` only the journal hears: a person's message and the conversation it began, in translation's words — the
chat, the person, what they wrote, each tool the model called with what it was handed and what it was answered, and
the words said back — so what a chat heard and said, and how the answer was found, can be read afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.journal import literal
from agent.metrics import Tag, Value

TRANSLATION = "http://example.org/orexis/translation#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
#  HOW MUCH OF A TOOL'S ANSWER IS JOURNALED: a vocabulary or fifty rows is kept whole, and a longer answer says it was cut.
RESULT_CHARS = 8000


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


@dataclass(frozen=True)
class Conversed:
    """A person's message answered: the chat, the person, what they wrote, each tool call as (tool, what it was
    handed, what it answered), the words said back where any were, how it ended and the model, at `at`."""
    chat: str
    person: str
    wrote: str
    calls: tuple = ()
    answer: str | None = None
    outcome: str | None = None
    model: str | None = None
    at: datetime | None = None

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the conversation, its chat and person, what was written and answered, and each call."""
        def said(name, value):
            return ox.Triple(node, ox.NamedNode(TRANSLATION + name), value)
        out = [ox.Triple(node, _TYPE, ox.NamedNode(TRANSLATION + "Conversed")),
               said("chat", ox.NamedNode(self.chat)), said("person", ox.NamedNode(self.person)),
               said("wrote", literal(self.wrote))]
        out += [said(name, literal(value)) for name, value in
                (("answer", self.answer), ("outcome", self.outcome), ("model", self.model)) if value]
        for order, (tool, handed, answered) in enumerate(self.calls):
            call = ox.BlankNode()
            text = answered if len(answered) <= RESULT_CHARS else answered[:RESULT_CHARS] + " [cut]"
            out += [said("call", call),
                    ox.Triple(call, ox.NamedNode(TRANSLATION + "order"), literal(order)),
                    ox.Triple(call, ox.NamedNode(TRANSLATION + "tool"), literal(tool)),
                    ox.Triple(call, ox.NamedNode(TRANSLATION + "handed"),
                              literal(json.dumps(handed, ensure_ascii=False, sort_keys=True))),
                    ox.Triple(call, ox.NamedNode(TRANSLATION + "answered"), literal(text))]
        return out
