"""The vocabulary, as the code sees it — the ONE place any name is written down.

Everything here is a **T-Box term**: a class, a property, or a capability. Those are public
and well-known, and code is written against them exactly as it is written against a function
signature. What must never appear in code is an **instance** — no `"supplier"`, no
`ag:world`, no `"sensors/{id}/moisture"`. Instances are discovered from the graph, starting
from the single identifier a process is given: its own agent id.

The T-Box itself is modular (`ontology/*.ttl`), one module per capability. This file mirrors
that split so it is obvious which vocabulary a code module is entitled to read.
"""

from __future__ import annotations

AG = "http://example.org/agora#"
SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"


def term(name: str) -> str:
    return AG + name


# --- capabilities: the name of a module, as composed onto an agent -------------------------
POLLING = term("Polling")
LISTENING = term("Listening")
BIDDING = term("Bidding")
HOSTING = term("Hosting")
ACTUATION = term("Actuation")

# --- the modules, in load order. Each name is up to four files, and that is the whole
# anatomy of a capability:
#     ontology/<name>.ttl  the vocabulary        shapes/<name>.ttl  the rules
#     rules/<name>.ru      how it is derived     modules/<name>.py  the code
MODULE_FILES = ("core", "transport", "polling", "market", "actuation", "water")

# --- named graphs ---------------------------------------------------------------------------
_GRAPH = "http://example.org/agora/graph/"
ONTOLOGY_GRAPH = _GRAPH + "ontology"  # the T-Box, all modules
WORLD_GRAPH = _GRAPH + "world"  # topology + composed capabilities: public, versioned
SENSED_GRAPH = _GRAPH + "sensed"  # what sensors read
_BELIEFS = _GRAPH + "beliefs/"


def beliefs_graph(agent_id: str) -> str:
    """The graph holding ONE agent's private parameters. Also its write boundary."""
    return _BELIEFS + agent_id


BANDS = ("LOW", "OK", "HIGH")


def band_for(value: float, low: float, high: float) -> str:
    """A reading judged against ONE agent's own limits. Never stored — always recomputed."""
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "OK"
