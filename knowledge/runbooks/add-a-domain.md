---
type: Runbook
title: Add a domain
description: >-
  What to write to give worlds a new body of knowledge - a directory under `domains/` of documents,
  each saying which graph it is - its words, its actions, what its words mean when wanted, its
  rules - and the gates that hold it. No Python, no registry, nothing edited to admit it.
---

# What to create

`domains/<name>/`, and in it whichever of these the domain needs. Every document states its own
kind on `<>`; the file's name is for eyes.

| file | first line | holds |
|---|---|---|
| `ontology.ttl` | `<> a orexis:OntologyGraph ; owl:imports <actions.ttl> , …` | the classes and properties, invariant individuals, the parameters actions take — and the imports of the others |
| `actions.ttl` | `<> a orexis:ActionGraph` | the [actions](/domain/kernel/action.md): what each takes, its precondition, its effect, its implementation, its cost |
| `shapes.ttl` | `<> a planning:ShapesGraph` | met-tests a desire's `planning:metWhen` points at, and the selects `planning:estimates` points at |
| `rules.ttl` | `<> a sh:RulesGraph` | rules the deliberator runs over the beliefs — the market's revisions of its documents, the tower's [bridges](/domain/planning/bridge.md) |
| `drifts.ttl` | `<> a orexis:DriftGraph` | what a value does by itself, `prediction:Drift`s |

A domain that combines others imports them: the tower's ontology imports `<../hanoi/ontology.ttl>`
and `<../courier/ontology.ttl>` beside its own rules.

A domain whose agents play a part only its words can name declares that as a
[role](/domain/kernel/role.md) in its `ontology.ttl`, `rdfs:subClassOf` each package role it needs —
the market's `market:Host` is beneath the planner, the executor, the speaker and, since it ships
`rules.ttl`, the deliberator — and beside it a SHACL shape targeting the role whose `sh:sparql`
select returns a row where the world lacks what the role is founded on, `market:hosts` for the host.
A world's agents are then declared in the domain's word, and nobody lists what it runs.

# The rules its texts live by

- **Every SPARQL text declares its own prefixes.** The store's dictionary never learns a domain's
  namespace, so each precondition, rule, command and select carries `PREFIX name: <…>` at its
  head; `tests/test_store.py` fails a text using a name nobody declared.
- **A text names no graph.** The runner hands a precondition its world, scopes an effect's delete
  `WITH` the new world, and hands a rule the source beside public knowledge.
- **Effects speak concepts the rules conclude**, not numbers: a dose predicts `sensing:inside`, and
  its command sizes the act from the present when the step is taken.
- **An estimate never overstates** the cost left, in the unit `planning:costs` is stated in; that
  promise is the domain's, since no world can keep it.

# How a world uses it

`owl:imports <../../domains/<name>/ontology.ttl>` on the world's own `<>`. The boot follows imports
transitively and loads only what a world asks for. An action only some of a domain's worlds have goes
in a document the ontology does not import, and those worlds import it beside the ontology — the
courier's boarding, `domains/courier/driver.ttl`, which `world/driver/` asks for and the dispatcher
never loads, since an action admitting nothing still splits a world's scopes (#913). Nothing in `agent/` or `onboarding/` may name a
domain's IRI — `tests/test_layout.py` fails one that does — so the domain stays a plug-in.

# How it is held

By a world that uses it: `world/<name>/tests/` boots the world from its files and runs it to its
answer. A domain has no tests of its own; what it means is what the worlds that speak it do.
