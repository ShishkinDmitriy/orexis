"""The manifest: what this scaling contributes to a build."""

from .scaling import IdentityScaling

PROVIDES = (IdentityScaling,)
