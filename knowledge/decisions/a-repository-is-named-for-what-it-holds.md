---
type: Decision
title: A repository is named for what it holds, and its methods say what they return
description: >-
  A repository in Domain-Driven Design's sense is a collection of domain objects, backed by a
  store and not owning one - so `Store` is infrastructure and keeps its name, and the repository
  layer above it is mostly absent: two exist, and everywhere else domain code holds the store
  and writes SPARQL, 136 calls and 236 query strings across 18 files. The convention for the
  ones that exist and the ones that should: a repository is the PLURAL of its element, its
  methods are Spring Data's `find_all`, `find_all_by_x`, `find_first_by_x`, and a name that
  answers anything but what is inside must say in its page why. `Wants` was built first and
  taught the rest - it is handed a STORE and never learns which one, rather than the agent it
  first took; it ANNOUNCES its writes rather than re-deriving the projection they staled, since
  that is the assembler's call; and pyoxigraph's own store is too narrow to hand it, because
  the adapter's update is what keeps the door's caches and the keeper's listeners true. Every
  plural read is bounded by a defaulted `limit`/`offset`, ordered before it is cut - an
  unordered LIMIT picks by engine layout - and says so when a page comes back full.
status: accepted
timestamp: 2026-09-17T12:00:00Z
---

# A repository is a collection of domain objects, not a store

The word has been carrying two things. A **repository** in Domain-Driven Design's sense is a
collection of domain objects — `Wants`, `Beliefs`, `Affordances` — that answers questions in the
domain's terms. A **store** is infrastructure: quads, graphs, a SPARQL engine, a file on disk.

A repository is usually BACKED by a store and does not own one. `Wants` and `Beliefs` may hold a
reference to the same store; what makes them two repositories rather than one is that each knows
its own queries and its own graph names, and neither exposes either. `Store` is therefore not a
repository and never was, and the convention below does not apply to it: it keeps its name
because its name is right.

# Which means the layer is mostly absent

