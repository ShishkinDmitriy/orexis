---
type: Decision
title: Public knowledge is five graphs, split by who put the fact there
description: Asserted, derived and entailed facts live in separate named graphs; an ordinary query still reads all of them, because the default graph is their union.
status: accepted
timestamp: 2026-08-09T00:00:00Z
---

# Context

`refresh_public` loaded the ratified files into `:world`, then ran every package's `rules.ru`,
which `INSERT`ed into **the same graph**. So `orexis:hasCapability` — computed from the wiring — sat
indistinguishably beside topology a sovereign typed. [one-graph-both-engines-read](one-graph-both-engines-read.md)
then materialised the RDFS closure into those same two graphs, and a third kind of fact joined
the pile.

The rule that these are different things is real and load-bearing. AGENTS.md states it
(*"capabilities are derived, never declared; world.ttl must not contain orexis:hasCapability"*),
`world.ttl` carries a comment saying so, and `tests/test_capabilities.py` asserts the derivation
produces the right answer. **None of that is readable from the store.** Nothing an agent, a
shape, or a query could ask distinguished a fact somebody wrote from one something computed.

# Decision

Public knowledge is **five named graphs**, and the axis is who put the fact there:

| graph | what is in it |
|---|---|
| `graph/ontology` | the T-Box as each package asserts it |
| `graph/ontology/entailed` | what that vocabulary implies |
| `graph/world` | topology, as the sovereign ratified it |
| `graph/world/derived` | what each package's `rules.ru` computed |
| `graph/world/entailed` | what the vocabulary implies of world instances |

## Why entailed is not the same as derived

Both are computed, and it would have been cheaper to have one graph for "not asserted". The
difference is **authorship**:

- an **entailment has no author**. `?x a sensing:Sensor` follows from RDFS semantics; nobody could
  have decided otherwise and still be doing RDFS, and any engine agrees.
- a **rule-derivation is authored**. *"A scheduled sensor gives its agent `sensing:Subscribing`"* is a
  design decision living in a `rules.ru` that could have said something else. The fact has no
  latitude once the rule exists — but the rule had latitude when it was written.

That pays in the two places you feel it. **Debugging**: *why is the probe a Sensor* sends you to
the class hierarchy, *why does fern subscribe* sends you to a rule somebody wrote. **Blast
radius**: amending an entailment means changing a class hierarchy that touches everything;
amending a derivation edits one file.

## The store says what each graph is — the names are not the record

A first cut put the distinction in the graph **names**, with the explanation in a comment beside
them. That is the filename mistake one level up: a shape could not check it, an agent could not
query it, and anyone with a SPARQL client saw five graphs and no way to ask which held computed
facts. The proof it was not enough is that **renaming all five to `g1`..`g5` would leave every
query in this repository working** — nothing parses these strings, they are constants referenced
by name. So the names could not be where the knowledge lived.

`graph/provenance` carries an account of the other five, in **PROV-O and nothing else**. No
`ag:Ratified`, no `ag:DerivedGraph`, no term of ours: `prov:` is already in `store.PREFIXES` and
every observation already records its author with `prov:wasGeneratedBy`, so this is the existing
habit rather than a new vocabulary.

- **asserted** — `prov:wasDerivedFrom` each file it was read from
- **derived** — `prov:wasGeneratedBy` an activity `prov:wasAssociatedWith` the `rules.ru` that
  ran, each a `prov:SoftwareAgent`
- **entailed** — `prov:wasGeneratedBy` an activity that `prov:used` the graphs it closed over

## A graph IRI is an instance, so code may not name one

The same mistake had a second floor. Having stopped the *names* carrying the meaning, the code
still **listed** them: five constants in `ontology.py`, a `PUBLIC_GRAPHS` tuple, and — worst —
four `USING` lines typed by hand into every rule of every capability's `rules.ru`.

