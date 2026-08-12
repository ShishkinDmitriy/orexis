"""The manifest: what this codec contributes to a build."""

from .codec import JsonCodec

PROVIDES = (JsonCodec,)
