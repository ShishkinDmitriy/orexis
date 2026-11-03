"""Translation's part over its test world: a person's prose on a chat's channel becomes a statement the agent hears
and believes, or a question answered in a conversation the model is briefed for, calling as many askables as it
needs; what the agent says to a person is rendered and sent back on
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
from agent.translation.create import CONVERSE_SYSTEM, SAY_SYSTEM, SILENT, TURNS, UNADDRESSED, WRITING_S
from agent.translation.model import Answer, Turn
from agent.translation.sayable import document_of, sayables
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
    """A model that answers what the test says: a turn calling each of `calls` in order, while tools are offered and
    the turn is not the last, then `text`; and `text` to a rendering asked in one call."""
    calls: list = field(default_factory=list)
    text: str = ""
    asked: list = field(default_factory=list)

    def converse(self, system, messages, tools=(), *, last=False):
        self.asked.append((list(system), list(messages), [t["name"] for t in tools]))
        n = sum(1 for m in messages if m["role"] == "assistant")
        if n < len(self.calls) and tools and not last:
            name, inputs = self.calls[n]
            return Turn("", [(f"call{n}", name, inputs)], [{"type": "tool_use", "id": f"call{n}", "name": name, "input": inputs}])
        return Turn(self.text, [], [{"type": "text", "text": self.text}])

    def ask(self, system, text, tools=()):
        self.asked.append((system, text, []))
        return Answer(self.text)


def _results(messages) -> list[str]:
    """What each tool call was answered with, in the order the conversation handed them back."""
    return [block["content"] for m in messages if m["role"] == "user" and isinstance(m["content"], list)
            for block in m["content"]]


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
    part.model = StandIn(calls=[("ViewingOffer", {"listing": "the two-room flat on Kastanienallee", "at": "2026-11-02T18:00:00+00:00"})],
                         text="Thank you, Clara: Tuesday at six.")
    _write(runtime, V + "clara_telegram", "I can show you Kastanienallee on Tuesday the 2nd at 6pm. Clara")
    (system, messages, offered), (_, after, _) = part.model.asked
    assert system[0] == CONVERSE_SYSTEM and messages[0]["content"].startswith("From Clara:")
    assert {"ViewingOffer", "viewings_offered"} <= set(offered), "every sayable and every askable, in one conversation"
    beliefs = runtime.beliefs
    assert graphs_of(beliefs, STATEMENT_GRAPH), "kept as a peer's document"
    found = rows(beliefs, "PREFIX : <http://example.org/orexis/world/viewing#>\n"
                          "SELECT ?l ?by WHERE { ?o a :ViewingOffer ; :listing ?l ; speech:saidBy ?by }", graphs_of(beliefs, BELIEF))
    assert found == [{"l": V + "flat_12", "by": V + "clara"}], "and believed of it by the extraction"
    assert _results(after) == ["kept: the agent believes it now"]
    assert bot.said == [(V + "clara_telegram", "Thank you, Clara: Tuesday at six.")], "and the model says so"


def test_the_model_is_briefed_with_who_the_agent_is_what_the_chat_reads_and_what_it_holds_now(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="I am the seeker; I look for a flat.")
    _write(runtime, V + "clara_telegram", "who are you?")
    ((instructions, who, now), messages, offered), = part.model.asked
    assert instructions == CONVERSE_SYSTEM and who.startswith("YOU SPEAK FOR seeker.")
    assert "WHAT THIS CHAT LETS YOU READ" in who and " - speech (" in who, "the vocabularies by name, loaded on asking"
    assert now.startswith("WHAT IT HOLDS NOW") and "nothing to say yet" in now, "and its status, apart"
    assert {"vocabulary", "query"} <= set(offered), "Clara's chat reads the beliefs, so the model may too"
    assert bot.said == [(V + "clara_telegram", "I am the seeker; I look for a flat.")], "answered with no tool called"


def test_the_model_loads_a_vocabulary_and_queries_what_the_chat_reads(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(calls=[("vocabulary", {"name": "speech"}),
                                ("query", {"sparql": "SELECT ?c WHERE { ?c a speech:Chat }", "kinds": ["orexis:BeliefGraph"]}),
                                ("query", {"sparql": "SELECT * WHERE { SERVICE <http://elsewhere.example/> { ?s ?p ?o } }",
                                           "kinds": ["orexis:BeliefGraph"]})],
                         text="We speak here, and in three other chats.")
    _write(runtime, V + "clara_telegram", "in which chats are you?")
    vocabulary, chats, refused = _results(part.model.asked[-1][1])
    assert "speech:Chat" in vocabulary and "seeker_and_clara" in chats and "household" in chats
    assert refused.startswith("refused: it holds a SERVICE clause")
    assert bot.said == [(V + "clara_telegram", "We speak here, and in three other chats.")]


def test_a_chat_reading_nothing_offers_no_query(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "seeker, how is the search going?", V + "anna")
    (_, who, _), _, offered = part.model.asked[0]
    assert "vocabulary" not in offered and "query" not in offered and "beyond the questions offered as tools" in who


def test_status_is_answered_for_nothing(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="unused")
    _write(runtime, V + "clara_telegram", "/status")
    assert part.model.asked == [], "a command costs nothing"
    (channel, said), = bot.said
    assert channel == V + "clara_telegram" and said == "seeker at 2026-11-01 09:00 UTC\nnothing to say yet", \
        "the one askable takes a field, so no section"


def test_a_question_is_answered_by_as_many_askables_as_it_needs_and_their_rows_handed_back(seeker):
    """Clara offers a viewing, which the seeker comes to believe; Anna asks about two flats, and the model calls the
    domain's askable for each, over two turns, the seeker answering each from its store, then answers in words.
    Nothing is written by the questions."""
    runtime, part, bot = seeker
    part.model = StandIn(calls=[("ViewingOffer", {"listing": "the two-room flat on Kastanienallee", "at": "2026-11-02T18:00:00+00:00"})])
    _write(runtime, V + "clara_telegram", "I can show you Kastanienallee on Tuesday the 2nd at 6pm.")
    before = len(runtime.beliefs)
    part.model = StandIn(calls=[("viewings_offered", {"listing": "the two-room flat on Kastanienallee"}),
                                ("viewings_offered", {"listing": "the studio on Rigaer Straße"})],
                         text="Kastanienallee on Tuesday at 18:00; nothing yet for the studio.")
    _write(runtime, V + "clara_telegram", "when can I see Kastanienallee, and the studio?")
    assert len(part.model.asked) == 3, "a turn for each call, then the words"
    found, none = _results(part.model.asked[-1][1])
    assert "at: 2026-11-02 18:00 UTC, by: clara" in found and none == "(no rows)", (found, none)
    assert bot.said[-1] == (V + "clara_telegram", "Kastanienallee on Tuesday at 18:00; nothing yet for the studio.")
    assert len(runtime.beliefs) == before, "a question writes nothing"


def test_a_conversation_says_what_it_spent_where_it_is_heard(seeker):
    runtime, part, bot = seeker
    heard = []
    part.translated.connect(heard.append)
    part.model = StandIn(calls=[("viewings_offered", {"listing": "the studio on Rigaer Straße"})], text="Nothing yet.")
    _write(runtime, V + "clara_telegram", "anything for the studio?")
    runtime.run(passes=1, poll_s=0)
    (spent,) = heard
    assert (spent.act, spent.outcome, spent.requests) == ("answer", "said", 2.0), spent
    assert spent.input_tokens == 0.0 and spent.duration_s >= 0, "a stand-in spends nothing, and says so"


def test_a_conversation_is_said_with_what_was_written_called_and_answered_where_it_is_heard(seeker):
    runtime, part, bot = seeker
    heard = []
    part.conversed.connect(heard.append)
    part.model = StandIn(calls=[("viewings_offered", {"listing": "the studio on Rigaer Straße"})], text="Nothing yet.")
    _write(runtime, V + "clara_telegram", "anything for the studio?")
    runtime.run(passes=1, poll_s=0)
    (conversed,) = heard
    assert (conversed.wrote, conversed.answer, conversed.outcome) == ("anything for the studio?", "Nothing yet.", "said")
    ((tool, handed, answered),) = conversed.calls
    assert tool == "viewings_offered" and handed == {"listing": "the studio on Rigaer Straße"} and answered


def test_a_conversation_ends_in_words_by_its_last_turn(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(calls=[("viewings_offered", {"listing": "the studio on Rigaer Straße"})] * 10, text="I could not find out.")
    _write(runtime, V + "clara_telegram", "ask until you know")
    assert len(part.model.asked) == TURNS and bot.said == [(V + "clara_telegram", "I could not find out.")]


def test_a_model_that_writes_no_words_is_said_to_have_failed(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="")
    _write(runtime, V + "clara_telegram", "what is the forecast?")
    assert bot.said == [(V + "clara_telegram", "seeker could not answer: its model wrote no words (no reason given).")]


def test_in_a_group_an_agent_answers_when_named_keeps_silent_when_another_is_and_says_nothing_it_does_not_know(seeker):
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "keeper, is the door locked?", V + "anna")
    assert part.model.asked == [] and bot.said == [], "words to another agent of the chat"
    _write(runtime, V + "household_telegram", "seeker, how is the search going?", V + "anna")
    (system, _, offered), = part.model.asked
    assert system[0] == CONVERSE_SYSTEM and "ViewingOffer" in offered, "named: briefed, and every act offered"
    assert bot.said == [(V + "household_telegram", "I am looking at two flats.")]
    bot.said.clear()
    part.model = StandIn(text=SILENT)
    _write(runtime, V + "household_telegram", "is anyone watching the plants?", V + "clara")
    (system, _, offered), = part.model.asked
    assert system[0] == CONVERSE_SYSTEM + UNADDRESSED and offered == ["viewings_offered"], "unnamed in a group: the askables alone"
    assert bot.said == [], "what it holds does not answer it, so it keeps silent"
    _write(runtime, V + "household_telegram", "hello?", V + "nobody")
    assert len(part.model.asked) == 1, "someone the chat names not is not heard"


def test_in_a_group_words_that_tag_or_reply_to_the_agent_are_its_own_and_its_answer_replies_to_them(seeker):
    """The carrier says whom the words were for: tagged or replied to, the seeker hears them as if named — every
    sayable offered — and its answer replies to them; tagging or replying to someone else, it keeps silent, unless it
    is named too."""
    runtime, part, bot = seeker
    part.model = StandIn(text="I am looking at two flats.")
    _write(runtime, V + "household_telegram", "how is the search going?", V + "anna", addressed=False, message="41")
    assert part.model.asked == [] and bot.said == [], "words that tag or reply to someone else"
    _write(runtime, V + "household_telegram", "how is the search going?", V + "anna", addressed=True, message="42")
    (system, _, offered), = part.model.asked
    assert system[0] == CONVERSE_SYSTEM and "ViewingOffer" in offered, "tagged, it is addressed, with no silence asked of it"
    assert bot.said == [(V + "household_telegram", "I am looking at two flats.")] and bot.replies == ["42"]
    _write(runtime, V + "household_telegram", "seeker, and you?", V + "anna", addressed=False, message="43")
    assert len(part.model.asked) == 2 and bot.replies == ["42", "43"], "named in words, it answers whoever was tagged"
    _write(runtime, V + "household_telegram", "/status", V + "anna", addressed=True, message="44")
    assert len(part.model.asked) == 2 and bot.replies[-1] == "44", "a command replies to itself, for nothing"


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
        def converse(self, system, messages, tools=(), *, last=False):
            shown.append((list(bot.writing), dict(part.writing)))
            return super().converse(system, messages, tools, last=last)
    part.model = Slow(calls=[("viewings_offered", {"listing": "the studio on Rigaer Straße"})],
                      text="The seeker has nothing to say yet.")
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
        def converse(self, system, messages, tools=(), *, last=False):
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
