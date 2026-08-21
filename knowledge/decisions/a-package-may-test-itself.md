---
type: Decision
title: A package may test itself, and the gate had to stop naming a path
description: >-
  A package can now carry its own tests as plain test_*.py files beside the code they cover —
  not in a tests/ subdirectory, which collides on module names and reads as a subpackage. Only
  one file qualified, test_auction.py, and the count that motivated this was wrong: 17 rather
  than 29, because eleven "reporting unit tests" take a fixture that builds a real agent. The
  load-bearing part is that pytest tests -q stopped being the gate: a test inside a package is
  collected by neither that nor a bare pytest, so the suite would have gone green while
  skipping it.
status: accepted
timestamp: 2026-08-12T00:00:00Z
---

> **Current statement: [package](/domain/package.md).** This record is how the model got
> there and why; the domain concept is what it is now. Four records amend each other on
> this subject, so read the concept first unless you want the argument.

# Context

With one package tree, the question followed: can a package carry its own tests, so that
deleting it takes them with it? Most of this suite cannot — 389 of 459 test functions build a
world, and that is architectural rather than stylistic. **In this system the unit of behaviour is
usually the merged graph**: a shape, a `rules.ru`, the closure and provenance cannot be exercised
without every other package's T-Box.

# The count was wrong, and the correction is the useful part

The first measurement said 29 test functions in two packages — market 17, reporting 12. The
reporting twelve were **misclassified**. Eleven of them take an `agent` fixture built by
`conftest.build_agent`, whose own docstring is *"A real Agent — real world, real beliefs, real
modules"*. The classifier looked for a fixed list of integration markers — `genesis`, `Store`,
`refresh_public` — and `build_agent` was not on it.

Broadening the list to every conftest name over-corrected to zero, because it contains words like
`build`, `close`, `to` and `under` that match anywhere in prose. What settled it was asking the
precise question with the AST: **does this module import from conftest, or take a fixture defined
there?** `test_auction.py` does neither. `test_metrics.py` does both.

So one file qualified, not two. Worth recording because the wrong number was produced twice by
plausible-looking scripts, and only a question about *dependency* rather than *vocabulary* gave
the right one.

# Plain files, not a tests/ subdirectory

Both were tried. A `tests/` subdirectory **fails**:

```
ERROR packages/part/rgb_led/tests/test_shared_name.py
HINT: ... use a unique basename for your test file modules
Interrupted: 1 error during collection
```

A `tests/` subdir has no `__init__.py`, so pytest derives a module name from the basename and two
packages cannot both hold `test_config.py`. Plain files in the package do not collide — the
directory already has an `__init__.py`, so the module is
`packages.capability.market.test_auction`, unique by construction. Both same-named files ran.

It also matches the format. A package is **flat files** — `ontology.ttl`, `shapes.ttl`,
`terms.py`, `module.py` — and a `tests/` subdir would be the only nested thing in one, reading as
a subpackage it is not. A test file is simply another optional file, and most packages having
none is a statement: their behaviour only exists in the merged graph.

# The gate stopped naming a path, and that is the load-bearing change

Measured before moving anything, with `testpaths = ["tests"]`:

```
pytest tests -q     does not run it
pytest      (bare)  does not run it either
pytest <path>       1 passed
```

A bare `pytest` does **not** rescue it, because `testpaths` confines collection regardless. So the
suite would have gone green while skipping the file entirely — the same failure that cost 143
cases during the layout move, arriving by a different door.

`testpaths = ["tests", "packages"]` now, and `AGENTS.md`, `README.md` and `gates.yml` all run
`pytest -q` rather than naming a path. `tests/test_layout.py` asserts the link rather than either
fact alone: **if any package carries a test, `testpaths` must name the tree it lives in.**
Mutation-tested by narrowing it back, which fails with both the file and the setting in the
message.

# Seams left open

- **One package carries tests.** Whether this is a convention or an exception is better answered
  by the second package that wants it than by argument.
- **`test_metrics.py` stayed whole.** Eleven of its twelve are integration and splitting out the
  one unit test would strand it from the helpers it shares.
- **Nothing stops a package test from building a world.** It would work and it would be in the
  wrong place, and no rule here catches it. The honest guard is the ratio: if a package's tests
  start needing a world, they belong in `tests/`.
