"""ag:SimulatedActuation — redeem a voucher against a device that is not there.

Everything the real capability does except convince hardware: the dose is computed from the
device's own calibration, capped at its own limit regardless of what cleared, spent once by
`jti`, and announced on the device's command topic so a simulated subject can respond to it.

What it does **not** do is sign. A signature exists to convince a device, and there is no
device — claiming otherwise would be the one lie this package exists to avoid. A real board
that somehow heard this command would refuse it, which is correct.

This is a separate capability, not the production one disarmed. There is no dry-run mode over
there, and no flag anywhere: an agent holds `ag:hasActuator` or `ag:hasSimulatedActuator`, and
which it holds is a fact about the world.

Vocabulary: capabilities/simulated-actuation/ontology.ttl.
Derivation: capabilities/simulated-actuation/rules.ru.
"""

from __future__ import annotations

from agora.module import Module
from agora.store import bindings

from .terms import SIMULATED_ACTUATION

# The devices this agent pretends to hold, and what the world says they would do. Same
# calibration terms as a real valve: a simulation that dosed differently would be modelling a
# different piece of hardware.
_DEVICES_Q = """
SELECT ?device ?localId ?subject ?subjectId ?commandTopic ?mlPerSecond ?maxDoseMl
WHERE {{ GRAPH ?g {{
  <{agent}> ag:hasSimulatedActuator ?device .
  ?device ag:localId ?localId ; ag:actuates ?subject ; ag:commandTopic ?commandTopic ;
          ag:mlPerSecond ?mlPerSecond ; ag:maxDoseMl ?maxDoseMl .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
}} }}"""


class SimulatedActuationModule(Module):
    CAPABILITY = SIMULATED_ACTUATION
    name = "simulated-actuation"

    def __init__(self, agent):
        super().__init__(agent)
        self.settled: set[str] = set()
        self.devices = {
            r.get("subjectId") or r["subject"]: r
            for r in bindings(agent.store.query(_DEVICES_Q.format(agent=self.me.uri)))
        }
        self.log.info("simulated: %d device(s), nothing physical will move",
                      len(self.devices))

    def _device_for(self, subject_uri: str):
        for key, row in self.devices.items():
            if row["subject"] == subject_uri or key == subject_uri:
                return row
        return None

    def redeem(self, voucher):
        """Bounded, single-use, announced — and unsigned, because nothing is being convinced."""
        if voucher.jti in self.settled:
            raise ValueError(f"replay: jti {voucher.jti} already redeemed")
        device = self._device_for(voucher.sub)
        if device is None:
            raise ValueError(f"I hold no simulated actuator that serves {voucher.sub!r}")

        ml = min(voucher.amount_l * 1000.0, float(device["maxDoseMl"]))
        seconds = ml / float(device["mlPerSecond"])
        payload = {
            "jti": voucher.jti, "plant": device.get("subjectId") or voucher.sub,
            "scope": voucher.scope, "ml": round(ml, 1), "seconds": round(seconds, 2),
            "round_id": voucher.round_id,
        }
        self.publish(device["commandTopic"], payload)
        self.settled.add(voucher.jti)
        self.log.info("%s: %.0f ml -> %s (simulated)",
                      payload["plant"], ml, device["commandTopic"])
        return payload

    def redeem_all(self, vouchers) -> list[dict]:
        out = []
        for voucher in vouchers:
            try:
                out.append(self.redeem(voucher))
            except ValueError as exc:
                self.log.error("cannot redeem for %s: %s", voucher.sub, exc)
        return out
