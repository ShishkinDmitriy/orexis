//! HISTORY, as `agent/history/create.py` writes it: created where a history sink is loaded or a journal is kept, it
//! hears every event the agent's parts say and writes what each answers, one at a time as they happen — the point it
//! answers to the history sink, which the series store draws, and the triples it states to the journal, as an entry
//! named by the name it was said under, an incident where the entry's class is beneath `orexis:Incident` in the agent's
//! vocabulary. An event answering neither is passed over. A store that refuses is said in the log and costs the agent
//! nothing.

use std::collections::BTreeSet;
use std::sync::Arc;

use oxigraph::model::Term;

use orexis::Error;
use orexis::events::{RDF_TYPE, Watch};
use orexis::journal::Journal;
use orexis::ontology::BELIEF;
use orexis::runtime::Registers;
use orexis::series::Sink;
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

/// The history part: no job of its own, only what it hears.
pub struct History;

impl History {
    /// The part, hearing every event `watch` is said, writing points to `sink` and triples to `journal`, each an
    /// incident where its class is one of `incidents`.
    pub fn new(watch: &Watch, sink: Option<Sink>, journal: Option<Arc<Journal>>, incidents: BTreeSet<String>) -> Self {
        watch.connect(move |event, named| {
            if let (Some(sink), Some(point)) = (sink.as_ref(), event.point()) {
                sink.write(&[point]);
            }
            if let Some(journal) = journal.as_ref() {
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
            }
        });
        History
    }
}

impl History {
    /// HISTORY REGISTERING ITSELF on a runtime: a task that waits for nothing but the run's end, since what it keeps
    /// it hears on the watch.
    pub fn registers(self) -> Registers {
        Box::new(|runtime| {
            let starting = runtime.starting("history");
            runtime.register(starting, |mut seat| async move { while seat.next().await.is_some() {} });
            Ok(())
        })
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use oxigraph::model::{NamedNode, Triple};
    use oxsdatatypes::DateTime;

    use super::*;
    use orexis::events::{Event, Field, Point, typed};
    use std::sync::{Arc, Mutex};

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
        fn point(&self) -> Option<Point> {
            Some(Point {
                measurement: "published".into(),
                tags: BTreeMap::new(),
                fields: BTreeMap::from([("cost".to_string(), Field::Float(1.0))]),
                time: None,
            })
        }
    }

    #[test]
    fn an_event_of_a_class_beneath_incident_is_marked_and_no_other_and_a_point_goes_to_the_sink() {
        let journal = Arc::new(Journal::new(None, 600.0, Arc::new(DateTime::now)).unwrap());
        let written = Arc::new(Mutex::new(0));
        let counted = written.clone();
        let sink = Sink::new(
            "HISTORY",
            "h",
            Box::new(move |_, points| {
                *counted.lock().unwrap() += points.len();
                Ok(())
            }),
        );
        let watch = Watch::default();
        let _history = History::new(
            &watch,
            Some(sink),
            Some(journal.clone()),
            BTreeSet::from(["http://example.org/orexis/planning#WantUnreachable".to_string()]),
        );
        watch.emit(&Unreachable);
        watch.emit(&Published);
        let (_, body) = orexis::journal::answer(
            &journal.store,
            "SELECT ?k WHERE { ?e a <http://example.org/orexis#Incident>, ?k FILTER(?k != <http://example.org/orexis#Incident>) }",
        )
        .unwrap();
        let body = String::from_utf8(body).unwrap();
        assert!(
            body.contains("WantUnreachable") && !body.contains("PlanPublished"),
            "{body}"
        );
        assert_eq!(*written.lock().unwrap(), 1, "the one event that is a point");
    }
}
