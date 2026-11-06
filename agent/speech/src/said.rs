//! WHAT THIS AGENT TOLD A PEER, KEPT AS IT WAS SAID, as `agent/speech/said.py` keeps it: every graph a statement,
//! recorded and its own, replacing what it said under that name before. A graph of the name that arrived any other
//! way is refused, and the whole document with it, as is one saying whose a graph is or who the self is.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::ontology::{RECORDED, local_of};
use orexis::store::{Store, iri};

use crate::statements::statements;

const ARRIVED_Q: &str = "
SELECT ?arrival ?owner WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph orexis:arrivedBy ?arrival .
                                            OPTIONAL { $graph orexis:ownedBy ?owner } } }";

/// Keep `doc` as this agent said it; the names written, sorted.
pub fn said(store: &Store, me: &str, doc: &Document) -> Result<Vec<String>, Error> {
    doc.refuse_the_sovereigns(&format!("what {} said", local_of(me)))?;
    for graph in doc.kinds().into_keys() {
        for r in store.rows(&bind(ARRIVED_Q, &[("graph", Value::iri(graph.as_str()))])?, &[])? {
            let arrival = iri(&r, "arrival").unwrap_or_default();
            if arrival != RECORDED || iri(&r, "owner").as_deref() != Some(me) {
                return Err(Error::Document(format!(
                    "{} cannot say {graph} again: it arrived {}, not as this agent's word",
                    local_of(me),
                    local_of(&arrival)
                )));
            }
        }
    }
    store.put_document(&statements(store, doc)?, Some(me), None, Some(RECORDED), true)
}

#[cfg(test)]
pub(crate) mod tests {
    //! `said`, held as `agent/speech/tests/test_said.py` holds it: what this agent told a peer it believes it told —
    //! recorded and its own — and it may say again only what it said before.

    use oxigraph::model::{GraphName, Literal, NamedNode, Quad};

    use orexis::ontology::{BELIEF, CATALOGUE_GRAPH, OREXIS};
    use orexis::snapshots::namespaces;
    use orexis::store::value;

    use super::*;

    pub(crate) const T: &str = "http://example.org/test#";
    const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

    pub(crate) fn me() -> String {
        format!("{T}me")
    }

    pub(crate) fn store() -> Store {
        let st = Store::new(namespaces()).unwrap();
        st.update(&format!(
            "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph .
        <{T}heard> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Received ; orexis:ownedBy <{}> . }} }}",
            me()
        ))
        .unwrap();
        st
    }

    pub(crate) fn quads(graph: &str, fact: &str) -> Vec<Quad> {
        let g = NamedNode::new_unchecked(graph);
        vec![
            Quad::new(
                g.clone(),
                NamedNode::new_unchecked(format!("{T}says")),
                Literal::new_simple_literal(fact),
                g.clone(),
            ),
            Quad::new(
                g,
                NamedNode::new_unchecked(RDF_TYPE),
                NamedNode::new_unchecked(BELIEF),
                GraphName::DefaultGraph,
            ),
        ]
    }

    #[test]
    fn what_the_agent_said_is_recorded_and_its_own_and_may_be_said_again() {
        let store = store();
        let round = format!("{T}round");
        assert_eq!(
            said(&store, &me(), &Document::of_quads(quads(&round, "open"))).unwrap(),
            std::slice::from_ref(&round)
        );
        let q = format!(
            "SELECT ?a ?o WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{round}> orexis:arrivedBy ?a ; orexis:ownedBy ?o }} }}"
        );
        let found = store.rows(&q, &[]).unwrap();
        assert_eq!(value(&found[0], "a").unwrap(), format!("{OREXIS}Recorded"));
        said(&store, &me(), &Document::of_quads(quads(&round, "cleared"))).unwrap();
        assert_eq!(store.triples(&round).unwrap().len(), 1);
    }

    #[test]
    fn the_agent_cannot_say_again_what_a_peer_told_it() {
        let store = store();
        assert!(
            said(
                &store,
                &me(),
                &Document::of_quads(quads(&format!("{T}heard"), "overwritten"))
            )
            .is_err()
        );
    }

    #[test]
    fn the_agent_s_own_word_cannot_say_who_the_self_is_nor_whose_a_graph_is() {
        let store = store();
        let round = format!("{T}round");
        let mut selfish = quads(&round, "open");
        selfish.push(Quad::new(
            NamedNode::new_unchecked(format!("{T}someone")),
            NamedNode::new_unchecked(RDF_TYPE),
            NamedNode::new_unchecked(format!("{OREXIS}Self")),
            NamedNode::new_unchecked(&round),
        ));
        let refused = said(&store, &me(), &Document::of_quads(selfish))
            .unwrap_err()
            .to_string();
        assert!(refused.contains("only the world's own documents say"), "{refused}");
        let mut owned = quads(&round, "open");
        owned.push(Quad::new(
            NamedNode::new_unchecked(&round),
            NamedNode::new_unchecked(format!("{OREXIS}ownedBy")),
            NamedNode::new_unchecked(format!("{T}someone")),
            GraphName::DefaultGraph,
        ));
        assert!(said(&store, &me(), &Document::of_quads(owned)).is_err());
        assert!(store.triples(&round).unwrap().is_empty(), "refused whole");
    }
}
