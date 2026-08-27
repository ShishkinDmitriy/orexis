---
type: Runbook
title: Add a package
description: >-
  What to create, what is mandatory and enforced by which gate, what is merely recommended, and
  what an omission means. A package is a directory; adding one is adding a directory, and
  nothing anywhere is edited to admit it.
---

# The shortest package that works

```bash
mkdir -p packages/part/thermistor
```

```turtle
# packages/part/thermistor/ontology.ttl
@prefix thermistor: <http://example.org/orexis/thermistor#> .
@prefix : <http://example.org/orexis/thermistor#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

<http://example.org/orexis/thermistor> a owl:Ontology ;
    rdfs:label "Thermistor" ;
    rdfs:comment "A resistance thermometer, and what a world must say to fit one." .

:Thermistor a owl:Class ; rdfs:label "Thermistor" .
```

That is a complete package — run before this page was written, and removed again. **Nothing
else is edited** — no registry, no list, no import. The
loader walks two levels under `packages/`, finds it, merges its vocabulary, and `thermistor:`
reaches any query. Delete the directory and it is gone as completely.

Check it landed:

```bash
python -c "from assembly import loader; print(loader.prefixes()['thermistor'])"
orexis-validate simulation
```

# Where it goes

`packages/<family>/<name>/`. The **family is the parent directory and is declared nowhere** —
`kind` is read off the path.

| family | what it holds |
|---|---|
| `capability/` | what an agent can DO. The extendable axis |
| `transport/` | how a device is REACHED. Deliberately not a capability |
| `codec/` `scaling/` | how bytes become a document, and a document a quantity |
| `part/` `bus/` | the physical things and the protocols between them |
| `plant/` | a domain and its species — what a society is ABOUT |
| `sim/` | what stands in for hardware nobody built |
| `tool/` | vocabularies a generator reads, not the society |

**A family nobody thought of is still found.** `KINDS` in the loader is a sort order, not a
gate: a new family sorts after the known ones instead of being ignored. `packages/sim/` was
added without touching the loader.

# What may be in it, and what an omission means

Every file is optional, **and leaving one out is a statement**. `packages/part/esp32/` is an
ontology and nothing else, because a board has no behaviour a runtime could load.

| file | what it does | omitted means |
|---|---|---|
| `ontology.ttl` | the vocabulary — what its terms mean | it brings no words (rare; then why a package?) |
| `shapes.ttl` | what must be true of a thing that has it | nothing to check |
| `rules.ru` | the premise that GRANTS its capability | it grants none — knowledge only |
| `desires.ru` | what an agent holding it therefore wants | it implies no wants |
| `actions.ttl` | ways of acting: precondition, effect, `ag:takenBy` | nothing to plan with |
| `review.rq` | what an agent may reconsider about itself | nothing revisable |
| `__init__.py` | `PROVIDES = (…)` — the classes it contributes | **it ships no code at all** |
| `terms.py` | its terms as constants, and the families it asks others for | — |
| `beliefs.py` | its `Picks` — the private parameters it reads | it decides nothing |
| `module.py` | the code, reading only its own vocabulary | — |

A file the kernel does not name is still yours: sensing keeps a `measures.ttl` and reads it
itself. The list above is **the loader's reading list**, not a permitted set.

# Mandatory — and what refuses you

Each of these fails loudly. None is a matter of taste.

**Its ontology declares its own namespace twice.** A default prefix and a named one, both the
same IRI:

```turtle
@prefix thermistor: <http://example.org/orexis/thermistor#> .
@prefix : <http://example.org/orexis/thermistor#> .
```

The empty prefix carries the convention *unprefixed means mine*; the named one is what
`loader.prefixes()` discovers, because its regex needs a label. Enforced by
`tests/test_store.py::test_an_ontology_gives_its_own_terms_the_default_prefix`.

**One label, one namespace.** Two ontologies declaring the same prefix for different IRIs is a
`RuntimeError` at load: *"a query cannot mean both."*

