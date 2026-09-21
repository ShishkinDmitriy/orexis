---
type: Decision
title: The service is the page, and four words carry the bundle
description: >-
  Proposed by the sovereign: write one page per SERVICE, and let it carry the process it runs,
  the repositories it reads and the named graphs it writes — so `planner` holds planning, the
  imaginarium and the action templates rather than each getting a page. Four words, forced —
  Service, Process, Repository, Named Graph. Accepted for the wiring and REFUSED for the
  dictionary: a term several services share has no service page to live in, and `progression:Act` is
  written by one, committed by another and taken by a third. The diagram convention is adopted
  whole — a service is the hero and a graph is named by its TYPE, which is the rule the code
  already follows.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was proposed

One page per service, absorbing what today is several: instead of `planning` as a process page,
`menu` as a repository page and `action` as a data page, the **planner** page says *the planner
is a service, it runs planning, it reads these repositories and writes these named graphs*. Four
words are forced throughout — **Service**, **Process**, **Repository**, **Named Graph** — so that
`belief` and `beliefs` and *the belief base* stop being three ways of saying two things.

The pull behind it is provenance. Every graph is authored by exactly one writer, so a service's
outputs are the natural unit to describe it by.

# What is accepted

**The wiring belongs on the service page.** Which repositories a service reads, which named
graphs it writes, and what its one process is — these have no other home today, and
[deliberation](/domain/deliberator.md) has already grown them by itself: it carries *the menu*,
*what the search does with an effect* and *what deliberation does with an obligation*, three sections
that are wiring rather than concept. The proposal names something the bundle was already doing.

**A service is an `-er` and its process is the `-ing`.** `Planner` runs planning, `Keeper` runs
keeping, `Deliberator` runs deliberating — and those three already carry the name in code, which
is the test that makes the convention worth having. `deliberation.md` was named for the process
and is now [deliberator](/domain/deliberator.md); the page names the thing that acts, and the
process is a heading inside it.

**The convention is applied only where the code agrees, and that is deliberate.** Renaming a
page whose class keeps the old word would produce exactly the `belief` / `beliefs` split this
record exists to close — one vocabulary in the bundle and another in the source. Six services
would need a code rename first, and each has a defensible name waiting:

*(One of the six has since dissolved rather than been renamed: affording turned out to be a
COLLECTION derived per ask rather than a service that decides something, so `Afforder` is
`Affordances` and its page folded into [affordance](/domain/step.md) — the model keeps the
page and the collection lives in the code, which is the shape
[a-repository-is-named-for-what-it-holds](/decisions/a-repository-is-named-for-what-it-holds.md)
settles. The discipline below is what forced it: the page followed the code rather than drifting
from it.)*

**All six have landed.** `Executor` took the name a retired component held; `Afforder`, `Deducer`, `Ower` and `Reviser` renamed with their code, because a doc-only rename produces the split this convention exists to close. `Ower` is consistency rather than clarity and the honest note is that the gerund still reads better than the agent noun; `Reviser` turned out to REMOVE a collision, since `review:Revision` is a different thing — a record of a belief re-picked.

**`Executor` went to the service that carries out a plan**, and the page that held the name gave
it up. `executor.md` described the trusted actuator — and opened with a banner disambiguating
itself from execution, which is the tell that one word was standing between two things.
[thin-trusted-infra](/decisions/thin-trusted-infra.md) had already reframed it: *"actuation is
not separate region-want-free infra — the resource owner drives its own valves. The 'executor' is the
supplier's actuation ARM, not a distinct component."* A page for a component that had been
reframed away, holding a name a live service needed. Its body moved into
[actuation](/domain/actuation.md), which is where that decision put the thing, and eleven links
followed.

**A repository carries its own support functions, and they are not services.** Compaction was
written as one and is not: every service runs a process and writes a named graph, because what a
service concludes is a fact somebody authored, while compaction decides nothing, asserts nothing
and reclaims bytes belonging to one repository. It is a function of
[belief-base](/domain/belief-base.md), and no other repository is obliged to have the same ones.

The test that separates them is what a thing PRODUCES. Three services write no graph either —
the menu build returns rows, [executor](/domain/executor.md) only orchestrates,
[reviser](/domain/reviser.md) only marks — and all three stay services, because each decides
something. Writing no graph is the hint; deciding nothing is the finding.

**The four words are the vocabulary.** A page is about a Service or a Repository
([a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md)); what it runs is
a Process; what it touches is a Named Graph, referred to by its class.

