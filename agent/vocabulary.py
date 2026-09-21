"""Whether a store still speaks the vocabulary the code does.

A belief base outlives the code that wrote it, and that is the point of it: beliefs are authored
once at birth and never touched by start or stop, so an agent that restarts is the agent it had
become rather than the one the sovereign first described. The same property means a volume can be
**older than the vocabulary**. PR #85 made that concrete — 102 terms left `orexis:` for their
packages' namespaces, so a volume written before it holds `orexis:hasTarget` where the code now asks
`water:hasTarget`. The pattern matches nothing, and an agent with no target cannot bid.

**Nothing could see it.** Every test builds a fresh store from the current files, so a test never
meets a volume older than the code; `orexis-validate` reads the world files, which the sweep
rewrote. Both gates were green while every deployed agent was one restart from silence. It is the
same shape as the four silent breakages that sweep found, one step further out: a fact living
somewhere no gate reads.

## Why there is no version marker

The obvious fix is to stamp a store with a vocabulary version and compare on the way in. This
module does not, for two reasons.

A version is a fact somebody must remember to bump, and everywhere else this project derives
rather than declares. One that goes un-bumped is worse than none, because it asserts an agreement
nothing checked.

And it answers the wrong question. A version says the vocabulary moved; it cannot say whether
*this* volume is affected, and most would not be — a store using no moved term is perfectly
sound, and refusing it would be a lie told confidently. So the question asked here is the one
that matters: **does the vocabulary still declare what this store actually uses?** Nothing has to
be recorded to answer it, because the store already holds the evidence.

## What counts as stale, and why the positions differ

A **predicate** is always a term, so a project predicate the T-Box does not declare is wrong
however it got there — a rename, a deletion, or a typo in a hand-written beliefs file.

Anywhere else, a project IRI may be an instance: `orexis:fern_agent` is the shape of a term and is
not one. Those positions are flagged only when the rename map recognises them, which is the case
where the answer is known rather than guessed. `review:revisedTerm orexis:slowSleepS` is caught that
way — the object is a term, and the map says what it became.

See knowledge/decisions/a-volume-can-be-older-than-the-vocabulary.md and issue #87.
"""

from __future__ import annotations

import logging

from orexis_agent_progression.ontology import OREXIS, ONTOLOGY_GRAPH
from orexis_agent_progression.store import bindings
from orexis_agent_progression.ontology import PUBLIC

log = logging.getLogger("vocabulary")

# Every namespace this project owns starts here; everything else in a store — `sosa:`, `prov:`,
# `xsd:` — is somebody else's and not ours to hold to our own T-Box.
PROJECT = "http://example.org/orexis"

# What the vocabulary says about itself. A term is anything the T-Box makes a statement about:
# the packages declare `owl:Class` and `owl:ObjectProperty` and hang labels and comments on them,
# so being a subject there is the same test as being declared, without this file having to keep a
# list of which OWL types count.
_DECLARED = f"""
SELECT DISTINCT ?t WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?t ?p ?o }}
  FILTER(isIRI(?t) && STRSTARTS(STR(?t), "{PROJECT}") && CONTAINS(STR(?t), "#")) }}"""

# Every project IRI a graph uses, in any position, with the graph that uses it. `GRAPH ?g` is
# right here and is not the trap AGENTS.md warns about: that one is a SELECT narrowed to one
# graph, which silently drops facts kept elsewhere. This asks *which graph holds what*, which is
# the question a private graph is the only place to answer.
_USED = f"""
SELECT DISTINCT ?g ?t ?position WHERE {{
  GRAPH ?g {{
    {{ ?t ?p ?o . BIND("subject" AS ?position) }}
    UNION {{ ?s ?t ?o . BIND("predicate" AS ?position) }}
    UNION {{ ?s ?p ?t . BIND("object" AS ?position) }}
  }}
  FILTER(isIRI(?t) && STRSTARTS(STR(?t), "{PROJECT}") && CONTAINS(STR(?t), "#"))
}}"""


def _local(iri: str) -> str:
    return iri.rsplit("#", 1)[-1]


