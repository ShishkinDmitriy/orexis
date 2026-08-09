# Derivation: which agent may reconsider its own settings, from the room it was given.
#
# The premise is a MANDATE. An agent the world commits to a range must be able to move within
# it — room to move and the ability to use it are one decision, said once. So the capability is
# derived from a fact about the agent, exactly as perception's is derived from a fact about its
# hardware, and nothing is declared by hand.
#
# An agent with no commitment gets nothing, which is how a deployment that wants no drift says
# so: not by omitting a belief and hoping a side channel notices, but by granting no latitude.
# There is then nothing to review, no interval demanded, no summaries kept, and no arising —
# the whole mechanism is absent rather than idle.
#
# This replaces belief-presence activation. A beliefs file mentioning `ag:reviewIntervalS` used
# to be the signal, which existed only because a capability could not be granted without wiring
# to derive it from — and worked by a side channel nothing could validate. See
# knowledge/decisions/a-capability-is-granted-by-latitude.md.
#
# ag:Consulting is deliberately ABSENT. The vocabulary declares it because the judgement is the
# replaceable part and the T-Box should say so; but no module implements it, and granting a
# capability nothing provides would only produce a startup warning. What would SELECT between
# the two once both exist is an open seam — the rule is the last piece to add, not the first.

PREFIX ag: <http://example.org/agora#>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ag:Reckoning } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:commits ?commitment .
    ?commitment ag:onTerm ?term .
}
