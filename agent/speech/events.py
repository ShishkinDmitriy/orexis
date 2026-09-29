"""What speech says happened — the event its signal carries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Told:
    """A document for a peer: the agent it is `to`, and the document as TriG bytes."""
    to: str
    document: bytes