def declared(st) -> set[str]:
    """Every project term this vocabulary declares."""
    return {r["t"] for r in bindings(st.query(_DECLARED, st.graphs_of(PUBLIC)))}


#  Moves this project has actually made, written down because they cannot be computed.
#
#  `renames` infers a successor by LOCAL NAME, which answers the historical direction — terms
#  leaving `orexis:` for a package they now belong to — and answers nothing when a term moved the
#  other way, or moved and was renamed at once. Both happened when the mind's states became
#  kernel words (the-mind-is-six-graphs): `intention:outcome` has two candidates by local name
#  (`progression:outcome` and `review:outcome`) and nothing could choose, while `desire:desires` became
#  `orexis:holds` and has no candidate at all.
#
#  So a MOVE is data. Each entry is a decision somebody made once, and the alternative — a
#  heuristic that picks a namespace — would be this module guessing at meaning, which is the
#  one thing its own error message refuses to do.
MOVED = {
    #  #529: the kernel's terms by LAYER — a term one layer reads and writes carries its prefix.
    "http://example.org/orexis#Act": "http://example.org/orexis/progression#Act",
    "http://example.org/orexis#Candidate": "http://example.org/orexis/deliberation#Candidate",
    "http://example.org/orexis#Deliberation": "http://example.org/orexis/deliberation#Deliberation",
    "http://example.org/orexis#DeliberationGraph": "http://example.org/orexis/deliberation#DeliberationGraph",
    "http://example.org/orexis#Intention": "http://example.org/orexis/progression#Intention",
    "http://example.org/orexis#IntentionGraph": "http://example.org/orexis/progression#IntentionGraph",
    "http://example.org/orexis#PromisesGraph": "http://example.org/orexis/progression#PromisesGraph",
    "http://example.org/orexis#Step": "http://example.org/orexis/progression#Step",
    "http://example.org/orexis#adoptedAt": "http://example.org/orexis/progression#adoptedAt",
    "http://example.org/orexis#answeredWhen": "http://example.org/orexis/progression#answeredWhen",
    "http://example.org/orexis#asOf": "http://example.org/orexis/deliberation#asOf",
    "http://example.org/orexis#atDepth": "http://example.org/orexis/deliberation#atDepth",
    "http://example.org/orexis#baselineAt": "http://example.org/orexis/progression#baselineAt",
    "http://example.org/orexis#baselineValue": "http://example.org/orexis/progression#baselineValue",
    "http://example.org/orexis#becauseOf": "http://example.org/orexis/progression#becauseOf",
    "http://example.org/orexis#blind": "http://example.org/orexis/deliberation#blind",
    "http://example.org/orexis#budgetWorlds": "http://example.org/orexis/deliberation#budgetWorlds",
    "http://example.org/orexis#by": "http://example.org/orexis/progression#by",
    "http://example.org/orexis#chose": "http://example.org/orexis/deliberation#chose",
    "http://example.org/orexis#considered": "http://example.org/orexis/deliberation#considered",
    "http://example.org/orexis#deadlineAt": "http://example.org/orexis/progression#deadlineAt",
    "http://example.org/orexis#deliberatedOn": "http://example.org/orexis/deliberation#deliberatedOn",
    "http://example.org/orexis#endMet": "http://example.org/orexis/progression#endMet",
    "http://example.org/orexis#endVerifiedAt": "http://example.org/orexis/progression#endVerifiedAt",
    "http://example.org/orexis#fills": "http://example.org/orexis/progression#fills",
    "http://example.org/orexis#forAgent": "http://example.org/orexis/progression#forAgent",
    "http://example.org/orexis#maxPatienceS": "http://example.org/orexis/progression#maxPatienceS",
    "http://example.org/orexis#minPatienceS": "http://example.org/orexis/progression#minPatienceS",
    "http://example.org/orexis#notAfter": "http://example.org/orexis/progression#notAfter",
    "http://example.org/orexis#notBefore": "http://example.org/orexis/progression#notBefore",
    "http://example.org/orexis#observedValue": "http://example.org/orexis/progression#observedValue",
    "http://example.org/orexis#of": "http://example.org/orexis/progression#of",
    "http://example.org/orexis#outcome": "http://example.org/orexis/progression#outcome",
    "http://example.org/orexis#partOf": "http://example.org/orexis/progression#partOf",
    "http://example.org/orexis#patienceS": "http://example.org/orexis/progression#patienceS",
    "http://example.org/orexis#predictedValue": "http://example.org/orexis/progression#predictedValue",
    "http://example.org/orexis#predicts": "http://example.org/orexis/progression#predicts",
    "http://example.org/orexis#promisedBy": "http://example.org/orexis/progression#promisedBy",
    "http://example.org/orexis#pursues": "http://example.org/orexis/progression#pursues",
    "http://example.org/orexis#quantity": "http://example.org/orexis/progression#quantity",
    "http://example.org/orexis#resolvedAt": "http://example.org/orexis/progression#resolvedAt",
    "http://example.org/orexis#standsAt": "http://example.org/orexis/deliberation#standsAt",
    "http://example.org/orexis#step": "http://example.org/orexis/progression#step",
    "http://example.org/orexis#suspectAfter": "http://example.org/orexis/progression#suspectAfter",
    "http://example.org/orexis#taken": "http://example.org/orexis/progression#taken",
    "http://example.org/orexis#takenAt": "http://example.org/orexis/progression#takenAt",
    "http://example.org/orexis#then": "http://example.org/orexis/progression#then",
    "http://example.org/orexis#through": "http://example.org/orexis/progression#through",
    "http://example.org/orexis#tookSeconds": "http://example.org/orexis/deliberation#tookSeconds",
    "http://example.org/orexis#until": "http://example.org/orexis/progression#until",
    "http://example.org/orexis#untilNot": "http://example.org/orexis/progression#untilNot",
    "http://example.org/orexis#verdict": "http://example.org/orexis/deliberation#verdict",
    "http://example.org/orexis#whenLapsed": "http://example.org/orexis/progression#whenLapsed",
    "http://example.org/orexis#wouldReach": "http://example.org/orexis/deliberation#wouldReach",
    "http://example.org/orexis#wouldTake": "http://example.org/orexis/deliberation#wouldTake",
    #  #635: the ledger's words are the market's — they sat in `orexis:` because the ledger was
    #  the kernel's once. A volume written before reads through this row.
    **{f"http://example.org/orexis#{n}": f"http://example.org/orexis/market#{n}"
       for n in ("ObligationsGraph", "owedTo", "forClaim", "presented", "owedAt", "owedFrom",
                 "amountL", "dischargedAt")},
    **{f"http://example.org/orexis/intention#{n}": f"http://example.org/orexis#{n}"
       for n in ("Intention", "by", "Means",
                 "adoptedAt", "resolvedAt", "outcome", "becauseOf", "expectsValueTo",
                 "baselineValue", "baselineAt", "deadlineAt", "endMet",
                 "endVerifiedAt")},
    #  And the four figures that were the KEEPING member's own, when keeping was one way of
    #  having an ability. Every agent keeps a ledger now, so they are the kernel's; `patienceS`
    #  is the one a deployed volume actually holds, and the local names are unchanged, so this
    #  is the by-local-name path doing exactly what it was built for.
    **{f"http://example.org/orexis/intention#{n}": f"http://example.org/orexis#{n}"
       for n in ("patienceS", "suspectAfter", "minPatienceS", "maxPatienceS")},
    **{f"http://example.org/orexis/desire#{n}": f"http://example.org/orexis#{n}"
       for n in ("Aim", "aims", "Obligation", "owedTo", "forClaim", "presented", "owedAt",
                 "dischargedAt")},
    #  `toleratedMin` and `toleratedMax` were here and are not, because they went nowhere: the
    #  envelope is a shape now and its edges are `sh:minInclusive` inside it, which no rename
    #  can reach from two loose literals. They needed no migration either way — they only ever
    #  lived in the DERIVED constraint graph, which is public and rebuilt at every boot.
    #  Renamed as it moved: the region binds, so it is bounds, and an agent is held to it
    #  rather than desiring it — what it desires is the aim.
    #  Two moves in two days, so the map records the DESTINATION rather than the step: a
    #  volume migrated yesterday holds `orexis:boundedBy`, one migrated today holds neither, and
    #  both must land on what the vocabulary says now. A migration table is a record of where
    #  things went, not of how they travelled.
    #  The host's move left the kernel for the market (a-round-is-a-fact-and-offering-is-an-
    #  action): a ledger holding Offer intentions under either older spelling lands on the
    #  package's word — the destination, not the step, as the note above says.
    #  The means went to their packages and then went altogether: the ACTION is the kind
    #  (the-action-is-the-kind), so an intention's `progression:by` names the action node. Every older
    #  spelling — the intention package's, the kernel's, and the packages' short-lived means —
    #  lands on the node. `Apply` lands on the buyer's hold (Presenting): that was its meaning
    #  for every ledger old enough to hold it; the host's serve (Serving) is newer than the
    #  split and was never spelled Apply in a volume.
    **{old: "http://example.org/orexis/market#Offering" for old in (
        "http://example.org/orexis/intention#Offer", "http://example.org/orexis#Offer",
        "http://example.org/orexis/market#Offer")},
    #  The AIM went to sensing with the region it sits in (the-stake-is-sensings-want): a
    #  volume authored while it was the kernel's holds `orexis:aims`, and this is the rename.
    #  THE SUBSTRATE went to `packages/orexis-part-device/`: a BDI kernel says nothing about what a
    #  thing is made of (the-substrate-is-not-the-minds). It went in ONE word, because the rest
    #  of what the kernel held was never about substrate at all — a stand-in is the ABSENCE of a
    #  device, so it went to `packages/orexis-sim-standin/` under its own name, and the `model` prefix
    #  each of its physics terms carried to fake a namespace inside `orexis:` came off with the move
    #  (a-stand-in-is-not-a-device).
    "http://example.org/orexis#Device": "http://example.org/orexis/device#Device",
    **{f"http://example.org/orexis#{old}": f"http://example.org/orexis/sim#{new}"
       for old, new in (("simulatedBy", "simulatedBy"), ("DeviceModel", "Model"),
                        ("modelInitialValue", "initialValue"), ("modelDoseEffect", "doseEffect"),
                        ("modelLosesPerDay", "losesPerDay"), ("modelDailySwing", "dailySwing"),
                        ("modelTickSeconds", "tickSeconds"), ("modelMinValue", "minValue"),
                        ("modelMaxValue", "maxValue"), ("timeScale", "timeScale"),
                        ("strayDoseMeanDays", "strayDoseMeanDays"), ("rainTopic", "rainTopic"))},
    "http://example.org/orexis#Aim": "http://example.org/orexis/sensing#Aim",
    "http://example.org/orexis#aims": "http://example.org/orexis/sensing#aims",
    **{old: "http://example.org/orexis/sensing#Observing" for old in (
        "http://example.org/orexis/intention#Observe", "http://example.org/orexis#Observe",
        "http://example.org/orexis/sensing#Observe")},
    **{old: "http://example.org/orexis/actuation#Dosing" for old in (
        "http://example.org/orexis/intention#Actuate", "http://example.org/orexis#Actuate",
        "http://example.org/orexis/actuation#Actuate")},
    **{old: "http://example.org/orexis/market#Acquiring" for old in (
        "http://example.org/orexis/intention#Acquire", "http://example.org/orexis#Acquire",
        "http://example.org/orexis/market#Acquire")},
    **{old: "http://example.org/orexis/market#Presenting" for old in (
        "http://example.org/orexis/intention#Apply", "http://example.org/orexis#Apply",
        "http://example.org/orexis/market#Apply")},
    "http://example.org/orexis/desire#Desire": "http://www.w3.org/ns/shacl#NodeShape",
    "http://example.org/orexis/desire#desires": "http://example.org/orexis#holds",
    "http://example.org/orexis#boundedBy": "http://example.org/orexis#holds",
}


