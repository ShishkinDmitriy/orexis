"""The contract every transport answers, at the family's level: what the container needs of any
member — claim, open, handle, cadence, nudge — and nothing about bytes, which are sensing's."""

from __future__ import annotations

from agent.transport.transport import Transport


def test_the_contract_is_claim_open_handle_cadence_and_nudge_and_nothing_about_bytes():
    names = {n for n, v in vars(Transport).items() if not n.startswith("_") and (callable(v) or isinstance(v, classmethod))}
    assert names == {"claims", "open", "handle", "set_cadence", "sense_now"}
    assert "parse" not in names, "bytes to number is sensing's pipeline"
    t = Transport()
    assert Transport.claims(None, None) is False and t.open(None) == []
    assert t.handle(None, "any", b"", None) == []
    assert t.set_cadence(None, None, 60) is False and t.sense_now(None, None) is None
