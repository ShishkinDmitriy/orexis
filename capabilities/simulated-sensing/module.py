"""ag:SimulatedSensing — perceive a subject by holding a model of it.

There is no device. The agent computes its subject's state, records it exactly as a real
reading is recorded, and announces it exactly as a real one is announced — so nothing
downstream can tell, which is the property that makes a simulated world worth having.

**This is not the production capability with a switch.** It is its own package with its own
vocabulary: an agent is wired with `ag:models` or with `ag:polls`, never with something that
could be either. A world that simulates is a different world and reads like one.

What it shares with the real thing is deliberate and narrow:

- the **family** — `ag:SimulatedSensing` is an `ag:PerceptionCapability`, so a bidder asking
  for "whoever perceives" finds it without knowing which kind answered;
- the **recording** — `agora.observation`, in the kernel, because what an agent does with a
  number it has come to know does not depend on where the number came from.

The loop closes over MQTT like everything else. The subject dries on its own clock and gains
what a valve was told to give it; that command is public and addressed to a device this agent
does not own, which is exactly how a real board would learn the same thing.

Vocabulary: capabilities/simulated-sensing/ontology.ttl.
Rules: capabilities/simulated-sensing/shapes.ttl.
Derivation: capabilities/simulated-sensing/rules.ru.
"""

from __future__ import annotations

from agora.module import Module, Timer
from agora.observation import Observations
from agora.store import bindings

from .beliefs import SIMULATED_SENSING_BLOCK
from .terms import SIMULATED_SENSING

# Everything the model needs, and where a dose to this subject is announced. All public: the
# same facts a real board's world states, minus the board.
_MODEL_Q = """
SELECT ?subject ?subjectId ?observes ?initial ?dryRate ?tickSeconds ?litres ?commandTopic
WHERE {{ GRAPH ?g {{
  <{agent}> ag:models <{device}> .
  <{device}> ag:monitors ?subject ; sosa:observes ?observes .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
  OPTIONAL {{ <{device}> ag:modelledInitialValue ?initial }}
  OPTIONAL {{ <{device}> ag:modelledDryRate ?dryRate }}
  OPTIONAL {{ <{device}> ag:modelledTickSeconds ?tickSeconds }}
  OPTIONAL {{ ?subject ag:litresPerFraction ?litres }}
  OPTIONAL {{ ?valve ag:actuates ?subject ; ag:commandTopic ?commandTopic }}
}} }} LIMIT 1"""

_MODELS_Q = """
SELECT ?device WHERE {{ GRAPH ?g {{ <{agent}> ag:models ?device }} }}"""


class _Model:
    """One subject's state, and the physics the world states about it.

    A simulated subject that behaved differently from what the world says would be a second
    model of the same thing, so every number here is read rather than invented.
    """

    def __init__(self, row: dict):
        self.uri = row["device"]
        self.subject = row["subject"]
        self.subject_id = row.get("subjectId") or ""
        self.observes = row["observes"]
        self.local_id = row["device"].rsplit("#", 1)[-1]
        self.value = float(row.get("initial") or 0.5)
        self.dry_rate = float(row.get("dryRate") or 0.0)
        self.tick_s = float(row.get("tickSeconds") or 2)
        self.litres_per_fraction = float(row.get("litres") or 0.0)
        self.command_topic = row.get("commandTopic")

    def dry(self) -> None:
        self.value = max(0.0, min(1.0, self.value - self.dry_rate))

    def receive(self, ml: float) -> None:
        """Water arrived. How much it moves the subject is the world's fact, not the model's."""
        if ml > 0 and self.litres_per_fraction > 0:
            self.value = max(0.0, min(1.0, self.value + (ml / 1000.0) / self.litres_per_fraction))


class SimulatedSensingModule(Module):
    CAPABILITY = SIMULATED_SENSING
    name = "simulated-sensing"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(SIMULATED_SENSING_BLOCK)
        self.observations = Observations(agent)
        self.models = [
            _Model(dict(row, **bindings(agent.store.query(
                _MODEL_Q.format(agent=self.me.uri, device=row["device"])))[0]))
            for row in bindings(agent.store.query(_MODELS_Q.format(agent=self.me.uri)))
        ]
        self._timer: Timer | None = None

    # --- the perception family's interface, which a bidder relies on ---

    def sense_now(self) -> None:
        """Look now. For a model this is not best-effort — there is nothing to wake."""
        for model in self.models:
            self._read(model)

    def fresh_reading(self, subject_uri: str):
        """The latest reading, or None if it is older than I am willing to trust."""
        reading = self.agent.beliefs.current_reading(subject_uri)
        return reading if reading and reading.is_fresh(self.beliefs.max_age_s) else None

    # --- the world moving on its own ---

    def subscriptions(self) -> list[str]:
        # Nothing publishes readings to me. I listen for what is DONE to my subject, which is
        # the only thing besides time that can change it.
        return [t for m in self.models if (t := m.command_topic)]

    def handle(self, topic: str, payload: bytes) -> bool:
        for model in self.models:
            if model.command_topic != topic:
                continue
            doc = self.parse(payload) or {}
            model.receive(float(doc.get("ml") or 0.0))
            self.log.info("%s: received %.0f ml -> %.3f",
                          model.subject_id, float(doc.get("ml") or 0.0), model.value)
            return True
        return False

    def start(self) -> None:
        self._tick()

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
        self.observations.close()

    def _tick(self) -> None:
        for model in self.models:
            model.dry()
            self._read(model)
        if self._timer is None:
            every = min(m.tick_s for m in self.models) if self.models else 2.0
            self._timer = Timer(every, self._tick)
            self._timer.start()

    def _read(self, model: _Model) -> None:
        self.observations.record(self.log, model, model.value)
