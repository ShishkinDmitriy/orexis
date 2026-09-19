"""The kernel vocabulary — prefixes and graph names, and deliberately nothing else.

Everything here is true of every agent: how a term is spelled, and which graph a fact lives in.
A term that belongs to one capability — `sensing:Subscribing`, `market:Bidding` — is named by
that capability's own package, so this file never grows when one is added. That is the whole
reason it is this short.

It used to say "true of every CAPABILITY", which was the honest wording while wanting, keeping
and deciding were capabilities. They are not: a mind is not plug-in-able, so the states a mind
contains are here and every agent has them, granted by nothing. What a capability is remains what
it always was — an ability with interchangeable implementations, which after the dissolution means
equipment or a mandate. See knowledge/decisions/the-mind-is-not-a-package.md.

**Fourteen terms in the kernel's own `agent/ontology.ttl` still make that claim false, and they
are named rather than implied**: the eleven of the simulated world — the device model plus its clock and its
weather (`sim:timeScale`, `sim:strayDoseMeanDays`, `sim:rainTopic`) — which only `world/simulation`
uses and which want a simulation package that does not exist; and `orexis:ComputeHost`, `orexis:runsOn`
and `orexis:lanHost`, which only `world/sensing` states. See
knowledge/decisions/every-term-in-its-own-house.md.

`orexis:SelfReporting` was one more and has left, to `packages/orexis-capability-reporting/`. It was declared a
capability and granted by nothing; it is granted by a rule now, insisted on by a shape, and named
in its own namespace. See knowledge/decisions/telemetry-is-a-mandatory-capability.md.

Everything here is a **T-Box term**: a class or a property. Those are public and well-known,
and code is written against them exactly as it is written against a function signature. What
must never appear in code is an **instance** — no `"supplier"`, no `orexis:world`, no
`"sensors/{id}/moisture"`. Instances are discovered from the graph, starting from the single
identifier a process is given: its own agent id.

**Graph IRIs used to be listed here as though they were terms, and they are not.**
`orexis:WorldGraph` is the term; `…/graph/world` is a particular graph, no more a term than
`orexis:fern_agent` is. The instances now live in `agent/ontology.ttl`, typed by class,
and `store.graphs_of(PUBLIC)` asks the store which ones they are — so a query means "public
knowledge" without any Python knowing what that consists of, and a sixth public graph is a
vocabulary edit that touches no code.

What survives is the **bootstrap root** and the **write targets**, and they are different
things. The root is `ONTOLOGY_GRAPH`: the T-Box has to be loaded somewhere before it can be
asked anything, exactly as an agent is handed its own id before it can discover anything else.
The write targets are named because a writer must say where it writes — `picks_graph(id)`
does the same, from the one identifier it is given. Neither is a reader enumerating what to
read, which is what rule 1 is actually about.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

OREXIS = "http://example.org/orexis#"
#  THE LAYERS' OWN NAMESPACES (#529): a term one layer reads and writes carries its prefix, so
#  a query says which layer it speaks for; what every layer and package writes in stays `orexis:`.
PROGRESSION = "http://example.org/orexis/progression#"
# **The kernel's namespace, and the kernel is `agent/`.** `orexis:` is the base every package layers
# on: what an agent IS, what a graph is, and — since the mind came home — what a mind CONTAINS.
# A package names its own terms through its own `terms.py`; `market:`, `sensing:` and the
# hardware modules' `mc:`, `onewire:` and the rest have done so since pins-and-wires.
#
# **The label caught up with the name.** `ag` was short for *agora*, the project's first name.
# The rename to Orexis took the IRI — this is `…/orexis#` — and kept the label for a while, on
# the argument that it "reads as well for agent as it ever did for agora". The author asked for
# the label to follow, so it did: the prefix is `orexis:` everywhere a reader sees one, the IRI
# is unchanged, and no stored volume or serialized graph noticed — a prefix label is
# presentation, and only the presentation moved. History quoted in `knowledge/` keeps the old
# spelling where it quotes retired terms as they were written.
# See knowledge/decisions/the-society-is-named-for-its-appetite.md.
#
# This used to say the hardware layer could afford separate namespaces *precisely because no
# runtime code names those terms* — that `term()` and `store.PREFIXES` were therefore untouched,
# and the trap they exist to prevent unreachable. That was true of the arrangement and false as
# a rule: the constraint was never that a namespace must go unqueried, it was that
# `store.PREFIXES` was a kernel constant, so any package wanting one had to edit the kernel to
# be nameable in SPARQL. `agent.loader` now reads every project namespace off the ontology that
# declares it, so the prefix arrives with the package. See
# knowledge/decisions/a-package-owns-its-namespace.md.
PROV = "http://www.w3.org/ns/prov#"


#  WHICH NAMESPACE A KERNEL WORD LIVES IN, by local name (#529): the ledger's words and the
#  points answered on the progression and reactive rows carry those layers' prefixes; a name
#  not listed is `orexis:`, the vocabulary every layer and package writes in. The deliberation
#  layer's words are its own module's (`orexis_agent_deliberation.ontology`), never named here,
#  since a lower layer may not spell a higher one's vocabulary.
LAYER_OF = {
    "Act": PROGRESSION,
    "Intention": PROGRESSION,
    "IntentionGraph": PROGRESSION,
    "landsAt": PROGRESSION,
    "PromisesGraph": PROGRESSION,
    "Step": PROGRESSION,
    "adoptedAt": PROGRESSION,
    "answeredWhen": PROGRESSION,
    "baselineAt": PROGRESSION,
    "baselineValue": PROGRESSION,
    "becauseOf": PROGRESSION,
    "by": PROGRESSION,
    "deadlineAt": PROGRESSION,
    "endMet": PROGRESSION,
    "endVerifiedAt": PROGRESSION,
    "expectedFrom": PROGRESSION,
    "fills": PROGRESSION,
    "forAgent": PROGRESSION,
    "maxPatienceS": PROGRESSION,
    "minPatienceS": PROGRESSION,
    "notAfter": PROGRESSION,
    "notBefore": PROGRESSION,
    "observedValue": PROGRESSION,
    "of": PROGRESSION,
    "outcome": PROGRESSION,
    "partOf": PROGRESSION,
    "patienceS": PROGRESSION,
    "predictedUrgency": PROGRESSION,
    "predictedValue": PROGRESSION,
    "predicts": PROGRESSION,
    "promisedBy": PROGRESSION,
    "refusedBelow": PROGRESSION,
    "pursues": PROGRESSION,
    "quantity": PROGRESSION,
    "resolvedAt": PROGRESSION,
    "step": PROGRESSION,
    "suspectAfter": PROGRESSION,
    "taken": PROGRESSION,
    "takenAt": PROGRESSION,
    "then": PROGRESSION,
    "through": PROGRESSION,
    "until": PROGRESSION,
    "untilNot": PROGRESSION,
    "whenLapsed": PROGRESSION,
}
_DELIBERATIONS = {"Candidate", "Deliberation", "DeliberationGraph", "asOf", "atDepth", "blind", "budgetWorlds", "chose", "considered", "deliberatedOn", "standsAt", "tookSeconds", "verdict", "wouldReach", "wouldTake"}


def term(name: str) -> str:
    """A T-Box term by name — in the namespace the kernel's own layering gives it (#529). This
    is how a package names the capability it implements, and how one package refers to
    another's family without importing its Python."""
    if name in _DELIBERATIONS:
        raise ValueError(f"{name} is the deliberation layer's word — name it from its own module")
    return LAYER_OF.get(name, OREXIS) + name


