---
type: Decision
title: A deferred import is code no test runs, and three green gates said nothing about it
description: >-
  `pytest` passed, `orexis-validate` passed all three worlds, `lint-imports` kept four
  contracts — and every agent in every world crash-looped at boot on a `ModuleNotFoundError`.
  One import inside a function had not followed its module when the module moved packages, and
  an import inside a function is executed only when that function runs. Decided that every
  deferred import is resolved by an AST walk that executes nothing, and that a deferral needs a
  reason now that the one which caused this had stopped being true.
status: accepted
timestamp: 2026-08-28T20:00:00Z
---

# What happened

`packages/orexis-capability-reporting/module.py` held, inside `StoringModule.start()`:

```python
from agent.influx_writer import InfluxWriter  # deferred: nothing built for a test agent
```

[metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) moved that module into the
reporting package as `series.py` and renamed the class `SeriesWriter`. The line was not
repointed. By then `SeriesWriter` was already imported at the **top of the same file**, so the
deferral bought nothing at all and the deferred line was simply wrong.

Reporting is the capability every agent holds
([telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md)), and
`start()` runs on every boot. So every agent in every world raised `ModuleNotFoundError`, exited,
was restarted by `restart: unless-stopped`, and crash-looped — for four merged changes.

**Nothing said so.** `pytest`: 1424 passed. `orexis-validate`: three worlds, exit 0.
`lint-imports`: four contracts kept — the layering was never in question, only the existence of
the module. `podman compose up` and reading a log is what found it.

# Why the gates could not see it

An import at the top of a module is checked by the first test that imports the module, and
something imports every module. **An import inside a function is checked only when that function
runs**, and this one runs solely in a container. The comment said as much — *nothing built for a
test agent* — which is an accurate description of code no test executes, written as if it were a
justification.

This is [a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md)'s family: not
a wrong assertion but an absent one, and green either way.

# What is decided

**Every deferred import in shipped code resolves**, checked by
`tests/test_deferred_imports.py::test_every_deferred_import_resolves`. It walks the AST of
`agent/`, `packages/` and `onboarding/`, collects every `Import` and `ImportFrom` inside a
function body, and resolves each module and each imported name — a name that is an attribute, or
a submodule not yet loaded, which is the distinction a first draft got wrong and reported
thirteen false positives on.

It executes nothing: a deferred import stays deferred, and a module whose import is expensive or
circular is never actually imported by the walk unless resolving a NAME requires it.

Relative deferred imports (`from .series import X`) are skipped. Resolving one needs the
importing module's package context, and every one in this tree is a sibling the module-level
imports already reach; the line that broke was absolute, which is the shape a move across
packages produces.

**And a deferral needs a live reason.** The one here had expired twice over — the class moved
into the same package, and the top of the file imported it anyway. The fix was to delete the
line, not to repoint it.

# Seams left open

- **The guard proves a name exists, not that it is the right one.** `SeriesWriter` and
  `InfluxWriter` have the same constructor signature; had the old module survived under its old
  name with different behaviour, this would have passed.
- **Nothing runs a world in CI**, which is the only thing that would have caught this on the
  branch that introduced it — [#47](https://github.com/ShishkinDmitriy/orexis/issues/47). The
  guard is the cheap half; booting a society is the whole answer, and this is the first defect
  that makes the case concretely rather than in principle.
- **Deferred imports are not otherwise policed.** Nothing says which deferrals are legitimate,
  and the count today is 34. A rule ("defer only for cost or for a cycle, and say which") would
  need a reader to enforce, like the shape-comment question one door along.
