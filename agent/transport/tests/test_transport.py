"""The contract every transport answers, at the family's level: what the container needs of any
member — open, handle, cadence, nudge, a step's command — and nothing about bytes, which are
sensing's, and nothing about whether it is loaded, which the runtime reads off the roles and the
world before it is."""

from __future__ import annotations

import pytest

from agent.transport.transport import Transport, Transports


def test_the_contract_is_connect_open_handle_cadence_nudge_and_tell_and_nothing_about_bytes():
    names = {n for n, v in vars(Transport).items() if not n.startswith("_") and (callable(v) or isinstance(v, classmethod))}
    assert names == {"connect", "start", "stop", "open", "handle", "reaches", "set_cadence", "sense_now", "actuate", "tell",
                     "command", "tell_to"}
    assert "parse" not in names, "bytes to number is sensing's pipeline"
    assert "claims" not in names, "whether a member is loaded is the runtime's to read, before it is imported"
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

    def __init__(self, name, reached):
        self.name, self.reached, self.asked = name, reached, []

    def open(self, store):
        return [self.name]

    def handle(self, store, channel, payload, at, *, memo=None):
        self.asked.append(("handle", channel))
        return [(None, f"{self.name}:{channel}")]

    def reaches(self, store, device):
        return device in self.reached

    def sense_now(self, store, sensor):
        self.asked.append(("sense_now", sensor))


def test_a_started_member_hands_every_message_to_the_runtime_as_a_job_and_holds_the_agent(stand_in_runtime):
    """Its thread only queues: what a message means is handled when the runtime runs the job."""
    member = _Member("bus", set())
    runtime = stand_in_runtime(None, "me", None)
    member.start(runtime)
    assert runtime.attached == [member] and member in runtime.held and member.asked == []
    member.deliver("topic", b"{}", None)
    [job] = runtime.jobs
    assert job() == ["bus:topic"] and member.asked == [("handle", "topic")]


def test_a_command_is_sent_only_by_the_member_reaching_the_device(stand_in_runtime):
    """Linked to the executor's `commanded`, every member hears a command, and only the one reaching
    the actuator sends it."""
    sent = []
    bus, web = _Member("bus", {"urn:pump"}), _Member("web", set())
    for member in (bus, web):
        member.actuate = lambda store, actuator, payload, name=member.name: sent.append((name, actuator)) or True
        member.start(stand_in_runtime(None, "me", None))
    Transports([bus, web]).command("urn:pump", {"dose_ml": 100})
    assert sent == [("bus", "urn:pump")]


def test_several_members_are_one_transport_and_a_nudge_goes_to_the_member_reaching_it():
    bus, web = _Member("bus", {"urn:probe"}), _Member("web", {"urn:weather"})
    held = Transports([bus, web])
    assert held.open(None) == ["bus", "web"]
    assert held.handle(None, (1, "urn:weather"), b"{}", None) == [(None, "web:urn:weather")] and bus.asked == []
    held.sense_now(None, "urn:weather")
    held.sense_now(None, "urn:nobody")
    assert web.asked[-1] == ("sense_now", "urn:weather") and not any(a[0] == "sense_now" for a in bus.asked)
    assert held.reaches(None, "urn:probe") and not held.reaches(None, "urn:nobody")
