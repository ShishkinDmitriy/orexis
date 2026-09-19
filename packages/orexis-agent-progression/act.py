"""A step: a planned instance of an action. An act: the record that a step was taken.

An `orexis:Action` is a template (a precondition, an effect, a taker). A STEP is one filling of
it, planned and not yet done — the lever it goes through, the want it serves and what that want
is about, how much, for whom where it is an obligation's, its window, what the search predicted
taking it would reach, what it waits for, what follows. A plan is steps; an intention commits to
steps; a claim promises one. Nothing has happened yet. An ACT is the record that something did:
which step, when, whether anyone took it, and in time the verdict — history, and only history
(the sovereign's ruling, 2026-09-02: a plan is not executed, so its elements are not acts).
One step may be attempted more than once; each attempt is an act. See knowledge/domain/step.md,
knowledge/domain/act.md and knowledge/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from orexis_agent_progression.ontology import PUBLIC


@dataclass(frozen=True)
class Step:
    """One action, filled in and planned. Every step is an instance and no code names one."""

    action: str                       # which template — `market:Acquiring`, `actuation:Dosing`
    via: str                          # the lever it goes through — this venue, this valve
    want: str | None = None           # the desire it serves, by node
    about: str | None = None          # what that want is about (`orexis:about`), opaque here
    quantity: float | None = None     # how much, sized by the taker — nothing, for a look
    direction: str | None = None      # which way it moves what it is about, where it moves
    for_agent: str | None = None      # whom it serves, where it is an obligation's
    #  The window: when taking it counts. Not-after is what every hand-kept timer was saying
    #  (a bid not after the round closes, a serve not after the claim's expiry); not-before is
    #  the half nothing writes yet — where a held claim spent later would arrive.
    not_before: datetime | None = None
    not_after: datetime | None = None
    urgency_after: float | None = None  # the want's urgency in the world this step was predicted to reach
    predicts: tuple | None = None     # (adds, retracts): the canonical facts the search said this
                                      # step makes true and false — what the world is held to (#510)
    precondition: frozenset | None = None  # the canonical facts its rules READ in the world it
                                           # was planned from (#550)
    part_of: object = None            # the step this one was expanded from (#523): a Step while
                                      # planned, the ledger's step IRI once read back

    @classmethod
    def from_row(cls, row, quantity: float | None = None, not_after: datetime | None = None):
        """An affordance row, filled: sized, and windowed where the caller knows when. Handed
        a step already, it fills that one again — a search re-sizes a step it takes from a
        different world."""
        return cls(action=row.action, via=row.via, want=row.want, about=row.about,
                   quantity=quantity, direction=row.direction, for_agent=row.for_agent,
                   not_after=not_after)


@dataclass(frozen=True)
class Act:
    """The record that a step was taken: which step, when, and whether anyone took it. Written
    by execution into the ledger the moment the actors have been asked; the verdict on what
    the world made of it lands beside it when the world answers."""

    step: str                         # the ledger's step node, by IRI
    taken_at: datetime
    took: bool                        # some actor took it, or none could now — standing


def predicts_json(predicts) -> str:
    """The step's predicted diff as one literal for the ledger: two lists of canonical facts,
    exactly as `signature.facts` states them, so a step read back from the ledger can be
    checked against the world without an imaginarium."""
    import json
    adds, retracts = predicts
    return json.dumps({"adds": sorted(map(list, adds), key=repr),
                       "retracts": sorted(map(list, retracts), key=repr)})


def precondition_json(facts) -> str:
    """A step's precondition as one literal for the ledger: the canonical facts its rules
    read, stated as `signature.facts` states them, sorted so two writes of one set agree."""
    import json
    return json.dumps(sorted(map(list, facts), key=repr))


def precondition_from_json(text: str) -> frozenset:
    import json

    def tup(x):
        return tuple(tup(y) for y in x) if isinstance(x, list) else x
    return frozenset(tup(f) for f in json.loads(text))


def predicts_from_json(text: str) -> tuple:
    import json

    def tup(x):
        return tuple(tup(y) for y in x) if isinstance(x, list) else x
    d = json.loads(text)
    return (frozenset(tup(f) for f in d["adds"]), frozenset(tup(f) for f in d["retracts"]))


def method_of(query, action: str) -> list[str]:
    """The actions an action's `orexis:method` names, in list order (#523) — walked from the
    list's head, since a property path loses the order. Empty for an action with none, which
    is its own one step. Asked of the belief base, where the action graph is."""
    rows = list(query(f"""
SELECT ?head ?node ?first ?rest WHERE {{
  <{action}> orexis:method ?head . ?head rdf:rest* ?node . ?node rdf:first ?first ; rdf:rest ?rest }}""")["results"]["bindings"])
    if not rows:
        return []
    first = {r["node"]["value"]: r["first"]["value"] for r in rows}
    rest = {r["node"]["value"]: r["rest"]["value"] for r in rows}
    out, node = [], rows[0]["head"]["value"]
    while node in first:
        out.append(first[node])
        node = rest[node]
    return out


def takers_of(agent, action: str) -> list:
    """The modules that carry an action out: whoever contributes it, or — for an action with
    a method — whoever contributes any step it comes to, since an abstract action is taken
    through its steps (#523). Who sizes a bid is who tenders it."""
    actions = [action] + method_of(agent.beliefs.reader(PUBLIC), action)
    return [m for m in agent.modules if any(m.answer(a) is not None for a in actions)]
