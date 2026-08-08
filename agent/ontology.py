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


def beliefs_graph(agent_id: str) -> str:
    """The graph holding ONE agent's private parameters. Also its write boundary."""
    return _BELIEFS + agent_id
