"""Writing what a sensor read into :sensed — the agent's own assertion.

Trusted-agent mode: no witness, so the reading is authored by the agent that polled it
(`prov:wasGeneratedBy`). Everything about the observation is passed in from the world — the
subject, the sensor, and which property it observes — so nothing here knows a name.

One observation per subject **and observed property**, replaced each reading; the *series*
lives in Influx. The property is part of the identity because a subject can be watched by more
than one sensor: a pot with a moisture probe and a thermometer is one feature of interest with
two properties, and keying on the subject alone made the two overwrite each other. Worse than
the loss was the substitution — a lookup by subject returned whichever had written last, so a
caller asking for moisture could be handed a temperature, a plausible number in the wrong unit
that a market will act on without hesitating.

It also says HOW it was made. `sosa:usedProcedure` carries the sensor's sense mode, which is a
`sosa:Procedure`, and the difference it records is not recoverable from the number: *"0.183 at
13:22, on the interval the agent asked for"* and *"0.183 at 13:22, because the board chose that
moment"* are different claims. Under `ScheduledProcedure` a reading that does not arrive means the
board is late; under `PushProcedure` it may mean nothing happened worth reporting. Until now that
was knowable only by joining back to the sensor, which is the shape of fact this project keeps
finding out about the hard way.

It is the CLOCK part of how, and not the whole method — the codec, the pointer and the scaling
are also how that number came to be. SOSA asks for "a relation to link to *a* re-usable
Procedure", so a partial answer is a legitimate one; if the whole pipeline is ever modelled as a
Procedure this predicate gets re-pointed rather than a second one added.

The observation's own IRI is minted from the subject id and the property's local name, and
nothing ever looks it up by that name: readers match on `sosa:hasFeatureOfInterest` and
`sosa:observedProperty`. The IRI only has to be stable and distinct, which is why sanitising
it down to word characters is safe.

See knowledge/decisions/trusted-agent-mode.md and decisions/one-agent-many-sensors.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from orexis_progression_patience.ontology import STATE_GRAPH
from orexis_progression_patience.store import Store


def _slug(uri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", uri.rstrip("#/"))[-1])


def observation_uri(feature_id: str, observed_property: str) -> str:
    """The node one (feature, property) pair owns. Two properties, two nodes — and since #98
    the feature is the SAMPLE where the sensor states one, so two probes in two patches of one
    pot own two nodes instead of overwriting each other."""
    return f"ag:obs_{_slug(feature_id)}_{_slug(observed_property)}"


class SensedWriter:
    def __init__(self, store: Store):
        self.store = store

    def write(
        self,
        subject_uri: str,
        subject_id: str,
        value: float,
        sensor_uri: str,
        observed_property: str,
        author_uri: str,
        used_procedure: str,
        world_version: int | None = None,
        ts: str | None = None,
        sample_uri: str | None = None,
        phenomenon_ts: str | None = None,
    ) -> None:
        # The caller's instant, and it is always given now: `Observations.record` resolves one
        # per MESSAGE and hands the same string to every value that message carried, so two
        # readings from one 40-bit frame share a `sosa:resultTime` instead of differing by
        # however long the loop took. The fallback is for a caller with no message in hand.
        ts = ts or datetime.now(timezone.utc).isoformat()
        # The feature this observation is OF (#98): the patch the probe sits in, where one is
        # stated — sosa:Sample is the word for a representative piece of something not fully
        # accessible, and a pot's soil is exactly that — or the subject itself, which is the
        # ordinary rig and the unchanged default. The reader walks sosa:isSampleOf back up.
        foi = sample_uri or subject_uri
        obs = observation_uri(sample_uri or subject_id, observed_property)
        # The instant the result APPLIES TO, where the device said so itself (#101): a board
        # that timestamps its readings, or batches and sends later. `resultTime` keeps meaning
        # arrival — the honest instant the agent has — and the two coincide whenever the device
        # does not speak for itself, which is every device here today.
        pt = (f'    sosa:phenomenonTime "{phenomenon_ts}"^^xsd:dateTime ;\n'
              if phenomenon_ts else "")
        wv = f"    ag:underWorldVersion {int(world_version)} ;\n" if world_version is not None else ""

        self.store.update(f"""
WITH <{STATE_GRAPH}>
DELETE {{ {obs} ?p ?o }} WHERE {{ {obs} ?p ?o }} ;
INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{
  {obs} a sosa:Observation ;
    sosa:hasFeatureOfInterest <{foi}> ;
    sosa:observedProperty <{observed_property}> ;
    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
    sosa:resultTime "{ts}"^^xsd:dateTime ;
{pt}
    sosa:madeBySensor <{sensor_uri}> ;
    sosa:usedProcedure <{used_procedure}> ;
{wv}    prov:wasGeneratedBy <{author_uri}> .
}} }}
""")
