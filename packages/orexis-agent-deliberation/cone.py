"""The cone: the tree of possible worlds a pass builds under the present, as its two records.

What a cone HOLDS lives here — a node, and what the pass compiled once to judge every node by.
What a cone is FOR is `planner.py`, which grows it, re-roots it and searches it; the graphs its
nodes name are the imaginarium's. The three are one pass's machinery seen from three sides, and
this is the side that is data: neither record decides anything, and both are read far more
often than they are written.

They are `_`-private because nothing outside the search constructs one — a plan is what leaves
this package (`plan.py`), and a node is how the search got there.

See knowledge/domain/cone.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from orexis_agent_progression.ontology import STATE_GRAPH

from . import signature


@dataclass
class _Node:
    """One point in the search: a world, how it was reached, and what it is worth.

    The world is held ONCE, in the imaginarium, and `graph` names it — what the next step's
    rule reads and where its `$state` points. `readings` is that same graph as N-Triples text,
    written by the store's own engine, because the judge takes text at the border.

    It used to be held TWICE: the imaginarium graph AND the whole world flattened into an
    rdflib graph per node, which was 198,144 `Graph.add` calls and fifty-five percent of a
    hanoi solve — a full copy of a 2,300-triple world to express a step that changed four
    triples. The flat copy existed because pySHACL read rdflib; nothing does now (#481). What
    is left per node is the node's OWN readings, which is what actually differs: everything
    else a judged world holds is the same for every node in the pass and is written once, in
    `_begin`. See knowledge/runbooks/measure-the-search.md.
    """

    #  This node's graph as N-Triples, or None until somebody asks. LAZY since the measure
    #  that named it: a 3-disk solve forks 76 worlds and READS one — only a judged world needs
    #  text, and a want met by a pattern is judged by the store's own engine at `graph`, so
    #  most worlds are scored, weighed and discarded without ever being written out.
    readings: str | None = None
    graph: str = STATE_GRAPH                     # this node's readings, in the imaginarium
    judged: str | None = None                    # for a want met AT an instant: this world drifted to it (#619)
    taken: tuple = field(default_factory=tuple)   # the STEPS taken to get here, in order
    urgency: float = 1.0
    #  The net diff against the base world, in canonical facts — HALF of where this node is,
    #  the other half being `ground` (#587). The root stands nowhere but the world itself, so
    #  its diff is empty.
    diff: tuple = signature.EMPTY
    #  WHAT THIS WORLD IS PREDICTED ON (#587): the world's own branches taken to reach it —
    #  the happening edges, where `taken` holds the chosen ones. A step inherits its parent's;
    #  a prediction extends it. EMPTY is the present, observed, which is every node's ground
    #  until something predicts (#589), so a pass has one ground and `signature.where` is the
    #  diff it always was. Two worlds holding the same facts under different predictions are
    #  two worlds, because what happens next differs: a bed vented onto a warm afternoon is
    #  not the same world as the same bed vented onto a cold night.
    ground: tuple = ()
    #  Seconds after commitment this path's LAST world-change completes — each step's own
    #  `orexis:landsAfter`, summed, for holding a candidate to a Within want's room (#472).
    #  The root has taken nothing and lands immediately. NOT part of where this node is: a
    #  clock alone separates nothing, since what a later world holds differs only where
    #  something says the world moved, and that is the ground's to say.
    landing: float = 0.0
    #  What this world still owes the want, by the want's own declaration (`orexis:estimates`),
    #  or None where it declares none. Never compared across desires — only between worlds of
    #  one pass, which is the only comparison it means anything for.
    estimate: float | None = None
    #  What this path SPENDS, in the wallet's unit — each step's own `orexis:costs`, summed
    #  (#466). Free is the reading of an action that declares none.
    cost: float = 0.0
    #  The root-level candidate this path came through — see `Plan.origin`.
    origin: str | None = None
    #  THE CONE (#553): a node is its parent plus its two lists, and the graph is a cache.
    #  `added`/`retracted` are the raw triples the step's rules answered — identity and
    #  datatypes intact, which is what re-making the graph needs and what the canonical
    #  `diff` deliberately drops. `expanded` says whether the search has taken every row from
    #  here; `met` whether this world met the want when it was settled.
    #
    #  `added`, `retracted` and `materialised` were here because a world's graph was DROPPED
    #  once expanded and re-made from the nearest kept ancestor — the two lists were what
    #  re-made it. Worlds are kept now (`Planner._release`), so a graph is there for as long
    #  as the node is and the lists had nothing left to do. They were a memo either way: a
    #  step's diff is what its own rules produce from its parent, and the step's row in the
    #  store already names the action and every binding they take.
    parent: object = None
    changed: frozenset = frozenset()     # the PLACES the steps on this path changed (#643)
    expanded: bool = False
    menu: frozenset = frozenset()        # the rows this node was expanded with, for a resumed pass to compare
    met: bool = False
    legal: bool | None = None            # the society's verdict on this world, once asked
    #  A SURPRISE IS READ BY WHAT WAS NOT IMAGINED (#570): `verdict` is why this world, once
    #  forked, was refused a place on the frontier — forbidden, late, dearer than the bound —
    #  and None for a world the search kept; `withheld` is the rows this node never forked,
    #  with why — the budget spent, or dearer than the bound before simulation. A node is
    #  FULL when it is expanded and withheld nothing.
    verdict: str | None = None
    withheld: list = field(default_factory=list)


@dataclass
class _Compiled:
    """What a pass works out ONCE about the want and the world it stands in, and then only reads.

    Its lifetime is the CONE's, which is why it is one object: born in `_begin`, read by every
    pass that resumes the cone, and dropped whole by `reset()`. Fourteen fields sat on the
    planner before, written in one method and read in twenty, so what `reset()` forgot and what
    it left behind could only be established by reading all of it. Nothing here is written after
    `_begin` returns; what a pass or a re-root moves (`_base_facts`, `_invariant_text`, the
    frontier) is the planner's and stays there.
    """

    #  The wants, snapshotted: the graphs they came from, and the same triples as one rdflib
    #  graph, because a cbd walks blank nodes and the carves want one.
    want_graphs: tuple = ()
    shapes: object = None
    #  The flat belief world the pass judges against, and the shapes this agent holds, carved
    #  from it after the wants joined it (#547).
    base: object = None
    held: object = None
    #  Which beliefs are upserted and by what (`orexis:keyedBy`), and what each want is about:
    #  read once so the signature canonicalises a reading without this file knowing what one is.
    keys: dict | None = None
    about_of: dict = field(default_factory=dict)
    #  The pass's `Afforder`: the templates and what the agent holds, read once. The WORLD is
    #  not here — it is a parameter of each ask, so a search hands it a fresh `Affordances` per
    #  node (an-afforder-is-a-service-between-two-collections).
    afforder: object = None
    #  THE LAW THIS PASS PRUNES BY (#468) and its compiled selects, and the legality check's
    #  (#548) — None and empty where the world ratifies no such shape, and then it costs nothing.
    law: object = None
    law_selects: dict = field(default_factory=dict)
    legal: dict = field(default_factory=dict)
    #  Every graph a judged node's world holds besides the readings (#481).
    invariant_graphs: tuple = ()
    #  The want's violation select (#497), None where the want is not a shape; the levers that
    #  could serve it (#488) and what the menu is asked for, None meaning every row; and the
    #  predicates its closure names (#554, #565), None meaning every fact.
    unmet: object = None
    relevant: object = None
    asked: object = None
    view: object = None