| the page | the class | what it is |
|---|---|---|
| — | `Desires` | a repository, named for its content |
| — | `Intentions` | a repository, named for its content |
| [belief-base](/domain/belief-base.md) | `Beliefs` | a modality that FORWARDS the whole store surface — 122 calls pass through it |
| [menu](/domain/menu.md) | *none, and none is owed* | typed `Repository` here and on its own page, and it is a MODALITY — `Actions` and `Affordances` are the collections inside it (#686) |
| [imaginarium](/domain/imaginarium.md) | `Imaginarium` | a repository of worlds, named for a mood |

Two repositories exist. Everywhere else, domain code holds the store and writes SPARQL against
it: **136 direct calls to `.query`, `.update` and `.quads` on a belief base or a desires store,
across 18 files, and 236 SPARQL strings embedded in Python.** A deliberator, a keeper and a
bidder each know graph names and query text that a repository exists to keep from them.

The drift is old enough to have reached the bundle.
[a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) names the belief
base **`Beliefs`** in its own description, while the code has called it `Store` throughout. That
is not two names for one thing; it is the bundle naming the repository and the code naming the
infrastructure, with nothing in between.

# The convention

**A repository is the plural of the element it holds.** `Desires` holds `Desire`; `Wants` would
hold `Want`; `Affordances` holds `Affordance`. The name answers *what is in it* and nothing
else — not how it stores, not what it is for, not what it evokes.

**Its methods are Spring Data's**, in Python's spelling:

| | |
|---|---|
| `find_all(*, limit, offset)` | one page of every element |
| `find_all_by_x(x, *, limit, offset)` | one page of every element matching |
| `find_first_by_x(x)` | the first, or None |
| `save(e)` / `delete_by_x(x)` | the two writes |

**Every plural read is BOUNDED, and the bound has a default.** A collection whose size is the
world's is one an author sizes by hoping — wants are tens today, and nothing enforces that, since
a busy ledger mints one per claim and a stuck sweep leaves them standing. So `limit` and `offset`
are on every `find_all…`, defaulting to a page generous enough that no correct caller meets it.

Two things fall out of that and neither is optional. **A page is ordered before it is cut**:
SPARQL leaves an unordered result in whatever order the engine reached it, so a `LIMIT` over one
is a pick by internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the
PLANT for every pick until a load order changed. Ordered, `offset` walks the collection instead
of resampling it, and `find_first_by_…` answers the same way twice. **And a full page is said out
loud**: truncating in silence is the empty-result trap wearing a cap, so whoever meets the bound
is told, because they either page or have a leak.

The point is that the SIGNATURE carries the shape of the answer and the criterion. This tree's
current names carry neither: `owed()` does not say whether it returns one or many, `read()` and
`read_optional()` differ in a way only the body explains, and `quads(graph)` reads as an
accessor when it is a query. The docstrings are long and careful and say all of it — which is
the tell, because a docstring is where a name's failures are paid for.

# What this refuses, and what it costs

**It refuses letting the author judge.** That is what has been happening and it produced three
logics in five repositories, plus a bundle that disagrees with the code about one of them. The
same argument [a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) made
about `Component` applies to naming: *nothing the word said helped anyone choose it*.

**The price is two names worth something.** `Imaginarium` is the sovereign's word and its page
argues for it: *what is in it never happened*. `Menu` is a domain concept in its own right — the
thing a deliberator reads, the thing the precondition language is written against. Renamed
`Worlds` and `Affordances`, both lose an idea that the identifier currently carries for free.

The convention wins anyway, for one reason: **an evocative name is a claim a reader cannot
check.** "Imaginarium" tells you how to feel about the object; `Worlds` tells you what is in it,
and the page is still there to say what is special about these ones. The mood belongs in the
prose, which is where every other argument in this repository lives.

**Where a name is kept against the convention, its page must say why**, and "it reads better" is
not a why. That clause exists so the exception is auditable rather than habitual.

# A repository holds a store, and nothing else

The sovereign's rule, and the argument for it is Domain-Driven Design's own rather than this
project's: **an agent id is another AGGREGATE ROOT's identity**, so a collection of wants has no
business holding one. It is not the collection's job to know what an Agent is.

`Wants` held the holder's URI and the agent's local id; `Affordances`, for one change, held
identity and no store at all — the shape inverted — because moving the world onto the question
took the door out of its constructor and left the rest behind. Both take a store now and nothing
else, and **which** store is the agent's decision, since the agent owns both the stores and the
collections over them. A service may hold identity — `Afforder` is the agent's, and hands its URI
and its own graph down as criteria — because a service is somebody's where a collection is
nobody's.

Two things fall out that are worth stating, because neither was obvious before the rule was
applied:

- **The reads need no criterion at all.** One agent, one volume (rule 4), so the store IS the
  scope and every want in it is this agent's by construction. Only the writes take one, because a
  graph is NAMED for whose it is. A `find_all_by_agent` would have been a parameter that can only
  take one value, and worse, would imply another value returns somebody else's wants — it would
  return nothing, silently.
- **What a want records about its holder is the want's.** `<holder> orexis:holds <want>` is a
  stored fact in the want's own graph, so it moved onto the `Want` model rather than staying
  identity the collection carried.

# And a file is named the same way

`desire.py` holds the model, `desires.py` holds the collection; `want.py` and `wants.py`,
`judgment.py` and `judgments.py` likewise. A reader looking for what a thing IS opens the
singular and one looking for where they are kept opens the plural, and neither has to read the
other to find out which they wanted. It fell out of
[a-desire-is-declared-and-a-judgment-is-made](/decisions/a-desire-is-declared-and-a-judgment-is-made.md),
where one file held a model, a projection and a collection at once and the name could not say so.

# Not applied here, and it is not a rename

This record is the convention. Applying it is a layer, not a pass of `sed`:

- **`Desires` and `Intentions` comply** and need only their methods moved.
- **`Beliefs` is a modality, not yet a repository.** The class exists and discovers its own
  agent URI, but `__getattr__` forwards the entire store surface, so 122 of the calls above go
  straight through it to `query`, `update` and `quads`. Making it a repository means deciding
  which of them are domain questions — *what do I believe about this subject* — and which are
  genuinely infrastructure, and giving the first a method that owns the query.
- **`Imaginarium` → `Worlds`**, with its page folding the way `root-desire.md` folded into
  `desire.md`, or keeping its page and stating the exception under the clause above.
- **The menu was never a repository at all, and this record read it twice as one.** It had the
  menu's rows derived on every ask — which is the AFFORDANCES — and then, corrected, had it
  keeping templates — which is the ACTIONS. Both were wrong in the same way: `orexis:MenuGraph` is
  a MODALITY, one of the six the mind is made of, asserting *what I could do*. Two collections sit
  inside it and neither is named for it (#686).
- **`Judgments` is the exception the convention asks to be stated.** It is a repository by its
  name and a service by its work: nothing writes a judgment, so it assembles rather than reads —
  asking the choir, running an avoided state's select, compiling a shape into the select whose
  rows are its violations. It is kept on the collection side for the reason `menu` is, and for
  the same reason it is handed the whole AGENT rather than a store: a collection over stored rows
  needs a store, and one over CONTRIBUTED answers needs the contributors.
- **`Wants` is the one to build first**, because it is new: wants are derived, held in one graph
  family, and read by the planner, the keeper and the ask channel through three different query
  texts today. A repository there has no legacy to unpick. **Built in #677**, and what it took
  is the section below.

# A repository is handed a store, and announces its writes

`Wants` was first built taking the AGENT — reading through `agent.desires`, writing through
`agent.beliefs`, and calling `agent.desires.rebuild()` after each write. It worked, and it was
refused for two reasons the sovereign named.

**Taking the agent is taking the whole mind.** A collection that reaches into one modality to
read and another to write has a position on which modality answers what, which is the mind's
business. What a repository needs is somewhere to search, whoever holds the elements, and the
one identifier a process is legitimately handed (rule 1) — so `Wants(store, holder, agent_id)`,
and it never learns which store it got. That is what makes it testable against a bare one: six
tests, no world, no genesis, seventy milliseconds.

**Re-deriving a projection is not a collection's initiative.** A want is written to a store the
desire modality projects, so a write leaves that projection stale — and every writer used to
remember to rebuild. Moving the rebuild INTO the repository fixed the forgetting and bought a
worse thing: a collection reaching up a layer to decide what a write invalidated. It announces
instead — `on_saved` and `on_deleted`, appended to by whoever assembles the agent — and the
assembler rebuilds, because that is a decision about the mind's parts and it is made where the
parts are known.

**And the narrowing paid for itself.** Reading through the projection meant a want was invisible
between being written and the rebuild landing; reading through the store it was written to, it
is there at once. The one piece of the door that mattered — a graph whose period has ENDED is
handed to nobody (#645) — the repository now keeps itself, in one filter, because a want IS its
graph and this class is the one that names it.

**How narrow it could go is bounded by the store, not by taste.** Down to pyoxigraph's own
`Store` would be narrower still, and it is wrong: `Store.update` invalidates the caches the
door is computed from and fires the write listeners the keeper waits on (#512), so a write
straight to the engine leaves the graphs-I-own answer stale and the keeper unnotified. The
adapter is the floor.

The prize is not tidier names. It is that a graph name and a query text stop being things a
deliberator knows — which is the same discipline rule 1 already states for instances, applied to
where facts are kept rather than to what they are called.

# Seams left open

- **Nothing gates it.** A convention with no test is a convention until the first hurry. Whether
  a gate is worth writing — a check that every class the bundle types `Repository` is a plural
  with `find_` methods — is a question for after the first application, when the shape of the
  exceptions is known rather than guessed.
- **A Service's methods are not covered.** `find_all_by_x` says what a repository does; a
  deliberator deciding something is not a query and would read absurdly under it. The line is
  the one [a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) already
  drew, and this convention stops at it.
