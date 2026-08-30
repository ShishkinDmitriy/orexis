"""My sensors, from the world — sensing's own wiring, loaded by sensing.

`agent/world.py` used to load every package's wiring into one `Self`: sensors, actuators,
markets, each by that package's words, in the kernel. A kernel that loads packages should know
no sensor (self-is-bdi-and-wiring-is-the-packages); `Self` is what an agent IS — its id, its
capabilities, whom it acts for — and what it is WIRED TO is each package's to ask, here for
sensing. Same query, same dataclass, one directory over.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_progression.store import bindings

QueryFn = object


@dataclass(frozen=True)
class Sensor:
    """A device an agent may read, plus whatever its binding states about reaching it.

    The binding fields are optional on purpose: a self-clocked device has no command channel,
    and a device on some other transport would carry different fields entirely. Which driver
    speaks to it is decided from these — never from anything the agent believes.
    """

    uri: str
    local_id: str
    subject: str  # URI of what it monitors
    subject_id: str
    observes: str  # URI of the property it reads
    # WHO HOLDS THE CLOCK — sensing:ScheduledProcedure keeps an interval it is given, sensing:PushProcedure keeps its own.
    # The derivation already reads this to decide whether the agent gains sensing:Subscribing or
    # sensing:Listening; carrying it here is what lets the runtime partition what the derivation
    # separated. Without it an agent holding one of each gave both to both modules, and the
    # scheduled sensor's cadence was silently never re-aimed.
    sense_mode: str | None = None
    bus: str | None = None  # URI of the bus it declares itself on, if any
    reading_topic: str | None = None
    # WHICH value in that payload is mine — a JSON Pointer, and None means the default. Two
    # sensors on one board share a topic and differ only here: the board is one MQTT client
    # with one credential, so it sends one message and each sensor takes its own field.
    reading_pointer: str | None = None
    command_topic: str | None = None
    # The two ends of the pipeline the pointer sits in the middle of. Both are DERIVED — genesis
    # writes them from what the world stated, or from its silence — so neither is ever None in a
    # world that has been through genesis, and a shape refuses one that is.
    decoded_by: str | None = None     # which codec — codec:decodedBy
    scaled_by: str | None = None  # which calibration — scaling:scaledBy
    # What unit that quantity is in, as a QUDT IRI. Not the same kind of fact as the two above:
    # they choose an implementation, this states what the number MEANS. A board reporting soil
    # moisture 0.183 and air humidity 0.46 sends two numbers that look identical, and nothing but
    # this says they are the same dimension while 21.4 degrees is not.
    quantity_unit: str | None = None
    # The PATCH this probe actually sits in, when someone judged the pot's soil not one thing
    # (#98): a sosa:Sample whose isSampleOf is the subject above. Optional, and its absence is
    # the ordinary rig — the subject is the feature, and everything reads as it always did.
    sample: str | None = None
    # THIS channel is watched for crossings (#151): its band is commanded beside the cadence,
    # and silence between heartbeats means "nothing crossed" — information. Per sensor, because
    # which values a board can watch is a per-channel hardware fact.
    alarm: bool = False




def _sensors_q(agent_uri: str) -> str:
    """My sensors and their bindings. The binding parts are OPTIONAL: what a device states
    about how to reach it varies by transport, and a driver is picked from what is there."""
    return f"""
SELECT ?sensor ?localId ?subject ?subjectId ?observes ?senseMode ?bus ?readingTopic
       ?readingPointer ?commandTopic ?decodedBy ?scaledBy ?quantityUnit ?sample ?alarm
WHERE {{
  <{agent_uri}> sensing:polls ?sensor .
  ?sensor ag:localId ?localId ; sensing:monitors ?subject ; sosa:observes ?observes .
  # The mode is the DEVICE's (#96), reached through the stream the sensor shares with it —
  # a peripheral has no clock of its own, and its board's answer is the only answer there is.
  OPTIONAL {{ ?sensor mqtt:readingTopic ?stream .
              ?clockKeeper mqtt:readingTopic ?stream ; mqtt:onBus ?anyBus ;
                           sensing:senseMode ?senseMode }}
  # Whether THIS CHANNEL is watched for crossings (#151) — per sensor, not per board,
  # because which values a board can watch is a hardware fact per channel: a ULP reaches the
  # analog probe and never the DHT. The board wakes for any watched channel that crosses.
  OPTIONAL {{ ?sensor ssn:implements sensing:AlarmProcedure . BIND(true AS ?alarm) }}
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
  OPTIONAL {{ ?sensor sensing:samples ?sample }}
  OPTIONAL {{ ?sensor mqtt:onBus ?bus }}
  OPTIONAL {{ ?sensor mqtt:readingTopic ?readingTopic }}
  OPTIONAL {{ ?sensor mqtt:readingPointer ?readingPointer }}
  OPTIONAL {{ ?sensor mqtt:commandTopic ?commandTopic }}
  # Through the stream it publishes on, because an encoding is the stream's — see
  # knowledge/decisions/a-stream-is-a-thing.md. Both halves are derived; this query runs over
  # the whole store at boot rather than over `$given`, so it may read a conclusion.
  OPTIONAL {{ ?sensor mqtt:publishesOn ?readingChannel . ?readingChannel codec:decodedBy ?decodedBy }}
  OPTIONAL {{ ?sensor scaling:scaledBy ?scaledBy }}
  OPTIONAL {{ ?sensor scaling:quantityUnit ?quantityUnit }}
 }}"""




def sensors_of(query, agent_uri: str) -> tuple[Sensor, ...]:
    """Every sensor this agent polls, with everything the pipeline needs to read it."""
    return tuple(
        Sensor(
            uri=r["sensor"], local_id=r["localId"], subject=r["subject"],
            subject_id=r.get("subjectId") or "", observes=r["observes"],
            sense_mode=r.get("senseMode"),
            sample=r.get("sample"),
            alarm=bool(r.get("alarm")),
            bus=r.get("bus"), reading_topic=r.get("readingTopic"),
            reading_pointer=r.get("readingPointer"),
            command_topic=r.get("commandTopic"),
            decoded_by=r.get("decodedBy"), scaled_by=r.get("scaledBy"),
            quantity_unit=r.get("quantityUnit"),
        )
        for r in bindings(query(_sensors_q(agent_uri)))
    )


def event_topic_of(query, agent_uri: str) -> str | None:
    """Where this agent announces what it makes of a reading — the band goes there."""
    rows = bindings(query(f"SELECT ?t WHERE {{ <{agent_uri}> mqtt:eventTopic ?t }} LIMIT 1"))
    return rows[0]["t"] if rows else None
