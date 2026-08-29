---
type: Decision
title: The confirmation route is retired, and the cognitive rows survive the same audit
description: >-
  Seven terms were declared, stated on every action an author ships, and required by SHACL —
  and nothing branched on the answer, because every shipped effect gave the same one. Retired,
  with the constitutive/causal distinction kept in prose. The cognitive rows were audited the
  same way and REFUSED retirement: `assembly/loader.py` reads `ag:row`, and a test built on it
  holds a reactive hook out of the search — which is exactly the enforcement a retirement would
  have thrown away.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was measured

A term is read where code consults it — docstrings and comments stripped, because prose is not a
reader — or a `.rq`, `.ru` or shape names it, or a ratified world instantiates it.

| terms | stated on | read by |
|---|---|---|
| `ag:ConfirmationRoute`, its four routes, `ag:confirmedBy` | all 6 actions, **required** by `ag:ActionShape` | nothing |
| `ag:Modality` | nothing at all | nothing |
| `ag:Row`, its three individuals, `ag:row` | all 18 hooks | **`assembly/loader.py::extension_rows()`** |

# The routes are retired

The requirement was the expensive part: SHACL refused an action that stated no route, so every
package author picked one of four and wrote it down, and nothing asked which. Two of the four
appear on no action here. The planner did read it once — to decide which acts end a plan — and
since every shipped effect answers *by observation*, every lever ended one and the search never
reached its second step. That reading was removed and nothing replaced it.

Gone with the terms: the property shape that made a route compulsory, the route on each shipped
action, the column `effects.rule_for` selected into a dict no caller indexed, and the test that
held every effect to stating one.

**Rewiring was the live alternative**: let the route decide where a watch opens, since a
constitutive effect needs none and a causal one does. That is a real design and it changes what
an expectation IS — [#430](https://github.com/ShishkinDmitriy/orexis/issues/430)'s neighbour
rather than a cleanup. A term held against that day is a term held for a reader who does not
exist; the design can declare what it needs when someone builds it.

**What it distinguished stays.** [effect](/domain/effect.md) still separates a constitutive
effect from a causal one — that distinction is why conflating them produces code verifying an
agent wrote down what it just wrote down. It never needed an IRI to say so.

# The rows are not retired, and the audit is why

They looked identical from the kernel: eighteen declarations, no consumer in `agent/`,
`packages/` or `onboarding/`. **The reader is in `assembly/`** — `extension_rows()` parses every
ontology for `ag:row`, and three tests consume it. One of them,
`test_a_reactive_hook_never_reaches_the_planner`, holds a delivered message out of the search on
the delivering thread: it was a strict xfail until
[#392](https://github.com/ShishkinDmitriy/orexis/issues/392) landed, and it is the enforcement
the rows exist for.

So the rule is sharper than *nothing in the kernel reads it*: **a term is dead when nothing
anywhere consults it, and the search for the reader must cover every tree that loads the
vocabulary** — which `assembly/` does, being the thing that finds the ontologies at all.

# What this leaves

Twenty-odd terms are still declared and unread by the measure above, and most are part and plant
vocabularies — `bme280:Bme280`, `water:Band`. Those are NOT dead: a part class exists to be
instantiated by a world, and a world may live in another repository. A repo-wide guard would call
them dead and be wrong, which is why #430 asked for one and does not get one.

# Seams left open

- **The graph classes and arrival individuals are unmeasured.** Readers ask for the parent
  (`ag:PublicGraph`), so a subclass may be structural rather than dead, and telling those apart
  needs a different question than this one.
- **A column SELECTed and never indexed is invisible to every gate here.** `ag:confirmedBy` was
  read out of the store into a dict and dropped for two releases.
