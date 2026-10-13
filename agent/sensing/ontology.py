"""The words the sensing layer reads and writes, and the names it spells for eyes.

THE VOCABULARY IS SOSA'S AND SSN'S, AND THIS LAYER'S WHERE THEY HAVE NONE. A sensor
`sosa:observes` a property and `sosa:isHostedBy` what it is mounted in, and that pair is the
key an observation is of; how often it reports is its `ssn-system:Frequency`, and a range is
SSN-System's. What this layer declares is in `ontology.ttl` beside this file — the graph a
percept is kept in and a forecast's, the link from a percept to the one before it, the limits
an observer role states, the number a stuck sensor keeps giving, the margin a range's condition states for a domain's
transition to hold a state by, and the pipeline's concepts: a codec, the binding of a sensor to
one, the JSON member that ships, the pointer and the two a series is read by, the number a sensor
gave, and the scaling and calibration the rules make a quantity of it by — and nothing of the 0.1.0
packages' own: what an agent polled, what a sensor monitored or sampled, a device's sense mode and
a drift's horizons were SSN restated or read by nothing, and 0.2.0 speaks none of them. The drift
is the prediction package's. Not one word of any transport.

THE NAMES ARE FOR EYES. A percept's node and graph and a forecast's are spelled here for the writer,
from the one identifier a process is handed, the sensor and the instant of the reading; every
reader asks the catalogue by class and by pattern, and renaming one here would change nothing a
reader sees.
"""

from __future__ import annotations

import re
from datetime import datetime
from functools import cache
from pathlib import Path

from agent.ontology import GRAPH_PREFIX
from agent.store import document, rows

SENSING = "http://example.org/orexis/sensing#"

#  THE TERMS CODE READS: the graph a percept is kept in, and a forecast's, the two limits
#  an observer role states, and the codec that ships. Every other word of this layer is spoken by a
#  query text, under its prefix, and needs no constant here.
OBSERVATION_GRAPH = SENSING + "ObservationGraph"
FORECAST_GRAPH = SENSING + "ForecastGraph"
SILENT_AFTER_TERM = SENSING + "silentAfter"      # an observer role's limits: cadences, and readings
STUCK_AFTER_TERM = SENSING + "stuckAfter"
JSON_CODEC = SENSING + "Json"

#  THIS LAYER'S ONTOLOGY, where the observer shape states what holds of a limit no role states.
_ONTOLOGY = Path(__file__).resolve().parent / "ontology.ttl"

_DEFAULT_Q = """
SELECT ?default WHERE { ?shape sh:targetClass sensing:Observer ; sh:property ?p . ?p sh:path $limit ; sh:defaultValue ?default }"""


@cache
def default_of(limit: str) -> int:
    """What holds of `limit` — `sensing:silentAfter`, `sensing:stuckAfter` — where no observer role states
    it: the observer shape's `sh:defaultValue`, read off this layer's ontology, which is the one place
    the figure lives and the one the stuck rule reads too. Refused where the ontology states none or
    several, since a limit with no figure is a package shipped broken."""
    doc = document(_ONTOLOGY)
    found = {r["default"] for r in rows(doc, _DEFAULT_Q, [_ONTOLOGY.resolve().as_uri()], limit=limit)}
    if len(found) != 1:
        raise RuntimeError(f"sensing's ontology states {len(found)} defaults for {limit}, and one is the limit")
    return int(float(found.pop()))


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def _stamp(at: datetime) -> str:
    """An instant as a name's part: to the second, and to the microsecond where it has one."""
    return at.strftime("%Y%m%dT%H%M%S") + (f"{at.microsecond:06d}" if at.microsecond else "") + "Z"


def percept_of(sensor: str, at: datetime, n: int = 1) -> str:
    """The node of the reading `sensor` made at `at` — the `n`th of that instant, where a sensor read
    twice in one. Named off the sensor, as a want is named off its desire, so what is minted at
    runtime sits beside what it is of and never in a vocabulary's namespace. Distinct is all a
    reader relies on; it matches on SOSA's pattern and on the link a percept states to the one
    before it, never the name."""
    return f"{sensor}.{_stamp(at)}" + (f"_{n}" if n > 1 else "")


def forecast_of(sensor: str, starts: datetime) -> str:
    """The node of the stretch of `sensor`'s forecast that starts at `starts`, named off the sensor
    as a percept is. A sensor reading a series writes no percept, so the two never meet."""
    return f"{sensor}.{_stamp(starts)}"


def percept_graph(agent_id: str, sensor: str, at: datetime, n: int = 1) -> str:
    """Where the reading `sensor` made at `at` is kept — the `n`th of that instant."""
    return f"{GRAPH_PREFIX}observed/{agent_id}/{slug(sensor)}_{_stamp(at)}" + (f"_{n}" if n > 1 else "")


def forecast_graph(agent_id: str, sensor: str, starts) -> str:
    """Where one stretch of a sensor's forecast stands, named by the sensor and the stretch's
    start."""
    return f"{GRAPH_PREFIX}forecast/{agent_id}/{slug(sensor)}_{starts.strftime('%Y%m%dT%H%M%SZ')}"
