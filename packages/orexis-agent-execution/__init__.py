"""The manifest: the execution layer — what an agent does with a plan once it has one.

The bottom of Agent 2.0's stack and the successor of `orexis-agent-progression`, which it
replaces rather than extends. What it holds:

- the **keeper** — the ledger of what this agent is committed to, over the intentions store
  (`keeper.py`), and `plans.py`, the one function that copies a found plan into that ledger;
- the **store** — the free functions a reader needs over a `pyoxigraph.Store`: the catalogue,
  the graphs of a kind at an instant, the binder, the prefixes (`store.py`);
- the **vocabulary** — the kernel's terms and the graph classes every layer writes in
  (`ontology.py`, `graphs.py`, `ontology.ttl`);
- the **act** — what a step is made of and how its facts are carried (`act.py`);
- the **shape compiler** — a shape as the select whose rows are its violations
  (`violation.py`);
- the **clock** — one timeline, which may run fast (`clock.py`).

**A STORE IS A `pyoxigraph.Store` AND NOTHING IS WRAPPED AROUND IT.** That is the whole
difference from progression, and it is the reason this package exists rather than an edit to
that one. Progression's `Store` class owned a catalogue index, a memo and a class hierarchy it
had read once, and handing the engine out meant forgetting all three, because a wrapper cannot
see a write it did not make. Here every read is a function handed the engine and told what it
is reading — `query(engine, text, graphs)`, `graphs_of(engine, KIND)` — so there is nothing to
forget and nothing to hand out. See knowledge/decisions/an-agent-is-four-things.md.

Not a capability: nothing grants it and there is no `provides()` here. It imports nothing of
this repository's but `assembly`.
"""

from pathlib import Path

from assembly import contributes, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    """the layer's own words (#529)."""
    return [package / "ontology.ttl"]
