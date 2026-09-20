"""The terms this package implements — the Python end of `ontology.ttl`.

**This package owns a namespace**, and `term()` here builds into it. `orexis:` is what every agent
has whatever it composed; touching the physical world is not that, so its vocabulary is this
package's and says so. `tests/test_layout.py` holds `NS` and the `@prefix` in `ontology.ttl`
together — drifting them apart would have Python name terms SHACL never validates, and the world
would conform while the agent read nothing.
"""

from __future__ import annotations

NS = "http://example.org/orexis/actuation#"


def term(name: str) -> str:
    """A term of this package's, by local name."""
    return NS + name


ACTUATION = term("Actuation")  # holds the hardware, and may therefore touch the world

DOSING = term("Dosing")
TOLERANCE = term("tolerance")    # how close the world must land to a predicted reading (#518)            # the dose — the action, and the kind of act it is


#  WHAT A DOSING IS FILLED WITH — the actuator it acts through. The market's Serving takes the
#  same parameter, being the same kind of filling, which is why it is declared here and not
#  twice.
VALVE = term("valve")
