"""The kernel vocabulary — prefixes and graph names, and deliberately nothing else.

Everything here is true of *every* capability: how a term is spelled, and which graph a fact
lives in. A term that belongs to one capability — `perception:Subscribing`, `market:Bidding` — is named by
that capability's own package, so this file never grows when one is added. That is the whole
reason it is this short.

Everything here is a **T-Box term**: a class or a property. Those are public and well-known,
and code is written against them exactly as it is written against a function signature. What
must never appear in code is an **instance** — no `"supplier"`, no `ag:world`, no
`"sensors/{id}/moisture"`. Instances are discovered from the graph, starting from the single
identifier a process is given: its own agent id.

**Graph IRIs used to be listed here as though they were terms, and they are not.**
`ag:WorldGraph` is the term; `…/graph/world` is a particular graph, no more a term than
`ag:fern_agent` is. The instances now live in `vocabulary/agora/ontology.ttl`, typed by class,
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

AG = "http://example.org/agora#"
# **A package owns its namespace, and this is only the kernel's.** `ag:` is what every agent
# has; `capabilities/market` keeps `market:`, and the hardware modules have kept `mc:`,
# `onewire:` and the rest since pins-and-wires. A package names its own terms through its own
# `terms.py`, not through `term()` here.
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
# The hardware constants stay here because the trees under `vocabulary/` ship no Python at all,
# so there is no `terms.py` of their own to hold them — the one asymmetry left, and it follows
# from a vocabulary package being pure knowledge rather than from anything about namespaces.
MC = "http://example.org/agora/microcontroller#"
ONEWIRE = "http://example.org/agora/onewire#"
I2C = "http://example.org/agora/i2c#"
DHT11 = "http://example.org/agora/dht11#"
RGBLED = "http://example.org/agora/rgb-led#"
PROBE = "http://example.org/agora/moisture-probe#"
ESP32 = "http://example.org/agora/esp32#"

# And the packages the SOVEREIGN's tooling reads across. `onboarding/` builds full IRIs by
# interpolation rather than by prefix, because it queries the ratified files directly and not
# through a `Store` that would carry `store.PREFIXES`. That is a third way to name a term, after
# a `pkg:Term` in SPARQL text and a package's own `terms.py`, and it is the one a rename cannot
# see: an `AG`-interpolated `bidsIn` went on compiling and matching nothing from the moment
# market owned `market:bidsIn`, and a test that iterated its empty result asserted nothing while
# passing — for four merged PRs, until this sweep looked.
#
# These are NOT a prefix registry — `agent.loader` reads those off each ontology. They are the
# handful of namespaces one tree names in the other's terms, and a package listed here still
# owns its own vocabulary.
MARKET = "http://example.org/agora/market#"
MQTT = "http://example.org/agora/mqtt#"
PERCEPTION = "http://example.org/agora/perception#"
ACTUATION = "http://example.org/agora/actuation#"
REVIEW = "http://example.org/agora/review#"
WATER = "http://example.org/agora/water#"

SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"


def term(name: str) -> str:
    """A T-Box term by name. This is how a package names the capability it implements, and
    how one package refers to another's family without importing its Python."""
    return AG + name


# --- the kernel's own terms ----------------------------------------------------------------
CAPABILITY = term("Capability")  # the root every capability term is a kind of

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
_GRAPH = "http://example.org/agora/graph/"
ONTOLOGY_GRAPH = _GRAPH + "ontology"  # the T-Box as the packages assert it
ONTOLOGY_ENTAILED_GRAPH = _GRAPH + "ontology/entailed"  # what that vocabulary implies
WORLD_GRAPH = _GRAPH + "world"  # topology, as the sovereign ratified it
WORLD_DERIVED_GRAPH = _GRAPH + "world/derived"  # what each package's rules.ru computed
WORLD_ENTAILED_GRAPH = _GRAPH + "world/entailed"  # what the vocabulary implies of instances
SENSED_GRAPH = _GRAPH + "sensed"  # what sensors read
# What the five above ARE, in PROV-O, so the store can say it rather than this file's comments.
# Rename every graph to `g1`..`g5` and a reader could still work out which hold computed facts:
# that is the test this graph exists to pass, and the reason the names above are a convenience
# rather than the record. See agora/provenance.py.
PROVENANCE_GRAPH = _GRAPH + "provenance"
_BELIEFS = _GRAPH + "beliefs/"

# The class a graph must be an instance of to be read by an unqualified pattern. This is a TERM,
# and it is all the code needs: `store.public_graphs()` asks which graphs are instances of it,
# so nothing here lists them and adding one is a vocabulary edit.
#
# Why it matters beyond tidiness: a single basic graph pattern inside one `GRAPH` clause must
# match entirely within that graph, so `?agent perception:polls ?s . ?s a perception:Sensor` silently returns
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
