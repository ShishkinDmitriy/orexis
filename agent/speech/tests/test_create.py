"""Speech's part: it says a document as the agent said it, and tells each agent it is to by its own
`told` signal — which, linked, reaches every transport that can tell a peer."""

from __future__ import annotations

from agent.speech.create import create

from .test_said import ME, T, _doc, store  # noqa: F401 — the fixture


class _Transport:
    def __init__(self):
        self.told = []

    def tell_to(self, to, document):
        self.told.append(to)


def test_its_part_believes_what_was_said_and_tells_each_agent(store, stand_in_runtime):  # noqa: F811
    runtime = stand_in_runtime(store, ME, None)
    part, transport = create(runtime), _Transport()
    part.link({"speech": part, "transport": transport})
    assert part.say(document=_doc(T + "round", "open"), to=[T + "rose", T + "fern"]) == [T + "round"]
    assert transport.told == [T + "rose", T + "fern"]
