---
type: Runbook
title: Add a package
description: >-
  What to create, what is mandatory and enforced by which gate, what is merely recommended, and
  what an omission means. A package is a directory; adding one is adding a directory, and
  nothing anywhere is edited to admit it.
---

# The shortest package that works

Three files: a project saying what you need, a manifest saying what you bring, and the thing you
bring.

```bash
mkdir -p packages/orexis-part-thermistor
```

```toml
# packages/orexis-part-thermistor/pyproject.toml
[project]
name = "orexis-part-thermistor"
version = "0.1.0"
description = "A resistance thermometer"
requires-python = ">=3.10"
dependencies = ["orexis"]        # the manifest imports `assembly`; nothing else is needed

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["orexis_part_thermistor"]
package-dir = {"orexis_part_thermistor" = "."}

[tool.setuptools.package-data]
"orexis_part_thermistor" = ["*.ttl", "*.ru", "*.rq"]     # the knowledge IS the package
```

```python
# packages/orexis-part-thermistor/__init__.py
"""What a thermistor brings to a build. Knowledge only — no behaviour a runtime could load."""

from pathlib import Path

from assembly import contributes, VOCABULARY


@contributes(VOCABULARY)
def vocabulary(package: Path) -> list[Path]:
    return [package / "ontology.ttl"]
```

```turtle
# packages/orexis-part-thermistor/ontology.ttl
@prefix thermistor: <http://example.org/orexis/thermistor#> .
@prefix : <http://example.org/orexis/thermistor#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

<http://example.org/orexis/thermistor> a owl:Ontology ;
    rdfs:label "Thermistor" ;
    rdfs:comment "A resistance thermometer, and what a world must say to fit one." .

:Thermistor a owl:Class ; rdfs:label "Thermistor" .
```

That is a complete package. **Nothing else is edited** — no registry, no list, no import; the
workspace glob in the root `pyproject.toml` already matches `packages/*/*`. The
loader walks one level under `packages/`, finds it, asks what it contributes, merges its
vocabulary, and `thermistor:` reaches any query. Delete the directory and it is gone as
completely.

Check it landed:

```bash
pip install -e packages/orexis-part-thermistor   # or: uv sync --all-packages
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
gate: a new family sorts after the known ones instead of being ignored. `packages/orexis-sim-*/` was
added without touching the loader.

# What may be in it, and what an omission means

Every file is optional, **and leaving one out is a statement**. `packages/orexis-part-esp32/` is an
ontology and nothing else, because a board has no behaviour a runtime could load.

**The manifest is the only file the loader knows by name.** Everything else is named by the
manifest, so a package may split its shapes across three files or call its vocabulary anything —
the names below are what every package happens to use.

| file | what it does | omitted means |
|---|---|---|
| `__init__.py` | **the manifest** — what it contributes, and `provides()` | it contributes nothing and is invisible |
| `ontology.ttl` | the vocabulary — what its terms mean | it brings no words (rare; then why a package?) |
| `shapes.ttl` | what must be true of a thing that has it | nothing to check |
| `rules.ru` | the premise that GRANTS its capability | it grants none — knowledge only |
| `desires.ru` | what an agent holding it therefore wants | it implies no wants |
| `actions.ttl` | ways of acting: precondition, effect, `ag:takenBy` | nothing to plan with |
| `review.rq` | what an agent may reconsider about itself | nothing revisable |
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
importing that family's **contract** — `packages/orexis-codec-*` imports sensing's `Codec`. Reach
another capability through `agent.provider(family)` or the choir, never through Python.

**No package imports `onboarding`.** It mints credentials and reads the admin token.

**Only `store.PREFIXES` prefixes in SPARQL.** rdflib silently pre-binds common prefixes and
Fuseki does not, so a query can pass every test and 400 in production. Checked by scanning
source text.

**A new word gets a `knowledge/domain/` page in the SAME change.** A word used before it is
defined is a word everyone defines differently.

**`__init__.py` stays cheap**, and a test says so. Every one is imported at assembly, for every agent — so it may
import stdlib, its own `.terms`, and `assembly`, and nothing else
(`test_a_package_manifest_imports_nothing_expensive`). The heavy import lives inside `provides()`,
which is a function for exactly that reason: an agent granted none of your classes never pays
for them, and a missing optional extra costs only the agents that were granted the capability
needing it.

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

# Reaching anything outside your package

Four doors, and which one you want is decided by what you are asking for. This is the part a
package author previously had to learn by reading other packages.

| you want | the door |
|---|---|
| everyone's opinion, merged your way | `agent.ask(POINT)` — the [choir](/domain/choir.md) |
| whoever implements an ability | `agent.provider(family)` — answers `None` if nobody does |
| **a particular thing another package offers** | **annotate a field with its type** |
| another package's *contract* (a base class) | an ordinary import of its `contract` module — never its implementation |

```python
from orexis_deliberation.beliefs import Beliefs
from agent.metrics import Metrics

