//! WHAT A GRAPH STATES, told from what it says of itself (knowledge/domain/kernel/description.md).
//!
//! A graph describes itself: under its own name it says what kinds it is, how it arrived, whose it is, what it holds
//! by hash and when it holds, the last under a period. **The two are told apart by type**: a statement whose subject
//! the graph types `orexis:Graph` or `dcterms:PeriodOfTime` is description, and every other is a fact the graph
//! states. A text that reads a whole graph says so in its own pattern; these are the same rule for a reader that
//! holds a graph's statements in hand. They are functions over statements and no door of the store, which does not
//! know the difference: a reader that wants what a graph states says so where it reads.

use std::collections::HashSet;

use oxigraph::model::{NamedOrBlankNode, Quad, Term, Triple};

use crate::ontology::{GRAPH, PERIOD};
use crate::rdf::RDF_TYPE;

/// Whether a statement types its subject as a graph or as a period.
fn describes(predicate: &str, object: &Term) -> bool {
    predicate == RDF_TYPE
        && matches!(object, Term::NamedNode(class) if class.as_str() == GRAPH || class.as_str() == PERIOD)
}

/// What one graph's triples state: every triple but those whose subject the graph types as a graph or as a period.
pub fn stated(triples: Vec<Triple>) -> Vec<Triple> {
    let described: HashSet<NamedOrBlankNode> = triples
        .iter()
        .filter(|t| describes(t.predicate.as_str(), &t.object))
        .map(|t| t.subject.clone())
        .collect();
    if described.is_empty() {
        return triples;
    }
    triples
        .into_iter()
        .filter(|t| !described.contains(&t.subject))
        .collect()
}

/// What one graph's quads state, as `stated` says it of triples.
pub fn stated_quads(quads: Vec<Quad>) -> Vec<Quad> {
    let described: HashSet<NamedOrBlankNode> = quads
        .iter()
        .filter(|q| describes(q.predicate.as_str(), &q.object))
        .map(|q| q.subject.clone())
        .collect();
    if described.is_empty() {
        return quads;
    }
    quads.into_iter().filter(|q| !described.contains(&q.subject)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::Store;

    #[test]
    fn what_a_graph_says_of_itself_and_of_its_period_is_no_fact_it_states() {
        let store = Store::new().unwrap();
        store
            .update(
                "PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX orexis: <http://example.org/orexis#>
                INSERT DATA { GRAPH <urn:test:g> {
                    <urn:test:g> a orexis:BeliefGraph , orexis:Graph ; orexis:ownedBy <urn:test:me> ;
                        dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start 1 ] .
                    <urn:test:bed> <urn:test:soil> <urn:test:Dry> ; <urn:test:in> <urn:test:g> . } }",
            )
            .unwrap();
        let facts = |triples: Vec<Triple>| -> Vec<String> {
            let mut out: Vec<String> = triples.iter().map(|t| t.predicate.as_str().to_string()).collect();
            out.sort();
            out
        };
        assert_eq!(
            facts(stated(store.triples("urn:test:g").unwrap())),
            ["urn:test:in", "urn:test:soil"],
            "a fact naming the graph is a fact"
        );
        assert_eq!(stated_quads(store.quads("urn:test:g").unwrap()).len(), 2);
    }
}
