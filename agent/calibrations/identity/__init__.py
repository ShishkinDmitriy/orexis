"""The manifest: what this calibration contributes to a build."""

from .calibration import IdentityCalibration

PROVIDES = (IdentityCalibration,)
