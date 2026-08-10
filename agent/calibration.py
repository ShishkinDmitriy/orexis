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

**The same plug-in mechanism as a capability; a different bearer.** Rule 2 defines a capability
as a named ability with interchangeable implementations and says nothing about who bears it, so
this is one. What differs is what bears it, and selection follows from that: a capability is
borne by an AGENT and derived into the graph at genesis, while a calibration is borne by a
BINDING and chosen at runtime from what the sensor declares. An agent's capability is about what
it IS, which the world should hold and validate; a calibration is about what a device SPEAKS,
which only the device can say.

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

    `TERM` and `DEFAULT` work exactly as they do for a codec: a stated calibration is answered
    only by the member whose term it is, silence only by the default, and `agent.loader` refuses
    a build with two defaults or two members of one term. Explicit beats default structurally,
    not by ordering.
    """

    TERM: str = ""
    DEFAULT: bool = False

    @classmethod
    def claims(cls, sensor) -> bool:
        stated = getattr(sensor, "calibration", None)
        return stated == cls.TERM if stated else cls.DEFAULT

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
    """The calibration this binding selects, or None if this build carries no such member.

    None is reported rather than raised, as everywhere else here: a world naming a curve a
    leaner build does not carry should cost one unread sensor and a warning, not a dead agent.
    """
    for cls in loader.calibrations():
        if cls.claims(sensor):
            return cls()
    return None
