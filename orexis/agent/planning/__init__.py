"""The manifest: the planning layer — what an agent should do, by a bounded search.

The top of Agent 2.0's stack and the successor of `orexis-agent-deliberation`, which it
replaces rather than extends. One pipeline, and the package is what it is made of:

1. **the derivation** — `derive_wants` judges every desire at the present and at every instant
   a prediction reaches, and mints a want per cluster of what the met-tests read unmet;
   `withdraw` is its other half, taking away what the same rows no longer imply, one want at
   a time by `forget_want`; both read the ground standing at each instant, `world_at`;
2. **the scopes** — which predicates move together, read off what each action and each
   derivation touches (`touches.py`). A want is minted per scope of witnesses and searched
   in a world of its own (`scope_actions`, `scopes.py`);
3. **the imaginarium** — a store per scope, filled from the beliefs by `prepare_ground` and
   given its timeline by `lay_ground`, one ground per period a prediction makes;
4. **the search** — the Planner's own methods, `search` per want and `expand` per
   iteration, sequencing the acts: `admit` writes what the cheapest open world admits, `take`
   forks each candidate and writes the world's row, `weigh` judges what was reached and
   writes what it found, and `extract_plan` writes what the want's weighings come to. THE
   FRONTIER IS A QUERY: what is true of a world whoever asks is on its row, what a want's
   search worked out about it is a `planning:Weighing` — met there, on the frontier, opened —
   and a candidate passed over is weighed too, so a search called again on the same
   imaginarium takes up where it stopped. THE DERIVATION READS WEIGHINGS TOO: the Planner
   weighs every desire in every ground by the same `weigh`, and `derive_wants` reads the
   violation rows back to mint its wants — one judgment, one node, at two grains.

**A STAR, NOT A CHAIN.** `planner.py` sequences the acts and is the one module the rest of the
tree imports; an act calls no other act, and what it needs of another's work it reads off the
rows the other wrote — `unweighed` says what a pass weighs next, `world_at` what a rule reads
in a world. `tests/test_layout.py` holds that as imports.

**A FUNCTION STARTS IN THE STORE AND ENDS IN IT**, and takes the names of what it is about:
`weigh(store, want, world)`, `take(store, candidate, me)`, `admit(store, world, me)`. What one
act needs from another it reads off the rows the other wrote, so nothing is a Python value in
flight and the two classes that were (a candidate, a witness) are rows.

NOTHING COMES BACK. What a pass finds it READS OUT of the worlds it walked
(`extract_plan.py`): each possible world says which CANDIDATE reached it and the candidate
says which world it was taken in — candidates connect possible worlds — so a plan is one
world's ancestry: a `planning:Plan` graph per want, a step per candidate on it in the
LEDGER's own words, and why the pass ended. Then it hands them down, which is
`publish_plan.py` and the last act of a pass, since the imaginarium is memory and an
intention is all that outlives it. There was a Python record beside it saying the same thing, so the finding
existed twice and only one of the two could cross a layer — and the half a want most needs,
that no lever this agent holds points at it, was the half that could not. What happens to a
plan is the execution layer's: `plans.copy_plan` copies the graph into the intentions store.
Nothing here commits, because deciding a thing and remembering that it was decided are
different acts.

**WHAT THE PREDECESSOR HELD AND THIS DOES NOT.** It was twenty-nine modules and seven and a
half thousand lines; this is about three thousand, in modules named for what they do. Every absence is a thing that
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
- **`Beliefs` the class** — of which only the pick machinery was ever wanted, and only for
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

from .planner import Planner

#  THE ONE NAME THE REST OF THE TREE MAY USE. Every other function here is public to the
#  PACKAGE — tested by name, called by its siblings — and nothing outside it; a container
#  builds a `Planner` and calls `plan`, and `tests/test_layout.py` holds the tree to that.
__all__ = ["Planner"]
