---
type: Decision
title: A root holds always, and an outdated graph is dropped
status: accepted
timestamp: 2026-09-13T21:00:00Z
description: >-
  The sovereign's ruling of 2026-09-13, in the same discussion that moved the drift into
  sensing. A root desire is declared, not rebuilt from beliefs: authored once at genesis into a
  graph of the agent's own with NO period, which holds at every instant as the T-Box does, and
  endowed on amendment. Everything sourced at a time — a pursued child, an obligation, a call, a
  promise, a prediction, a round, a cooling row, a held claim — is a graph holding during a
  period, and ONE sweep drops any graph whose end has occurred, whatever its kind, after the
  verdict it leaves is written for the reviewer. Staleness is the first prediction dropped
  with no reading to replace it. Refused — a root re-derived at every rebuild, a horizon and a
  timer of staleness's own, and a sweep per kind.
---

# The claim

**A root is declared.** An `orexis:Desire` — the stake per property, the freshness desire per
sensor — is a declaration for the agent's whole life, and the modality re-derived it from
beliefs at every rebuild, carrying a foresight read off a pick. That made a root a function of
the agent's current state, which a root is not. It is authored once, at genesis, into a graph of
the agent's own with no period (`orexis:DesireGraph`), and a graph with no period holds at every
instant exactly as the T-Box does: a reader asking about any instant is handed it. It is
endowed on amendment — a never-held root arrives, a held one stays
([an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md)) — and a
rebuild never touches it. Foresight leaves the root and is read by the child's derivation at the
instant it derives. The argument of
[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
survives untouched: the sovereign's ranges are the source, genesis receives the root from them,
and an agent never authors one. What that record decided about the region — who works it out,
and that the how could differ — is about the met-test, which is still minted from the ranges.

**Only a child is built from a state at a time, and it says so with a period.** Everything
sourced at a time is a graph holding during its period
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)): a
[pursued](/domain/desire.md) child from its derivation to the instant it must hold at; an
[obligation](/domain/obligation.md) from its issue to its expiry; a [call](/domain/call.md)
until its round opens; a promise until the step above resolves; a
[prediction](/domain/prediction.md) during its window; a [round](/domain/round.md) during its
offer; a cooling row until its horizon; a held [claim](/domain/claim.md) until its window
closes. The rebuild of the desire modality then runs no rule: it is a projection of the roots
graph and the records, and nothing is deduced at runtime.

**An outdated graph is dropped, by one sweep.** The door already hides a graph outside its
period, so no reader ever depends on a sweep; the sweep is hygiene for a volume. One function,
in progression's housekeeping tick and at boot, drops every graph whose end has occurred,
whatever its class, and the sweeps each package kept — rounds expired, rows cooled, claims
lapsed, expectations forgotten — retire. The stretch record refused eager deletion, and that
refusal stands: it was about readings and the trend, which are the agent's history, and
lapsing and forgetting were two decisions. A want and a prediction are not history. What they
leave when they end is a VERDICT — a debt lapsed unserved, a step whose band never arrived, a
reading outside its set — and the verdict is written for the reviewer before the graph goes.
"A debt paid and a debt forgotten must not look alike" survives as: the ledger keeps the
verdict, not the want.

**Staleness is the first prediction dropped unreplaced.** A reading is evidence about now for a
bounded time, and the horizon that bounded it — the cadence in force plus the grace, an absolute
age for a device with no cadence — was sensing's prediction of the next observation event under
another name. The first prediction's window IS the horizon; its end is the one timer; the window
closing with no reading is what stale means, said once. `sensing:staleSince` stays the fact
readers ask, written at the instant the first prediction is dropped with no successor, since the
freshness want, the bidder and the actuator read a triple and should keep doing so. The
published horizon, the grace, the maximum age, the staleness timer and its handler fold into the
prediction's lifecycle.

# What was refused

- **A root re-derived at every rebuild.** A declaration recomputed from state is not a
  declaration; the identity was stable by accident and the content moved with a pick.
- **A horizon and a timer of staleness's own**, beside the prediction's window that says the
  same thing. Two mechanisms for one event is how the two drift apart.
