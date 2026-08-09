# Derivation: which version of a world is the CURRENT one.
#
# The head of the chain is the version nothing else revises. Computing it rather than stating it
# is what lets `versions.ttl` be append-only in the literal sense — ratifying ADDS a node and
# never rewrites a line. A file that had to be edited to say which of its entries was current
# would not be a chain; it would be a pointer with history attached.
#
# It is also provenance-correct, which matters now that the graphs are split: `ag:currentVersion`
# is computed, so it belongs in the derived graph beside `ag:hasCapability` and not among the
# facts a sovereign ratified. The sovereign states versions; which one is latest follows.
#
# Structural rather than numeric on purpose. `MAX(?number)` would trust the integer an author
# typed, and the integer is for ordering and intent — `prov:wasRevisionOf` is what actually
# builds the chain. When the two disagree, the link is right and the number is a typo, and a
# shape catches it rather than this rule silently preferring one.

PREFIX ag:   <http://example.org/agora#>
PREFIX prov: <http://www.w3.org/ns/prov#>

INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?world ag:currentVersion ?head } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> {
        ?world a ag:World .
        ?head a ag:WorldVersion .
        FILTER NOT EXISTS { ?later prov:wasRevisionOf ?head }
    }
}
