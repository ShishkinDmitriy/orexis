# Derivation: the avoidance wants — one per ratified avoided state (#468).
#
# Run by the desire modality's build like every `desires.ru`. The premise is this package's
# own authored statement (`aversion:avoids`), so the want exists exactly while the world
# states it and vanishes on the rebuild after an amendment drops it — never retracted, only
# no longer implied.
#
# NO `orexis:metWhen`, deliberately: the want's met-test IS its measure reading zero (the call
# road, #359), one text run by one engine against whichever world is judged — see the kind's
# own comment in ontology.ttl. The scope is stated even so: an avoidance binds ALWAYS — every
# step of each loop — which is what the planner's aggregation will read the day it sums
# avoided states a candidate world merely passes through.
#
# The statement's node and its select are COPIED into the derived graph: the desires store
# drops its public premises after the derivation, and a want whose pattern stayed behind in
# the world graph would hold a dangling reference to a text nothing can run.

PREFIX aversion: <http://example.org/orexis/aversion#>
PREFIX orexis: <http://example.org/orexis#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT { GRAPH $derived {
    $me orexis:holds ?want .
    ?want a orexis:Desire , aversion:Aversion ;
        orexis:bindsWhen orexis:Always ;
        orexis:about ?state ;
        prov:wasDerivedFrom ?state ;
        rdfs:label ?label .
    ?state ?p ?o . } }
$given
WHERE  {
    $me aversion:avoids ?state ; orexis:localId ?who .
    ?state ?p ?o .
    BIND(IRI(CONCAT("http://example.org/orexis#aversion.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?state), "#")))) AS ?want)
    BIND(CONCAT("steer clear: ", STRAFTER(STR(?state), "#")) AS ?label)
}
