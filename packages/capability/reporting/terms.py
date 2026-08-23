"""The terms this package implements — the Python end of `ontology.ttl`.

The axis here is **where an agent's account of itself goes**. Counting is not the variable part
and never was: every agent counts the same figures, in the kernel, because `Observations` counts
into them before any module exists. What can differ is the manner of reporting — a series store
today, the bus tomorrow — and the two fail independently, which for telemetry is the whole point.

Nothing outside this package names these. `agent.provider(REPORTING)` asks for whoever reports,
exactly as it asks for whoever perceives.
"""

from __future__ import annotations

NS = "http://example.org/orexis/reporting#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name


# The family. Anything that puts an agent's account of itself somewhere is one of these — so a
# caller may ask for "whoever reports" without knowing where it puts it.
REPORTING = term("ReportingCapability")

# The axis is WHERE the account goes, and these fail in different ways on purpose.
STORING = term("Storing")        # into its own series bucket — the implemented member
ANNOUNCING = term("Announcing")  # onto the bus — RESERVED, nothing implements it yet

# How often. An ordinary required parameter of the capability, exactly as review:reviewIntervalS
# is of reviewing — not a switch, because every agent has this capability.
INTERVAL_S = term("metricsIntervalS")
