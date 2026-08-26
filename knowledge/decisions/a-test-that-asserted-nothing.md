---
type: Decision
title: A test that asserted nothing passed by doing nothing
description: Four times a guard went green while checking nothing, because its assertions sat inside a loop over an empty collection. The check is now mechanical and asks the true question — did any assert in this test actually execute — rather than a proxy each site would spell differently. Per test FUNCTION rather than per parametrised case, because a scan over every source file legitimately asserts nothing for the files with no queries; checking cases separately called 54 of those a failure. Traced only for tests an AST scan finds at risk, so the cost is 4% rather than the whole suite.
status: accepted
timestamp: 2026-08-12T00:00:00Z
---

# What it does not catch, and one of those has now happened

Two blind spots were recorded when this landed: **a parametrisation that generated zero cases**,
and **a glob that still matches but no longer covers what it is named for**. The second arrived in
a third shape — not a glob that emptied, but a hand-written roster that stopped growing.

`test_provenance.py` and `test_isolation.py` each opened `WORLDS = ["simulation", "sensing"]`,
written on 2026-08-09 and 2026-08-07. `world/loner` was ratified on 2026-08-18 and received **none
of the eleven parametrised tests** between those two files, for as long as it had existed. Every
assertion ran, every test was green, and one shipped world was simply not among the subjects.

`test_shapes.py` had the answer in its own docstring the whole time — *found by looking, never
listed*. The roster is `conftest.shipped_worlds()` now, and all three files read it; each of the
two carries `assert len(WORLDS) > 2`, so a roster that SHRINKS fails where a roster that failed to
grow could not. Measured after the change: `loner` passes all eleven, which is luck rather than
evidence — nine days of silence is what this is about.

# The failure

An empty result set is not an error. A loop over one runs its body zero times, so every assertion
inside is skipped and the test passes — **indistinguishable from a test that checked a hundred
things**. Both gates are blind to it by construction: `orexis-validate` reads worlds, not tests, and
pytest reports a passing test identically whether it asserted a thousand times or none.

Four instances, all found by hand:

| | |
|---|---|
| the privacy query, dead four PRs | [#79](https://github.com/ShishkinDmitriy/orexis/issues/79) |
| the cadence guard, dead four PRs | a rename moved `sensing:seconds` out from under its query |
| a glob emptied twice by moving files | fixed locally in `test_store.py` |
| 143 cases lost in the layout move | the glob did not empty, it stopped covering what it was named for |

The tell is the third: **the defence had been invented locally, twice, by whoever got burned.**

# What is checked

The true invariant, not a proxy: **did any `assert` in this test actually execute?**

Not "is the collection non-empty" — every site would spell that differently, and #105's hand-written
counter is what that looks like done once. Not a source-text pattern — it cannot know what ran.
A trace counts executed `assert` lines while the test runs.

**Per test FUNCTION, not per parametrised case**, and getting that wrong is instructive.
`test_queries_use_only_declared_prefixes` is parametrised over every source file in the project and
correctly asserts nothing for the ones containing no queries. Checking each case separately called
**54 of those a failure**. What is actually wrong is a function that asserted nothing in *any* of
its runs.

**Where** is narrowed by an AST scan, because line-tracing every test would cost more than the
suite. Only tests with an `assert` inside a loop over something that could be EMPTY are traced — a
loop over a literal tuple cannot be, and is left alone. Of 50 such loops, 34 are at risk, in 24
functions. Measured cost: 175s against 170s, about 4%.

It reports at session end and **sets the exit status**, so CI fails. A guard that printed a warning
would be the same failure it exists to catch.

# It lives at the repo root

`conftest.py` beside `tests/`, not inside it, because a package may carry its own tests and a guard
in `tests/conftest.py` would cover half of them. Verified from both roots: a vacuous test under
`packages/capability/market/` fails the run exactly as one under `tests/` does.

Nothing else belongs in that file. Fixtures that build a world stay with the integration suite — a
package test needing one is a test in the wrong place.

# What this does NOT cover, and why the local guards stay

**A parametrisation that generated zero cases.** If a glob finds nothing, the test never runs at
all, so there is no execution to trace and no entry to check. That is a different hole and
`test_every_source_group_is_still_found` is still the thing that catches it — which is why it was
not deleted as a duplicate.

**A glob that still matches but stopped covering what it was named for.** The 143-case loss was
exactly this: `agent/**/*.py` matched plenty of files after capability Python moved out. Nothing
here would notice, because the tests that remained did assert. Only diffing collected test ids
against a known-good tree finds that, and nothing performs it automatically.

**#105's counter stays too.** This mechanism would have caught that guard, but with a generic
message; the local one says *"the query above has drifted off the vocabulary again"*, which is the
sentence that saves the next person twenty minutes. A domain-specific message earns its place.

# Seams left open

- **A test could assert something trivial and still check nothing.** `assert True` executes. This
  measures that assertions ran, not that they were about anything, and no mechanism reasonably can.
- **Tracing is skipped when a debugger holds the trace function.** `sys.settrace` is restored
  rather than chained, so running under a debugger silently disables the check for those tests.
