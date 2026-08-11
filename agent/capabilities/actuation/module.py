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

import json
import time
from dataclasses import asdict, dataclass

from agent import signing
from agent.module import Module, Timer

from .beliefs import ACTUATION_BLOCK
from .terms import ACTUATION

# How often the module looks for doses nobody confirmed. Not the deadline — that is per dose
# and derived — only how coarsely it is noticed. A sweep is cheap and lateness is not urgent.
SWEEP_S = 5.0


@dataclass(frozen=True)
class Command:
    jti: str
    plant: str
    scope: str
    ml: float
    seconds: float
    round_id: str


class ActuationModule(Module):
    CAPABILITY = ACTUATION
    name = "actuation"

    def __init__(self, agent):
        super().__init__(agent)
        self.settled: set[str] = set()
        # Commanded and not yet confirmed: jti -> (deadline, plant, ml). A dose leaves here on
        # the device's report, or on the sweep deciding nobody is going to send one.
        self.pending: dict[str, tuple[float, str, float]] = {}
        self.confirmed = 0
        self.unconfirmed = 0
        self.grace_s = agent.beliefs.read(ACTUATION_BLOCK).dose_grace_s
        self._sweep = Timer(SWEEP_S, self._expire)
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
            round_id=voucher.round_id,
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
        # Commanded is not delivered. The deadline is THIS dose's own duration — which this
        # agent computed, from the device's own calibration — plus the slack it believes the
        # bus needs. Relative and not absolute, for the reason `perception:readingGraceS` is:
        # an agent cannot ask a valve for a ninety-second pour and then call it late at thirty.
        if device.status_topic:
            self.pending[cmd.jti] = (time.monotonic() + cmd.seconds + self.grace_s,
                                     cmd.plant, cmd.ml)
        self.log.info("%s: open %.2fs (~%.0f ml) -> %s", cmd.plant, cmd.seconds, cmd.ml,
                      device.command_topic)
        return cmd

    # --- did it actually flow? -------------------------------------------------------------

    def subscriptions(self) -> list[str]:
        """Exactly my own valves' status channels — never a wildcard, and only where the world
        states one. A device wired without a status channel is a real deployment; what it costs
        is stated in `reports()`."""
        return [a.status_topic for a in self.me.actuators if a.status_topic]

    def start(self) -> None:
        self._sweep.start()

    def stop(self) -> None:
        self._sweep.stop()

    def handle(self, topic: str, payload: bytes) -> bool:
        """A device saying what it dispensed. Matched by `jti`, which is what makes it *this*
        dose's report and not the previous one's.

        Silence is the device's refusal — `firmware/simulated-valve` publishes here after
        dispensing and says nothing when it rejects a command — so this is only ever the happy
        path. The unhappy one is a deadline passing in `_expire`.
        """
        if topic not in self.subscriptions():
            return False
        try:
            report = json.loads(payload)
        except (ValueError, TypeError):
            self.log.warning("unreadable status on %s", topic)
            return True  # mine, and unreadable — saying so is the point
        jti = report.get("jti")
        waiting = self.pending.pop(jti, None)
        if waiting is None:
            # A report for a dose I am not waiting on. Not an error: a restarted agent has
            # forgotten what it commanded, and the device is right to report anyway.
            self.log.info("status for %s, which I was not waiting on", jti)
            return True
        self.confirmed += 1
        _, plant, ml = waiting
        self.log.info("%s: confirmed %.0f ml (jti %s)", plant, report.get("ml", ml), jti)
        return True

    def _expire(self) -> None:
        """Doses nobody confirmed. Reported and counted — never re-sent, and never un-spent.

        The issue that asked for this suggested not treating an unconfirmed voucher as spent.
        That is the wrong way round, for two reasons:

        - **The device refuses replays itself.** `firmware/simulated-valve` keeps its own spent
          set, so a re-sent command is refused rather than poured. Un-spending buys nothing
          and only removes this agent's own guard.
        - **The failures are not symmetric.** If the water flowed and the report was lost,
          re-sending risks pouring twice; if it did not flow, the plant misses this round and
          bids again in the next one. Over-watering is irreversible and a missed round is not,
          so the safe direction is to keep the jti spent and say loudly that nobody confirmed.

        What this produces is a number, `doses_unconfirmed`, which is the honest thing an agent
        can offer: it does not know whether the water flowed, and it stops pretending it does.
        """
        now = time.monotonic()
        for jti in [j for j, (due, _, _) in self.pending.items() if due <= now]:
            _, plant, ml = self.pending.pop(jti)
            self.unconfirmed += 1
            self.log.warning(
                "%s: no confirmation that %.0f ml flowed (jti %s) — the voucher stays spent, "
                "because a lost report and an unopened valve look identical from here",
                plant, ml, jti)

    def reports(self) -> dict:
        """What this capability adds to its agent's own health series.

        `doses_unconfirmed` is the field worth watching: it is the difference between a valve
        that dispensed and one that never heard, which was invisible before. An agent whose
        valves state no status channel reports zeroes for ever, which is itself a reading.
        """
        return {"doses_confirmed": self.confirmed, "doses_unconfirmed": self.unconfirmed}

    def redeem_all(self, vouchers) -> list[Command]:
        out = []
        for voucher in vouchers:
            try:
                out.append(self.redeem(voucher))
            except ValueError as exc:
                self.log.error("cannot redeem for %s: %s", voucher.sub, exc)
        return out