# --- the kernel's own terms ----------------------------------------------------------------
CAPABILITY = term("Capability")  # the root every capability term is a kind of

# --- the choir's questions, as terms (a-hook-is-a-term) ------------------------------------
HOOK = term("Hook")
PREDICTED = OREXIS + "predicted"    # a watch opened or closed: the intended branch, told to the predictor (#639)
FORESIGHT = OREXIS + "foresight"    # how far ahead a root foresees — the belief is a package's (#644)
REPREDICT = OREXIS + "repredict"    # a premise a prediction reads has moved: predict again (#643)
WITNESS = OREXIS + "witness"        # what the world shows for a predicted fact now — the residual (#518)
DESIRES = OREXIS + "desires"
DESIRE_URGENCY = OREXIS + "desireUrgency"
REPORTS = OREXIS + "reports"
SERIES = OREXIS + "series"
QUIET = OREXIS + "quiet"
OUTDATED = OREXIS + "outdated"      # a graph's period has ended and it is about to be dropped (#645)
BELIEF_REVISED = OREXIS + "beliefRevised"
#  What progression TELLS upward (#452): a lower layer never imports a higher one, so what it
#  has to say — a step taken, an expectation met or unmet — is an event through the choir.
STEP_DONE = OREXIS + "stepDone"
PLAN_FINISHED = OREXIS + "planFinished"
PLAN_FAILED = OREXIS + "planFailed"
SUBSCRIPTIONS = OREXIS + "subscriptions"
HANDLE = OREXIS + "handle"
SEND = OREXIS + "send"