def renames(st) -> tuple[dict[str, str], dict[str, list[str]]]:
    """What a kernel spelling became: `(settled, contested)`.

    Derived from the vocabulary alone rather than from what any store happens to contain, so the
    map is complete before anything is scanned: if a term now lives in a package and no kernel
    term of that name survives, then a kernel spelling of it can only be the old one.

    **A local name two packages both declare is contested, not settled.** `i2c:DataPinRole` and
    `onewire:DataPinRole` are both real and both correct — a data pin means something different
    on each protocol — so `orexis:DataPinRole` has no single answer. Refusing outright was the first
    attempt and it was wrong twice over: neither of those was ever a kernel term, so no volume
    can hold the old spelling, and raising here would have stopped every agent from booting over
    a collision that cannot be reached. Contested names are reported only if a store actually
    uses one, which is the difference between a hazard and a fact about the vocabulary.
    """
    terms = declared(st)
    kernel_locals = {_local(t) for t in terms if t.startswith(OREXIS)}
    candidates: dict[str, list[str]] = {}
    for term in sorted(terms):
        if term.startswith(OREXIS):
            continue
        name = _local(term)
        if name in kernel_locals:
            continue  # a kernel term of that name still exists; `orexis:name` is current, not stale
        candidates.setdefault(name, []).append(term)
    settled = {OREXIS + n: v[0] for n, v in candidates.items() if len(v) == 1}
    contested = {OREXIS + n: v for n, v in candidates.items() if len(v) > 1}
    return settled, contested


