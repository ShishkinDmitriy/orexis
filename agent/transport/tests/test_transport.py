"""The contract every transport answers, at the family's level: what the container needs of any
member — open, handle, cadence, nudge, a step's command — and nothing about bytes, which are
sensing's, and nothing about whether it is loaded, which is its premise and read before it is."""

from __future__ import annotations

import pytest

from agent.transport.transport import Transport, Transports


def test_the_contract_is_connect_open_handle_cadence_nudge_and_tell_and_nothing_about_bytes():
    names = {n for n, v in vars(Transport).items() if not n.startswith("_") and (callable(v) or isinstance(v, classmethod))}
    assert names == {"connect", "open", "handle", "reaches", "set_cadence", "sense_now", "actuate", "tell"}
    assert "parse" not in names, "bytes to number is sensing's pipeline"
    assert "claims" not in names, "whether a member is loaded is its premise, asked before it is imported"
    with pytest.raises(NotImplementedError):
        Transport.connect("me", lambda *a: None)
    t = Transport()
    assert t.open(None) == []
    assert t.handle(None, "any", b"", None) == []
    assert t.set_cadence(None, None, 60) is False and t.sense_now(None, None) is None
    assert t.actuate(None, "urn:pump", {"dose_ml": 100}) is False, "a member that reaches nothing sends nothing"
    assert t.tell(None, "urn:peer", b"") is False, "nor tells anybody anything"
    assert t.reaches(None, "urn:probe") is False


class _Member(Transport):
    """A member that reaches what it is told it reaches and records what it is asked."""

    def __init__(self, name, reached, deliver):
        self.name, self.reached, self.deliver, self.asked = name, reached, deliver, []

    @classmethod
    def kind(cls, name, reached):
        return type(name, (cls,), {"connect": classmethod(lambda c, me, deliver, **kw: c(name, reached, deliver))})

    def open(self, store):
        return [self.name]

    def handle(self, store, channel, payload, at, *, memo=None):
        self.asked.append(("handle", channel))
        return [(None, f"{self.name}:{channel}")]

    def reaches(self, store, device):
        return device in self.reached

    def sense_now(self, store, sensor):
        self.asked.append(("sense_now", sensor))


def test_several_members_are_one_transport_and_each_message_goes_back_to_its_member():
    queued = []
    held = Transports.connect("me", lambda *message: queued.append(message),
                              members=[_Member.kind("bus", {"urn:probe"}), _Member.kind("web", {"urn:weather"})])
    bus, web = held.members
    assert held.open(None) == ["bus", "web"]
    web.deliver("urn:weather", b"{}", None)
    [(channel, payload, at)] = queued
    assert held.handle(None, channel, payload, at) == [(None, "web:urn:weather")] and bus.asked == []
    held.sense_now(None, "urn:weather")
    held.sense_now(None, "urn:nobody")
    assert web.asked[-1] == ("sense_now", "urn:weather") and not any(a[0] == "sense_now" for a in bus.asked)
    assert held.reaches(None, "urn:probe") and not held.reaches(None, "urn:nobody")


def test_one_member_is_itself():
    member = _Member.kind("bus", set())
    assert type(Transports.connect("me", lambda *m: None, members=[member])) is member
