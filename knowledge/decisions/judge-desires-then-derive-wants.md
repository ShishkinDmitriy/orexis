---
type: Decision
title: The road is two functions over the store, and a judgment is written down
description: >-
  The sovereign's shape for the road - functions over the triple store, each reading what it
  needs and writing its own graph with provenance and time, and the SHACL results in the
  store too. Two functions, one contract each - after the call, all of it is in the store.
  `judge_desires` judges every desire at the present and at every foreseen instant and writes
  the judgments as SHACL validation reports to a working graph, replaced whole - handed the
  engine, a pyoxigraph store, and nothing else; `derive_wants` mints the wants from that
  graph and nothing in hand. Refused - a view per instant, which the judgment's own instant
  makes needless; one union query over every desire, measured at thirteen times the cost;
  the verb "check", where the dictionary says judge; writing the urgency half now, which is
  the seam left open; a wrapper between the judge and the engine; the choir's judgment for a
  met-test the compiler refuses; and the present as an argument or a row. Each function is
  held to a snapshot of the store it leaves, and the eleven cases leave the wants the
  one-function road left.
status: accepted
timestamp: 2026-09-19T18:00:00Z
---

# The question

The sovereign, after the road's cases were held to snapshots of the whole store: make the road
functions over the triple store. Each reads what it needs and inserts into a graph of its own,
with provenance and time; the SHACL results go to the store as well; and a judgment says
satisfied or not, and only where not carries the results. A function is about ALL the desires
— it may iterate inside where that is better — and the contract is only that after the call,
everything is in the store.

# The decision

**Two functions, each a file of its own — `judge_desires.py`, `derive_wants.py` — one contract each**, and a third beside them since, `scope_actions.py`, which writes the scopes the derivation clusters by.

- `judge_desires(store)`: every desire's compiled met-test run over the graphs holding at the present
  and at every prediction's start, and the answers written as one `deliberation:Judgment` per
  desire per instant — a `sh:ValidationReport`: `sh:conforms` true is met, false is unmet, and
  only an unmet one carries `sh:result`s, each naming the focus node, what it is about, which
  block refused it and the offending value. The instant rides on the judgment as
  `orexis:holdsAt`, absent for the present, exactly as a want's does. The graph,
  `deliberation:JudgmentGraph`, is written whole and replaced on every run. **It is handed
  the engine — `pyoxigraph.Store` — and nothing else**, the sovereign's second ask: which
  graphs hold desires, which are predictions and which hold at an instant it asks of the
  catalogue in its own texts; who holds a desire it reads off `orexis:holds`, and writes one
  judgment graph per holder, named for the holder and owned by them; the shapes it parses
  once from the graphs of desires and wants; and the present is the clock's, the layer's one
  read of time. A store holding several agents' desires — the test fixture's, never a
  volume's — is judged for each holder over what that holder owns and what nobody does.
- `derive_wants(agent)`: the judgments read back — and nothing in hand — grouped by scope and
  instance under each desire, the earliest instant per cluster, and a want minted where none
  stands, by the same `mint` as before. A desire unmet at the present derives wants at no
  instant; one met at the present derives them at the instants it foresees unmet.

**The judgment graph is a working graph**, like the deliberation trace. The bundle keeps only
testimony as record and a judgment is a conclusion; so it is never carried into a possible
world and never a record, and it earns its place the way the trace does: it is the evidence a
reader outside the process cannot recompute, since the belief base is locked by the process
holding it, and what the snapshots show beside the wants.

**Each function has its own cases and is held to a snapshot** of the store it leaves. A case
in `packages/orexis-agent-deliberation/tests/judge_desires/` is a world as an agent finds it;
one in `packages/orexis-agent-deliberation/tests/derive_wants/` is the judged state alone — the judgments, the desires, the levers whose effects say what a
scope is, whatever stands — and nothing of the world that was judged, so a case that gave the
function more would not be testing its contract. Beside each, `<case>.snapshot.trig` is the
whole store afterwards in the case's own order, and `diff` of case against snapshot is what the
function did. All eleven cases leave the wants, classifications and periods the one-function
road left.