That is rule 1, violated in the open. `orexis:WorldGraph` is a T-Box term and code may name it;
`…/graph/world` is a particular graph and is no more nameable than a world's `:fern_agent` — which, since worlds took their individuals out of `orexis:` entirely, no longer even shares the vocabulary's namespace. The
asymmetry gave it away: `beliefs_graph(agent_id)` *constructs* its IRI from the one identifier a
process is legitimately handed, exactly as the rule allows, while the public five were bare
constants nobody had questioned.

The cost was not aesthetic. The same five were written out in three places — `ontology.py`,
`provenance.py`, and by hand in every rule — so **a capability author maintained a copy of a
registry**, correctly, per rule, or the derivation silently returned nothing.

So the instances moved into the kernel's ontology (`agent/ontology.ttl`), typed by class, and code asks:

- `orexis:PublicGraph` is the term. `store.public_graphs()` returns whatever is an instance of it.
- A rule writes `$given` and `$derived`; the loader substitutes. No `rules.ru` names a graph.
- Adding a public graph is a **vocabulary edit that touches no Python**, and there is a test
  that says so.

**Membership is by declaration, never by exclusion.** The tempting inversion — public means "not
one of the private kinds" — fails in the dangerous direction, because a new private graph nobody
remembered to exclude leaks into every query. Declared membership fails the safe way round: a
graph nobody typed is invisible until someone says what it is.

**Two things are still named, and they are not the same act.** The *bootstrap root*
`ONTOLOGY_GRAPH`, because the T-Box has to be loaded somewhere before it can be asked anything —
the same shape as the exception rule 1 already carries for an agent's own id. And the *write
targets*, because a writer must say where it writes, exactly as `beliefs_graph(id)` does. Rule 1
is about a reader enumerating what to read, and no reader does that any more.

**One consequence worth flagging**: the discovery query walks `rdfs:subClassOf*` by hand, which
the guard from #27 otherwise forbids. It is exempt for a stated reason — it runs *before* the
closure, because it is what tells the loader which graphs the closure lands in. `inference.py`
and `store.py` are the only two files that may, and both because they precede the thing they
would otherwise read.

## The per-agent catalog is derived, not written

Every world used to carry `<…/graph/beliefs/fern> a orexis:BeliefsGraph ; orexis:beliefsOf :fern_agent`,
once per agent, beside the roster it restated. A second list is a second thing to drift, and this
one drifted silently — nothing failed if an agent was added and its line was not.

It is a function of the roster, so the kernel's `agent/rules.ru` derives it, building the IRI from
the agent's own `orexis:localId` exactly as `ontology.beliefs_graph()` does. That also closes the seam
an earlier pass recorded, where a computed description stood beside a hand-written one.

## Sovereign is a role, and a user is the identity

The chain does not stop at the file. It was going to — on the reasoning that the sovereign is
outside the model and naming one would be a fiction — and that was wrong. **The sovereign is not
outside the model; it is unnamed in three places where it already exists**: Grafana's admin
login, the installation CA that `orexis-infra-certs` runs, and `orexis-keygen`, which already mints
named keypairs into a world's `secrets/`.

But there is no *sovereign identity* either, and modelling one would be the real mistake. An
installation has several users — one authors a world, another operates it with fewer powers, more
later — so being sovereign is a **capacity somebody acted in on one occasion**, not a kind of
person. PROV-O models exactly this, and naming a role is what it expects a domain to do:

```turtle
<…/graph/world> prov:wasGeneratedBy <…/activity/ratification> .
<…/activity/ratification> a prov:Activity ; prov:qualifiedAssociation
    [ a prov:Association ; prov:agent <…/user/…> ; prov:hadRole orexis:Sovereign ] .
```

`orexis:Sovereign a prov:Role` is the one term added, in `agent/ontology.ttl` — the kernel,
because a world's ratification is true of every world and `orexis:World` already lives there. **There
is no `orexis:Sovereign` agent and there must not be**; a test refuses one, because the moment the
role is also an identity, "who is the sovereign" becomes permanent and a second user cannot
exist. `orexis:Operator` and whatever follows are deliberately absent: the role set is open, and a
role no activity cites is speculation.

