"""The kernel vocabulary — prefixes and graph names, and deliberately nothing else.

Everything here is true of every agent: how a term is spelled, and which graph a fact lives
in. A term that belongs to one capability is named by that capability's own package, so this
file never grows when one is added. That is the whole reason it is this short.

Everything here is a **T-Box term**: a class or a property. Those are public and well-known,
and code is written against them exactly as it is written against a function signature. What
must never appear in code is an **instance** — no `"supplier"`, no `orexis:world`, no
`"sensors/{id}/moisture"`. Instances are discovered from the graph, starting from the single
identifier a process is given: its own agent id.

**Graph IRIs are not terms.** `orexis:WorldGraph` is the term; `…/graph/world` is a particular
graph, no more a term than `orexis:fern_agent` is. The instances are declared in the kernel's
own `ontology.ttl`, typed by class, and `graphs_of(store, PUBLIC)` asks which ones they
are — so a query means "public knowledge" without any Python knowing what that consists of.
What survives here is the **bootstrap root** (the T-Box has to be loaded somewhere before it
can be asked anything) and the **write targets** (a writer must say where it writes, built
from the one id a process is handed). Neither is a reader enumerating what to read.

Three things the predecessor carried are NOT here, and each absence is a statement:

- **the choir's extension points.** `orexis:desires`, `orexis:reports`, `orexis:series`,
  `orexis:stepDone` and the rest were the questions a container asked every module it had
  loaded. Agent 0.2.0 loads no modules, so there is nobody to ask; the terms come back with the
  thing that needs them, and not before (an-agent-is-four-things).
- **the planning layer's graph.** What a pass considered was named here while the class that
  typed it lived a layer up, which is a lower layer naming a higher one's furniture. It is
  `agent.planning.ontology` now, where its class already was.
- **the EXECUTION layer's own words.** `execution:`, its `patienceS` and the intention graph's
  name are `agent.execution.ontology`, which is the whole of what this file's `.ttl`
  turned out to declare: twenty-seven `execution:` terms and not one `orexis:` one. What is
  here is the vocabulary EVERY layer writes in, which is what makes it sit beside them rather
  than inside one of them.
- **three builders nobody read** — `desires_graph`, `obligations_graph`, and the `LAYER_OF`
  table with the `term()` that consulted it. The table had no reader at all and `term()` had
  one call, in this file, which is `EXECUTION + name` said the long way.
"""

from __future__ import annotations

OREXIS = "http://example.org/orexis#"
def local_of(iri: str) -> str:
    """An IRI's local part — what a package's own prefix would write after the colon.

    The name a parameter answers to in three places at once: the variable its action's
    precondition projects, the `$token` its rules read, and the column a row binds. One
    spelling, so a package that declares `hanoi:disk` writes `?disk` and `$disk` and nothing
    maps between them.
    """
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


# --- named graphs ---------------------------------------------------------------------------
#
# Public knowledge is several graphs, not one, and the axis is **who put the fact there**:
#
#   asserted   somebody wrote it in a file — a package's vocabulary, or the sovereign's world
#   derived    a rule computed it: the fact has no latitude once the rule exists, but the rule
#              had latitude when it was written
#   entailed   RDFS said it. No author, no alternative
#
# Which is why they are different graphs rather than one "computed" one: amending the two has
# utterly different blast radius. See knowledge/decisions/who-put-the-fact-there.md.
_GRAPH = "http://example.org/orexis/graph/"
#  Where every graph lives in the IRI space. Exported because a package that owns graphs of its
#  own builds their names from here — where a graph SITS is the kernel's, what it HOLDS is not.

#  WHAT A GRAPH HOLDS, as a hash — written on the graph's own catalogue row beside its class
#  and its period, because it is a fact OF the graph and not one IN it. `hash_named_graph`
#  computes it; two graphs carrying one value hold the same facts, which is what tells a
#  search that a world has been seen before.
#
#  NOT `signature`, which this project already uses for the other thing: an actuator
#  co-signs a command, and onboarding mints the keys that make that possible. A digest of
#  content is a HASH, and a word doing two jobs is how one concept becomes two.
#
#  THE VALUE SAYS ITS ALGORITHM — `sha256:<hex>` — so a row is readable without knowing
#  what wrote it, and so the day the algorithm changes an old row cannot be compared with a
#  new one by accident.
HASH = OREXIS + "hash"

GRAPH_PREFIX = _GRAPH

#  WHAT THE VOCABULARY ENTAILS: every `rdfs:subClassOf` step the ontology graphs reach, written
#  by the runtime at boot into one graph of its own, classified `orexis:OntologyGraph` and
#  derived. Every other public graph is a document's, named by the document and found by its
#  kind; this is the one no file holds.
CLOSURE_GRAPH = _GRAPH + "ontology/closure"

#  THE CATALOGUE: the one graph that says what every graph IS — class, owner, arrival, period —
#  and describes itself, so no reader knows this name: `store.catalogue_of` finds the graph
#  that says of itself `a orexis:CatalogueGraph`. Named here for the one writer that CREATES
#  it, genesis, and for nothing else (one-catalogue-describes-every-graph-and-itself).
CATALOGUE_GRAPH = _GRAPH + "catalogue"

#  THE KINDS A READER ASKS FOR. A graph is read by what the catalogue says it IS, never by its
#  name (a-reader-states-the-kinds-it-reads): a reader lists the kinds it means and the instant
#  it stands at, `store.graphs_of` answers with the graphs, and nothing decides on anyone's
#  behalf. Each kind is a kernel term a package may put its own graph under, which is how a
#  package's record reaches every rule without the kernel learning the package's name.
PUBLIC = OREXIS + "PublicGraph"          # everyone's: the vocabulary, the world, the actions
BELIEF = OREXIS + "BeliefGraph"          # what IS: the state, the instruments, a claim held
STATE = OREXIS + "StateGraph"            # the readings — what a plan forks and an effect rewrites
PREDICTION = OREXIS + "PredictionGraph"  # what is expected, holding during its window
RECORD = OREXIS + "RecordGraph"          # an agent's own record, worth believing during its period
DESIRE = OREXIS + "DesireGraph"          # desires
WANT = OREXIS + "WantGraph"              # wants
SHAPES = OREXIS + "ShapesGraph"          # what a met-test and an estimate point at
#  What a RULE is answered over — a met-test, a precondition, an availability select, an
#  effect: everyone's knowledge, what is, the records, the desires and the wants. Stated once
#  here and named at every runner, so a runner says what it hands a text.
KNOWN = (PUBLIC, BELIEF, RECORD, DESIRE, WANT)
#  ...and, for a reader standing at an instant, what is expected to hold then.
FORESEEN = (*KNOWN, PREDICTION)

#  A GRAPH'S NAME IS FOR EYES. The builders below spell a readable convention for the graphs
#  the kernel writes — `intentions/<agent>` — and nothing in code depends on
#  the spelling: an owner classifies what it writes (`store.classify`) and every reader asks
#  the class (`store.graphs_of`). Rename one here and only the eyes notice.


