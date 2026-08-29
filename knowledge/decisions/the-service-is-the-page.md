---
type: Decision
title: The service is the page, and four words carry the bundle
description: >-
  Proposed by the sovereign: write one page per SERVICE, and let it carry the process it runs,
  the repositories it reads and the named graphs it writes — so `planner` holds planning, the
  imaginarium and the action templates rather than each getting a page. Four words, forced —
  Service, Process, Repository, Named Graph. Accepted for the wiring and REFUSED for the
  dictionary: a term several services share has no service page to live in, and `ag:Act` is
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
[deliberation](/domain/deliberation.md) has already grown them by itself: it carries *the menu*,
*what the search does with an effect* and *what deliberation does with a duty*, three sections
that are wiring rather than concept. The proposal names something the bundle was already doing.

**The four words are the vocabulary.** A page is about a Service or a Repository
([a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md)); what it runs is
a Process; what it touches is a Named Graph, referred to by its class.

**A diagram per service, inside its own page, and the service is the hero.** A ```mermaid block
in the article rather than a file beside it: it renders where the page is read, it stays text
like the prose around it, and there is one source instead of two to keep in step. The service is
the middle node, repositories are subgraphs, arrows run in for reads and out for writes.

**A graph is named by its TYPE, never its instance** — `ag:StateGraph`, not `graph/sensed`. This
is not a drawing convention borrowed from nowhere: it is rule 1 and the store's own discipline,
which is why a reader asks `?g a ag:StateGraph` and never names a graph. A diagram that named
instances would teach the opposite of what the code enforces.

**And the type is not always enough.** `graph/ontology` and `graph/ontology/entailed` are both
`ag:OntologyGraph`; only `ag:arrivedBy` separates them. So a service writing back into the type
it read carries the arrival beside it — [inference](/domain/inference.md) is the case, and the
only one.

# What is refused, and why it is the interesting half

**The dictionary does not fold into the services.** `knowledge/domain/` is the shared vocabulary,
and a word is defined before it is used. Fold the data pages into service pages and a term used
by several services has no owner: [act](/domain/act.md) is sized by the planner, committed by
execution, handed to an [actor](/domain/actor.md), and promised by a
[commitment](/domain/commitment.md). Putting `ag:Act` inside any one of those pages picks an
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
`ag:PossibleGraph` (a world per search node) and `ag:DeliberationGraph` (the trace) — and the
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
  reach each other, and [clearing](/domain/clearing.md), [executor](/domain/executor.md) and
  [gateway](/domain/gateway.md) are separate processes outside the agent's repositories. A
  diagram of repos they do not have would assert something false.
- **Nothing renders the mermaid at build time.** GitHub and any OKF viewer draw it; a broken
  block fails silently in a plain `cat`. The blocks are small enough that this has not bitten.