The rule files keep the plain `prov:wasAssociatedWith` they already had. A role would distinguish
them from nothing — every one of them is a `prov:SoftwareAgent` doing the only thing it does.

### Three choices worth stating

**Where users are declared: nowhere, yet.** A user is installation-level — AGENTS.md rule 3 puts
what is true of an installation in `infra/` — and an agent is given only its world and never sees
`infra/`. So **the world references a user URI and declares nothing about them**: no name, no key,
not even `a prov:Person`. It is an identifier the agent never resolves, exactly as `mqtt:brokerHost`
names a host it never introspects. Typing the user in the world graph would be a world asserting
facts about the installation it runs in, which it has no standing to do — and would make an
agent's provenance depend on a file it is deliberately not given.

**What the world declares versus references:** one triple, `:world prov:wasAttributedTo <user>`,
authored by the sovereign in `world.ttl`. `provenance.py` reads it and copies the identifier into
the association. A world that names nobody simply has no association, and the shape still passes —
it asks a graph where it came from, not who to blame.

## Attribution is testimony, not evidence

**Without signing, the ratified graph asserting who ratified it is circular.** Anyone who can edit
the file can edit the claim, so this records what the files say about themselves and nothing
stronger. That is worth having — legible, queryable, and a shape can reason about it — but it must
not be mistaken for proof, and the distinction belongs where somebody deciding whether to trust it
will read it.

Closing it needs no new design: `orexis-keygen <world> sovereign` already mints a named keypair
with no code changes, and [thin-trusted-infra](thin-trusted-infra.md) already points at signed
artifacts as the direction. Deliberately not done here — a signature that nothing verifies is
worse than an honest claim, and verification is its own pass.

**A file is identified under our own namespace**, `…/file/<repo-relative-path>`, not as an
absolute path or a `file:` IRI. A world sits at `/app/world/` in a container and `world/<name>/`
on a host, so an absolute path would bake one machine into the store and make the same world
describe itself differently depending on where it was built. World files are named from the world
directory's own name for the same reason — a mounted world has no relationship to this checkout.

`orexis:PublicGraphShape` refuses a `prov:Entity` that records neither. It cannot catch **silence** —
a graph nobody described is not a `prov:Entity`, so nothing targets it — so
`test_provenance.py::test_every_public_graph_accounts_for_itself` walks `PUBLIC_GRAPHS` instead of
waiting to be told. A shape catches an incomplete description; a test catches a missing one.

## Where the meta-graph is not

**Out of `PUBLIC_GRAPHS`, deliberately.** Putting it in would make `?g prov:wasGeneratedBy ?a`
work as an ordinary pattern, which is tempting — and it would merge statements *about* the graphs
into the same default graph as facts *in* the world. That use/mention confusion is not
theoretical: `orexis-wokwi` really does ask `?device a ?class`, and it would start returning
activities. Every graph IRI would become a subject in a society that otherwise contains only
things a society has.

So readers name it. The one place that must see it is the **sovereign's** check — `conforms` is
given the meta-graph by `onboarding/validate.py`, which runs unfocused over the whole world. An
agent's own startup check is focused on its own node and could never fire a shape about graphs,
so it is not given it and nothing pretends otherwise.

## The split costs a reader nothing

`store.query` passes all five as the query's **default graph**. So an ordinary pattern reads
whatever the society knows, and a reader never learns which graph holds its fact:

```sparql
SELECT ?agent WHERE { ?agent sensing:polls ?s . ?s a sensing:Sensor }
```

`sensing:polls` is the sovereign's and `a sensing:Sensor` may be entailed. Naming a graph still reads
exactly that one, which is what keeps a review's write boundary checkable.

# The trap this would otherwise have set