def stale(st) -> dict[str, dict[str, str | list[str] | None]]:
    """Per private graph, the terms it uses that this vocabulary no longer declares.

    The value is what the term became: an IRI where that is settled, a list of candidates where
    two packages contest the name, and `None` where nothing of that name remains — deleted rather
    than moved. All three are refusals; only the first can be migrated.

    The successor is found by LOCAL NAME among what the vocabulary declares, whatever namespace
    the old spelling wore. The map used to know only kernel spellings — `orexis:X` became `pkg:X`,
    the shape of the great sweep — and that quietly assumed a term moves namespace at most once.
    The sensing rename broke the assumption: a volume authored after the sweep holds
    `perception:slowSleepS`, an old spelling that never was a kernel one, and mapping it needs
    nothing more than the same lookup unanchored from `orexis:`. `renames()` keeps the kernel view,
    which is that lookup's oldest special case.

    Public graphs are excluded because they are not the agent's: `refresh_public` replaces them
    from the ratified files on every start, so they are current by construction and a stale term
    in one would mean the files themselves are wrong.
    """
    public = set(st.graphs_of(PUBLIC))
    known = declared(st)
    by_local: dict[str, list[str]] = {}
    for term in sorted(known):
        by_local.setdefault(_local(term), []).append(term)
    out: dict[str, dict[str, str | list[str] | None]] = {}
    for row in bindings(st.query(_USED, st.graphs_of(PUBLIC))):
        graph, term, position = row["g"], row["t"], row["position"]
        if graph in public or term in known:
            continue
        #  A recorded MOVE wins over the local-name inference, and is the only thing that
        #  can answer where a term changed namespace and name at once, or where its local
        #  name is contested by a package that also declares it.
        #  A move may chain (#529): `intention:outcome` became `orexis:outcome`, which became
        #  `progression:outcome` — follow the table until it lands on what is declared.
        moved = MOVED.get(term)
        seen = set()
        while moved is not None and moved not in known and moved in MOVED and moved not in seen:
            seen.add(moved)
            moved = MOVED[moved]
        if moved is not None and moved in known:
            out.setdefault(graph, {})[term] = moved
            continue
        candidates = by_local.get(_local(term), [])
        if position != "predicate" and not candidates:
            # An instance and a term are the same shape of IRI, so only a recognisable rename
            # makes an object or a subject worth flagging. `orexis:fern_agent` lives here and is
            # not a term — no declared term shares its name, so it is left alone.
            continue
        out.setdefault(graph, {})[term] = (
            candidates[0] if len(candidates) == 1 else (candidates or None))
    return out


