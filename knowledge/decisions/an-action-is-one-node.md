---
type: Decision
title: An action is one node — precondition, effect and taker — and whom a row serves is a column, not a mode
description: >-
  Adding a way of acting meant writing to three files and a fourth surface: `affordances.rq`
  for availability, `honoured.rq` for the obligation-shaped rows, `effects.ttl` for what it makes
  true, and `orexis:takenBy` in the ontology for who carries it out. They were four statements
  about one thing, and the STRIPS operator this architecture rests on IS one thing. Now a
  package ships `actions.ttl` — one `orexis:Action` node per way of acting — and `orexis:Mode`,
  `orexis:Chosen`, `orexis:Honoured` and `orexis:effectOf` are retired: whether a row is the agent's own or
  an obligation is whether its availability query bound `?for_agent`.
status: accepted
timestamp: 2026-08-25T00:00:00Z
---

# What was true before

[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) found that this
architecture was already classical planning: a menu row's WHERE clause is an action schema's
precondition, an effect rule its add/delete list, an intention a committed step. What it did not
do was make the schema one object. The precondition lived in `affordances.rq` (and, for an obligation,
`honoured.rq`), the effect in `effects.ttl` keyed back to the means by `orexis:effectOf`, and — since
[an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md) — the
taker in `ontology.ttl` as `orexis:takenBy` on the means. The loader found three file kinds, the menu
read two of them, the planner joined the third by a term, execution joined a fourth. An author
adding a way of acting learned four conventions to say one thing, and the sovereign asked for a
bare minimum of BDI concepts that a new package could reuse rather than re-learn.

The two-mode vocabulary was the same shape one level down. `orexis:Chosen` and `orexis:Honoured` were
individuals of `orexis:Mode`, bound by hand in every `affordances.rq` (`BIND(orexis:Chosen AS ?mode)`),
and what they encoded was already stated by another column: an honoured row carried `?buyer`, a
chosen row did not. Two terms for a fact one column states is a second owner of that fact.

# What is decided

**An [action](/domain/action.md) is one node**, `a orexis:Action`, in a package's `actions.ttl`:

| part | property | what it is |
|---|---|---|
| kind | ~~`orexis:means`~~ | the node itself, since [the-action-is-the-kind](/decisions/the-action-is-the-kind.md) |
| precondition | `orexis:available` | a SELECT binding `?property ?via ?direction`, and `?for_agent` for an obligation |
| effect | `sh:construct`, `orexis:retracts`, `orexis:landsAfter`, `orexis:confirmedBy` | unchanged from the effect rule |
| taker | `orexis:takenBy` | the capability whose module carries it out |

The loader finds `actions.ttl` where it found three files; genesis loads it into the **action
graph** (`orexis:ActionGraph`, was the effect graph); `menu_of` runs every action's `orexis:available`;
`effects.rule_for` and `execution.taken_by` join on `orexis:means`. Nothing lists the actions, and a
new way of acting is a node in a new directory plus a `take()`.

**Whom a row serves is a column.** An [affordance](/domain/affordance.md) with `for_agent` bound
is an obligation's — exercised for that counterparty on a valid presentation and never proposed for the
agent's own gap; one without is the agent's own option. `Affordance.is_own` reads the column;
the planner's filter and the deliberator's obligation fallback read the same column; `orexis:Mode`,
`orexis:Chosen`, `orexis:Honoured` and `ag:mode` are gone from the vocabulary, and `honoured.rq` is a
second `orexis:Action` (the host's `market:Serving`) in the same file as `market:Acquiring`.

**`orexis:effectOf` is gone.** An effect is not a thing that is *of* a means; it is a part of the
action that has the means. The join every reader walks is `orexis:means`, once.

# What did not change

- The queries. Every availability SELECT and every effect CONSTRUCT is the text it was, moved
  into a literal — the `.rq` files already went through `store.query` with the store's
  prefixes, and so do the literals.
- The gate. `orexis-validate` still refuses a world in which a means on some agent's menu has
  no effect: an action without `sh:construct` puts rows on the menu and simulates nothing, and
  `rule_for` returns None for it exactly as it did for a means with no rule.
- The search, the keeper, execution. They read the same columns from the same rows.
- Private volumes. Actions and menu rows only ever lived in public graphs rebuilt at boot, so
  no term here needs `vocabulary.MOVED`.

# What it cost

The linker scans a third TTL kind for SPARQL literals; the source-scan tests that named
`affordance_files()` name `action_files()`; `tests/test_store` parses the availability
literals out of the nodes instead of reading `.rq` files. The dangling-term guard still sees
every IRI in every query, because the TTL loop already resolves SPARQL inside literals.

# Seams left open

- **The means are still the kernel's five.** An action names one; it does not declare one. A
  package could declare a sixth (`means.md` claims it can), and then `keeper.on_reading_recorded`
  — which satisfies `ag:Observe` by name — is the one place the kernel would have to learn a
  package word. The day a package needs a means the kernel does not have is the day that
  becomes a hook.
- **A stale `graph/effects` in a volume born before this.** Public graphs are rebuilt at boot
  under their current names; the old one is neither classified nor read, so it is inert, and
  `rebirth` drops it. Nothing sweeps it.
- ~~`sh:condition` is carried and not evaluated by the planner~~ — closed: it was deleted, with
  the two condition-only shapes, because a second statement of a precondition nothing reads is
  one that can disagree with the first. A shape's validation report — *why* an action is
  unavailable — is the one thing it would add, and it is added the day it is wanted
  ([action](/domain/action.md)).
