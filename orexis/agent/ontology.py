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
own `ontology.ttl`, typed by class, and `store.graphs_of(engine, PUBLIC)` asks which ones they
are — so a query means "public knowledge" without any Python knowing what that consists of.
What survives here is the **bootstrap root** (the T-Box has to be loaded somewhere before it
can be asked anything) and the **write targets** (a writer must say where it writes, built
from the one id a process is handed). Neither is a reader enumerating what to read.

Three things the predecessor carried are NOT here, and each absence is a statement:

- **the choir's extension points.** `orexis:desires`, `orexis:reports`, `orexis:series`,
  `orexis:stepDone` and the rest were the questions a container asked every module it had
  loaded. Agent 2.0 loads no modules, so there is nobody to ask; the terms come back with the
  thing that needs them, and not before (an-agent-is-four-things).
- **the planning layer's graph.** What a pass considered was named here while the class that
  typed it lived a layer up, which is a lower layer naming a higher one's furniture. It is
  `orexis.agent.planning.ontology` now, where its class already was.
- **`graphs.py`.** The intention graph's name sat apart on the argument that a graph IRI is an
  instance and a term is not — beside four other graph-IRI builders in this very file. One
  file, one argument: the builders are together and `intentions_graph` is among them.
"""

from __future__ import annotations

OREXIS = "http://example.org/orexis#"
#  THE LAYER'S OWN NAMESPACE (#529): a term one layer reads and writes carries its prefix, so
#  a query says which layer it speaks for; what every layer and package writes in stays
#  `orexis:`. This is the execution layer's, and it holds what the ledger is made of.
EXECUTION = "http://example.org/orexis/execution#"
PROV = "http://www.w3.org/ns/prov#"


#  WHICH NAMESPACE A KERNEL WORD LIVES IN, by local name (#529): the ledger's words carry this
#  layer's prefix; a name not listed is `orexis:`, the vocabulary every layer and package
#  writes in. The planning layer's words are its own module's, never named here, since a lower
#  layer may not spell a higher one's vocabulary.
LAYER_OF = {
    "Act": EXECUTION,
    "Intention": EXECUTION,
    "IntentionGraph": EXECUTION,
    "Step": EXECUTION,
    "adoptedAt": EXECUTION,
    "by": EXECUTION,
    "deadlineAt": EXECUTION,
    "fills": EXECUTION,
    "forAgent": EXECUTION,
    "landsAt": EXECUTION,
    "notAfter": EXECUTION,
    "notBefore": EXECUTION,
    "of": EXECUTION,
    "outcome": EXECUTION,
    "partOf": EXECUTION,
    "patienceS": EXECUTION,
    "predicts": EXECUTION,
    "pursues": EXECUTION,
    "quantity": EXECUTION,
    "refusedBelow": EXECUTION,
    "resolvedAt": EXECUTION,
    "step": EXECUTION,
    "taken": EXECUTION,
    "takenAt": EXECUTION,
    "then": EXECUTION,
    "through": EXECUTION,
}


def term(name: str) -> str:
    """A T-Box term by name — in the namespace this layer's own layering gives it (#529)."""
    return LAYER_OF.get(name, OREXIS) + name


#  HOW LONG A COMMITMENT IS GIVEN before a fresh impulse to do the same thing is decided
#  again — the one figure of the ledger's that something outside the ledger reads: a want
#  foreseen at an instant holds until that instant plus this, because the last step is placed
#  AT the instant and its verdict comes after. It sat on the keeper in the predecessor, which
#  made a higher layer import a class to get at a word; a term lives with the terms.
PATIENCE_S = term("patienceS")


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
GRAPH_PREFIX = _GRAPH

ONTOLOGY_GRAPH = _GRAPH + "ontology"                    # the T-Box as the packages assert it
ONTOLOGY_ENTAILED_GRAPH = _GRAPH + "ontology/entailed"  # what that vocabulary implies
WORLD_GRAPH = _GRAPH + "world"                          # topology, as the sovereign ratified it
WORLD_DERIVED_GRAPH = _GRAPH + "world/derived"          # what each package's rules.ru computed
WORLD_ENTAILED_GRAPH = _GRAPH + "world/entailed"        # what the vocabulary implies of instances
#  The world's current state as this agent holds it — what an effect rewrites and a plan forks.
#  The IRI still says "sensed", for every volume that holds readings under it.
STATE_GRAPH = _GRAPH + "sensed"
#  What every ACTION makes true, loaded from the packages at genesis (#238). Public, because a
#  search reads it on every pass; asserted from files, so it is replaced at each boot.
ACTIONS_GRAPH = _GRAPH + "actions"
#  The desire and want roots a world ratifies — write targets, projected by nothing now that
#  nothing stands between a desire and a want.
DESIRE_ASSERTED_GRAPH = _GRAPH + "desire/asserted"
WANT_ASSERTED_GRAPH = _GRAPH + "want/asserted"
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
#  What a RULE is answered over — a met-test, a precondition, an availability select, an
#  effect: everyone's knowledge, what is, the records, the desires and the wants. Stated once
#  here and named at every runner, so a runner says what it hands a text.
KNOWN = (PUBLIC, BELIEF, RECORD, DESIRE, WANT)
#  ...and, for a reader standing at an instant, what is expected to hold then.
FORESEEN = (*KNOWN, PREDICTION)

#  A GRAPH'S NAME IS FOR EYES. The builders below spell a readable convention for the graphs
#  the kernel writes — `intentions/<agent>`, `picks/<agent>` — and nothing in code depends on
#  the spelling: an owner classifies what it writes (`store.classify`) and every reader asks
#  the class (`store.graphs_of`). Rename one here and only the eyes notice.


def picks_graph(agent_id: str) -> str:
    """The graph holding ONE agent's picks — its record of picking, birth's first entries and
    review's revisions. Also its write boundary, in the strong sense: a review may write here
    and nowhere else."""
    return _GRAPH + "picks/" + agent_id


def intentions_graph(agent_id: str) -> str:
    """What this agent is committed to, standing and resolved. Its own, and only its own.

    NOT public, and the absence is the design: an intention disclosed is strategy leaked. Apart
    from the picks graph on purpose — a pick has one value, held to `sh:maxCount 1`, while
    intentions accumulate a history: every resolved one stays, with its outcome and its reason,
    because a ledger that forgot its resolutions could not answer the only question an operator
    brings to it, which is what this agent thought it was doing and why it stopped.
    """
    return _GRAPH + "intentions/" + agent_id


def desires_graph(agent_id: str) -> str:
    """One agent's desires, authored at genesis and holding at every instant (#644).

    THE NAME STILL SAYS `roots/`, and deliberately. It was written when a desire was called a
    root desire; there is only a DESIRE now and wants are derived from it, so the identifier
    says that. The NAME is for eyes and no reader depends on it — but a WRITER does: an agent
    whose volume already holds `roots/<id>` would gain a second graph of the same class the
    first time anything endowed into a renamed one, and both would be read. A graph is renamed
    with a migration or not at all."""
    return _GRAPH + "roots/" + agent_id


def obligations_graph(agent_id: str) -> str:
    """The record of ONE agent's debts. The graph CLASS and every word written in it are the
    ledger's package's (#635); the name is built here because the readers that project the
    record should not import a package for a name built from the one id rule 1 allows."""
    return _GRAPH + "obligations/" + agent_id
