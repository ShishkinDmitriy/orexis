# Derivation: who steers clear of anything, from the statements the world ratifies.
#
# The premise is the STATEMENT ITSELF — the latitude pattern, not the equipment one: being told
# what to avoid is the whole of what makes steering meaningful, exactly as a mandate is the
# whole of what makes reviewing meaningful (self-review-is-a-capability). An agent whose world
# avoids nothing composes no module and runs no pattern: absent rather than idle, which is how
# a deployment that wants no aversions says so.
#
# AUTHORED premises only, per the standing trap: a grant may not rest on another package's
# conclusions, and aversion:avoids is stated in the world's own files.

PREFIX aversion: <http://example.org/orexis/aversion#>
PREFIX orexis: <http://example.org/orexis#>

INSERT { GRAPH $derived {
    ?agent orexis:hasCapability aversion:Heeding } }
$given
WHERE  {
    ?agent a orexis:Agent ; aversion:avoids ?state .
}
