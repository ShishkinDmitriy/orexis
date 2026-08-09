"""The kernel vocabulary — prefixes and graph names, and deliberately nothing else.

Everything here is true of *every* capability: how a term is spelled, and which graph a fact
lives in. A term that belongs to one capability — `ag:Subscribing`, `ag:Bidding` — is named by
that capability's own package, so this file never grows when one is added. That is the whole
reason it is this short.

Everything here is a **T-Box term**: a class, a property, or a graph. Those are public and
well-known, and code is written against them exactly as it is written against a function
signature. What must never appear in code is an **instance** — no `"supplier"`, no `ag:world`,
no `"sensors/{id}/moisture"`. Instances are discovered from the graph, starting from the
single identifier a process is given: its own agent id.

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
_GRAPH = "http://example.org/agora/graph/"
ONTOLOGY_GRAPH = _GRAPH + "ontology"  # the T-Box, every package merged
WORLD_GRAPH = _GRAPH + "world"  # topology + composed capabilities: public, versioned
SENSED_GRAPH = _GRAPH + "sensed"  # what sensors read
_BELIEFS = _GRAPH + "beliefs/"
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