**A package implements the terms IT declares.** A module's `CAPABILITY` must be in the
package's own namespace, or the loader refuses: *"a package implements the terms it declares,
which is what lets imports follow grants (#216)."*

**One term, one module.** Two classes claiming the same `CAPABILITY` is a `RuntimeError`, not a
resolution — the alternative is settled by whichever package the filesystem yielded first.
The same holds for `TERM` on a codec or scaling member.

**Every provided class says what activates it.** A capability module needs `CAPABILITY`; a
family member needs `TERM`. A class with neither is refused by name.

**No capability imports another capability.** `lint-imports` holds an `independence` contract
over actuation, market, sensing and review. The one written exception is a family's plug-ins
importing that family's **contract** — `packages/codec/*` imports sensing's `Codec`. Reach
another capability through `agent.provider(family)` or the choir, never through Python.

**No package imports `onboarding`.** It mints credentials and reads the admin token.

**Only `store.PREFIXES` prefixes in SPARQL.** rdflib silently pre-binds common prefixes and
Fuseki does not, so a query can pass every test and 400 in production. Checked by scanning
source text.

**A new word gets a `knowledge/domain/` page in the SAME change.** A word used before it is
defined is a word everyone defines differently.

**If it declares an extension point, the point publishes its signature.** `assembly:signature`
on the term, checked strictly against every filler's parameter names — that is what lets
another package contribute without importing yours.

# Recommended — nothing enforces these

- **Name the directory for the thing, not the role.** `dht11`, not `temperature_sensor_driver`.
  Underscores, never hyphens: the directory is a Python package name.
- **The prefix label is the package name**, and the namespace is
  `http://example.org/orexis/<label>#`. Short and full-word — `sensing:`, `market:`, `device:`,
  not `sns:`.
- **Write the `rdfs:comment` for someone who will have to change it**, not for a catalogue. Say
  why the term exists and what breaks without it. Every comment in this project is doing that.
- **A package may carry its own tests** — plain `test_*.py` beside the code — for the rare thing
  that means something alone. `pytest` collects both roots.
- **Ship a capability you cannot yet implement, if the vocabulary is honest.** `sensing:Polling`
  is declared with no rule granting it and no module providing it: the room is kept on purpose,
  and adding it later is a class and one line of `PROVIDES`.

# When it is a capability

Three extra things, in this order:

1. **A premise in `rules.ru`.** Each capability is granted by whatever fact makes it meaningful
   — equipment, a position in a market, or latitude — and there is no pattern to fit a new one
   into. Ask what makes *yours* meaningful. A premise may use AUTHORED or ENTAILED facts and
   **never another package's conclusions**: derivations run once, in package order, and a rule
   resting on another's output matches nothing and says nothing.
2. **Capabilities are worked out at genesis, never hand-declared.** `world.ttl` must not contain
   `ag:hasCapability`.
3. **A shape for what an agent holding it must believe.** Capability-aware: it applies only to
   agents the world derived that capability for.

# Before you call it done

```bash
pytest -q                    # BOTH roots — not `pytest tests`
orexis-validate simulation   # and every other world you have
lint-imports                 # the layering
./tools/validate-okf.sh knowledge
```

`pytest` and `orexis-validate` are the two gates and both must pass. If the package touches the
bus or the store, `pytest infra -q -n0` is a third thing, run deliberately.

# What you will get wrong first

- **Naming a package's instance instead of its term.** Code may reference T-Box terms and never
  an instance. `term("Subscribing")` is fine; `"sensors/fern/moisture"` is not.
- **Wrapping `GRAPH <…>` around a SELECT.** Public knowledge is several graphs merged as the
  default graph. Narrowing returns nothing the moment a fact lives elsewhere — silently.
- **Expecting an empty result to be an error.** It is not, and a loop over one runs zero times
  with every assertion inside it skipped.