# --- named graphs ---------------------------------------------------------------------------
#
# Public knowledge is five graphs, not one, and the axis is **who put the fact there**. Three
# kinds, and the difference between the last two is the one that took arguing:
#
#   asserted   somebody wrote it in a file — a package's vocabulary, or the sovereign's world
#   derived    a rule computed it. `orexis:hasCapability` is a DESIGN DECISION living in a
#              `rules.ru` that could have said otherwise; the fact has no latitude once the
#              rule exists, but the rule had latitude when it was written
#   entailed   RDFS said it. No author, no alternative — any engine applying the same
#              vocabulary gets the same answer, and nobody could have decided differently
#
# Which is why they are different graphs rather than one "computed" one: *why is the probe a
# Sensor* sends you to the class hierarchy, *why does fern subscribe* sends you to a rule
# somebody wrote, and amending the two has utterly different blast radius.
#
# See knowledge/decisions/who-put-the-fact-there.md.
_GRAPH = "http://example.org/orexis/graph/"
ONTOLOGY_GRAPH = _GRAPH + "ontology"  # the T-Box as the packages assert it
ONTOLOGY_ENTAILED_GRAPH = _GRAPH + "ontology/entailed"  # what that vocabulary implies
WORLD_GRAPH = _GRAPH + "world"  # topology, as the sovereign ratified it
WORLD_DERIVED_GRAPH = _GRAPH + "world/derived"  # what each package's rules.ru computed
WORLD_ENTAILED_GRAPH = _GRAPH + "world/entailed"  # what the vocabulary implies of instances
#  The world's current state as this agent holds it — what an effect rewrites and a plan forks.
#  The IRI still says "sensed", for every volume that holds readings under it; the NAME says
#  what the kernel knows about it, which is not that (the-stake-is-sensings-want).
STATE_GRAPH = _GRAPH + "sensed"

