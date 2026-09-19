---
type: Decision
title: The road is two functions over the store, and a judgment is written down
description: >-
  The sovereign's shape for the road - functions over the triple store, each reading what it
  needs and writing its own graph with provenance and time, and the SHACL results in the
  store too. Two functions, one contract each - after the call, all of it is in the store.
  `judge_desires` judges every desire at the present and at every foreseen instant and writes
  the judgments as SHACL validation reports to a working graph, replaced whole; `derive_wants`
  mints the wants from that graph and nothing in hand; `scope_actions` writes the partition
  they cluster by. All three are handed the engine, a pyoxigraph store, and nothing else. Refused - a view per instant, which the judgment's own instant
  makes needless; one union query over every desire, measured at thirteen times the cost;
  the verb "check", where the dictionary says judge; writing the urgency half now, which is
  the seam left open; a wrapper between any of the three and the engine; the choir's judgment
  for a met-test the compiler refuses; a holder argument; and the present as an argument or a
  row. The FORESIGHT is deleted: the judgments already say which instants fail, and the
  drifts' horizons say how far ahead the agent sees. Each function is
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
- `derive_wants(store)`: the judgments read back — and nothing in hand — grouped by scope and
  instance under each desire, the earliest instant per cluster, and a want minted where none
  stands. A desire unmet at the present derives wants at no instant; one met at the present
  derives them at the instants it is judged unmet. **The engine and nothing else**, like the
  function before it: each judgment graph says whose it is, so the wants a holder's judgments
  imply are written where that holder's belong; what a desire is about and what its met-test
  says come from the graphs of desires, what already stands from the graphs of wants, and how
  long a plan is given after its instant from the pick record. Where `Wants.save` wrote a want,
  `wants.save_want` writes it over the engine and the collection calls the same function, so
  where a want is kept stays in one file (#677).
- `scope_actions(store)`: the actions clustered into the scopes their effects join, written as
  one scope graph. **The engine and nothing else**, and it names no agent at all: the partition
  is a function of the actions the store holds and the derivations loaded, and every agent
  reading one store would compute the same one, so there is nobody to name it after.

**The derivations' edges are in the store, put there by genesis.** The partition joins
predicates wherever one action *or one derivation* reads or writes both; the actions were rows
in the store all along and the derivations were rule texts on disk, which `scope_actions` read
through the loader. `genesis.describe_derivations` now computes each loaded rule's read and
write predicates where the rules are already being read and run, and writes them to a public
graph — public because the loaded rule set is the same for everyone reading the store, exactly
as the actions are, and computed, so it is cleared and rewritten on every refresh. A side whose
predicates cannot be read says `deliberation:Anything` and joins everything, as it always did.
The edges the store gives back are the edges the files give, measured as multisets on the
simulation world.

**The foresight is gone.** A desire met now and judged unmet at a foreseen instant derived a
want only if that instant was nearer than `sensing:foresightS` — a per-agent pick, asked of
the choir at derivation time. The sovereign, on being shown what the function reached for:
*derive_wants should accept only judgments; it is just decomposition of judgments into wants*.
The judgments already say which instants fail and when, and how far ahead the agent sees is
said by the drifts, each declaring the horizons it predicts at (1 hour, 5 hours, 24 hours in
every shipped package). The pick was measured to have exactly two states in practice —
unbounded for the market's root and absent everywhere else, absent meaning *never derive a
foreseen want* — so it was an on/off switch wearing a horizon's name, and no shipped world set
it. Deleted with it: `orexis:foresight` the extension point, `orexis:foresees` the kernel
property, `sensing:foresightS` the pick, both packages' answers, and the injection in seven
test files. What replaces it is nothing: a want is derived at every instant a judgment says a
desire fails.

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

**A holder argument, so a store with several agents' desires derives for one.** A volume
holds one agent (rule 4), so the question only arises in a test fixture that births a whole
world into one store — and there the answer is that every holder's judgments are judged and
every holder's wants derived, each into graphs that holder owns. What the fixture exposed
instead was a reader that had stopped saying whose it meant: `Wants` names its own graphs in
its own text and so lost the owner clause `graphs_of` applies to every read that goes through
it. It asks for its own again, which is what one agent, one volume always meant.

**Keeping the foresight by writing it down.** The first cut had sensing own a graph of
`orexis:foresees` rows, rewritten whenever the pick moved, and the market state a constant in
its rule — a graph class, a writer, a revision hook and a rule clause to express *never* and
*no filter*. It was built and then deleted when the sovereign asked what the number was for.

**The present as a second argument, or as a row.** One argument was the ask, and the instant
is not the store's to state: a row saying *now* is the interpreter asserting what it already
knows (model-it-only-if-a-plan-would-branch-on-it), and the paced clock is a deployment fact
the mind cannot ask for. `clock.now()` is the one read outside the store.

# Seams left open

- **The urgency half.** A package's urgency written on the judgment it belongs to, and the
  container's `Judgments` reading the store rather than asking the choir — which flips the
  principle that a collection over contributed answers is handed the agent, on purpose.
- **A write through the engine announces nothing.** `Wants.save` tells its listeners and the
  desire modality rebuilds; the road writes through `wants.save_want` and tells nobody, so
  `pursuit.derived` rebuilds the projection when something was minted. One caller does it
  today. Whether the store should emit an event for a write it did not make — `on_write` has
  the same gap — is not settled here.
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
