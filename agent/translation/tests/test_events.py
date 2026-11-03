"""What translation says happened: one use of the model, counted, tagged by what it did and how it ended, with
the requests and the tokens it spent as values the metrics part aggregates."""

from __future__ import annotations

from agent.metrics.model import TAG, VALUE, counted, fields_of, measurement
from agent.translation.events import Translated
from agent.translation.model import TOKENS


def test_a_use_of_the_model_is_counted_by_act_outcome_and_model_with_what_it_spent():
    assert measurement(Translated) == "translated" and counted(Translated)
    assert fields_of(Translated, TAG) == ("act", "outcome", "model")
    assert fields_of(Translated, VALUE) == ("requests", *TOKENS, "duration_s"), "the tokens by the API's own names"


def test_a_conversation_is_journaled_with_each_call_in_order_and_is_no_metric():
    from datetime import datetime, timezone

    import pyoxigraph as ox

    from agent.translation.events import RESULT_CHARS, TRANSLATION, Conversed
    assert measurement(Conversed) is None, "the journal's alone"
    event = Conversed("urn:chat", "urn:anna", "how dry is it?",
                      (("query", {"sparql": "ASK {}"}, "true"), ("series", {}, "x" * (RESULT_CHARS + 5))),
                      "It is dry.", "said", "claude", datetime(2026, 11, 3, tzinfo=timezone.utc))
    store = ox.Store()
    node = ox.NamedNode("urn:uuid:one")
    store.extend(ox.Quad(t.subject, t.predicate, t.object) for t in event.statements(node))
    rows = list(store.query(f"""PREFIX t: <{TRANSLATION}>
        SELECT ?wrote ?answer ?tool ?handed ?answered WHERE {{ ?c a t:Conversed ; t:wrote ?wrote ; t:answer ?answer ;
          t:call ?k . ?k t:order ?o ; t:tool ?tool ; t:handed ?handed ; t:answered ?answered }} ORDER BY ?o"""))
    assert [(r["tool"].value, r["handed"].value) for r in rows] == [("query", '{"sparql": "ASK {}"}'), ("series", "{}")]
    assert rows[0]["wrote"].value == "how dry is it?" and rows[0]["answer"].value == "It is dry."
    assert rows[1]["answered"].value.endswith(" [cut]") and len(rows[1]["answered"].value) == RESULT_CHARS + 6
