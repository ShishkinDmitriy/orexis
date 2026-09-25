"""The contract every transport answers, at the family's level: what the container needs of any
member — claim, open, handle, cadence, nudge, a step's command — and nothing about bytes, which are sensing's."""

from __future__ import annotations

import pytest

from agent.transport.transport import Transport


def test_the_contract_is_connect_claim_open_handle_cadence_and_nudge_and_nothing_about_bytes():
    names = {n for n, v in vars(Transport).items() if not n.startswith("_") and (callable(v) or isinstance(v, classmethod))}
    assert names == {"connect", "claims", "open", "handle", "set_cadence", "sense_now", "actuate"}
    assert "parse" not in names, "bytes to number is sensing's pipeline"
    with pytest.raises(NotImplementedError):
        Transport.connect("me", lambda *a: None)
    t = Transport()
    assert Transport.claims(None, None) is False and t.open(None) == []
    assert t.handle(None, "any", b"", None) == []
    assert t.set_cadence(None, None, 60) is False and t.sense_now(None, None) is None
    assert t.actuate(None, "urn:pump", {"dose_ml": 100}) is False, "a member that reaches nothing sends nothing"