class MyModule(Module):
    CAPABILITY = MY_TERM      # has a value: an ordinary attribute
    beliefs: Beliefs          # no value: a service, required
    ring: Ring | None         # `| None`: one it can work without

    def start(self):
        self.metrics.event("started", "")     # resolved on first touch
```

**A field with no value is a service** — the same convention `dataclasses` uses, chosen over a
decorator because an annotation is visible to your IDE and your type checker where an attribute
conjured by a decorator is not. It may not shadow a name a base class already has: `desires`
collides with `Module.desires()`, and that raises rather than silently skipping.

**The key is the type you would import anyway.** `packages -> agent` is allowed, so the kernel's
services are keyed by their classes; another package's service is keyed by the contract in its
`contract` module, which is the one cross-package import the layering has always permitted. A
term works too, for a service with no importable contract — but a type is the default, because
it needs no second name kept in step with the first.

**Declare it rather than reaching for `self.agent.<something>`.** Twelve attributes were in use
that way before services existed, none of them written down anywhere. Declaring means the gate
can see what you need — `orexis-validate` refuses a build where something required is offered by
nobody — where reaching means the first to find out is you, at runtime.

To offer one, put it in your manifest — the function runs when an agent first asks, so the
import is paid only by an agent that wants it:

```python
@provides
def history(agent) -> HistoryRing:  # the key is the return annotation
    from .ring import Ring          # the implementation, lazily
    return Ring(agent)
```

One key, one provider: offering something another package already offers is refused at load.

**If it needs closing, yield it** — what follows the yield runs at shutdown, newest first:

```python
@provides
def history(agent) -> HistoryRing:
    ring = Ring(agent)
    yield ring
    ring.flush()
```

**If you can work without it, annotate `X | None`.** The attribute is `None` where nothing
offers it and no gate fails your build — where a plain annotation nothing offers is refused
before anything runs. Declare it either way: an undeclared reach is invisible, which is what
this replaced.

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

# If it needs a third-party dependency

**Declare it in your own `pyproject.toml`.** You import it, so you depend on it — nobody declares
it on your behalf, and the root does not know your package exists.

```toml
dependencies = [
    "orexis",
    "some-model-client>=1.0",
]
```

`tests/test_projects.py` holds this list to what your Python actually imports, in **both**
directions: a dependency you import and did not declare fails, and one you declared and do not
import fails too. That second direction is the one that catches most, because a dependency stops
being needed when the last import of it goes and nothing about deleting a line of Python makes
anyone open a TOML file. Four defects were sitting in the single list the day it was split, and
all four were of these two kinds — see
[every-package-is-a-project](/decisions/every-package-is-a-project.md).

**A sibling package is a dependency like any other.** `packages/orexis-codec-json` implements sensing's
`Codec`, so it depends on `orexis-capability-sensing` and says so. That is the one written
exception to packages not importing each other: a family's plug-ins import the family's contract.

**If the dependency is heavy and only some agents need it**, keep it an extra and import it
inside `provides()`:

```toml
[project.optional-dependencies]
consulting = ["some-model-client>=1.0"]
```

```python
def provides() -> tuple:
    from .consulting import ConsultingModule    # the import that needs the extra
    return (ConsultingModule,)
```

An agent granted the capability pays for it and **an agent that was not pays nothing**:
`_provider_in` catches the `ImportError`, logs that the capability is unavailable, and every
other agent in the society starts normally. What changed is only *whose* `pyproject.toml` the
extra goes in — yours, not the root's.

# You cannot add a member to somebody else's family

A package may implement only the terms IT declares, and that is enforced at load. So a different
matching algorithm goes in `packages/orexis-capability-market/`, and a model-backed review in
`packages/orexis-capability-review/` — beside the family that declared them, not in a package of your
own. What a new package brings is a NEW ability: its own family, its own terms, its own members.
See [a-family-is-closed-and-that-is-a-choice](/decisions/a-family-is-closed-and-that-is-a-choice.md),
which also says what it would take to change that.

# Before you call it done

```bash
pip install -e packages/orexis-<family>-<name>   # a project is not installed by existing
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
