"""The manifest: the planning layer — what an agent should do, by a bounded search.

The top of Agent 2.0's stack and the successor of `orexis-agent-deliberation`, which it
replaces rather than extends. One pipeline, and the package is what it is made of:

1. **the derivation** — `derive_wants` judges every desire at the present and at every instant
   a prediction reaches, and mints a want per cluster of what the met-tests read unmet;
   `forget_wants` is its other half, withdrawing what the same rows no longer imply
   (`derive_wants.py`, `forget_wants.py`, `want.py`, `wants.py`);
2. **the scopes** — which predicates move together, read off what each action and each
   derivation touches. A want is minted per scope of witnesses and searched in a world of its
   own (`scope_actions.py`, `scopes.py`, `relevance.py`);
3. **the imaginarium** — a store per scope, filled from the beliefs by `init_imaginarium`,
   holding one graph per world the search reaches (`imaginarium.py`, `signature.py`);
4. **the search** — best-first over those worlds: what a world affords (`steps.py`), what a
   step would change (`effects.py`), whether the want is met there (`planner.py`), and what
   was found (`plan.py`).

What comes back is a plan, written into its imaginarium's own graph in the LEDGER's words.
What happens to it is the execution layer's: `plans.copy_plan` copies it into the intentions
store. Nothing here commits, because deciding a thing and remembering that it was decided are
different acts.

**WHAT THE PREDECESSOR HELD AND THIS DOES NOT.** It was twenty-nine modules and seven and a
half thousand lines; this is fourteen and under four thousand. Every absence is a thing that
returns attached to whatever needs it, never a thing quietly lost
(an-agent-is-four-things):

- **the `Deliberator`** — the mind's whether and its clock, which asked the search on the
  agent's patience. A container calls `Planner.plan` now.
- **`pursuit`** — plan, commit, hand down. The commit half is the execution layer's; there is
  nothing yet to hand down to.
- **`considering`** — the collection that presented what an agent was considering, and the
  `Desires` projection it read. The search reads the desire and want graphs straight out of
  the beliefs store, which is what removed the projection's whole reason to exist.
- **the `reviser`** — the belief-revision thread that marked a want when something moved.
- **`Beliefs` the class** — of which only the picks machinery was ever wanted, and only for
  one number.
- **the judge** (`conformance`) — it belongs at the gates, where a world is entire and the
  question can be asked at all. What the search reads is the SELECT a shape compiles to, which
  is the execution layer's `violation`.
- **the relevance closure, the cone, remembered plans and the trace** — a narrowing, a resume,
  a reuse and a record. Three are speed and the fourth is for a reader; none of them is what a
  plan IS.

NOTHING IS CONTRIBUTED AND NOTHING IS GRANTED. This carried a `@contributes(VOCABULARY)`
manifest, which is how the 1.0 assembly discovers a package's ontology by walking `packages/`.
This tree is not under `packages/` and does not ask that loader anything: `orexis.agent.store`
reads the ontologies of its OWN tree, so a subtree arriving as its own distribution brings its
words with it and no registry learns its name.
"""

