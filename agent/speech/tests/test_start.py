"""Speech's `start`: once started it hears what a step said, believes the document as the agent said
it, and tells each agent it is to — through whichever transport reaches that agent."""

from __future__ import annotations

from agent.events import SAID, TOLD
from agent.speech.start import start

from .test_said import ME, T, _doc, store  # noqa: F401 — the fixture


def test_started_it_believes_what_was_said_and_tells_each_agent(store, stand_in_runtime):  # noqa: F811
    runtime = stand_in_runtime(store, ME, None)
    start(runtime)
    [spoken] = runtime.listeners[SAID]
    assert spoken(document=_doc(T + "round", "open"), to=[T + "rose", T + "fern"]) == [T + "round"]
    told = [what["to"] for event, what in runtime.emitted if event == TOLD]
    assert told == [T + "rose", T + "fern"]
