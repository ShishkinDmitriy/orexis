"""actuation:Actuation — redeem a voucher against real hardware.

There is no "armed" flag and no dry-run mode. This capability actuates; that is what it is
for. An installation that must NOT move water does not disarm the module — it declares
devices that do not move water, and derivation gives its agent a different capability. What a
thing does belongs in the model, not in an environment variable that can disagree with it.


Held by the resource owner, never by the winner: a voucher is a *claim on the owner*, and the
owner is the one with the valves. This module decides nothing. It maps a voucher's subject to
the device that serves it (`actuation:actuates`), converts litres into open-seconds with that
device's own calibration (`actuation:mlPerSecond`), caps the dose at the device's own limit
(`actuation:maxDoseMl`) regardless of what cleared, co-signs, and publishes to the device's own
command topic. Every one of those is read from the world.

Single-use is enforced here by `jti`; the device enforces its own fail-safe watchdog. Two
independent limits, because the interesting failures are the ones where one of them is wrong.

Vocabulary: capabilities/actuation/ontology.ttl. Rules: capabilities/actuation/shapes.ttl.
Derivation: capabilities/actuation/rules.ru.
See knowledge/domain/executor.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agent import signing
from agent.module import Module

from .terms import ACTUATION


@dataclass(frozen=True)
class Command:
    jti: str
    plant: str
    scope: str
    ml: float
    seconds: float
    auction_id: str


class ActuationModule(Module):
    CAPABILITY = ACTUATION
    name = "actuation"

    def __init__(self, agent):
        super().__init__(agent)
        self.settled: set[str] = set()
        # v1 in-process: the settlement side holds both keys and co-signs. The device opens
        # only for a token signed by BOTH the host and clearing.
        self.host_key = self.clearing_key = None
        try:
            self.host_key = signing.load_private("host")
            self.clearing_key = signing.load_private("clearing")
        except Exception:
            self.log.warning("no signing keys (run agora-keygen) — devices will reject commands")

    def command_for(self, voucher) -> tuple[Command, object]:
        device = self.me.actuator_for(voucher.sub)
        if device is None:
            raise ValueError(f"I own no actuator that serves {voucher.sub!r}")
        ml = min(voucher.amount_l * 1000.0, device.max_dose_ml)  # the device's own cap
        return Command(
            jti=voucher.jti, plant=voucher.sub, scope=voucher.scope,
            ml=round(ml, 1), seconds=round(ml / device.ml_per_second, 2),
            auction_id=voucher.auction_id,
        ), device

    def redeem(self, voucher) -> Command:
        if voucher.jti in self.settled:
            raise ValueError(f"replay: jti {voucher.jti} already redeemed")
        cmd, device = self.command_for(voucher)
        payload = asdict(cmd)
        if self.host_key is not None and self.clearing_key is not None:
            data = signing.canonical(payload)
            payload["match_sig"] = signing.sign(self.host_key, data)  # the seller authorises
            payload["val_sig"] = signing.sign(self.clearing_key, data)  # clearing validated
        self.publish(device.command_topic, payload)
        self.settled.add(voucher.jti)  # single-use either way: a dry run still spends the jti
        self.log.info("%s: open %.2fs (~%.0f ml) -> %s", cmd.plant, cmd.seconds, cmd.ml,
                      device.command_topic)
        return cmd

    def redeem_all(self, vouchers) -> list[Command]:
        out = []
        for voucher in vouchers:
            try:
                out.append(self.redeem(voucher))
            except ValueError as exc:
                self.log.error("cannot redeem for %s: %s", voucher.sub, exc)
        return out
