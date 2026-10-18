"""`create`: the prediction package's part (a-package-starts-itself) — the agent's foresight, offered to
whoever lays the grounds. It hears nothing and writes nothing: the flows are integrated from each
ground as the planner lays them (a-flow-is-integrated-where-the-ground-is-laid, #1000), so what this
part has to offer is `foresee`, the integration made fresh from the belief base at the start of a pass,
and the planner's part takes it at link, through the runtime, with neither package importing the other —
as the executor takes the planner's signals (planning-and-execution-meet-at-the-store).

It answered every percept and every belief written by rewriting the forecasts of every key (#996); a
forecast of the predictor's own is no longer a graph of the belief base, so there is nothing to answer
with, and a planner that is no predictor is handed none and foresees nothing.
"""

from __future__ import annotations

from .foresee import foresee


class _Prediction:
    def foresee(self, beliefs, now, *, placed=None):
        """The agent's foresight from `now`, off `beliefs` — `foresee`'s answer, for the planner to
        advance ground by ground; None where no key is moved by any flow."""
        return foresee(beliefs, now, placed=placed)


def create(runtime) -> _Prediction:
    """The prediction package's part: its foresight, offered at link."""
    return _Prediction()
