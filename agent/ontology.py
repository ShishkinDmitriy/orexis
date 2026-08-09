"""The kernel vocabulary — prefixes and graph names, and deliberately nothing else.

Everything here is true of *every* capability: how a term is spelled, and which graph a fact
lives in. A term that belongs to one capability — `ag:Subscribing`, `ag:Bidding` — is named by
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
# The hardware layer keeps namespaces of its own, one per module, and NOT `ag:`. It is the
# layer that grows a term per pin, and one shared namespace would make every one of them carry
# its board's name to stay unambiguous — `ag:Esp32Gpio34` against `esp32:Gpio34Pin`. It can
# afford this precisely because no runtime code names these terms: an agent never queries a
# pin, so `term()` and `store.PREFIXES` are untouched and the trap they exist to prevent — a
# prefix declared in one file and used in another — is not reachable from here.
MC = "http://example.org/agora/microcontroller#"
ONEWIRE = "http://example.org/agora/onewire#"
I2C = "http://example.org/agora/i2c#"
DHT11 = "http://example.org/agora/dht11#"
RGBLED = "http://example.org/agora/rgb-led#"
PROBE = "http://example.org/agora/moisture-probe#"
ESP32 = "http://example.org/agora/esp32#"

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
# match entirely within that graph, so `?agent ag:polls ?s . ?s a ag:Sensor` silently returns
# nothing the moment those two facts land in different graphs. The default graph is what closes
# that trap, and the trap's failure is an empty result rather than an error — which is why the
# set must never be something a reader can forget to update.
PUBLIC_GRAPH = term("PublicGraph")
_REVISIONS = _GRAPH + "revisions/"
_EVIDENCE = _GRAPH + "evidence/"
_SUMMARIES = _GRAPH + "summaries/"


def beliefs_graph(agent_id: str) -> str:
    """The graph holding ONE agent's private parameters. Also its write boundary.

    Write boundary in the strong sense now: a review may write here and nowhere else. It reads
    the world as constraint and `:sensed` as evidence, and changes neither — which is what makes
    the four graph classes above load-bearing rather than documentation.
    """
    return _BELIEFS + agent_id


def revisions_graph(agent_id: str) -> str:
    """What this agent has decided about itself, and when each is worth revisiting.

    Apart from the beliefs graph on purpose. A belief has exactly one value — every capability's
    shapes say so with `sh:maxCount 1` — so a decision cannot live beside the value it replaced
    without making the agent fail its own validation.
    """
    return _REVISIONS + agent_id


def evidence_graph(agent_id: str) -> str:
    """The reviewer's scratch, rebuilt at every arising. Nothing else ever reads it."""
    return _EVIDENCE + agent_id


def summaries_graph(agent_id: str) -> str:
    """What this agent's readings came to — running totals, not readings.

    Apart from `:sensed` deliberately, and the separation is what makes the write boundary
    checkable: `:sensed` is the measurement record, written by whatever observed and NEVER by a
    review, while a summary is the agent's own derived account of its past and is rolled over
    every time it arises. Keeping them in one graph would have made "a review does not touch the
    sensed record" untestable, and an invariant nothing can check is a comment.
    """
    return _SUMMARIES + agent_id
