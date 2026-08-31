# Derivation: every agent reports on itself.
#
# The premise is being an agent, and that is the whole of it. This is the first capability here
# granted UNCONDITIONALLY, and the unconditionality is the point rather than an oversight:
#
#   * a silent agent must not be indistinguishable from a dead one. Health telemetry is the only
#     thing that can tell them apart, and an agent that could lose the ability to say it is
#     unwell is precisely the one you most need to hear from;
#   * #53 — an agent losing its broker session for days and nothing saying so — would become
#     permanently unfixable for exactly the agents that cannot speak for themselves;
#   * and self-review-is-a-capability reads the ABSENCE of the revision lines as "this agent was
#     never granted any latitude". That reading only works if the agent is still reporting.
#     Granting reporting conditionally would destroy that signal, silently, because the series
#     would look the same as an agent that had simply gone quiet.
#
# Mandatory is not the same as uniform. What makes this a capability rather than a function is
# that the SINK could differ — reporting:Storing writes to a series bucket, reporting:Announcing
# would publish on the bus, and the two fail independently. Rule 2 asks whether the how could
# differ, not whether every agent has it.
#
# Derived, never declared, exactly like every other: `world.ttl` still contains no
# orexis:hasCapability, and the prohibition is untouched. What is new is a shape that REFUSES an
# agent lacking this, so "every agent reports" is a fact the world is held to rather than a
# convention nothing checks — which is what it was while the term sat in the kernel, declared a
# capability and granted by nothing.
#
# reporting:Announcing is deliberately ABSENT. With one implemented member the rule names it
# directly, the same way review's does; what would SELECT between two once both exist is an open
# seam and the last piece to add, not the first.

PREFIX reporting: <http://example.org/orexis/reporting#>
PREFIX orexis: <http://example.org/orexis#>

INSERT { GRAPH $derived {
    ?agent orexis:hasCapability reporting:Storing } }
$given
WHERE  {
    ?agent a orexis:Agent .
}
