"""The manifest: what this capability contributes to a build.

Note what is absent: a `beliefs.py`. This capability decides nothing, so there is nothing for
its holder to believe — it reads the device's own calibration from the world and obeys.
"""

from .module import ActuationModule, Command
from .terms import ACTUATION

PROVIDES = (ActuationModule,)

__all__ = ["PROVIDES", "ActuationModule", "Command", "ACTUATION"]
