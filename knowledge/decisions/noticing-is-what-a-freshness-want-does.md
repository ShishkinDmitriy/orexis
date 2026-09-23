---
type: Decision
title: Noticing is what a freshness want does, so the hook is retired
description: >-
  `ag:notices` asked every module which subject-property pairs were unknown or too stale, and the
  deliberator collected them — until freshness became a want and nothing asked again. Two
  releases of a term, a base method and a real implementation in sensing, computing on request a
  judgment nobody requested. Retired rather than rewired, because the want covers the same ground
  and is PURSUED where the hook was merely reported. The guard that would have caught it the day
  the deliberator stopped now exists. Amended for Agent 0.2.0 (#783): the failure is still
  pursued as a want, and its owner is the region desire's `unmeasured` side rather than a
  freshness desire of sensing's own.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was there

A hook, `ag:notices`, with everything a hook needs except a caller: the term in the kernel's
ontology, a base method on `Module` returning `[]`, and a real implementation in sensing that
walked every sensor and reported the pairs it had never read or had let go cold.

Its consumer was the deliberator. It stopped asking when freshness became a **want** — a
`sensing:Freshness` desire derived per instrument, `orexis:violationIs orexis:Stale`, which the
[deliberator](/domain/deliberator.md)'s tick hands to the [executor](/domain/executor.md) like anything
else the agent pursues. The hook was left computing the same judgment, one layer earlier,
answerable to nothing.

# What is decided

**Retired, not rewired.** The want covers the same ground and does more with it: a noticed gap
was a report, and a want is pursued — planned over, committed to, and resolved in a ledger. Two
ways to say the same thing where one of them cannot act on it is not a choice worth keeping.

Gone together: the term, the constant, the base method, sensing's override, the test, and the
paragraph in [gap](/domain/gap.md) that was built on it. That page now answers *who notices a
gap* with **nobody** — being unmet is a fact about the world rather than an opinion a module
holds.

**No coverage was lost.** `test_sensing_notices_what_it_has_never_seen` asserted that a freshly
born agent sees both its channels as gaps; `test_freshness.py::test_stale_and_unmeasured_are_told_apart`
asserts the same thing through the want, and tells the two states apart, which the hook could
not.

# The guard, which is the half that matters

`test_every_declared_hook_has_an_asker` refuses any `assembly:Extension` that nothing calls.
This is the check
[the-assembly-is-not-the-mind](/decisions/the-assembly-is-not-the-mind.md) left as a seam, and it
could not land while `notices` was the one thing failing it.

**An asker counts two ways**, because there are two doors to the same contract: `ask`/`tell` with
the point's constant for a kernel-owned question, and a direct call on whoever provides it for
`size` and `take`, which are reached through `agent.provider(family)`.

**It pins its own count, and that was earned.** The first version matched `:record` but not
`orexis:handle`, so it silently checked five of seventeen hooks and passed — the empty-glob failure
[a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md) records, wearing a
regex. It now asserts a floor on how many declarations it found, so a pattern that stops matching
a prefix form fails instead of narrowing.

# Amended for Agent 0.2.0 (#783)

The premise holds — being unmet is a fact about the world, and what is unmet is pursued as a
want — and the owner moves. Sensing in `agent/` derives no desire: a reading is a graph with a
period, so a reading missing or past its horizon is a way the domain's own region desire
fails, `orexis:Unmeasured` beside below and above, and the look is the lever that repairs
that side and no other. The `sensing:Freshness` desire and the horizon it read
(`sensing:staleAfterS`) stay the 0.1.0 container's and retire with it.

# Seams left open

- **A hook asked in only one place is not distinguished from a well-used one.** The guard proves
  an asker exists, not that the point earns its keep; a hook with one caller may still be a
  function wearing a contract.
