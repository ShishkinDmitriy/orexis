# Derivation: which agent may reconsider its own settings, from the room it was given.
#
# The premise is a MANDATE. An agent the world commits to a range must be able to move within
# it — room to move and the ability to use it are one decision, said once. So the capability is
# derived from a fact about the agent, exactly as sensing's is derived from a fact about its
# hardware, and nothing is declared by hand.
#
# An agent with no commitment gets nothing, which is how a deployment that wants no drift says
# so: not by omitting a belief and hoping a side channel notices, but by granting no latitude.
# There is then nothing to review, no interval demanded, no summaries kept, and no arising —
# the whole mechanism is absent rather than idle.
#
# This replaces belief-presence activation. A beliefs file mentioning `review:reviewIntervalS` used
# to be the signal, which existed only because a capability could not be granted without wiring
# to derive it from — and worked by a side channel nothing could validate. See
# knowledge/decisions/a-capability-is-granted-by-latitude.md.
#
# review:Consulting is deliberately ABSENT. The vocabulary declares it because the judgement is the
# replaceable part and the T-Box should say so; but no module implements it, and granting a
# capability nothing provides would only produce a startup warning. What would SELECT between
# the two once both exist is an open seam — the rule is the last piece to add, not the first.

PREFIX review: <http://example.org/orexis/review#>
PREFIX orexis: <http://example.org/orexis#>

#  ROOM means room. A mandate whose ends meet grants nothing: it is how an author says a figure
#  is not up for review — by leaving nowhere to go rather than by a flag somewhere saying not to
#  look — and `review.Range.fixed` reads it exactly that way. Without the filter, `succulent`,
#  whose cadence its world pins at 900, would hold a capability whose every arising could only
#  conclude nothing. Granting is by LATITUDE, so where there is none there is nothing to grant.
#
#  Both ends are optional in a mandate — one side may be narrowed and the world's figure hold on
#  the other — so this asks for the pair rather than assuming it, and a one-sided mandate is
#  latitude too.
INSERT { GRAPH $derived {
    ?agent orexis:hasCapability review:Reckoning } }
$given
WHERE  {
    ?agent a orexis:Agent ; review:commits ?commitment .
    ?commitment review:onTerm ?term .
    OPTIONAL { ?commitment review:notBelow ?below }
    OPTIONAL { ?commitment review:notAbove ?above }
    FILTER(!BOUND(?below) || !BOUND(?above) || ?below < ?above)
}
