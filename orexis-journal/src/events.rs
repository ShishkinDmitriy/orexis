//! THE EVENTS, KEPT: every event the agent's packages say that states triples is written to the journal as it is
//! said, one at a time — an entry named by the name it was said under, an incident where the entry's class is
//! beneath `orexis:Incident` in the agent's vocabulary. An event stating nothing is passed over. A journal that
//! refuses is said in the log and costs the agent nothing.

use std::collections::BTreeSet;
use std::sync::Arc;

use oxigraph::model::Term;

use crate::journal::Journal;
use orexis::Error;
use orexis::events::{RDF_TYPE, Watch};
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri};

/// What the vocabulary says is an incident: every class beneath it, off the closure.
const INCIDENTS_Q: &str = "SELECT DISTINCT ?c WHERE { ?c rdfs:subClassOf orexis:Incident }";

/// Every class `beliefs` holds beneath `orexis:Incident`, read off the common beliefs, where the closure is.
pub fn incidents(beliefs: &Store) -> Result<BTreeSet<String>, Error> {
    let common = beliefs.graphs_of(
        &[BELIEF],
        &Within {
            common: true,
            ..Within::default()
        },
    )?;
    let common: Vec<&str> = common.iter().map(String::as_str).collect();
    Ok(beliefs
        .rows(INCIDENTS_Q, &common)?
        .iter()
        .filter_map(|r| iri(r, "c"))
        .collect())
}

/// What keeps the events: no job of its own, only what it hears.
pub struct History;

impl History {
    /// The part, hearing every event `watch` is said, writing its triples to `journal`, each an incident where its
    /// class is one of `incidents`.
    pub fn new(watch: &Watch, journal: Arc<Journal>, incidents: BTreeSet<String>) -> Self {
        watch.connect(move |event, named| {
            let node = named.clone();
            if let Some(triples) = event.statements(&node) {
                let incident = triples.iter().any(|t| {
                    t.subject == node.clone().into()
                        && t.predicate.as_str() == RDF_TYPE
                        && matches!(&t.object, Term::NamedNode(c) if incidents.contains(c.as_str()))
                });
                if let Err(e) = journal.record(&node, triples, event.at(), incident) {
                    log::warn!("the journal refused an event: {e}");
                }
            }
        });
        History
    }
}

#[cfg(test)]
mod tests {
    use oxigraph::model::{NamedNode, Triple};
    use oxsdatatypes::DateTime;

    use super::*;
    use orexis::events::{Event, typed};
    use std::sync::Arc;

    struct Unreachable;
    impl Event for Unreachable {
        fn statements(&self, node: &NamedNode) -> Option<Vec<Triple>> {
            Some(vec![typed(
                node.clone(),
                "http://example.org/orexis/planning#WantUnreachable",
            )])
        }
    }

    struct Published;
    impl Event for Published {
        fn statements(&self, node: &NamedNode) -> Option<Vec<Triple>> {
            Some(vec![typed(
                node.clone(),
                "http://example.org/orexis/planning#PlanPublished",
            )])
        }
    }

    #[test]
    fn an_event_of_a_class_beneath_incident_is_marked_and_no_other() {
        let journal = Arc::new(Journal::new(600.0, Arc::new(DateTime::now)).unwrap());
        let watch = Watch::default();
        let _history = History::new(
            &watch,
            journal.clone(),
            BTreeSet::from(["http://example.org/orexis/planning#WantUnreachable".to_string()]),
        );
        watch.emit(&Unreachable);
        watch.emit(&Published);
        let (_, body) = crate::journal::answer(
            &journal.store,
            "SELECT ?k WHERE { ?e a <http://example.org/orexis#Incident>, ?k FILTER(?k != <http://example.org/orexis#Incident>) }",
        )
        .unwrap();
        let body = String::from_utf8(body).unwrap();
        assert!(
            body.contains("WantUnreachable") && !body.contains("PlanPublished"),
            "{body}"
        );
    }
}
