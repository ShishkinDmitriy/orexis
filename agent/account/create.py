"""`create`: the account part — created where the self plays `account:Reporter`.

LINKED, it keeps every part that has something to say of itself (`account()`, answering lines); STARTED, it hears
the runtime's pass end and, when the text the parts answer differs from the last it published, publishes it
retained on the topic the agent `account:accountsOn`, through the transport, as `{"account": text, "at": now}`. A
quiet agent costs the bus nothing, and a reader that restarts finds the latest without asking.
"""

from __future__ import annotations

import logging

from agent.ontology import BELIEF, SELF_GRAPH, local_of
from agent.store import graphs_of, rows

log = logging.getLogger("account")

#  WHAT EACH PART'S SECTION IS CALLED, in the person's words: the package's name where none is given.
_SECTIONS = {"sensing": "observes", "planning": "wants", "execution": "does"}
_TOPIC_Q = "SELECT ?topic WHERE { ?me a orexis:Self ; account:accountsOn ?topic }"


class _Account:
    def __init__(self, runtime):
        self.runtime = runtime
        self.parts: dict[str, object] = {}
        self.last: str | None = None

    def link(self, parts) -> None:
        self.parts = {name: part for name, part in parts.items() if callable(getattr(part, "account", None))}
        self.runtime.passed.connect(self._passed)

    def text(self) -> str:
        """The account as it stands: a heading with who and when, then each part's section, or that there is
        nothing to say yet."""
        head = f"{local_of(self.runtime.me)} at {self.runtime.now.isoformat(timespec='minutes')}"
        sections = []
        for name, part in self.parts.items():
            lines = part.account()
            if lines:
                sections.append(f"{_SECTIONS.get(name, name)}:\n" + "\n".join(f" - {line}" for line in lines))
        return head + "\n" + ("\n".join(sections) if sections else "nothing to say yet")

    def _passed(self, passed):
        text = self.text()
        if text.split("\n", 1)[1:] == (self.last or "\n").split("\n", 1)[1:]:
            return []                                       # the heading's instant alone moved
        beliefs = self.runtime.beliefs
        topics = [r["topic"] for r in rows(beliefs, _TOPIC_Q, [*graphs_of(beliefs, BELIEF, common=True), *graphs_of(beliefs, SELF_GRAPH)])]
        transport = self.runtime.transport
        if not topics or transport is None:
            log.warning("%s accounts on no topic, or over no transport: its account goes nowhere", local_of(self.runtime.me))
            return []
        if transport.publish_on(beliefs, topics[0], {"account": text, "at": self.runtime.now.isoformat()}, retain=True):
            self.last = text
            log.info("%s gave an account of itself", local_of(self.runtime.me))
        return []


def create(runtime) -> _Account:
    """The account part: what the parts say of the agent, published retained when it changes."""
    return _Account(runtime)