def _became(value: str | list[str] | None) -> str:
    if value is None:
        return "NOTHING — no term of that name remains, so what it meant has to be decided"
    if isinstance(value, list):
        return "AMBIGUOUS — " + " or ".join(value) + ", and nothing here can choose"
    return value


def _describe(found: dict[str, dict[str, str | list[str] | None]]) -> str:
    lines = []
    for graph in sorted(found):
        lines.append(f"  {graph}")
        for term, became in sorted(found[graph].items()):
            lines.append(f"    {term}  ->  {_became(became)}")
    return "\n".join(lines)


def migrate(st, found: dict[str, dict[str, str | list[str] | None]] | None = None) -> int:
    """Rewrite every stale term to what it became. Returns how many were rewritten.

    Deliberately not `rebirth`. That returns an agent to what the sovereign authored and throws
    away everything it revised for itself, which for an agent with `review:commits` latitude is
    exactly the history worth keeping — a rename should not cost that. This changes how a value
    is spelled and never which value it is.

    Refuses the whole migration if any term has no successor, rather than doing the part it can:
    a store half in one vocabulary is harder to reason about than one honestly stuck.
    """
    found = stale(st) if found is None else found
    undecidable = {t: became for g in found.values() for t, became in g.items()
                   if not isinstance(became, str)}
    if undecidable:
        raise SystemExit(
            "cannot migrate — these have no single successor, so what they meant has to be "
            "decided rather than computed:\n"
            + "\n".join(f"    {t}  ->  {_became(v)}" for t, v in sorted(undecidable.items()))
        )
    public = ", ".join(f"<{g}>" for g in st.graphs_of(PUBLIC))
    moved: dict[str, str] = {t: became for g in found.values()
                             for t, became in g.items() if isinstance(became, str)}
    for old, new in sorted(moved.items()):
        for subject, predicate, obj in (("<%s>" % old, "?p", "?o"),
                                        ("?s", "<%s>" % old, "?o"),
                                        ("?s", "?p", "<%s>" % old)):
            fresh = [p.replace("<%s>" % old, "<%s>" % new)
                     for p in (subject, predicate, obj)]
            st.update(f"""
                DELETE {{ GRAPH ?g {{ {subject} {predicate} {obj} }} }}
                INSERT {{ GRAPH ?g {{ {fresh[0]} {fresh[1]} {fresh[2]} }} }}
                WHERE  {{ GRAPH ?g {{ {subject} {predicate} {obj} }}
                          FILTER(?g NOT IN ({public})) }}""")
    return len(moved)


