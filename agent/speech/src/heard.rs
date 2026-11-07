//! A PEER'S DOCUMENT, KEPT AS WHAT WAS SAID — OR REFUSED WHOLE, as `agent/speech/heard.py` keeps it: every graph it
//! names a statement, each replacing what a peer said under that name before, received and this agent's. Refused,
//! said in the log, where the payload is no document, a graph of its name arrived another way, or it says whose a
//! graph is or who the self is, since the hearer owns what it hears and no peer tells this agent who it is.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::ontology::{RECEIVED, local_of};
use orexis::store::{Store, iri};

use crate::statements::statements;

const ARRIVED_Q: &str =
    "SELECT ?arrival WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph orexis:arrivedBy ?arrival } }";

/// Keep the document `payload` holds as a peer said it; the names written, sorted, and none where it was refused.
pub fn heard(store: &Store, me: &str, payload: &[u8]) -> Result<Vec<String>, Error> {
    let doc = match refused(store, payload) {
        Ok(doc) => doc,
        Err(why) => {
            log::warn!("{}: a document heard and not kept: {why}", local_of(me));
            return Ok(Vec::new());
        }
    };
    store.put_document(&statements(store, &doc)?, Some(me), None, Some(RECEIVED), true)
}

fn refused(store: &Store, payload: &[u8]) -> Result<Document, Error> {
    let doc = Document::of(payload)?;
    for graph in doc.kinds().into_keys() {
        let arrived: Vec<String> = store
            .rows(&bind(ARRIVED_Q, &[("graph", Value::iri(graph.as_str()))])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "arrival"))
            .collect();
        if !arrived.is_empty() && arrived != [RECEIVED] {
            return Err(Error::Document(format!(
                "{graph} is not a peer's to say again — it arrived {}",
                arrived.iter().map(|a| local_of(a)).collect::<Vec<_>>().join(", ")
            )));
        }
    }
    Ok(doc)
}

#[cfg(test)]
mod tests {
    //! `heard`, held as `agent/speech/tests/test_heard.py` holds it: a peer's document is kept as what was said —
    //! every graph a statement, whatever kind it says — where a graph of its name was a peer's word too (#958).

    use oxigraph::model::{GraphNameRef, NamedNodeRef};

    use orexis::ontology::{ACTION, BELIEF, CATALOGUE_GRAPH, OREXIS};
    use orexis::snapshots::namespaces;
    use orexis::store::{Within, value};

    use super::*;
    use crate::ontology::STATEMENT_GRAPH as STATEMENT;

    const T: &str = "http://example.org/test#";

    fn me() -> String {
        format!("{T}me")
    }

    pub(crate) fn store() -> Store {
        let st = Store::new(namespaces()).unwrap();
        st.update(&format!(
            "INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . <{T}vocabulary> a orexis:OntologyGraph .
                               <{T}mine> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{T}vocabulary> {{ <{T}RoundGraph> rdfs:subClassOf <{STATEMENT}> , orexis:Graph .
                           <{STATEMENT}> rdfs:subClassOf orexis:Graph . }} }}"
        ))
        .unwrap();
        st
    }

    pub(crate) fn doc(graph: &str, kind: &str, fact: &str) -> Vec<u8> {
        format!("<{graph}> {{ <{graph}> <{T}says> \"{fact}\" }}\n<{graph}> a <{kind}> .").into_bytes()
    }

    fn kinds(store: &Store, kind: &str) -> Vec<String> {
        store.graphs_of(&[kind], &Within::default()).unwrap()
    }

    fn said_in(store: &Store, graph: &str) -> Vec<String> {
        store
            .engine()
            .quads_for_pattern(
                None,
                Some(NamedNodeRef::new_unchecked(&format!("{T}says"))),
                None,
                Some(GraphNameRef::NamedNode(NamedNodeRef::new_unchecked(graph))),
            )
            .filter_map(|q| q.ok())
            .map(|q| match q.object {
                oxigraph::model::Term::Literal(l) => l.value().to_string(),
                other => other.to_string(),
            })
            .collect()
    }

    #[test]
    fn a_round_heard_is_kept_as_a_statement_the_agent_s_own_and_received() {
        let store = store();
        let round = format!("{T}round");
        assert_eq!(
            heard(&store, &me(), &doc(&round, &format!("{T}RoundGraph"), "open")).unwrap(),
            std::slice::from_ref(&round)
        );
        assert!(
            kinds(&store, STATEMENT).contains(&round),
            "a statement, its kinds closed on its row"
        );
        assert!(
            kinds(&store, &format!("{T}RoundGraph")).contains(&round),
            "a kind of statement it said is kept"
        );
        assert!(!kinds(&store, BELIEF).contains(&round), "and no belief");
        let q = format!(
            "SELECT ?a ?o WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{round}> orexis:arrivedBy ?a ; orexis:ownedBy ?o }} }}"
        );
        let found = store.rows(&q, &[]).unwrap();
        assert_eq!(found.len(), 1);
        assert_eq!(value(&found[0], "a").unwrap(), format!("{OREXIS}Received"));
        assert_eq!(value(&found[0], "o").unwrap(), me());
    }

    #[test]
    fn a_round_said_again_replaces_the_one_before() {
        let store = store();
        let (round, kind) = (format!("{T}round"), format!("{T}RoundGraph"));
        heard(&store, &me(), &doc(&round, &kind, "open")).unwrap();
        heard(&store, &me(), &doc(&round, &kind, "cleared")).unwrap();
        assert_eq!(said_in(&store, &round), ["cleared"]);
    }

    #[test]
    fn whatever_kind_a_peer_says_what_is_kept_is_what_was_said() {
        for kind in [
            ACTION.to_string(),
            "http://example.org/orexis/planning#DesireGraph".to_string(),
            BELIEF.to_string(),
            format!("{OREXIS}WorldGraph"),
        ] {
            let store = store();
            let wish = format!("{T}wish");
            assert_eq!(
                heard(&store, &me(), &doc(&wish, &kind, "want")).unwrap(),
                std::slice::from_ref(&wish),
                "{kind}"
            );
            let expected: Vec<String> = if kind == BELIEF {
                vec![format!("{T}mine")]
            } else {
                vec![]
            };
            assert_eq!(kinds(&store, &kind), expected, "the kind it said is not kept: {kind}");
            assert_eq!(kinds(&store, STATEMENT), [wish]);
        }
    }

    #[test]
    fn a_peer_cannot_rewrite_what_this_agent_said_nor_send_what_is_no_document() {
        let store = store();
        assert!(
            heard(
                &store,
                &me(),
                &doc(&format!("{T}mine"), &format!("{T}RoundGraph"), "forged")
            )
            .unwrap()
            .is_empty()
        );
        assert!(heard(&store, &me(), b"this is not TriG {").unwrap().is_empty());
    }

    #[test]
    fn a_peer_cannot_say_who_the_self_is_nor_whose_a_graph_is() {
        let store = store();
        let self_said = format!(
            "<{T}round> {{ <{T}round> <{T}says> \"open\" . <{T}someone> a <{OREXIS}Self> }}\n<{T}round> a <{T}RoundGraph> ."
        );
        assert!(heard(&store, &me(), self_said.as_bytes()).unwrap().is_empty());
        let whose = format!(
            "<{T}round> {{ <{T}round> <{T}says> \"open\" }}\n<{T}round> a <{T}RoundGraph> ; <{OREXIS}ownedBy> <{T}someone> ."
        );
        assert!(heard(&store, &me(), whose.as_bytes()).unwrap().is_empty());
        assert!(said_in(&store, &format!("{T}round")).is_empty(), "refused whole");
    }
}