- **A sweep per kind.** Each was correct and each was a copy; the lookup by period decides for
  every reader at once, and dropping what no reader is handed needs no knowledge of the kind.
- **Dropping without a verdict.** Refused with the stretch record: forgetting is a decision, and
  what is forgotten here is the want, never what it taught.

# What is built, in the order it is built

1. **Roots authored at genesis, and the rebuild a projection**
   ([#644](https://github.com/ShishkinDmitriy/orexis/issues/644), built): `orexis:DesireGraph`, a
   per-agent graph with no period; `genesis.author_roots` runs the packages' desire rules at
   birth and, at every boot, copies in only a root the volume never held; the modality's
   build is `Projection` and runs no rule; foresight left the root for the choir
   (`orexis:foresight`, sensing answering from its belief) and the aim left the label. The
   foresight has since left the agent altogether — a want is derived at every instant a
   judgment says the desire fails
   ([judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md)).
2. **Staleness as the first prediction's end**, inside the move of the drift
   ([#642](https://github.com/ShishkinDmitriy/orexis/issues/642)).
3. **Every want sourced at a time as a graph with a period, and one sweep**
   ([#645](https://github.com/ShishkinDmitriy/orexis/issues/645), built): a round, a held
   claim, a cooling row, a debt and a pursued child are each a graph of their own with a
   period — a round's from its offer to its close, a claim's from its claiming to its
   window's end, a cooling row's over the cooldown, a debt's from its issue to its expiry, a
   child's from its derivation to its instant plus the patience its plan is given after it —
   beside the prediction's window of #642; `Store.outdated` lists what has ended,
   `Store.drop_graph` drops one whole, and `upkeep.sweep` drops them all on the housekeeping
   tick and at boot, telling `orexis:outdated` first. `orexis:sweep`, `rounds.sweep_expired`,
   `sweep_cooled` and its timer, and the bidder's lapsed-claim sweep retired. A restart keeps
   what a graph said of itself at its write, so what lapsed while the process was down is
   found outdated and swept before the first pass. The ledger's keeper writes a debt's verdict
   — `market:dischargedAt` carried over, or `market:lapsedAt` — into the untimed obligations
   record before the graph goes, and `Ower.settled` is the sovereign's door to it.

# Seams left open

- **A root whose premise an amendment removed.** A property a subject no longer states a range
  for leaves a held root with no met-test; endowment adds and never removes, so removing a
  stake is a rebirth until somebody needs it not to be.
- **A frozen probe** ([#462](https://github.com/ShishkinDmitriy/orexis/issues/462)) stays fresh
  under this as under the timer: a reading that keeps arriving is inside its window.
- **Retention of verdicts.** How long the reviewer's evidence is kept is the review package's
  bound, and the stretch record's retention seam moves there.
- **A promise and a call end by an event, not by the clock** — the step above resolving, the
  round opening — so they stay rows in their untimed graphs, dropped by the event, and no
  period is said of them. A period whose end nobody knows at the write is not a period.
- **A child outlives its instant by the patience.** Its plan's last step is placed AT the
  instant and the verdict comes after; a child dropped at the instant would leave a standing
  plan pursuing a want nobody holds, and a second plan adopted beside it.
- **A record is read as it stands now, whatever instant is asked about.** The drift is
  evaluated at each window's far end, where a debt's own graph will have ended, and a debt
  standing today is an arrival at every later instant; a forecast the agent received is a
  fluent and must be read as of the far end. So a period means one of two things, and the
  vocabulary says which: `orexis:RecordGraph` — the obligations record subclasses it — is
  handed by the door as of the present, and every other timed graph as of the instant.

# Amendment: the word is retired, the claim is not

A desire was called a **root** desire, and what the derivation produced under it a **child**.
There is one kind of desire now and a want is derived FROM it, so `root` no longer names a
desire anywhere in the code — `pursuit.desire_of`, `derive_wants`' parameters,
`ontology.desires_graph`. What keeps the word is the search's own: `planner`'s `root` is the
root WORLD a pass stands in, which is a different thing and a true one.

Nothing here is withdrawn by that. This record's argument is about which node a search is
handed and which one is authored; read it with "desire" wherever it says root, and the two
graph names it mentions are spellings for eyes that a rename would have to migrate.