**A diagram per service, embedded in its page, and the service is the hero.** PlantUML source in
`knowledge/diagrams/service-<name>.puml`, a rendered SVG beside it, and the page shows the SVG.
The service is the middle node, repositories are containers, arrows run in for reads and out for
writes.

**A committed image is safe here because a gate keeps it fresh**, which is the objection
[a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md)
raised against committing one at all — *a rendered image rots while the source stays checkable*.
True, and answerable: `tools/render-diagrams.sh` stamps each SVG with the sha256 of its source,
and `test_a_committed_diagram_is_not_stale` compares the two. Edit a source, forget to re-render,
and the suite names the file.

**The check needs no renderer, and that is the part that makes it acceptable.** A gate that ran
only where PlantUML is installed could not run on a fresh clone — the failure
[a-guard-that-asks-the-filesystem-asks-about-somebodys-machine](/decisions/a-guard-that-asks-the-filesystem-asks-about-somebodys-machine.md)
names. Rendering needs the tool; comparing two hashes does not.

**Mermaid was tried first and dropped.** It rendered without a build step, which is a real
advantage, but PlantUML draws repositories as containers rather than boxes-in-boxes and the
project already had it. The nine sources were generated FROM the mermaid they replace, so the
picture and the prose began identical.

**A graph is named by its TYPE, never its instance** — `orexis:StateGraph`, not `graph/sensed`. This
is not a drawing convention borrowed from nowhere: it is rule 1 and the store's own discipline,
which is why a reader asks `?g a orexis:StateGraph` and never names a graph. A diagram that named
instances would teach the opposite of what the code enforces.

**And the type is not always enough.** `graph/ontology` and `graph/ontology/entailed` are both
`orexis:OntologyGraph`; only `orexis:arrivedBy` separates them. So a service writing back into the type
it read carries the arrival beside it — [inference](/domain/inference.md) is the case, and the
only one.

# What is refused, and why it is the interesting half

**The dictionary does not fold into the services.** `knowledge/domain/` is the shared vocabulary,
and a word is defined before it is used. Fold the data pages into service pages and a term used
by several services has no owner: [act](/domain/act.md) is sized by the planner, committed by
execution, handed to an [actor](/domain/actor.md), and promised by a
[commitment](/domain/commitment.md). Putting `progression:Act` inside any one of those pages picks an
arbitrary owner for a word the other three must speak.

So the split is by **how many services share the word**:

| | where it lives |
|---|---|
| a term one service owns | that service's page |
| a term several services speak | its own dictionary page, as now |
| the wiring — repos, graphs, the process | the service page, always |

That keeps `test_no_two_domain_pages_state_the_same_claim` doing the work it already does: a
service page that restated what an act is would be a second owner, and the gate would say so.

# Two things the exercise measured

**Provenance does not force one output graph per service.** It forces that every graph has
exactly ONE author — a function from graph to service, not a bijection. `inference` writes two
graph types, `sensing` two, `review` three, `genesis` five. A graph carries author *and*
subject, and collapsing to one output per service would conflate them.

What the planner does support is a sharper claim: **one service, one output MODALITY.** It writes
`orexis:PossibleGraph` (a world per search node) and `deliberation:DeliberationGraph` (the trace) — and the
second is a subclass of the first, so both are possible-modality: the worlds that die with the
pass, and the record that survives it because the health series read it.

**Two graphs cannot be drawn by type at all.** The desires store's graphs carry no class, retired
by [#312](https://github.com/ShishkinDmitriy/orexis/issues/312) when the modality became a store.
Every other repository can be drawn by the type rule above; that one is a hole the convention
finds immediately.

# Seams left open

- **Nothing yet enforces a service page's shape.** A gate could require that a page typed
  `Service` names at least one repository and one process, which would make the convention real
  rather than encouraged. It is not written.
- **Five services have a page and no wiring diagram**, on purpose: [actor](/domain/actor.md) is a
  contract rather than a service that holds a store, [choir](/domain/choir.md) is how services
  reach each other, and [clearing](/domain/clearing.md), [actuation](/domain/actuation.md) and
  [gateway](/domain/gateway.md) are separate processes outside the agent's repositories. A
  diagram of repos they do not have would assert something false.
- - **Nothing renders the mermaid at build time.** GitHub and any OKF viewer draw it; a broken
  block fails silently in a plain `cat`. The blocks are small enough that this has not bitten.
