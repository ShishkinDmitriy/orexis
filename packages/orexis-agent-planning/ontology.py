"""The planning layer's own namespace (#529): what a pass FINDS, what the derivations read
and write, and the scopes that partition follows. Declared here — never in the execution
layer's term module — since a lower layer may not spell a higher one's vocabulary.

11 TERMS, AND THE PREDECESSOR HAD FIFTY-FOUR. What is gone is the trace — everything a pass
recorded about itself for a reader — and the remembered plan, both read by code this layer no
longer has. A term nobody reads is annotation; they come back with their readers.

TERMS AND NOTHING ELSE. Two graph-NAME builders sat here — one for a want's graph, one for
the store's scopes — and each had exactly one caller, the module that writes the graph. A term
is public and code is written against it; a graph's name is for eyes and belongs with its
writer, which is why `test_layout.py` refuses a reader that imports one.
"""
from __future__ import annotations

PLANNING = "http://example.org/orexis/planning#"

#  WHAT A PASS FINDS, per want: a graph of its own in the imaginarium, holding the steps in
#  the ledger's own words. Named by `imaginarium.plan_graph` and copied out by the execution
#  layer; nothing here is written to the belief base.
PLAN_GRAPH = PLANNING + "PlanGraph"
FOR_WANT = PLANNING + "forWant"


#  A DERIVATION (scope-actions): one INSERT of one loaded rule, as the edge it makes. Written
#  at every refresh of public knowledge, so the partition is a function of the store and not of
#  the files — the actions are in the store already and the rules were not.
DERIVATION = PLANNING + "Derivation"
READS = PLANNING + "reads"
WRITES = PLANNING + "writes"
ANYTHING = PLANNING + "Anything"
DERIVATION_GRAPH = PLANNING + "DerivationGraph"

#  A SCOPE (scope-actions): which predicates some one action or derivation moves together.
SCOPE = PLANNING + "Scope"
IN_SCOPE = PLANNING + "inScope"


