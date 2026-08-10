"""The quantity is the raw value.

The only calibration this project has, and the reason it is worth writing down rather than
leaving implicit: the stage is not missing, it is set to identity. `firmware/moisture-sensor`
maps its ADC counts to a fraction before it publishes, so what arrives has already been through
a curve — one that lives in C, on the board, where changing it means reflashing.

Issue #26 is the proposal to move that work here. What makes it interesting is not the
arithmetic but where the curve then lives: in the agent, as a belief, within stated bounds and
open to being re-picked as a probe drifts.
"""

from __future__ import annotations

from agent.calibration import Calibration

from .terms import IDENTITY


class IdentityCalibration(Calibration):
    """Pass the number through, unchanged and unrounded."""

    TERM = IDENTITY

    def apply(self, sensor, raw: float) -> float:
        """The raw value, as it stands.

        Deliberately not `float(raw)` or a rounding — this member's contract is that nothing
        happens, and a conversion here would be a conversion nobody asked for. The unit the
        result is in is the sensor's to state; identity does not mean dimensionless.
        """
        return raw
