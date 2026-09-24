"""The contract a transport's driver implements: what only a transport knows, and no `parse`."""

from __future__ import annotations

import inspect

from agent.sensing.driver import Driver


def test_the_contract_is_reach_own_nudge_and_cadence_and_nothing_about_bytes():
    names = {n for n, v in vars(Driver).items() if not n.startswith("_") and callable(v) or isinstance(v, classmethod)}
    assert names == {"claims", "subscriptions", "owns", "set_cadence", "sense_now"}
    assert "parse" not in names, "bytes to number is the pipeline's"
    d = Driver()
    assert Driver.claims(None, None) is False and d.subscriptions(None, None) == []
    assert d.owns(None, None, "any") is False and d.set_cadence(None, None, 60) is False
    assert d.sense_now(None, None) is None
