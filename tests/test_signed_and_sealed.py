"""The winner's own hand, and an envelope only it can open — #144 and #145, driven end to end.

The pair completes the boundary work #132 started: the ACL keeps other agents out (broker-
enforced), the signature takes the broker out of the AUTHENTICITY boundary (a forged
presentation needs fern's private key, not fern's topic), and the seal takes it out of the
CONFIDENTIALITY one (a port mirror carries an envelope, not a claim). Both interoperate with
the pre-key era by the roster: no published key, no demand — a world onboarded before keygen
learned agents behaves exactly as it always did, which the rest of the suite proves by running
keyless.
"""

from __future__ import annotations

import json

import pytest

from agent import signing
from orexis_agent_progression.ontology import WORLD_GRAPH
from onboarding.keygen import (create_agent_signing_keypair, create_keypair,
                               create_sealing_keypair)

from conftest import build_agent, genesis_store, wired_actuator_for, wired_hosted_markets, wired_markets

FERN = "http://example.org/orexis/world/simulation#fern_agent"


@pytest.fixture
def keyed(tmp_path, monkeypatch):
    """A store whose world attests fern's keys, and a secrets dir holding their private halves.

    The roster triples are injected straight into the world graph — exactly what sweeping a
    generated keys.ttl produces — and the private halves are minted into a tmp secrets dir the
    way `orexis-keygen` mints them, so both halves are real and only the file layout is
    simulated.
    """
    monkeypatch.setenv("OREXIS_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    create_agent_signing_keypair("fern")
    create_sealing_keypair("fern")

    st = genesis_store({"fern": 0.30})
    sign_b64 = signing.raw_public_b64(signing.load_signing_private("fern").public_key())
    seal_b64 = signing.raw_public_b64(signing.load_sealing_private("fern").public_key())
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{FERN}> orexis:signingKey "{sign_b64}" ; orexis:sealingKey "{seal_b64}" . }} }}""")
    return st


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds: build_agent(agent_id, ds, monkeypatch)


def market_of(agent):
    return (wired_hosted_markets(agent) or wired_markets(agent))[0]


def _open_and_win(host):
    """One full round with fern the only bidder."""
    host.deliver("readings/fern", {"agent": "fern", "subject": "http://example.org/orexis/world/simulation#fern",
                                   "property": "http://example.org/orexis/water#SoilMoisture",
                                   "value": 0.05, "band": "LOW"})
    rid = host.sent.to(market_of(host).offer_topic)[-1]["auction_id"]
    host.deliver(f"{market_of(host).bid_topic}/fern",
                 {"auction_id": rid, "agent": "fern", "max_qty_l": 0.5,
                  "max_price_per_l": 0.6, "balance": 100.0})
    host.hosting().close()


# --- the seal (#145) ---------------------------------------------------------

def test_a_claim_travels_sealed_and_only_its_winner_opens_it(keyed, make):
    """The wire carries an envelope: no jti, no amount, no debit in the clear — the bus is out
    of the confidentiality boundary. And the winner's ordinary flow opens it: the claim is
    held, the Apply stands, exactly as a plaintext claim would have arrived."""
    host = make("supplier", keyed)
    _open_and_win(host)
    on_wire = host.sent.to(f"{market_of(host).claim_topic}/fern")[-1]
    assert set(on_wire) == {"sealed"}, "a sealed claim must expose nothing else"

    fern = make("fern", keyed)
    fern.deliver(f"{market_of(fern).claim_topic}/fern", on_wire)
    assert fern.bidding().holding is not None
    assert fern.bidding().holding["jti"]     # the sealed content reached the holder intact


def test_a_winner_without_a_published_sealing_key_gets_plaintext(make, monkeypatch, tmp_path):
    """The pre-#145 era, kept legal by the roster: no key published, no seal demanded."""
    monkeypatch.setenv("OREXIS_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    host = make("supplier", genesis_store({"fern": 0.30}))
    _open_and_win(host)
    on_wire = host.sent.to(f"{market_of(host).claim_topic}/fern")[-1]
    assert "sealed" not in on_wire and on_wire["jti"]


# --- the signature (#144) ----------------------------------------------------

def test_a_presentation_carries_the_winners_own_signature(keyed, make):
    fern = make("fern", keyed)
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    fern.deliver(f"{market.claim_topic}/fern", {"jti": "v1", "amount_l": 0.5, "debit": 0.2})
    #  The bound is the keeper's deadline now (#512): fire it as the scheduler would.
    from orexis_capability_market.terms import PRESENTING
    fern.keeper.lapse(fern.keeper.standing(action=PRESENTING)[0].uri)
    presented = fern.sent.to(f"{market.redeem_topic}/fern")[-1]
    assert presented["sig"]
    payload = {k: v for k, v in presented.items() if k != "sig"}
    pub = signing.load_signing_private("fern").public_key()
    assert signing.verify(pub, signing.canonical(payload), presented["sig"])


def test_the_host_refuses_a_presentation_that_fails_the_published_key(keyed, make):
    """The broker is out of the authenticity boundary: writing redeem/fern is no longer proof.
    A presentation without a signature — or with a tampered one — from an agent whose roster
    entry says it signs, moves no water and earns a log line."""
    host = make("supplier", keyed)
    _open_and_win(host)
    sealed = host.sent.to(f"{market_of(host).claim_topic}/fern")[-1]
    jti = json.loads(signing.unseal(signing.load_sealing_private("fern"),
                                    sealed["sealed"]))["jti"]
    valve = wired_actuator_for(host, "fern")

    host.deliver(f"{market_of(host).redeem_topic}/fern", {"jti": jti, "sub": "fern"})
    assert host.sent.to(valve.command_topic) == [], "unsigned must be refused — the key is published"

    good = {"jti": jti, "sub": "fern"}
    sig = signing.sign(signing.load_signing_private("fern"), signing.canonical(good))
    host.deliver(f"{market_of(host).redeem_topic}/fern", {**good, "sig": sig[:-4] + "AAAA"})
    assert host.sent.to(valve.command_topic) == [], "a tampered signature must be refused"

    host.deliver(f"{market_of(host).redeem_topic}/fern", {**good, "sig": sig})
    assert len(host.sent.to(valve.command_topic)) == 1, "the true hand opens the valve"


# --- the roster: real IRIs, not a naming convention --------------------------

def test_the_roster_attests_keys_against_each_agents_real_node(tmp_path, monkeypatch):
    """`<http://example.org/orexis/world/simulation#supplier>` has no `_agent` suffix — a roster that built IRIs from localIds by
    convention attested keys for nodes that do not exist, and rule 1 is exactly the rule
    against that guess. The IRI travels with the id from the ratified files, so every agent's
    keys land on its actual node, supplier included."""
    import shutil

    from agent import genesis
    from onboarding.keygen import publish_roster, roster

    worlds = tmp_path / "worlds"
    shutil.copytree(genesis.world_dir("simulation"), worlds / "sim2")
    (worlds / "sim2" / "keys.ttl").unlink(missing_ok=True)  # this machine's, not this test's
    monkeypatch.setattr(genesis, "WORLDS_ROOT", worlds)
    # conftest filters keys.ttl out of every sweep so tests stay hermetic against whatever this
    # machine last deployed — this test GENERATES one and needs it swept, so the real glob
    # comes back for its duration.
    monkeypatch.setattr(genesis, "world_files", lambda w: sorted(w.glob("*.ttl")))
    monkeypatch.setenv("OREXIS_WORLD", "sim2")
    monkeypatch.delenv("OREXIS_WORLD_DIR", raising=False)

    ids = roster("sim2")
    assert ("http://example.org/orexis/world/simulation#supplier", "supplier") in ids
    assert ("http://example.org/orexis/world/simulation#fern_agent", "fern") in ids

    for _, agent_id in ids:
        create_agent_signing_keypair(agent_id)
        create_sealing_keypair(agent_id)
    publish_roster("sim2", ids)

    # Built straight from the tmp world's own directory — conftest's helper resolves the
    # repo's world/ by its own constant, and the whole point here is the generated keys.ttl
    # sitting beside the COPY.
    from orexis_agent_progression.store import Store, bindings

    st = Store()
    genesis.refresh_public(st, worlds / "sim2")
    rows = bindings(st.query("""SELECT ?a WHERE { ?a orexis:signingKey ?k }"""))
    subjects = {r["a"] for r in rows}
    assert "http://example.org/orexis/world/simulation#supplier" in subjects
    assert "http://example.org/orexis/world/simulation#fern_agent" in subjects
    assert len(subjects) == len(ids)
