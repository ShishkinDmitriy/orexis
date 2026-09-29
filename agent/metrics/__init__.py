"""How the agent is doing, told to whoever administers it — the metamodel every package's events
speak (`model.py`), the window they are tallied in (`window.py`), and the part that hears every
signal where a metrics sink is loaded (`create.py`).

METRICS ARE THE ADMINS' INSTRUMENTATION OF THE AGENT — code watching code, not a description of
anything — so they live in code and nowhere in the model. A package reports by EVENTS it already
says: each event class it declares in `agent/<package>/events.py` names its measurement and marks
the fields that are reported (`Tag`, `Value`, `Flag`, `Level`), and the metrics part, linked to
every part, tallies whatever it hears. No package imports anything of this but the marks, and
nothing here names a package's word; `orexis-dashboards` draws what the events declare.
"""

from .model import FLAG, LEVEL, TAG, VALUE, Flag, Laps, Level, Tag, Value, counted, fields_of, marked, measurement, reported  # noqa: F401
