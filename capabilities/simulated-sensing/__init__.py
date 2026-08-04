"""The manifest: what this capability contributes to a build."""

from .module import SimulatedSensingModule
from .terms import SIMULATED_SENSING

PROVIDES = (SimulatedSensingModule,)

__all__ = ["PROVIDES", "SimulatedSensingModule", "SIMULATED_SENSING"]
