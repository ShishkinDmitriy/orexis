"""SHACL validation, in the two places it belongs.

The constitution is "checked by code, not persuasion", and the checks are **capability-aware**:
a shape applies to an agent only if that agent derived the capability it belongs to. An agent
that holds sensing:Subscribing with no sensor or no interval fails — before it fails at 3am.

Where each check lives follows from who owns the data:

- **an agent's own beliefs** are checked by that agent, at startup, and it refuses to run if
  they do not hold. The check sits where the data is, it happens *before the agent acts*
  rather than when an operator remembers to run a command, and refusing to start is not
  self-report — the consequence is not running, not a claim to be fine.
- **the ratified world** is checked centrally, against the files, because there is one world
  and it is public. That is the sovereign's check on their own authorship.

  orexis-validate [world]

See knowledge/decisions/where-the-belief-base-lives.md.
"""

from __future__ import annotations

import logging


from agent import genesis

from orexis_agent_progression.ontology import OREXIS, STATE_GRAPH
from orexis_agent_progression.store import Store
#  THE JUDGE IS THE FLOOR'S. `conforms` and its helpers were this file's, and went to
#  `orexis_agent_deliberation.conformance` when the kernel split along its layers (#452): the
#  search holds candidate worlds to the same verdict and may not import the container, and
#  the boot check must not pull the search. Re-exported here because every caller that asks
#  for the verdict by this module's name — onboarding, the review capability, the tests — is
#  asking the agent's check, and that check IS this verdict.
from orexis_agent_deliberation.conformance import (  # noqa: F401 — re-exported on purpose
    _shapes_and_vocabulary, conforms, graph_from)

log = logging.getLogger("validate")


class BeliefsInvalid(RuntimeError):
    """An agent's beliefs do not satisfy the shapes of the capabilities it derived."""


# --- the agent's own check, at startup --------------------------------------------------------

def validate_agent(st: Store, agent_id: str, agent_uri: str, capabilities,
                   desires=None) -> None:
    """Hold ONE agent to the shapes of the capabilities it derived. Raises if it fails.

    Checked against its own store, which holds the world it booted with and its own beliefs —
    everything a capability-scoped shape needs, and nothing belonging to anyone else. Since
    #312 the wants are not in that store: the desire modality derives them, so a caller with
    one passes it and its quads join the data graph — sensing's `DesirerShape` demands a region and
    `AimShape` holds the aim to it, and both would fire falsely against a store that
    rightly no longer holds either. `None` stays legal for the world-level caller, which
    builds the modality itself per agent.
    """
    if not capabilities:
        return
    # Every public graph, flattened. pyshacl gets one graph and no reasoner, so anything the
    # vocabulary merely IMPLIES has to arrive already asserted — leave the entailed graphs out
    # and the shapes go quiet rather than failing, which is the worst way to be wrong. Passing
    # Asking the store which graphs are public, rather than naming them, means a sixth can never
    # be forgotten — and that nothing here has to know what the five happen to be called.
    #  INSTRUMENTS too, because the freshness want reads the horizon this agent published for
    #  its own sensors (#240). Leave it out and that shape binds nothing, fires never, and says
    #  so to no one — the silent direction to be wrong, which this file has met before.
    #  The pick record travels THROUGH the modality when one is given, never beside it: the
    #  flatten serialises and re-parses, which relabels blank nodes, so a record arriving by
    #  both roads splits every aim into two nodes — and AimShape rightly calls two aims for
    #  one property not steering.
    #  ASKED, never enumerated (#444): every graph this agent owns, the pick record among
    #  them. Which is why the record is SUBTRACTED where the modality carries it — naming it
    #  to take it out is not the enumeration the rule forbids, it is saying which road it
    #  came by.
    recorded = st.recorded_graphs()
    if desires is not None:
        picks = set(st.graphs_of(OREXIS + "PickRecordGraph"))
        recorded = [g for g in recorded if g not in picks]
    private = [STATE_GRAPH, *recorded]
    data = graph_from(st, *st.public_graphs(), *private)
    if desires is not None:
        from orexis_agent_deliberation import effects
        for triple in desires.construct(
                "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
            data.add(effects._triple(triple))
    ok, report = conforms(data, focus=agent_uri)
    if not ok:
        raise BeliefsInvalid(
            f"{agent_id} will not start: its beliefs do not satisfy the shapes for the "
            f"capabilities the world derived for it.\n{report}"
        )
    log.info("%s: beliefs satisfy the shapes for %d capability(ies)",
             agent_id, len(capabilities))


# `conforms` and `graph_from` are public because onboarding's world-wide check runs the same
# machinery over the same graphs. What is NOT here is that check itself: it is the sovereign's,
# runs before anything starts, and an agent has no use for it. See onboarding/validate.py.