# What was refused

**A view per instant.** [an-update-takes-no-dataset](/decisions/an-update-takes-no-dataset.md)
drew the road as updates on two conditions, one of them a copy of the world per foreseen
instant so the met-test could run inside one `GRAPH`. The judgment carries its instant, so the
dataset per instant is chosen where the record said choice must stay — the door, in Python —
and the derivation is a function of the judgment graph alone. The view is not needed.

**One query over every desire.** The compiler's own measurement stands: a single UNION of
every shape's select cost 843 ms on the simulation world where the selects asked one by one
cost 65. So judging iterates, one select per desire per instant, inside a function whose
contract is the whole.

**`check_desires`.** The dictionary's verb for running a met-test against the world is judge —
a desire is declared and a judgment is made, the SHACL seat is `judge.py` — and *check* is the
repo's word for a boot gate. The confusion between the verb and the noun dissolves because the
stored thing is the judgment.

**Writing the urgency now.** A judgment has two halves: what the met-test read, and how badly
the thing is wanted. The first is written; the second is still the choir's answer, assembled
per pass by `agent.judgments`. Folding them is the seam below.

**A Python object for a stored judgment.** The first cut had one, and a collection over it,
named apart from the choir's `Judgment` to avoid the clash — a second word for one thing. The
sovereign asked whether it was needed at all, and it is not: `judge_desires` hands the
engine's own rows to `save_judgments`, and `derive_wants` reads the graph back with one
SELECT (`judgments.py`). Nothing stands between the two functions but the store.

**A wrapper between `judge_desires` and the engine.** The first cut took the agent and reached
through it for the belief base, the desire collection, the choir and a cache — four ways of
not being a function over the store. The sovereign asked for the engine alone, and everything
the four supplied was in the store already: the catalogue says which graphs are which and when
they hold, the desire graph says who holds a desire, the predictions' periods say what is
foreseen. What the wrapper still owns is a cached view of the catalogue it cannot see a
foreign write invalidate, so it is handed out through `Store.engine`, which forgets what the
store learned by asking and tells no listener — a write through the engine is not an event the
wrapper emits. Measured on the simulation store, five holders and twelve roots: 45 ms a run.

**The choir's judgment for a met-test the compiler refuses.** A desire the compiler could not
compile was judged by the container's `pursuing()` and derived its one want about everything —
a voice a function over the store has no way to ask. Every shipped met-test compiles, so the
fallback stood for no desire; such a desire is not judged now, and the log says so. The
matching branch in `derive_wants` — a present judgment unmet with no result — is dead until
that function is treated the same way.

**The present as a second argument, or as a row.** One argument was the ask, and the instant
is not the store's to state: a row saying *now* is the interpreter asserting what it already
knows (model-it-only-if-a-plan-would-branch-on-it), and the paced clock is a deployment fact
the mind cannot ask for. `clock.now()` is the one read outside the store.

# Seams left open

- **The urgency half.** A package's urgency written on the judgment it belongs to, and the
  container's `Judgments` reading the store rather than asking the choir — which flips the
  principle that a collection over contributed answers is handed the agent, on purpose.
- **`derive_wants` and `scope_actions` over the engine.** Both still take the agent, and
  `find_judgments` reads through the wrapper; the second function writes wants, which the
  keeper's conditions read, so whether a write through the engine should reach `on_write`
  is decided when it goes.
- **`derive_wants` as one update.** The scope partition is data now — `scope_actions`, a
  third function, writes it at boot as the scope graph, and `derive_wants` reads it — so what
  is left of the trial the update record proposed is the derivation itself as an update.
- **Every desire, on every call.** A pass standing on one root, and the ledger writing one debt,
  judge and derive every desire — one select per desire per instant, milliseconds each. The
  first measurement found the cost elsewhere: the two carves of a shape parsed the whole
  belief base once per root and once per want, half a second each, which judging every desire
  multiplied by the number of desires; they parse the desire graphs alone now, and a fresh
  agent's first judge and derive fell from 4.8 s to 0.6 s. What a world with many desires and
  many predictions pays per pass in the selects themselves is still unmeasured.
