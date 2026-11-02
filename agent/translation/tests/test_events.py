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