**A basic graph pattern inside one `GRAPH` clause must match entirely within that graph.** So
the query above, written as `GRAPH <…/world> { ?agent sensing:polls ?s . ?s a sensing:Sensor }`, returns
**nothing** the moment those two facts land in different graphs — silently, because an empty
result is not an error.

Two mechanisms avoid it, and they are not interchangeable:

- **queries** get `default_graph` on `Store.query`, set once, so every reader is right by default;
- **updates** take no such argument and must say it in the text — `USING <g>` is to
  `DELETE/INSERT … WHERE` what `FROM` is to `SELECT`. Every `rules.ru` carries them now.

`tests/test_provenance.py` fails any `SELECT` in `agent/` or `onboarding/` that narrows itself to
one public graph. It reads string literals via `ast` rather than grepping, so the prose
explaining all this cannot trip it.

## A derivation reads what is given, never what another rule concluded

Each `rules.ru` names the asserted and entailed graphs in its `USING`, and deliberately **not**
`graph/world/derived`. A rule that could see another rule's output would depend on the order
packages happen to load in, which nothing states and nothing guards.

# Two engines, one derivation

`agent/ratified.py` used to be a second implementation: rdflib parsed the same files and re-ran
the same rules, so the operator's tools derived a world separately from the way an agent does. It
now builds a `Store`, runs `refresh_public`, and pours the result into an rdflib Dataset —
**rdflib only ever reads the answer.**

That was not tidiness. The two had already diverged: after the closure was materialised, the
rdflib side had none of its own, so a device typed as a *kind* of actuator was not observably an
actuator there. `roster()` stopped deriving `actuation:Actuation` for the supplier, and the next
`orexis-compose` would have written a compose file with the signing keys silently unmounted — the
supplier unable to co-sign a dose, and every claim redemption failing. Nothing noticed, because
`compose.yaml` is committed and regenerating it is not a gate.

`test_provenance.py::test_both_engines_derive_the_same_world` is what would have caught it.

It also sidesteps an rdflib behaviour worth knowing: **`USING` there attempts to dereference the
graph IRI over HTTP** rather than resolving it against the dataset, so the rules could not have
run on that engine at all once they spanned graphs.

# World files are TriG

Parsed as TriG rather than Turtle, so a world file can name its own graphs.

**Nothing had to be rewritten.** Turtle is a syntactic subset of TriG, and `to_graph` is the
destination for a document's *default* graph only — explicit `GRAPH` blocks are honoured and land
where the file says. So every existing file behaves exactly as it did, and a `GRAPH` block becomes
opt-in per file with no flag day.

Landed now rather than later because the thing that will need it — a value genesis picked inside a
range the sovereign stated, sitting beside the range itself — then becomes a vocabulary change
rather than a parser change plus a migration.

**Files keep the `.ttl` extension.** Nothing uses a `GRAPH` block yet, so renaming would be churn
across the world glob, the compose mounts and both draw-tools' output paths for no present gain,
and mixed extensions later are their own annoyance. A file that grows a `GRAPH` block should be
renamed then.

**Scope is world files only.** A package's `ontology.ttl` and `shapes.ttl` need no graph
structure — a term's provenance is the directory it lives in. Note that `validate.py`'s
`_shapes_and_vocabulary` parses those with rdflib `format="turtle"` and would need the same
treatment if that ever changes.

# Consequences

- **The guarantee is now readable from the store**, not from AGENTS.md. `test_capabilities.py` is
  *not* made redundant by this — it tests what the derivation produces, which still needs testing.
  What was only prose is the rule that a capability must never be *declared*, and that had no test
  at all; it is now structural and covered for every world.
- **Re-running the rules without clearing leaves stale conclusions.** `refresh_public` clears the
  computed graphs first, so production is fine — but anything re-deriving by hand must too. One
  test was silently passing on a stale `sensing:Subscribing` until this landed.
