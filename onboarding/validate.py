"""orexis-validate — hold a whole ratified world to every package's shapes, before anything runs.

  orexis-validate society

**This is the sovereign's check, not an agent's.** An agent validates *itself* at boot and
refuses to start if its own beliefs do not hold — that is `agent.validate.validate_agent`, and it
belongs in the runtime because the consequence is not running. This one asks a different
question: does the world I just authored hold together *at all*, for every agent in it, before I
grant anything or start anything?

So it lives here. It runs before onboarding, and `orexis-onboard` runs it first for a reason worth
stating: onboarding an inconsistent world mints real credentials for agents that will then fail
their own startup validation, and leaves them lying around.

It builds exactly what an agent would build — the vocabulary, the world, the derivation, and
every agent's opening beliefs — and needs no store, no server and no credentials to do it. The
machinery is `agent.validate`'s, shared with the agent's self-check, because two ways to decide
whether beliefs hold is one too many.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import logging
import sys

from agent import genesis
from agent.ontology import PROVENANCE_GRAPH
from agent.store import Store
from agent.validate import conforms, graph_from

log = logging.getLogger("validate")


def validate_world(world: str) -> bool:
    """Check a whole ratified world, from its files, without running anything.

    Builds exactly what an agent would build — the vocabulary, the world, the derivation and
    every agent's opening beliefs — and validates the lot. This is what genesis is checked
    with, and it needs no store, no server and no credentials.
    """
    # The LINK step first (#210): a world built on packages that reference terms nobody
    # declares would validate against constraints that match nothing — the vacuous kind of
    # green. Cheapest check, loudest failure, so it goes before anything is built.
    from onboarding import linker

    if broken := linker.dangling():
        for iri, files in broken.items():
            log.error("dangling reference: <%s> is declared by no loaded ontology "
                      "(referenced by %s)", iri, ", ".join(files))
        return False

    path = genesis.world_dir(world)
    st = Store()  # in memory: built, read, thrown away
    genesis.refresh_public(st, path)

    everyone = [genesis.agent_id_of(p) for p in sorted(path.glob(genesis.BELIEFS_GLOB))]
    for agent_id in everyone:
        genesis.birth(st, path, agent_id)

    # Every public graph — asserted, derived and entailed — plus the meta-graph describing
    # them, so `ag:PublicGraphShape` can fire. This check runs UNFOCUSED, over the whole
    # world, which is the only place a shape about graphs could ever fire: an agent's own
    # startup check is focused on its own node and would skip it silently.
    #
    # Each agent's WANTS arrive through its desire modality (#312): genesis derives none, so
    # the sovereign's check builds per agent exactly what the agent's own boot builds, and
    # judges the world against it. The pick records travel the same road and only that road —
    # flattened beside their projections they would split every blank-node aim in two.
    data = graph_from(st, *st.public_graphs(), PROVENANCE_GRAPH)
    from agent import effects
    from agent.beliefs import Beliefs
    from agent.desire import Desires

    desires = {a: Desires(Beliefs(st, a)) for a in everyone}
    for a in everyone:
        for triple in desires[a].construct(
                "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
            data.add(effects._triple(triple))
    ok, report = conforms(data)
    print(report)

    #  And the two questions no shape can ask, because both are about what the loaded
    #  PACKAGES say rather than about what the world's files hold.
    if not deliberable(st, desires):
        ok = False

    for agent_id, caps in genesis.derived(st):
        marker = "" if agent_id in everyone else "   (no opening beliefs authored)"
        log.info("  %-10s %s%s", agent_id, caps, marker)
    return ok


def deliberable(st, desires: dict) -> bool:
    """Can every agent in this world actually be deliberated FOR? Refuse here if not.

    There is one road through deliberation now — the search — and a search answers by
    simulating each lever and ranking the world it would reach. Two things have to be true
    for that to mean anything, and neither is a fact about this world alone: every lever on
    an agent's menu must have an effect rule to simulate, and every stake it holds must have
    a measure to rank by. Where one is missing the search does not fail, it CONCLUDES from
    part of the evidence — a lever nobody could simulate is passed over, and a want nothing
    measures scores the same flat 1.0 in every candidate world, so "no move improves on doing
    nothing" comes back with confidence and the agent stops acting.

    Both used to be survivable at runtime because there was a second road: a partial plan and
    an unmeasured want both deferred to the reflex, which decided by the gap's sign. Deleting
    the reflex is what makes this a gate. The choice was the sovereign's and it is the same
    one this project keeps taking — refuse at genesis rather than degrade silently — and it
    is affordable exactly because both questions are answerable from ratified files: which
    levers a world implies, and which packages are loaded.

    See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md.
    """
    from agent import effects
    from assembly import loader
    from agent.afforder import affordances_of
    from orexis_capability_sensing.regions import regions_of
    from agent.world import load_self

    from agent.ontology import beliefs_graph
    from agent.store import bindings

    faults = 0
    #  EVERY ACTION THAT CAN PUT A ROW ON A MENU, not every row a menu happens to hold now.
    #  A premise may be a fact an agent is told at runtime — an open round (#358) — so the
    #  menu at genesis is not the menu at noon, and a gate that read the rows would have
    #  waved through the very lever that matters. The action's own node says whether it
    #  states an effect; that is a fact about the loaded packages, and it is asked as one.
    for action in bindings(st.query(
            "SELECT ?action WHERE { ?action a ag:Action ; "
            "ag:available ?q FILTER NOT EXISTS { ?action sh:construct ?c } }")):
        faults += 1
        log.error("%s offers rows and no loaded package says what that DOES — a "
                  "search that cannot simulate a lever passes it over, and then concludes "
                  "from the rest of the menu", action["action"].rsplit("#", 1)[-1])
    for agent_id, wants in desires.items():
        me = load_self(st.query, agent_id)
        for row in affordances_of(st.query, me.uri, wants.query_union, beliefs_graph(agent_id)):
            if effects.rule_for(st, row.action) is None:
                faults += 1
                log.error("%s could take %s through %s, and no loaded package says what that "
                          "DOES — a search that cannot simulate a lever passes it over, and "
                          "then concludes from the rest of the menu", agent_id,
                          row.action.rsplit("#", 1)[-1], row.via.rsplit("#", 1)[-1])
        #  Asked of the CLASSES this agent's grants would load, never of a built agent: an
        #  agent needs credentials onboarding has not minted yet, and a gate that had to run
        #  the runtime would be checking the thing it exists to run before.
        answering = loader.registry_for(me.capabilities).values()
        for observed_property in sorted(regions_of(wants.query_union, me.uri)):
            if any(getattr(cls, "measures", None) is not None
                   and cls.measures(st.query, observed_property) for cls in answering):
                continue
            faults += 1
            log.error("%s holds a stake in %s and nothing it composed can measure one — "
                      "every possible world would score alike, and the search would report "
                      "that nothing helps", agent_id, observed_property.rsplit("#", 1)[-1])
    return not faults


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-validate",
        description="Validate one ratified world and the opening beliefs it authors.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(genesis.worlds()))
    sys.exit(0 if validate_world(p.parse_args().world) else 1)


if __name__ == "__main__":
    main()
