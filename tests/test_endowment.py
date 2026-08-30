"""An amendment endows what it grants — and touches nothing the agent holds (#202).

Beliefs are authored once at birth and never reset by start or stop. But an amendment may
grant an agent a NEW capability, whose opening beliefs an existing volume has never held —
the dealer's buy side arrived exactly so, and the agent crash-looped while the only remedy
was discarding who it had become. Endowment is the missing half: never-held (subject,
predicate) pairs arrive with their structures, held pairs stay the agent's whatever their
value, and `rebirth` remains the explicit act of discarding.
"""

from pathlib import Path

from agent import genesis
from orexis_agent_progression.ontology import beliefs_graph
from orexis_agent_progression.store import Store, bindings

NS = "http://example.org/orexis/world/simulation#"
MARKET = "http://example.org/orexis/market#"
SENSING = "http://example.org/orexis/sensing#"   # the aim is sensing's (the-stake-is-sensings-want)
PROLOG = """@prefix : <http://example.org/orexis/world/simulation#> .
@prefix market: <http://example.org/orexis/market#> .
@prefix sensing: <http://example.org/orexis/sensing#> .
@prefix ag:   <http://example.org/orexis#> .
@prefix ssn: <http://www.w3.org/ns/ssn/> .
@prefix schema: <https://schema.org/> .
"""


def world_with(tmp_path: Path, beliefs: str) -> Path:
    (tmp_path / genesis.BELIEFS_DIR).mkdir(exist_ok=True)
    (tmp_path / genesis.BELIEFS_DIR / "dealer.ttl").write_text(PROLOG + beliefs)
    return tmp_path


def value_of(st: Store, term: str) -> list[str]:
    rows = bindings(st.query(
        f"SELECT ?v WHERE {{ GRAPH <{beliefs_graph('dealer')}> {{ ?s <{term}> ?v }} }}"))
    return sorted(r["v"] for r in rows)


def test_a_new_block_arrives_and_a_revised_pick_survives(tmp_path):
    """The bench story, as a unit: born before the amendment, revised since, endowed after.

    The volume holds a reserve the agent re-picked (0.35 where 0.20 was authored). The
    amendment authors a wallet the volume never held. Endowment delivers the wallet and
    leaves the re-pick alone — which is the entire difference from rebirth."""
    st = Store()
    world = world_with(tmp_path, ":dealer market:reservePricePerL 0.20 .")
    assert genesis.birth(st, world, "dealer")
    st.update(f"""DELETE WHERE {{ GRAPH <{beliefs_graph('dealer')}> {{
                    ?s <{MARKET}reservePricePerL> ?v }} }}""")
    st.update(f"""INSERT DATA {{ GRAPH <{beliefs_graph('dealer')}> {{
                    <{NS}dealer> <{MARKET}reservePricePerL> 0.35 }} }}""")

    world_with(tmp_path, ":dealer market:reservePricePerL 0.20 ; market:hasEndowment 50.0 .")
    endowed = genesis.endow(st, world, "dealer")
    assert endowed == [MARKET + "hasEndowment"]
    assert [float(v) for v in value_of(st, MARKET + "hasEndowment")] == [50.0]
    assert [float(v) for v in value_of(st, MARKET + "reservePricePerL")] == [0.35], \
        "the re-pick is the agent's — an amendment must never overwrite it"


def test_a_structure_arrives_whole(tmp_path):
    """An aim is a blank-node structure, not a triple: the never-held pair brings its whole
    closure, because half an aim (a value with no property) would fail the agent at boot."""
    st = Store()
    world = world_with(tmp_path, ":dealer market:hasEndowment 50.0 .")
    assert genesis.birth(st, world, "dealer")

    world_with(tmp_path, """:dealer market:hasEndowment 50.0 ;
        sensing:aims [ ssn:forProperty <http://example.org/orexis/water#StoredLitres> ;
                      schema:value 3.0 ] .""")
    assert genesis.endow(st, world, "dealer") == [SENSING + "aims"]
    rows = bindings(st.query(f"""
        SELECT ?p ?v WHERE {{ GRAPH <{beliefs_graph('dealer')}> {{
            ?s <{SENSING}aims> ?aim . ?aim <http://www.w3.org/ns/ssn/forProperty> ?p ;
               <https://schema.org/value> ?v }} }}"""))
    assert rows and float(rows[0]["v"]) == 3.0, "the closure travels with the pair"


def test_every_ordinary_boot_endows_nothing(tmp_path):
    st = Store()
    world = world_with(tmp_path, ":dealer market:hasEndowment 50.0 .")
    assert genesis.birth(st, world, "dealer")
    assert genesis.endow(st, world, "dealer") == []
    assert genesis.endow(st, world, "dealer") == []


def test_the_unborn_are_not_endowed(tmp_path):
    """Birth's business stays birth's: no volume means opening beliefs, not a top-up."""
    st = Store()
    world = world_with(tmp_path, ":dealer market:hasEndowment 50.0 .")
    assert genesis.endow(st, world, "dealer") == []
    assert not st.has_graph(beliefs_graph("dealer"))