- **Decimal literals reach the operator's tools canonicalised.** `agent/ratified.py` now hands
  rdflib what the store computed, so a value written `2.0` in a world file arrives as `2` —
  oxigraph's fixed-point decimal canonicalises it. The value is identical and every consumer
  parses a number (`SIM_LITRES_PER_FRACTION` is read with `_float`), but a generated file's *text*
  changed, which is worth knowing before someone diffs one and goes looking for a bug.
- **A generated artefact stopped depending on unspecified result order.** `orexis-wireviz` emitted
  wires in whatever order the store scanned; five graphs changed it, and the committed harness
  went out of step. The query now says `ORDER BY`. Same wires, same pairings — `connections:`
  permutes with `colors:` — but the order is specified rather than incidental.

# Amended: there are six, and a package may own one

[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
added `…/graph/constraint`, so **"five" is now the count at the time of writing and not the claim**.
Read every "five" below as "the public set", which is what the record actually argues for — the
whole point of `orexis:PublicGraph` being a class is that the number is data.

Nothing about the axis moved. A region is **derived**: a rule computed it, the rule could have
said otherwise, and it lands beside `orexis:hasCapability` in provenance terms even though it lands
in a different graph. What changed is only that a rule may now name **which** derived graph its
conclusions belong in, by naming a graph *class* — `$into(orexis:ConstraintGraph)` — which genesis
resolves. So *no rule names a graph* survives intact, and three things that were true of exactly
one graph because there was exactly one are now asked of the rules rather than remembered: what
`$given` excludes, what is cleared before a recompute, and what the meta-graph must account for.
That last one closes the fourth seam below from one direction: a graph a **rule** writes is
described automatically now, and a graph a **world file** declares still is not.

# Amended: and the saying is not inside the said

Every graph says who put it there, and where it SAYS it is beside the graph rather than in it —
the ontology graph for a static one, `graph/classification` for a per-agent one written at boot,
`graph/provenance` for the PROV account of a load. Asked whether the description should live in
the graph it describes, and refused: a graph is a scope a reader is handed, so a description
inside it is inherited by every reader of the data, which is the hazard the provenance graph is
kept out of the default union to avoid. The argument is in
[a-graph-says-what-it-speaks-for](/decisions/a-graph-says-what-it-speaks-for.md),
which had to settle the same question for an interval.

# Seams left open

- **A `GRAPH` block in a world file is not cleared on refresh.** `put_graph` is told one graph
  name and removes that one; a file declaring another would accumulate across starts. Nothing
  declares one yet, and the fix — enumerate what the files name, clear exactly those — is the
  same shape as `COMPUTED_GRAPHS`.
- **`deduced` is not a class here.** A value genesis picked inside a sovereign's range is a fourth
  kind of fact, distinguishable from a ratified one only when world files start carrying both.
  That is what the TriG parsing is for and it is not built.
- **`owl:` axioms are still not materialised**, unchanged from
  [one-graph-both-engines-read](one-graph-both-engines-read.md). Nothing declares one.
- **A world file with its own `GRAPH` block still needs somewhere to be described.** The
  meta-graph names the five; a sixth arriving from inside a TriG file would be silent until
  `provenance.py` learned about it, which is the same seam as the one above seen from the other
  end.
- **Nothing is signed, so attribution is testimony.** See the section above: closing it is
  `orexis-keygen <world> sovereign`, which already works, plus verification — and verification is
  the part that makes it worth doing.
- **A hand-written graph catalog still sits in every `world.ttl`.** `<…/graph/world> a
  orexis:WorldGraph` and two siblings, restated per world, covering three of the five and read by
  nothing except the owned-graph shape (`orexis:OwnedGraphShape`, once `ag:BeliefsGraphShape`) — which needs the beliefs entries, since `orexis:beliefsOf`
  carries information nothing else has. It is the partial answer that existed before this record
  and it was missed on the first pass. Left alone deliberately: it is ratified content, removing
  it is a world-file change with its own review, and a computed description now stands beside it.
  Reconciling the two is a small pass and should happen before someone adds a sixth graph to the
  hand-written half.