#  THE KINDS A READER ASKS FOR. A graph is read by what the catalogue says it IS, never by
#  its name (a-reader-states-the-kinds-it-reads): a reader lists the kinds it means and the
#  instant it stands at, `Store.graphs_of` answers with the graphs, and the store decides
#  nothing on anyone's behalf. Each kind is a kernel term a package may put its own graph
#  under, which is how a package's record reaches every rule without the kernel learning the
#  package's name.
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
#  What this agent knows about its own instruments — the rhythm each is running and the
#  horizon that follows from it. Private, and separate from `sensed` because a cadence is
#  not a reading: it is what the agent believes about the instrument that produced one.
#  `graph/instruments` is sensing's, declared in its ontology and named in its terms.
#  The desire modality's own graphs — named by the kernel as write/bootstrap roots, exactly
#  the two-category exception the graph-IRI rule states: the build WRITES the first and
#  projects the second, and no reader ever enumerates either (reads go through the modality's
#  union surface).
DESIRE_ASSERTED_GRAPH = _GRAPH + "desire/asserted"
# What the five above ARE, in PROV-O, so the store can say it rather than this file's comments.
# Rename every graph to `g1`..`g5` and a reader could still work out which hold computed facts:
# that is the test this graph exists to pass, and the reason the names above are a convenience
# rather than the record. See orexis/provenance.py.
#  What every MEANS makes true, loaded from the packages at genesis (#238). Public, because
#  a planner reads it on every pass and a model must be able to see the whole tool list;
#  asserted from files, so it is replaced at each boot rather than accumulated.
ACTIONS_GRAPH = _GRAPH + "actions"
#  What the planner considered on its last pass, per desire — the record's one sanctioned
#  materialisation of a possible world, for the reader who cannot re-run the search from
#  outside because the belief base is locked by the process holding it. Private, replaced per
#  pass, never read back by the planner itself. See the deliberation layer's DeliberationGraph.
DELIBERATION_GRAPH = _GRAPH + "deliberation"
#  THE CATALOGUE: the one graph that says what every graph IS — class, owner, arrival, period,
#  and the PROV account of the load — and describes itself, so no reader knows this name:
#  `Store.catalogue` finds the graph that says of itself `a orexis:CatalogueGraph`. Named
#  here for the one writer that CREATES it, genesis, and for nothing else
#  (one-catalogue-describes-every-graph-and-itself).
CATALOGUE_GRAPH = _GRAPH + "catalogue"
# The class a graph must be an instance of to be read by an unqualified pattern. This is a TERM,
# and it is all the code needs: `store.graphs_of(PUBLIC)` asks which graphs are instances of it,
# so nothing here lists them and adding one is a vocabulary edit.
#
# Why it matters beyond tidiness: a single basic graph pattern inside one `GRAPH` clause must
# match entirely within that graph, so `?agent sensing:polls ?s . ?s a sensing:Sensor` silently returns
# nothing the moment those two facts land in different graphs. The default graph is what closes
# that trap, and the trap's failure is an empty result rather than an error — which is why the
# set must never be something a reader can forget to update.
PUBLIC_GRAPH = term("PublicGraph")

# Where every graph lives in the IRI space. Exported because a capability that owns graphs of its
# own builds their names from here — where a graph SITS is the kernel's, what it HOLDS is not.
# See capabilities/review/graphs.py, which owns three.
GRAPH_PREFIX = _GRAPH
#  A GRAPH'S NAME IS FOR EYES. The helpers below spell a readable convention for the graphs
#  the kernel writes — `roots/<agent>`, `beliefs/<agent>` — and nothing in code depends on
#  the spelling: an owner classifies what it writes (`Store.classify`) and every reader asks
#  the class (`Store.graphs_of`, `recorded_graphs`). Rename one here and only the eyes notice.


def picks_graph(agent_id: str) -> str:
    """The graph holding ONE agent's picks — its record of picking (`orexis:PickRecordGraph`),
    birth's first entries and review's revisions. Also its write boundary.

    Write boundary in the strong sense now: a review may write here and nowhere else. It reads
    the world as constraint and `:sensed` as evidence, and changes neither — which is what makes
    the graph classes above load-bearing rather than documentation.

    Called `beliefs/<agent>` until a-graph-class-is-named-for-what-it-holds, from the file it
    is authored from — a name that said where the picks came from rather than what they are,
    and the misnaming `orexis:BeliefGraph`'s own comment records. A volume written under the
    old name is moved once at boot (`genesis._move_pick_record`).
    """
    return _GRAPH + "picks/" + agent_id


def promises_graph(agent_id: str) -> str:
    """ONE agent's promises (#523): the wants a step of a taker-less action raises for the
    level beneath, translated through the bridge — each an `orexis:Desire` the agent holds
    while the step waits, gone when the step's verdict lands. A record the desire modality
    projects like its debts, so `pursuing` lifts a promise as it lifts any want."""
    return _GRAPH + "promises/" + agent_id


def roots_graph(agent_id: str) -> str:
    """One agent's ROOT desires, authored at genesis and holding at every instant — the name
    `orexis:DesireGraph` declares the prefix of, built from the one id a process is handed
    (#644). The desire modality projects it; nothing rebuilds it."""
    return _GRAPH + "roots/" + agent_id


def obligations_graph(agent_id: str) -> str:
    """The record of ONE agent's debts. The graph CLASS and every word written in it are the
    ledger's package's (#635); the name is built here because the desire modality projects
    the record and the planner's wants snapshot reads it, neither of which should import a
    package for a name built from the one id the rules allow building from."""
    return _GRAPH + "obligations/" + agent_id
