"""The terms this package implements — the Python end of `ontology.ttl`.

Every capability package names its terms in one small file like this, so nothing central has
to know they exist. `term()` builds the IRI from the kernel prefix; nothing is imported from
another capability, because a term is spelled the same way wherever it is referred to.
"""

from __future__ import annotations

from agora.ontology import term

# The family. Anything that perceives is one of these — which is what lets another capability
# ask for "whoever perceives" without knowing there are two ways to do it.
PERCEPTION = term("PerceptionCapability")

POLLING = term("Polling")  # the agent drives its sensors, and owns a cadence
LISTENING = term("Listening")  # the device announces on its own clock; the agent records
