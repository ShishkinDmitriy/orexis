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
weather (`ag:timeScale`, `ag:strayDoseMeanDays`, `ag:rainTopic`) — which only `world/simulation`
uses and which want a simulation package that does not exist; and `ag:ComputeHost`, `ag:runsOn`
and `ag:lanHost`, which only `world/sensing` states. See
knowledge/decisions/every-term-in-its-own-house.md.

`ag:SelfReporting` was one more and has left, to `packages/capability/reporting/`. It was declared a
capability and granted by nothing; it is granted by a rule now, insisted on by a shape, and named
in its own namespace. See knowledge/decisions/telemetry-is-a-mandatory-capability.md.

Everything here is a **T-Box term**: a class or a property. Those are public and well-known,
and code is written against them exactly as it is written against a function signature. What
must never appear in code is an **instance** — no `"supplier"`, no `ag:world`, no
`"sensors/{id}/moisture"`. Instances are discovered from the graph, starting from the single
identifier a process is given: its own agent id.

**Graph IRIs used to be listed here as though they were terms, and they are not.**
`ag:WorldGraph` is the term; `…/graph/world` is a particular graph, no more a term than
`ag:fern_agent` is. The instances now live in `agent/ontology.ttl`, typed by class,
and `store.public_graphs()` asks the store which ones they are — so a query means "public
knowledge" without any Python knowing what that consists of, and a sixth public graph is a
vocabulary edit that touches no code.

What survives is the **bootstrap root** and the **write targets**, and they are different
things. The root is `ONTOLOGY_GRAPH`: the T-Box has to be loaded somewhere before it can be
asked anything, exactly as an agent is handed its own id before it can discover anything else.
The write targets are named because a writer must say where it writes — `beliefs_graph(id)`
does the same, from the one identifier it is given. Neither is a reader enumerating what to
read, which is what rule 1 is actually about.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

AG = "http://example.org/orexis#"
# **The kernel's namespace, and the kernel is `agent/`.** `ag:` is the base every package layers
# on: what an agent IS, what a graph is, and — since the mind came home — what a mind CONTAINS.
# A package names its own terms through its own `terms.py`; `market:`, `sensing:` and the
# hardware modules' `mc:`, `onewire:` and the rest have done so since pins-and-wires.
#
# **The label is a leftover that turned out to be right.** `ag` was short for *agora*, the
# project's first name. The rename to Orexis took the IRI — this is `…/orexis#` — and kept the
# label, on the argument that it "reads as well for agent as it ever did for agora". That was a
# little generous at the time, since the vocabulary lived in `packages/core/orexis/` and `agent/`
# was merely the loader. It is exact now: the kernel's directory is `agent/` and the kernel's
# namespace is `ag:`, and they name the same thing. Nobody needs the history to read it.
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
#
#  THE PACKAGE NAMESPACE CONSTANTS WERE HERE — twelve of them, `MC` to `REVIEW`, every one
#  interpolated by onboarding's generators and by nothing in the kernel — and are
#  `onboarding/namespaces.py`'s, where they are consumed (the ratchet's KIND 3, paid). The
#  kernel names no package's namespace: a package's own is in its `terms.py`, and a runtime
#  query reaches any of them by the prefix `agent.loader` reads off the declaring ontology.
#
#  SOSA was here and is `onboarding/namespaces.py`'s: the kernel spells no reading (#378).
PROV = "http://www.w3.org/ns/prov#"


def term(name: str) -> str:
    """A T-Box term by name. This is how a package names the capability it implements, and
    how one package refers to another's family without importing its Python."""
    return AG + name


# --- the kernel's own terms ----------------------------------------------------------------
CAPABILITY = term("Capability")  # the root every capability term is a kind of

# --- the choir's questions, as terms (a-hook-is-a-term) ------------------------------------
HOOK = term("Hook")
DESIRES = term("desires")
DESIRE_URGENCY = term("desireUrgency")
SIZE = term("size")
TAKE = term("take")
REPORTS = term("reports")
SERIES = term("series")
NOTICES = term("notices")
QUIET = term("quiet")
BELIEF_REVISED = term("beliefRevised")
SUBSCRIPTIONS = term("subscriptions")
HANDLE = term("handle")
SEND = term("send")

# --- named graphs ---------------------------------------------------------------------------
#
# Public knowledge is five graphs, not one, and the axis is **who put the fact there**. Three
# kinds, and the difference between the last two is the one that took arguing:
#
#   asserted   somebody wrote it in a file — a package's vocabulary, or the sovereign's world
#   derived    a rule computed it. `ag:hasCapability` is a DESIGN DECISION living in a
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
#  What this agent knows about its own instruments — the rhythm each is running and the
#  horizon that follows from it. Private, and separate from `sensed` because a cadence is
#  not a reading: it is what the agent believes about the instrument that produced one.
#  `graph/instruments` is sensing's, declared in its ontology and named in its terms.
#  The desire modality's own graphs — named by the kernel as write/bootstrap roots, exactly
#  the two-category exception the graph-IRI rule states: the build WRITES the first and
#  projects the second, and no reader ever enumerates either (reads go through the modality's
#  union surface).
DESIRE_DERIVED_GRAPH = _GRAPH + "desire/derived"
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
#  pass, never read back by the planner itself. See ag:DeliberationGraph.
DELIBERATION_GRAPH = _GRAPH + "deliberation"
PROVENANCE_GRAPH = _GRAPH + "provenance"
#  What this agent's own graphs ARE, said by the agent at boot: public, because a
#  modality-scoped query must resolve `?d a ag:DesireGraph` without naming an instance.
CLASSIFICATION_GRAPH = _GRAPH + "classification"
_BELIEFS = _GRAPH + "beliefs/"

# The class a graph must be an instance of to be read by an unqualified pattern. This is a TERM,
# and it is all the code needs: `store.public_graphs()` asks which graphs are instances of it,
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


def beliefs_graph(agent_id: str) -> str:
    """The graph holding ONE agent's private parameters. Also its write boundary.

    Write boundary in the strong sense now: a review may write here and nowhere else. It reads
    the world as constraint and `:sensed` as evidence, and changes neither — which is what makes
    the graph classes above load-bearing rather than documentation.
    """
    return _BELIEFS + agent_id


def obligations_graph(agent_id: str) -> str:
    """The record of ONE agent's debts — kernel-named since `ag:ObligationsGraph` became a
    kernel record class (#312): the desire modality projects it, the planner's imaginarium
    copies it, and an effect rule may read it, none of which should import a package for a
    name built from the one id the rules allow building from."""
    return GRAPH_PREFIX + "obligations/" + agent_id
