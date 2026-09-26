---
type: Decision
title: The knowledge is filed like the code, and a record lives where it still binds
status: accepted
timestamp: 2026-09-26
description: >-
  The dictionary is filed by the package that owns each word, gated to name only live terms, and
  the decision records split into the ones something current cites and the 0.1.0 history. Refused
  - a flat dictionary with pages marked historical, deleting the history, and judging by hand
  which records still hold.
---

# What was found

After 0.1.0 was deleted, 38 of the 88 dictionary pages went on describing it in the present tense,
and 161 of 185 records still said `accepted`, many about code that no longer existed. Nothing gates
prose against the thing it describes, and the bundle ran three lines to every line of code.

# What was done

- **The dictionary mirrors the code.** A page sits in the folder of the package that owns its word
  — `kernel`, `sensing`, `transport`, `belief`, `prediction`, `planning`, `execution`, `speech`,
  `market`, `actuation`, `onboarding` — and `tests/test_knowledge.py` holds that a bound term is in
  its folder's namespace, that it is declared by a LIVE ontology, and that a page names no retired
  term and no retired tree. Retiring a term now fails the build until its page follows.
- **A concept gone from the code is a page gone from the dictionary.** Forty were retired; a link
  to one keeps its words, and the records still narrate them.
- **A record is current while something current cites it** — a dictionary page, a runbook, AGENTS.md,
  README or the live code — and the rest, 113, are filed under
  [decisions/0.1.0](/decisions/0.1.0/index.md), superseded by
  [agent-0-2-0-replaced-the-kernel](/decisions/agent-0-2-0-replaced-the-kernel.md) where nothing
  more specific superseded them.

# What was refused

- **A flat dictionary with a marker on stale pages.** A marker is a second thing to keep true, and
  it is exactly what nobody updated. Filing by package gives the gate something to check: the
  folder names the namespace.
- **Deleting the history.** A record's value is often the alternative it refused, and 0.2.0 was
  built by refusing 0.1.0's shapes one argument at a time; the arguments stay reachable.
- **Judging each record by hand.** Citation is a rule anyone can re-run and the next retirement
  can apply mechanically. Three live principles AGENTS.md states without naming their records were
  kept current by hand, and that is the known gap of the rule.
