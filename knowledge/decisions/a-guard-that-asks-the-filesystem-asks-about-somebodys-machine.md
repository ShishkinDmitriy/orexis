---
type: Decision
title: A guard that asks the filesystem is asking about somebody's machine
description: >-
  The bundle's path check called `Path.exists()`, so its verdict depended on gitignored local
  state in both directions — generated paths absent in a fresh clone read as broken documents,
  and a deleted world kept alive by a leftover `secrets/` directory read as fine. It was red
  everywhere and green where it was written, which is why five documents naming a removed world
  survived three readings. Decided that the guard asks git: tracked, ignored, or missing are
  three different answers, and only the third is a defect.
status: accepted
timestamp: 2026-08-27T22:00:00Z
---

# What was true before

`tests/test_knowledge.py::test_no_document_names_a_path_that_is_not_there` resolved every path a
document names with `Path.exists()`, against the working tree. That is a question about the
machine the test is running on, and the working tree holds three kinds of thing: what git tracks,
what git ignores, and whatever else happens to be lying around.

Both of the other two broke it, in opposite directions:

- **Generated paths read as broken documents.** `infra/.env`, `world/<w>/secrets/`, a board's
  `include/config.h`, `infra/grafana/dashboards/<world>/` — every one is gitignored and created by
  onboarding, so a fresh clone or a new worktree failed the guard on five documents that were
  perfectly correct. Three readers in a row called the failure environmental and moved on. They
  were right about that part.
- **A deleted path read as fine.** `two-worlds-were-one` removed `world/society`, and five
  documents went on naming it. The checkout those documents were written in still held an empty
  `world/society/secrets/` — untracked, gitignored, invisible to `git status` — and `exists()` said
  yes. **The guard was green in the one place anybody was looking and red everywhere else**, and
  the noise above is what taught everyone to ignore the difference.

A guard whose verdict differs between two checkouts of the same commit is not a guard. Worse, the
two failure modes protect each other: the false alarms train a reader to dismiss the real alarm.

# What is decided

**Ask git.** A path a document names is fine if git **tracks** it, or if git **ignores** it — a
generator's output, legitimately named in prose, whose presence is nobody's business here. Anything
else is a rename that did not reach the bundle. Three answers where there was one, and the same
three on every machine.

- tracked: `git ls-files`, plus every directory on the way to a tracked file;
- ignored: `git check-ignore --stdin`, asked once for everything the first question could not
  answer — and asked about `path` and `path/` both, because a directory-only pattern like
  `world/*/secrets/` will not match a path git cannot stat, which every ungenerated path is;
- neither: the failure, and the message says so — *git neither tracks nor ignores* — with a note
  that ungenerated paths are not in the list.

**Historical mentions stay an explicit list**, unchanged. A record narrating a path that USED to
exist is not drift, git cannot tell the difference, and a human writing the entry has to say which
record narrates it and why — which is the part that keeps the list honest.

# What this found

Five documents naming `world/society`. Three were already history and correct — a struck-through
seam, the pair of worlds that WAS device-for-device identical, the two that once shared a broker.
Two were present-tense and false: `genesis.md` said that world has a market, and
`domain/genesis-process.md` used it as a column header for "the two shipped worlds". A third,
`a-stream-is-a-thing`, cited a test by a name it no longer has, quoting a phrase the successor's
own docstring disowns as overclaiming.

# The same shape, one door along

`test_no_document_names_a_graph_the_store_has_never_had` was written in the same change, for
[#269](https://github.com/ShishkinDmitriy/orexis/issues/269), and it is the same move: the graphs
are **enumerable** — declared in an ontology as `…/graph/<name>`, or spelled by a helper as the
convention a per-agent graph's name follows — so
the guard resolves against what is declared instead of against a list of forbidden words. A bundle
writes a graph and an individual with the same shorthand and neither carries a namespace, so it
asks one question of both: does the project declare this?

It found `:attested`, `:opinion`, `:claims`, `:ledger` and `:exp/<agent>` across nine documents,
none of them ever built — and, unprompted, `:barrel1_market`, which
[a-market-arises-where-want-meets-supply](/decisions/a-market-arises-where-want-meets-supply.md)
still named in the present tense after the change that record argues for derived the venue instead.

# Seams left open

- **The historical list is still a list.** Nothing checks that an entry's record still narrates
  its path, so an entry outlives the sentence that justified it. Every one carries the sentence in
  a comment, which is a reader's guard rather than a machine's.
- **A per-agent graph's agent is unchecked.** `:picks/nobody` passes: the prefix is declared and
  the suffix is whatever agents a world holds, and a document naming `:picks/fern` as an example
  is not claiming that world exists. The half that can rot is the half before the slash.
- **Prose outside backticks is invisible to both.** A document that writes *world/society* without
  backticks says the same false thing and nothing sees it. Widening the pattern would sweep up
  ordinary English; the backtick is doing real work as a marker of "this is a name".
