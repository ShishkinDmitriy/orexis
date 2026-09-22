"""Running one action's effect INTO a named graph — the act, where `effects.py` beside it
holds the questions.

**TWO HALVES THAT ARE NOT THE SAME KIND OF THING.** `sh:construct` is SHACL-AF's and holds a
query yielding the triples applying the action would ADD, asked of the world the step is taken
in. `orexis:retracts` is ours, because the standard has none, and holds a `DELETE … WHERE`
naming `GRAPH $state` — an ACT, run against the world the step MAKES. The asymmetry is the
domain's: what an effect adds is concrete, and what it takes away is whatever is standing in
that place, which nobody can name in advance.

**ITS OWN FILE BECAUSE IT IS ITS OWN ACT.** `effects.py` answers questions about an action and
writes nothing — its row, what it costs, how long it takes to land. This writes, and the two
things a caller would otherwise have to know to do it right are here rather than at the call
site: that retraction precedes addition, and that `$state` means a DIFFERENT graph in each
half. Both are facts about what an effect IS.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from orexis.agent.store import Raw, add_quads, bind as bind_text, construct, update

from .effects import over, rule_for

log = logging.getLogger("apply_effects")


def apply_effects(store, action: str, into: str, graphs=None, *, memo=None, **bind) -> bool:
    """Run one action's effect INTO the graph `into`: what it makes true added there, what it
    replaces deleted from it. Answers whether anything happened at all.

    **ONE ACT AND NOT TWO QUESTIONS.** It was `adds` and `retraction`, a list of triples and a
    bound update, which the caller then applied to a graph it had forked — three steps in which
    the caller had to know that retraction precedes addition and that `$state` means a
    different graph in each. The order and the binding are this module's business, because
    they are facts about what an effect IS.

    `graphs` and `bind` describe the world the step is taken IN: the construct is asked of it,
    and `$state` in `bind` names it. **The retraction is re-bound to `into`**, because that is
    what it deletes from — the one place the two halves differ, and the reason this is one
    function rather than a caller's three lines. Since `into` is a fork of that world the
    construct sees the same facts either way; what it must not see is the deletion, because a
    construct reuses the very node its retraction names and asking afterwards finds it gone.

    **`store` is whichever dataset the question is being asked ABOUT.** An actuator asks about
    the world it is standing in and passes its own belief base; a search passes the
    imaginarium, where `$state` names the world a node's path reached. Nothing here
    distinguishes them, and nothing should.

    `bind` fills the rule's placeholders the way every other shipped query here is filled:
    `$me`, `$subject`, `$property`, `$litres`. Substitution rather than SPARQL's own binding
    because the text is a literal in the graph and the engine takes a string.
    """
    rule = rule_for(store, action, memo)
    if rule is None:
        return False
    #  WHICH WORLD, IN THE LIST THE CALLER BUILT AND NOT IN THE TEXT (#666). `graphs` carries
    #  the readings a rule's patterns read — this agent's own where a caller means "here", a
    #  node's where a search means "there" — and the rule names neither.
    added = _run(store, rule.get("construct"), bind, graphs)
    retract = _retraction(rule.get("retracts"), into, bind)
    if not added and retract is None:
        return False
    if retract is not None:
        try:
            update(store, retract)
        except Exception as exc:                                    # noqa: BLE001
            #  A rule that will not run is a package's bug and must not take an agent down:
            #  the lever still works, and what is lost is a world holding two readings where
            #  it should hold one — which is the exact failure the retraction exists to close.
            log.error("an effect's retraction would not run, so it retracts nothing: %s", exc)
    node = ox.NamedNode(into)
    add_quads(store, (ox.Quad(t.subject, t.predicate, t.object, node) for t in added))
    return True


def _retraction(text: str | None, into: str, bind: dict) -> str | None:
    """One action's `orexis:retracts`, bound to the graph it deletes from — or None.

    **IT IS AN UPDATE AND NOT A QUESTION.** `orexis:retracts` holds a `DELETE … WHERE` naming
    `GRAPH $state`. It was a CONSTRUCT whose triples the caller removed by term; what that
    bought — a materialised diff — is wanted by `execution:predicts`, which this tree does not
    write, and by an emptiness test the world's own hash already answers.

    IT READS THE WORLD AND NOT THE DATASET, which is what the change cost. A CONSTRUCT was
    handed the whole graph list the runner built; an UPDATE's WHERE reads the unnamed default
    graph unless `USING` says otherwise, and `Store.update` takes no dataset — so a retraction
    names `GRAPH $state` in both halves and sees only the world it deletes from. Public
    knowledge holds no readings, so nothing shipped here wanted more; a retraction that needs
    to join the vocabulary is the case that would bring `USING` back.

    `orexis:retracts` exists because SHACL-AF has no deletion, and it is not optional: the
    sensed graph upserts one observation node per (subject, property), so an effect predicting
    a reading that did not retract the node it replaces would leave two results on one node.
    """
    if not text:
        return None
    try:
        return bind_text(text, **{**bind, "state": Raw(f"<{into}>")})
    except Exception as exc:                                        # noqa: BLE001
        log.error("an effect's retraction would not bind, so it retracts nothing: %s", exc)
        return None


def _run(store, text: str | None, bind: dict, graphs=None) -> list:
    if not text:
        return []
    try:
        return list(construct(store, bind_text(text, **bind), over(store, graphs)))
    except Exception as exc:
        #  A rule that will not run is a package's bug and must not take an agent down: the
        #  lever still works, and what is lost is the ability to reason about it in advance.
        log.error("effect rule for this means would not run: %s", exc)
        return []
