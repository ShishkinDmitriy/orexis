"""Translation's part over its test world: a person's prose on a chat's channel becomes a statement the agent hears
and believes, or a question answered from its account; what the agent says to a person is rendered and sent back on
the chat's channel; and in a group with several agents, an agent answers when it is named or when its account speaks
to an unnamed question, and keeps silent otherwise."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import BELIEF
from agent.runtime import Runtime, boot
from agent.speech.events import Told
from agent.speech.ontology import STATEMENT_GRAPH
from agent.store import graphs_of, rows
from agent.translation.create import ACCOUNT_SYSTEM, HEAR_SYSTEM, SAY_SYSTEM, SILENT, UNADDRESSED
from agent.translation.model import Answer
from agent.translation.sayable import NOTHING, document_of, sayables
from agent.transport.transport import Prose, Transport

WORLD = Path(__file__).parent / "world"
V = "http://example.org/orexis/world/viewing#"
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
SEEKER = V + "seeker"


class Bot(Transport):
    """A member standing for every carrier: what it is handed it says as `prose`, and what is said to a channel it
    keeps."""

    def __init__(self):
        self.prose = Signal("prose")
        self.said: list[tuple[str, str]] = []

    def handle(self, store, channel, payload, at, *, memo=None):
        said = json.loads(payload)
        return [(None, g) for g in self.prose.emit(Prose(channel, said.get("from"), said["text"], at))]

    def say_to(self, store, channel, text):
        self.said.append((channel, text))
        return True


@dataclass
class StandIn:
    """A model that answers what the test says: a tool call where tools are offered, text otherwise."""
    call: tuple | None = None
    text: str = ""
    asked: list = field(default_factory=list)

    def ask(self, system, text, tools=(), tool_choice=None):
        self.asked.append((system, text, [t["name"] for t in tools]))
        return Answer("" if tools else self.text, [self.call] if self.call and tools else [])


@pytest.fixture
def seeker(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    bot = Bot()
    runtime = Runtime(boot(WORLD, "seeker"), "seeker", transport=bot)
    part = runtime.parts["translation"]
    part.spawn = lambda work: work()
    return runtime, part, bot


def _write(runtime, channel: str, text: str, sender: str | None = None):
    runtime.deliver(channel, json.dumps({"from": sender, "text": text}).encode(), NOW)
    runtime.run(passes=1, poll_s=0)


def test_a_persons_prose_becomes_a_statement_the_agent_hears_and_believes(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(call=("ViewingOffer", {"listing": "the two-room flat on Kastanienallee", "at": "2026-11-02T18:00:00+00:00"}))
    _write(runtime, V + "clara_telegram", "I can show you Kastanienallee on Tuesday the 2nd at 6pm. Clara")
    (system, text, offered), = part.model.asked
    assert system == HEAR_SYSTEM and text.startswith("From Clara:") and NOTHING in offered and "ViewingOffer" in offered
    beliefs = runtime.beliefs
    assert graphs_of(beliefs, STATEMENT_GRAPH), "kept as a peer's document"
    found = rows(beliefs, "PREFIX : <http://example.org/orexis/world/viewing#>\n"
                          "SELECT ?l ?by WHERE { ?o a :ViewingOffer ; :listing ?l ; speech:saidBy ?by }", graphs_of(beliefs, BELIEF))
    assert found == [{"l": V + "flat_12", "by": V + "clara"}], "and believed of it by the extraction"
    assert bot.said == [], "a statement is answered by nothing"


def test_account_is_answered_for_nothing_and_a_question_from_the_account_by_the_model(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(call=(NOTHING, {"why": "a question"}), text="The seeker observes nothing yet.")
    _write(runtime, V + "clara_telegram", "/account")
    assert part.model.asked == [], "a command costs nothing"
    (channel, said), = bot.said
    assert channel == V + "clara_telegram" and said.startswith("seeker at 2026-11-01 09:00 UTC") and "nothing to say yet" in said
    bot.said.clear()
    _write(runtime, V + "clara_telegram", "what are you doing?")
    assert [a[0] for a in part.model.asked] == [HEAR_SYSTEM, ACCOUNT_SYSTEM], "no sayable filled, so a question"
    assert "nothing to say yet" in part.model.asked[1][1] and "what are you doing?" in part.model.asked[1][1]
    assert bot.said == [(V + "clara_telegram", "The seeker observes nothing yet.")]


def test_in_a_group_an_agent_answers_when_named_keeps_silent_when_another_is_and_says_nothing_it_does_not_know(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "keeper, is the door locked?", V + "anna")
    assert part.model.asked == [] and bot.said == [], "words to another agent of the chat"
    _write(runtime, V + "household_telegram", "seeker, how is the search going?", V + "anna")
    assert [a[0] for a in part.model.asked] == [HEAR_SYSTEM, ACCOUNT_SYSTEM], "named: a sayable first, then the account, nobody else's"
    assert bot.said == [(V + "household_telegram", "I am looking at two flats.")]
    bot.said.clear()
    part.model = StandIn(text=SILENT)
    _write(runtime, V + "household_telegram", "is anyone watching the plants?", V + "clara")
    (system, text, offered), = part.model.asked
    assert system == ACCOUNT_SYSTEM + UNADDRESSED and offered == [], "unnamed in a group: no sayable, the account alone"
    assert bot.said == [], "its account does not speak to it, so it keeps silent"
    _write(runtime, V + "household_telegram", "hello?", V + "nobody")
    assert len(part.model.asked) == 1, "someone the chat names not is not heard"


def test_what_the_agent_says_to_a_person_is_rendered_and_sent_through_their_chat(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="Dear Clara, could I view the studio on Rigaer Straße? Weekday evenings suit me. — seeker")
    request = next(s for s in sayables(runtime.beliefs) if s.name == "ViewingRequest")
    statement = document_of(request, {"listing": "the studio on Rigaer Straße", "hours": "weekday evenings"}, by=SEEKER, prose="", at=NOW)
    part.told(Told(V + "clara", statement))
    runtime.run(passes=1, poll_s=0)
    (system, text, _), = part.model.asked
    assert system == SAY_SYSTEM and "To: Clara" in text and "hours: weekday evenings" in text
    assert bot.said == [(V + "clara_telegram", part.model.text)], "her own chat, not the household's group she is in too"
    part.told(Told(V + "keeper", statement))
    assert len(part.model.asked) == 1, "a document to an agent is the bus's, not translation's"
