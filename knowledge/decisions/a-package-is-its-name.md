---
type: Decision
title: A package is its name — the directory, the distribution and the module are one string
description: >-
  The family was stated twice: a package's path said `capability/market` while its distribution
  said `orexis-capability-market`, and nothing held the two together, so a package could be
  filed under one family and published under another. Decided: the tree goes flat, the directory
  name IS the distribution name, the module is that name with underscores, and the family is its
  second segment. The shared `packages.` import root goes with it, which closes the question of
  what namespace an outside developer is asked to share — and costs three import contracts that
  a wildcard cannot express, moved to a test that finds packages by looking.
status: accepted
timestamp: 2026-08-27T22:00:00Z
---

# What was true before

Two levels — `packages/<family>/<name>/` — with the family read off the path, and every package
a distribution named `orexis-<family>-<name>` importable as `packages.<family>.<name>` through a
PEP 420 namespace that twenty-two distributions shared.

# What was wrong with it

**The family was stated twice.** The path said `capability/market`. The distribution said
`orexis-capability-market`. Nothing compared them, so a package could sit in `part/` and publish
as `orexis-plant-something` and every gate would pass. That is the shape this project keeps
removing — a fact with two owners drifts, and the drift is silent
([one concept, one article](/domain/package.md) is the same rule for prose).

**And `packages` was a very general name to ask an outside developer to share.** That was the
second seam [every-package-is-a-project](/decisions/every-package-is-a-project.md) left open:
a package from another repository had to claim a slice of a top-level namespace called
`packages`, which says nothing about whose it is.

# What is decided

**A package is its name.** `packages/orexis-capability-market/` is the directory, the
distribution is `orexis-capability-market`, and the module is `orexis_capability_market` — one
string in three spellings, fixed by punctuation and by nothing anyone has to keep in step. The
family is the **second segment**, and it is stated nowhere else.

**The tree is flat.** `agent.loader` walks one level. `packages/` is a plain directory — somewhere
to keep projects, not somewhere to import from — and each package owns a **top-level module**, so
there is no shared root to join and none to shut anybody out of.

**A directory that is not named `orexis-<family>-<name>` is refused, not skipped.** A skipped
package is the failure this project keeps meeting: the thing silently not there, which no test
sees because an empty result is not an error
([a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md)).

# What it cost, measured

Three `import-linter` contracts named `packages` as one module — the kernel reaching into a
package, assembly reaching into one, a package reaching for onboarding. **A wildcard cannot
replace that**: `grimp` rejects `orexis_*` outright, because its wildcards match whole segments
and never part of one. Measured before the change was written, not discovered after.

The alternative was listing twenty-one modules in `pyproject.toml`, which is a registry — the one
thing this tree exists not to have, since adding a package is adding a directory and a contract
somebody must remember to edit is wrong the first time they do not. So those three claims moved
to `tests/test_layering.py`, where the list is **discovered** by the same `loader.packages()` call
the runtime makes. That is stricter than what it replaced, not looser, and all three were
verified by breaking them.

What stays in `pyproject.toml` is the layering among the root distribution's three trees, which
is fixed and few.

# The second cost: pytest derived module names from paths

A package's own `test_*.py` was imported as `<package dir>.test_auction`, because pytest's
default `prepend` mode walks up from a test file while it keeps finding `__init__.py` — and every
package has one. With the directory named for the distribution, that name has hyphens in it and
is not an identifier, so all twenty-one of the market's tests failed to **collect**.

That is the dangerous kind of failure and the reason it is recorded rather than just fixed: a
test that cannot be imported is a test that does not run, and it is one `continue` away from
being a suite that is green while a file of it never executed — the same family as
[a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md), arriving through
collection instead of through an empty loop.

The fix is `--import-mode=importlib`, the mode pytest recommends, which derives no module name
from any path. It also stops inserting directories into `sys.path`, so `pythonpath = ["tests"]`
is set for the one test that reads helpers out of a sibling. One consequence worth knowing: that
mode permits duplicate test basenames, which removes half the argument in
[a-package-may-test-itself](/decisions/a-package-may-test-itself.md) — amended there.

# What it found

Making the packages top-level made the root's imports of them visible for the first time — the
dependency scan had skipped anything under `packages.`, so it had never compared them.
`onboarding/` imports three packages in four places, to derive an ACL and to validate regions.
That is rule 1 owed by the operator's tools, it is **not** declared as a dependency (a cycle, and
it would break the image's dependency-first layer), and it is now held by a ratchet that can only
fall to zero (#426).

# A test that was still passing and had stopped checking

The collected-id diff — run because moving a test file is exactly how tests vanish quietly — found
that `test_no_package_carries_an_init_that_makes_it_a_regular_subpackage` had survived an edit
that was meant to replace it. It asserted that no `__init__.py` sat at `packages/` **or** at
`pkg.parent`. With the tree flat, `pkg.parent` **is** `packages/`, so it checked one file twice,
said nothing whatever about the shape that replaced the namespace, and passed.

It is the third form of the same failure this project keeps meeting — after the empty loop
([a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md)) and the collection
error above. A green assertion is not evidence that the thing asserted still exists. What caught
it was diffing test FUNCTION names against `main` rather than trusting a count, and the
replacement was verified by creating an `__init__.py` at the root of `packages/` and watching
twenty-one tests fail.

**And one test moved into a package.** `test_regions.py` went to `tests/` when the desire package
was deleted, on the reasoning that the arithmetic had come to the kernel with it. That stopped
being true — `Region` lives in sensing's `regions.py`, and `agent/regions.py` does not exist — so
it is back beside the code it covers. Two other candidates were examined and left where they are:
`test_prior_sample.py` guards an agreement between the package and the FIRMWARE, so it belongs to
neither alone, and `test_actuation.py` spans two packages. The criterion is the record's own —
[a-package-may-test-itself](/decisions/a-package-may-test-itself.md) — and it is narrow on
purpose: fifty-eight of sixty test files assert something about the merged graph, which is
`tests/`.

# Seams left open

- **The `orexis-` prefix is load-bearing for discovery.** A package must be named for this
  project to be found at all, which is fine for a monorepo and is a question the day someone
  publishes `acme-capability-forecasting`. Discovery would then be by entry point rather than by
  prefix, which is #424's business and not settled here.
- **Out-of-tree enumeration is unchanged.** #424 stands exactly as written: a package installed
  elsewhere can be imported by name and not discovered by looking.
- **Versions still move together**, all `0.1.0`.
