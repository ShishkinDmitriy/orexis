"""The assembly-time contribution points, as constants a package's `__init__` can import.

Deliberately tiny and deliberately dependency-free: every package's `__init__.py` imports this
at assembly, so anything expensive here would be paid by every agent for every package —
including the packages that agent was never granted (#216).
"""

BASE = "http://example.org/orexis/assembly#"


def term(name: str) -> str:
    return BASE + name


#  What a package brings to a build. Each is asked of every package's `__init__`, and each is
#  declared in `assembly/ontology.ttl` with the signature that fills it.
VOCABULARY = term("vocabulary")
SHAPES = term("shapes")
DERIVATION = term("derivation")
WANTS = term("wants")
ACTIONS = term("actions")
REVIEW = term("review")