def check(st, migrating: bool = False) -> None:
    """Refuse to run on a store this vocabulary cannot read, or migrate it if asked.

    Loud rather than empty. An agent whose beliefs are spelled in a vocabulary the code no longer
    speaks does not fail — it finds nothing, keeps running, and bids on a target it cannot see.
    That is the failure mode this project keeps rediscovering, and the only remedy that works is
    to stop and say which terms and what they became.

    Migration is a flag and not a side effect, for the reason `rebirth` is: a persistent store
    rewritten by the mere act of starting is a thing nobody asked for, and doing it by accident
    is the bug the separation prevents.
    """
    found = stale(st)
    if not found:
        return
    if migrating:
        n = migrate(st, found)
        log.warning("migrated %d term(s) to this vocabulary:\n%s", n, _describe(found))
        remaining = stale(st)
        if remaining:  # a rewrite that did not take is worse than one that never ran
            raise SystemExit(
                "migration did not settle — still stale after rewriting:\n"
                + _describe(remaining))
        return
    raise SystemExit(
        "this belief base was authored against a vocabulary this code no longer speaks, and "
        "reading it would silently find nothing:\n"
        + _describe(found)
        + "\n\nSet OREXIS_MIGRATE_BELIEFS=1 to rewrite them in place, which changes how a value "
          "is spelled and never which value it is. `rebirth` would also clear this, and would "
          "throw away everything the agent revised for itself — see orexis/vocabulary.py."
    )

