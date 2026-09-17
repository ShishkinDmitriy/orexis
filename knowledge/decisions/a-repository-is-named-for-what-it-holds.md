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
  answers anything but what is inside must say in its page why.
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
| [belief-base](/domain/belief-base.md) | *none* | a page typed `Repository`; `agent.beliefs` is a raw `Store` |
| [menu](/domain/menu.md) | *none* | a page typed `Repository`; the rows are computed per ask |
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
| `find_all()` | every element |
| `find_all_by_x(x)` | every element matching |
| `find_first_by_x(x)` | the first, or None |
| `save(e)` / `delete_by_x(x)` | the two writes |

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

# Not applied here, and it is not a rename

This record is the convention. Applying it is a layer, not a pass of `sed`:

- **`Desires` and `Intentions` comply** and need only their methods moved.
- **`Beliefs` does not exist.** Making it exist means deciding which of the 136 store calls are
  domain questions — *what do I believe about this subject* — and which are genuinely
  infrastructure, and giving the first a method on a repository that owns the query.
- **`Imaginarium` → `Worlds`**, with its page folding the way `root-desire.md` folded into
  `desire.md`, or keeping its page and stating the exception under the clause above.
- **The menu may stay classless.** Its rows are derived on every ask and never stored, which is
  a reason rather than an omission — but then its page should say what kind of thing it is more
  carefully than `Repository` does.
- **`Wants` is the one to build first**, because it is new: wants are derived, held in one graph
  family, and read by the planner, the keeper and the ask channel through three different query
  texts today. A repository there has no legacy to unpick.

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
