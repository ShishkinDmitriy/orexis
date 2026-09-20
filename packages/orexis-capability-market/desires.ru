PREFIX orexis: <http://example.org/orexis#>
PREFIX market: <http://example.org/orexis/market#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#################  WHAT A HOST WANTS OF ITS OWN LEDGER  #################
#
#  ONE DESIRE, declared once at genesis: **no overdue debts**. It is the standing rule a host
#  holds for its whole life — `orexis:Desire` says so by its type — and it is never handed to a
#  search; a desire is
#  the premise of what is pursued, not the thing pursued
#  (knowledge/domain/desire.md). What a claim arriving derives under it is the WANT: close THIS
#  debt before its window closes, which the ledger mints beside the debt it is about.
#
#  IT WAS MISSING, and the absence is what made the vocabulary look self-contradictory. Every
#  other want in the tree is derived from something standing — sensing's region desire per
#  property, its freshness desire per sensor — and a debt was minted as an `orexis:Desire` with
#  NOTHING above it and `prov:wasDerivedFrom` a claim id, which is a string rather than a node.
#  So the market produced wants with no desire to have derived them from, and the page that
#  described the model listed "every debt honoured" among the roots an agent holds while no
#  package shipped one.
#
#  THE PREMISE IS HOSTING, not bidding. Only an agent that hosts a venue issues claims, and
#  only an issued claim becomes a debt — so a buyer holds no such desire and a world with no
#  market composes none of this, which is the same discipline every other capability's premise
#  follows.
#
#  OVERDUE rather than UNPAID, and the sovereign's word is the load-bearing one. "No unpaid
#  debts" would read unmet from the instant a claim cleared until the water was poured, so a
#  host would stand permanently in violation of its own rule and the state would say nothing
#  about whether anything was wrong. "No overdue debts" is MET while every debt still has time
#  to run, which is the true state of a host that owes water and has not yet poured it — and it
#  is what the wants under it exist to keep true.
INSERT { GRAPH $derived {
    $me orexis:holds ?desire .
    ?desire a orexis:Desire ;
        rdfs:label "no overdue debts — every claim I issued honoured before its window closes" ;
        rdfs:comment "The standing rule a host holds over its own ledger. A claim arriving derives a want under it, to close that debt before its window closes; the desire itself is never pursued." ;
        #  THE MET-TEST, askable now that overdue is an instant the door can be asked at
        #  (one-function-mints-every-want): the ledger writes, beside each debt, a PREDICTION
        #  that it lapses at its deadline — a graph holding from that instant on. A debt with a
        #  lapse in view is the violation; asked at the prediction's start, the row names the
        #  debt and the instant, and the derivation mints the want that must hold AT it. Asked now,
        #  no prediction holds yet and every debt with time to run reads met — which is what
        #  "no OVERDUE debts" was always supposed to say.
        orexis:metWhen ?honoured .
    ?honoured a sh:NodeShape ;
        sh:targetSubjectsOf market:forClaim ;
        #  TWO WAYS A DEBT IS NOT HONOURED, each ABOUT THE DEBT ITSELF — `sh:this` names the
        #  focus node, so the want minted under this desire is about one debt and a Serving
        #  step can name its claim. SPARQL rather than a property block, because both must
        #  read MET in a world where a serve has written the discharge — the search judges a
        #  candidate's end-world by this test, and the lapse prediction still holds there.
        #
        #  (1) it is about to LAPSE and is not paid: the prediction the ledger wrote beside it
        #      holds — from its deadline on — and nothing has discharged it;
        sh:sparql [
            sh:prefixes orexis: ;
            orexis:about sh:this ;
            sh:message "a debt of mine is about to lapse unserved" ;
            sh:select """SELECT $this WHERE {
                $this market:lapsesAt ?when .
                FILTER NOT EXISTS { $this market:dischargedAt ?paid } }""" ] ;
        #  (2) the holder has PRESENTED and it is not paid: somebody is waiting now, whatever
        #      the deadline — and a claim that named none is served this way alone.
        sh:sparql [
            sh:prefixes orexis: ;
            orexis:about sh:this ;
            sh:message "a claim of mine is presented and unserved" ;
            sh:select """SELECT $this WHERE {
                $this market:presented true .
                FILTER NOT EXISTS { $this market:dischargedAt ?paid } }""" ] .
    ?desire
        #  THE MET-TEST ABOVE WAS MISSING until the lapse became a prediction, and this
        #  comment kept the reason: "overdue" was unaskable without a clock. "Overdue" is
        #  not askable without a clock today: the door already hides a debt whose window has
        #  closed (#645), so a select over what a reader sees cannot find one; and
        #  `market:lapsedAt`, which the record keeps, is PERMANENT — a desire tested on it
        #  would read unmet for ever after a single miss, and the derivation would derive a
        #  want under it on every pass. A rule may not ask `NOW()` (#646): a possible world is
        #  judged at the instant a pass chose, and a rule that read the wall clock would answer
        #  about a world nobody is in. What makes the test expressible is the crossing —
        #  the desire asked at the start of each prediction the agent holds — which is #675,
        #  and the market already writes ledger-derived predictions (#626) for it to use.
        #
        #  Until then this desire is what the wants under it point AT: the standing rule that
        #  says why a debt is worth closing, and the node `prov:wasDerivedFrom` lands on. It is
        #  never unmet, so nothing is ever derived under it, and the ledger stays
        #  the only deriver — which is what was chosen for now.
        rdfs:seeAlso <https://github.com/ShishkinDmitriy/orexis/issues/675> .
} }
$given
WHERE {
    #  `$given` above is the USING list genesis binds — public knowledge and this agent's own
    #  beliefs. Without it an update's WHERE reads the UNNAMED default graph, which in the
    #  scratch store genesis builds is empty: the rule runs, binds nothing, inserts nothing,
    #  and says so to nobody. It is the trap AGENTS.md records, met on the first run of this
    #  file.
    $me market:hosts ?venue .
    BIND(IRI(CONCAT(STR($me), ".no_overdue_debts")) AS ?desire)
    BIND(IRI(CONCAT(STR($me), ".no_overdue_debts.honoured")) AS ?honoured)
}
