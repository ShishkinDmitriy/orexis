"""How a raw value becomes a quantity — the last stage, and a family.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[calibration]→ quantity

A raw value is a bare number: what the device put on the wire, 730 or 0.183 or 21.4. A
**quantity** is a number with a unit, and getting from one to the other is two things a
calibration does:

  * **scaling** — 730 counts become 0.17 of full scale, by whatever curve this probe follows;
  * **naming the unit** — and 0.17 is a dimensionless fraction while 21.4 is degrees Celsius.

The second is the half that is easy to forget and the one that bites first. Since a board may
report several properties, one store now holds soil moisture 0.183, air humidity 0.46 and air
temperature 21.4 — three numbers in two dimensions, two of which look identical. Which is which
was a convention in prose; it is a stated fact now, and `calibration:quantityUnit` is where a
sensor says it.

**The same mechanism as a capability; a different bearer.** A capability is derived onto an
agent as `ag:hasCapability`; a calibration is derived onto a SENSOR as
`calibration:calibratedBy`, from the `calibration:curve` its world states or from the absence of
one. Premise in the world, conclusion in the derived graph, lookup at runtime — the discipline
is the same, and only the bearer and the predicate differ.

**Today's member is `Identity`, and that is honest rather than a placeholder.** The firmware
already scales before it publishes, so from the agent's side the calibration genuinely is the
identity function — the stage is not missing, it is set to identity. Issue #26 is the proposal
to move that work off the board, and it is what makes a non-identity member exist: at that
point a calibration stops being a constant compiled into C and becomes a belief, with the
bounds and the second thoughts that implies.

See knowledge/decisions/bytes-become-a-quantity-in-stages.md.
"""

from __future__ import annotations

from . import loader


class Calibration:
    """One way of turning a raw value into a quantity.

    `TERM` names what this class implements, and there is no default here: which member serves a
    sensor that states no curve is decided by `calibrations/identity/rules.ru`.
    """

    TERM: str = ""

    def apply(self, sensor, raw: float) -> float:
        """The quantity this raw value stands for, in the unit the sensor declares.

        Takes the sensor because a calibration is per-device: two probes of one model in
        different soil do not share a curve, which is the whole reason this is a family and not
        a constant. Nothing here converts BETWEEN units — a member scales into the unit its
        sensor states, and a sensor that states none is saying the raw number was already the
        quantity.
        """
        raise NotImplementedError


def calibration_for(sensor) -> Calibration | None:
    """Whichever calibration genesis decided serves this sensor, or None if this build lacks it.

    A lookup of the derived `calibration:calibratedBy`. None is reported rather than raised, as
    everywhere else here: a world naming a curve a leaner build does not carry should cost one
    unread sensor and a warning, not a dead agent.
    """
    cls = loader.calibrations().get(sensor.calibrated_by)
    return cls() if cls else None
