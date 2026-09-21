"""Bringing an older agent's intention ledger across to what the keeper writes now.

These two migrations lived in `agent/vocabulary.py` beside the belief-base ones, and came here
with the keeper because they are the LEDGER's: what an intention row used to look like is a
fact about this layer, and the kernel's vocabulary file should not have to know what a ledger
is to keep it current (a-volume-can-be-older-than-the-vocabulary, #87). The keeper runs them
once, at construction, on the volume it is handed.
"""

from __future__ import annotations

import logging

from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import bindings

log = logging.getLogger("intention")

#  The ledger used to key a row on the property its want was about; a row is keyed on the
#  want now (the-region-want-is-sensings-want, #380), so a volume from before is brought across:
#  a row with a property and no want is given the want that property named for this agent —
#  found through `orexis:about`, which is what the deriver says a want is about — and the property
#  triple is then dropped from every row. The retired term is spelled here for the same
#  reason `vocabulary.MOVED` spells its left-hand sides: a migration names what it migrates FROM.
_LEDGER_PROPERTY = "http://www.w3.org/ns/ssn/forProperty"


def migrate_ledger(intentions, graph: str, about_of: dict[str, str]) -> int:
    """Bring one agent's intention ledger from property-keyed rows to want-keyed ones.

    `about_of` maps each want the agent holds to what it is about; a row whose property names
    no want is left as it is and said so, because inventing a want for it would be authorship.
    Returns how many rows gained a want.
    """
    want_of = {about: want for want, about in about_of.items()}
    rows = bindings(intentions.query_over(f"""
        SELECT ?i ?property WHERE {{ GRAPH <{graph}> {{
            ?i <{_LEDGER_PROPERTY}> ?property .
            FILTER NOT EXISTS {{ ?i progression:pursues ?want }} }} }}""", graph))
    given = 0
    for row in rows:
        if (want := want_of.get(row["property"])) is None:
            log.warning("ledger row %s is about %s, and no want of this agent's is — left "
                        "keyed by a property the kernel no longer reads", row["i"],
                        row["property"])
            continue
        intentions.update(f"""INSERT DATA {{ GRAPH <{graph}> {{
            <{row['i']}> progression:pursues <{want}> }} }}""")
        given += 1
    intentions.update(f"""
        DELETE {{ GRAPH <{graph}> {{ ?i <{_LEDGER_PROPERTY}> ?p }} }}
        WHERE  {{ GRAPH <{graph}> {{ ?i <{_LEDGER_PROPERTY}> ?p }} }}""")
    return given


def migrate_ledger_acts(intentions, graph: str) -> int:
    """Bring an intention that names an ACTION under `progression:by` to one that names an ACT.

    Before an-act-is-a-filled-action, `progression:by` pointed at the action node and `progression:through` sat on
    the intention. Such a row is rebuilt: an act node is minted, `progression:fills` the action,
    `progression:through` moved onto it, and `progression:by` repointed. Told apart by structure — a `by` object
    that is not `a progression:Act` in the ledger — so the migration is idempotent. Returns how many.
    """
    rows = bindings(intentions.query_over(f"""
        SELECT ?i ?action ?through WHERE {{ GRAPH <{graph}> {{
            ?i progression:by ?action .
            OPTIONAL {{ ?i progression:through ?through }}
            FILTER NOT EXISTS {{ ?action a progression:Act }} }} }}""", graph))
    for row in rows:
        act = row["i"].replace("intent_", "act_", 1) if "intent_" in row["i"] else row["i"] + ".act"
        through = f'<{act}> progression:through <{row["through"]}> .' if row.get("through") else ""
        intentions.update(f"""
            DELETE {{ GRAPH <{graph}> {{ <{row['i']}> progression:by <{row['action']}> ;
                                                    progression:through ?t }} }}
            INSERT {{ GRAPH <{graph}> {{ <{row['i']}> progression:by <{act}> .
                                        <{act}> a progression:Act ; progression:fills <{row['action']}> .
                                        {through} }} }}
            WHERE  {{ GRAPH <{graph}> {{ <{row['i']}> progression:by <{row['action']}> .
                                        OPTIONAL {{ <{row['i']}> progression:through ?t }} }} }}""")
    #  And the watch's deadline, which sat on the intention as `progression:deadlineAt` before the
    #  window was the act's: moved onto the act as `progression:notAfter`.
    intentions.update(f"""
        DELETE {{ GRAPH <{graph}> {{ ?i progression:deadlineAt ?d }} }}
        INSERT {{ GRAPH <{graph}> {{ ?act progression:notAfter ?d }} }}
        WHERE  {{ GRAPH <{graph}> {{ ?i progression:deadlineAt ?d ; progression:by ?act }} }}""")
    return len(rows)
