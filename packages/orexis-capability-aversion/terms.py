"""The terms this package implements — the Python end of `ontology.ttl`.

The axis is HOW the steering-clear is judged. Heeding runs the ratified pattern itself;
whatever asked a model where a pattern cannot be written would be a sibling in the same
PROVIDES. Nothing outside this package names these: the kernel asks the choir, and the
choir answers by kind.
"""

from __future__ import annotations

NS = "http://example.org/orexis/aversion#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name


# The family: anything that steers an agent away from ratified avoided states.
AVERSION_CAPABILITY = term("AversionCapability")

# The member: judge by running the ratified pattern, deterministically.
HEEDING = term("Heeding")

# The premise and the grant in one statement: a world says what this agent avoids.
AVOIDS = term("avoids")

# The KIND a derived avoidance want carries — how the choir knows a want is this package's.
AVERSION = term("Aversion")
