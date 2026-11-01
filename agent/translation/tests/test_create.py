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
from agent.translation.chat import chats_of
from agent.translation.create import ANSWER_SYSTEM, HEAR_SYSTEM, SAY_SYSTEM, SILENT, UNADDRESSED, WRITING_S
from agent.translation.model import Answer
from agent.translation.sayable import document_of, sayables
from agent.translation.shape import NOTHING
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
        self.writing: list[str] = []
        self.replies: list[str | None] = []

    def handle(self, store, channel, payload, at, *, memo=None):
        said = json.loads(payload)
        return [(None, g) for g in self.prose.emit(Prose(channel, said.get("from"), said["text"], at,
                                                         addressed=said.get("addressed"), message=said.get("message")))]

    def say_to(self, store, channel, text, *, reply=None):
        self.said.append((channel, text))
        self.replies.append(reply)
        return True

    def writing_in(self, store, channel):
        self.writing.append(channel)
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


def _write(runtime, channel: str, text: str, sender: str | None = None, **carried):
    runtime.deliver(channel, json.dumps({"from": sender, "text": text, **carried}).encode(), NOW)
    runtime.run(passes=1, poll_s=0)


def test_a_persons_prose_becomes_a_statement_the_agent_hears_and_believes(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(call=("ViewingOffer", {"listing": "the two-room flat on Kastanienallee", "at": "2026-11-02T18:00:00+00:00"}))
    _write(runtime, V + "clara_telegram", "I can show you Kastanienallee on Tuesday the 2nd at 6pm. Clara")
    (system, text, offered), = part.model.asked
    assert system == HEAR_SYSTEM and text.startswith("From Clara:")
    assert {"ViewingOffer", "viewings_offered", NOTHING} <= set(offered), "every sayable and every askable, in one call"
    beliefs = runtime.beliefs
    assert graphs_of(beliefs, STATEMENT_GRAPH), "kept as a peer's document"
    found = rows(beliefs, "PREFIX : <http://example.org/orexis/world/viewing#>\n"
                          "SELECT ?l ?by WHERE { ?o a :ViewingOffer ; :listing ?l ; speech:saidBy ?by }", graphs_of(beliefs, BELIEF))
    assert found == [{"l": V + "flat_12", "by": V + "clara"}], "and believed of it by the extraction"
    assert bot.said == [], "a statement is answered by nothing"


def test_status_is_answered_for_nothing_and_words_that_fit_nothing_from_the_status_by_the_model(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(call=(NOTHING, {"why": "a question"}), text="The seeker has nothing to say yet.")
    _write(runtime, V + "clara_telegram", "/status")
    assert part.model.asked == [], "a command costs nothing"
    (channel, said), = bot.said
    assert channel == V + "clara_telegram" and said == "seeker at 2026-11-01 09:00 UTC\nnothing to say yet", \
        "the one askable takes a field, so no section"
    bot.said.clear()
    _write(runtime, V + "clara_telegram", "what are you doing?")
    assert [a[0] for a in part.model.asked] == [HEAR_SYSTEM, ANSWER_SYSTEM], "nothing fits, so the status answers"
    assert "nothing to say yet" in part.model.asked[1][1] and "what are you doing?" in part.model.asked[1][1]
    assert bot.said == [(V + "clara_telegram", "The seeker has nothing to say yet.")]


def test_a_question_an_askable_fits_is_answered_by_its_select_and_the_rows_phrased(seeker):
    """Clara offers a viewing, which the seeker comes to believe; Anna asks when she can see the flat, the model
    calls the domain's askable with the listing, the seeker answers it from its store, and the model phrases the
    rows. Nothing is written by the question."""
    runtime, part, bot = seeker
    part.model = StandIn(call=("ViewingOffer", {"listing": "the two-room flat on Kastanienallee", "at": "2026-11-02T18:00:00+00:00"}))
    _write(runtime, V + "clara_telegram", "I can show you Kastanienallee on Tuesday the 2nd at 6pm.")
    before = len(runtime.beliefs)
    part.model = StandIn(call=("viewings_offered", {"listing": "the two-room flat on Kastanienallee"}),
                         text="Clara offered a viewing on Tuesday 2 November at 18:00.")
    _write(runtime, V + "clara_telegram", "when can I see Kastanienallee?")
    (hear, _, offered), (answer, rows, tools) = part.model.asked
    assert (hear, answer, tools) == (HEAR_SYSTEM, ANSWER_SYSTEM, []) and "viewings_offered" in offered
    assert "at: 2026-11-02 18:00 UTC, by: clara" in rows and "when can I see Kastanienallee?" in rows, rows
    assert bot.said == [(V + "clara_telegram", "Clara offered a viewing on Tuesday 2 November at 18:00.")]
    assert len(runtime.beliefs) == before, "a question writes nothing"


def test_in_a_group_an_agent_answers_when_named_keeps_silent_when_another_is_and_says_nothing_it_does_not_know(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "keeper, is the door locked?", V + "anna")
    _write(runtime, V + "household_telegram", "Kim, is the door locked?", V + "anna")
    assert part.model.asked == [] and bot.said == [], "words to another agent of the chat, by its id or its name"
    _write(runtime, V + "household_telegram", "seeker, how is the search going?", V + "anna")
    assert [a[0] for a in part.model.asked] == [HEAR_SYSTEM, ANSWER_SYSTEM], "named: one call, and nothing fits, so the status"
    assert bot.said == [(V + "household_telegram", "I am looking at two flats.")]
    bot.said.clear()
    part.model = StandIn(text=SILENT)
    _write(runtime, V + "household_telegram", "is anyone watching the plants?", V + "clara")
    (system, text, offered), = part.model.asked
    assert system == HEAR_SYSTEM and offered == ["viewings_offered", NOTHING], "unnamed in a group: the askables alone"
    assert bot.said == [], "no askable fits, so it keeps silent"
    part.model = StandIn(call=("viewings_offered", {"listing": "the studio on Rigaer Straße"}), text=SILENT)
    _write(runtime, V + "household_telegram", "is the studio still free?", V + "clara")
    assert [a[0] for a in part.model.asked] == [HEAR_SYSTEM, ANSWER_SYSTEM + UNADDRESSED] and bot.said == [], \
        "its rows do not answer it, so it keeps silent"
    _write(runtime, V + "household_telegram", "hello?", V + "nobody")
    assert len(part.model.asked) == 2, "someone the chat names not is not heard"


def test_in_a_group_words_that_tag_or_reply_to_the_agent_are_its_own_and_its_answer_replies_to_them(seeker):
    """The carrier says whom the words were for: tagged or replied to, the seeker hears them as if named — every
    sayable offered, and the status answering where nothing fits — and its answer replies to them; tagging or
    replying to someone else, it keeps silent, unless it is named too."""
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "how is the search going?", V + "anna", addressed=False, message="41")
    assert part.model.asked == [] and bot.said == [], "words that tag or reply to someone else"
    _write(runtime, V + "household_telegram", "how is the search going?", V + "anna", addressed=True, message="42")
    (hear, _, offered), (answer, _, _) = part.model.asked
    assert (hear, answer) == (HEAR_SYSTEM, ANSWER_SYSTEM) and "ViewingOffer" in offered, \
        "tagged, it is addressed: the sayables are offered and the status answers, with no silence asked of it"
    assert bot.said == [(V + "household_telegram", "I am looking at two flats.")] and bot.replies == ["42"]
    _write(runtime, V + "household_telegram", "seeker, and you?", V + "anna", addressed=False, message="43")
    assert len(part.model.asked) == 4 and bot.replies == ["42", "43"], "named in words, it answers whoever was tagged"
    _write(runtime, V + "household_telegram", "/status", V + "anna", addressed=True, message="44")
    assert len(part.model.asked) == 4 and bot.replies[-1] == "44", "a command replies to itself, for nothing"


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


def test_the_person_sees_the_agent_writing_from_the_words_heard_to_the_answer_said(seeker):
    runtime, part, bot = seeker
    shown = []

    class Slow(StandIn):
        def ask(self, system, text, tools=(), tool_choice=None):
            shown.append((list(bot.writing), dict(part.writing)))
            return super().ask(system, text, tools, tool_choice)
    part.model = Slow(call=(NOTHING, {"why": "a question"}), text="The seeker has nothing to say yet.")
    _write(runtime, V + "clara_telegram", "what are you doing?")
    assert [w for w, _ in shown] == [[V + "clara_telegram"]] * 2, "shown before the model is asked"
    assert all(len(p) == 1 for _, p in shown), "and still while the model answers"
    assert bot.said == [(V + "clara_telegram", "The seeker has nothing to say yet.")] and part.writing == {}, \
        "and shown no more once the answer is said"
    part.model = StandIn(text=SILENT)
    _write(runtime, V + "household_telegram", "is anyone watching the plants?", V + "clara")
    assert bot.writing == [V + "clara_telegram"], "unaddressed in a group the agent may keep silent, so it shows nothing"


def test_an_answer_still_thought_is_shown_again_every_while(seeker):
    runtime, part, bot = seeker
    chat = next(c for c in chats_of(runtime.beliefs) if c.channel == V + "clara_telegram")
    part.writing[chat.iri] = [chat, 1]
    part._still_writing()
    assert bot.writing == [V + "clara_telegram"] and WRITING_S < 5, "within the five seconds Telegram shows it for"


def test_a_model_that_fails_says_so_in_the_chat_where_the_agent_was_addressed(seeker, caplog):
    runtime, part, bot = seeker

    class Refusing(StandIn):
        def ask(self, system, text, tools=(), tool_choice=None):
            raise OSError("HTTP Error 401: Unauthorized")
    part.model = Refusing()
    _write(runtime, V + "clara_telegram", "what are you doing?")
    runtime.run(passes=1, poll_s=0)
    assert bot.said == [(V + "clara_telegram", "seeker could not answer: its model would not answer "
                                               "(HTTP Error 401: Unauthorized).")]
    assert part.writing == {} and "could not answer Clara" in caplog.text
    bot.said.clear()
    _write(runtime, V + "household_telegram", "is anyone watching the plants?", V + "clara")
    runtime.run(passes=1, poll_s=0)
    assert bot.said == [], "unaddressed in a group, a failure is the log's alone"
