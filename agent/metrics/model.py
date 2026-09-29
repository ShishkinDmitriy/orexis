"""What an event's class says of how it is reported — the metamodel every package speaks and the
metrics part reads, so the metrics part knows no package's words and a package names no metric
anywhere but on its own events.

AN EVENT IS REPORTED WHERE ITS CLASS SAYS `metric`, the measurement's name, and marks its fields:

- `Tag`, a string with few values — a desire, a scope, an outcome — by which the window's tallies
  are kept apart. An IRI is no tag: a want is minted per instance, and a tag of unbounded values
  breaks the series store's index;
- `Value`, a number, aggregated over the window as its sum, its mean and its max;
- `Flag`, a truth, counted where it is raised;
- `Level`, a figure that IS the state now — worlds kept, intentions standing, sensors silent —
  whose last in the window is written as it stands.

A field left unmarked — a want, a plan, a document — is the event's and not the metric's: a handler
reads it, history may write it, and the metrics part passes over it. An event marking only tags and
values is COUNTED; one whose marks beyond its tags are levels is a report of state, and is not.

A duration is real time, never the agent's (`Laps`): a metric is about the process, and the agent's
clock may run fast or, in a test, tick per read.
"""

from __future__ import annotations

import dataclasses
import time
from functools import cache
from typing import Annotated, get_origin, get_type_hints


class _Mark:
    def __init__(self, kind: str):
        self.kind = kind

    def __repr__(self) -> str:
        return self.kind


TAG, VALUE, FLAG, LEVEL = _Mark("tag"), _Mark("value"), _Mark("flag"), _Mark("level")

Tag = Annotated[str | None, TAG]
Value = Annotated[float | None, VALUE]
Flag = Annotated[bool, FLAG]
Level = Annotated[float | None, LEVEL]


@cache
def marked(cls: type) -> dict[str, _Mark]:
    """Every field of the event class `cls` that is reported, and how: its marks, in field order."""
    if not dataclasses.is_dataclass(cls):
        return {}
    hints = get_type_hints(cls, include_extras=True)
    out = {}
    for field in dataclasses.fields(cls):
        hint = hints.get(field.name)
        if get_origin(hint) is Annotated:
            for mark in hint.__metadata__:
                if isinstance(mark, _Mark):
                    out[field.name] = mark
    return out


def measurement(cls: type) -> str | None:
    """The measurement events of `cls` are reported under, or None where the class reports nothing."""
    return getattr(cls, "metric", None) if marked(cls) else None


def fields_of(cls: type, mark: _Mark) -> tuple[str, ...]:
    """The fields of `cls` marked `mark`, in field order."""
    return tuple(name for name, m in marked(cls).items() if m is mark)


def counted(cls: type) -> bool:
    """Whether an event of `cls` is counted: it marks values or flags, or it marks tags alone."""
    kinds = set(marked(cls).values())
    return bool(kinds & {VALUE, FLAG}) or kinds == {TAG}


def reported(module) -> list[type]:
    """Every event class the module holds that is reported, in the order it states them — what a
    package reports, read off its `events.py`, and what the dashboards draw."""
    return [v for v in vars(module).values()
            if isinstance(v, type) and v.__module__ == module.__name__ and measurement(v)]


class Laps:
    """Real seconds spent per part of something, each lap from the last, as `<part>_s` — by
    `perf_counter`, the process's clock and not the agent's."""

    def __init__(self):
        self.spent: dict[str, float] = {}
        self._mark = time.perf_counter()

    def __call__(self, part: str) -> None:
        now = time.perf_counter()
        self.spent[f"{part}_s"] = round(self.spent.get(f"{part}_s", 0.0) + (now - self._mark), 6)
        self._mark = now
