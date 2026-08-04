"""The manifest: what this capability contributes to a build."""

from .module import SimulatedActuationModule
from .terms import SIMULATED_ACTUATION

PROVIDES = (SimulatedActuationModule,)

__all__ = ["PROVIDES", "SimulatedActuationModule", "SIMULATED_ACTUATION"]
