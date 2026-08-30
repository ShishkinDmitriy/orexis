"""My actuators, from the world — actuation's own wiring, loaded by actuation.

See sensing's `wiring.py` for why this left `agent/world.py`: what an agent is wired to is
each package's to ask, in its own words, and the kernel names none of them.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_progression_patience.store import bindings


@dataclass(frozen=True)
class Actuator:
    """A device an agent may drive, with its own calibration and hard cap."""

    uri: str
    local_id: str
    subject: str
    subject_id: str
    command_topic: str
    ml_per_second: float
    max_dose_ml: float
    # Where the device says what it actually dispensed. OPTIONAL because a world may wire a
    # valve it cannot hear back from, and that is a real deployment rather than an error — but
    # an agent with no status channel cannot tell a delivered dose from a refused one, which is
    # what `ActuationModule` reports when it is missing.
    status_topic: str | None = None




def _actuators_q(agent_uri: str) -> str:
    return f"""
SELECT ?actuator ?localId ?subject ?subjectId ?commandTopic ?mlPerSecond ?maxDoseMl ?statusTopic
WHERE {{
  <{agent_uri}> actuation:hasActuator ?actuator .
  ?actuator ag:localId ?localId ; actuation:actuates ?subject ; mqtt:commandTopic ?commandTopic ;
            actuation:mlPerSecond ?mlPerSecond ; actuation:maxDoseMl ?maxDoseMl .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
  OPTIONAL {{ ?sensor sensing:samples ?sample }}
  OPTIONAL {{ ?actuator mqtt:statusTopic ?statusTopic }}
 }}"""




def actuators_of(query, agent_uri: str) -> tuple[Actuator, ...]:
    return tuple(
        Actuator(
            uri=r["actuator"], local_id=r["localId"], subject=r["subject"],
            subject_id=r.get("subjectId") or "", command_topic=r["commandTopic"],
            ml_per_second=float(r["mlPerSecond"]), max_dose_ml=float(r["maxDoseMl"]),
            status_topic=r.get("statusTopic"),
        )
        for r in bindings(query(_actuators_q(agent_uri)))
    )


def actuator_for(actuators, subject_id: str) -> Actuator | None:
    return next((a for a in actuators if a.subject_id == subject_id), None)
