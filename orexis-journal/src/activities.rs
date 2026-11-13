//! THE ACTIVITIES, KEPT: what the agent did, where it can be asked. Every activity a package begins and ends is one entry of the
//! agent's journal, written as it ends and named by the activity, in PROV's words:
//!
//! ```turtle
//! <activity> a planning:Planning , prov:Activity ;
//!     prov:startedAtTime "…" ; prov:endedAtTime "…" ;    # the agent's clock
//!     orexis:tookS 3.66 ;                                 # real seconds
//!     prov:wasStartedBy <trigger> , <trigger> ;           # what its start names: an event, a graph, a step
//!     dcterms:isPartOf <activity> .                       # the activity it was begun inside, where one was
//! <event> prov:wasGeneratedBy <activity> ; a belief:Revised ;   # each event said while it was open,
//!     prov:generatedAtTime "…" .                                #   and the instant it was said at
//! <graph> prov:wasGeneratedBy <activity> .                      # each graph its turn wrote
//! ```
//!
//! SO WHAT CAUSED WHAT IS A QUERY, and no package is asked: an activity started by something another generated was
//! caused by it - `?b prov:wasStartedBy ?x . ?x prov:wasGeneratedBy ?a` - and a cycle through four packages is a path.
//! Kept so, a storm of plannings at one instant was read off a test's own tracer for want of this.
//!
//! THE HOT RECORD, AND NOTHING ELSE: an activity is kept for the journal's window and swept after, as a log record
//! is, unless an incident keeps the minutes before it. Sending them to a tracer as spans, and keeping them longer, is
//! another crate's, `orexis-journal-otlp/`, which reads them here. It knows no package's words: a class is whatever the event said it is.
//!
//! WHICH ACTIVITY AN EVENT IS SAID IN is told by the thread that says it: a task begins and ends an activity within
//! one turn, on one thread, and two tasks' turns may run side by side.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread::ThreadId;

use oxigraph::model::{NamedNode, Triple};
use oxsdatatypes::DateTime;

use crate::journal::{ACTIVITY, Journal};
use orexis::activity::{Ended, Started, Wrote};
use orexis::events::{Event, Watch, as_of, double, instant, triple, typed};

pub const STARTED_AT: &str = "http://www.w3.org/ns/prov#startedAtTime";
pub const ENDED_AT: &str = "http://www.w3.org/ns/prov#endedAtTime";
pub const STARTED_BY: &str = "http://www.w3.org/ns/prov#wasStartedBy";
pub const GENERATED_BY: &str = "http://www.w3.org/ns/prov#wasGeneratedBy";
pub const GENERATED_AT: &str = "http://www.w3.org/ns/prov#generatedAtTime";
pub const PART_OF: &str = "http://purl.org/dc/terms/isPartOf";
pub const TOOK_S: &str = "http://example.org/orexis#tookS";

/// An activity begun and not ended.
struct Open {
    activity: NamedNode,
    kind: &'static str,
    triggers: Vec<NamedNode>,
    began: DateTime,
    parent: Option<NamedNode>,
    /// Each event said while it was open, the class it said it is, where it said one, and the instant it was said at.
    generated: Vec<(NamedNode, Option<&'static str>, DateTime)>,
}

/// The activities open on each thread, innermost last.
struct Keeper {
    journal: Arc<Journal>,
    open: HashMap<ThreadId, Vec<Open>>,
}

impl Keeper {
    fn heard(&mut self, event: &dyn Event, said: &NamedNode) {
        let thread = std::thread::current().id();
        if let Some(started) = as_of::<Started>(event) {
            let open = self.open.entry(thread).or_default();
            let parent = open.last().map(|o| o.activity.clone());
            open.push(Open {
                activity: started.activity.clone(),
                kind: started.kind,
                triggers: started.triggers.clone(),
                began: started.at,
                parent,
                generated: Vec::new(),
            });
        } else if let Some(ended) = as_of::<Ended>(event) {
            //  WHEREVER IT WAS BEGUN: an activity ended on another thread than it began on is still the one named.
            let found = self.open.iter_mut().find_map(|(_, open)| {
                let i = open.iter().rposition(|o| o.activity == ended.activity)?;
                Some(open.remove(i))
            });
            if let Some(open) = found {
                self.keep(open, ended);
            }
        } else if let Some(wrote) = as_of::<Wrote>(event) {
            let triples = wrote
                .graphs
                .iter()
                .filter_map(|g| NamedNode::new(g.as_str()).ok())
                .map(|g| triple(g, GENERATED_BY, wrote.by.clone()))
                .collect();
            if let Err(e) = self.journal.add(&wrote.by, triples) {
                log::warn!("the journal refused what an activity wrote: {e}");
            }
        } else if let Some(open) = self.open.get_mut(&thread).and_then(|o| o.last_mut()) {
            let at = event.at().unwrap_or_else(|| self.journal.now());
            open.generated.push((said.clone(), event.kind(), at));
        }
    }

    fn keep(&self, open: Open, ended: &Ended) {
        let activity = open.activity.clone();
        let mut triples: Vec<Triple> = vec![
            typed(activity.clone(), open.kind),
            typed(activity.clone(), ACTIVITY),
            triple(activity.clone(), STARTED_AT, instant(open.began)),
            triple(activity.clone(), ENDED_AT, instant(ended.at)),
            triple(activity.clone(), TOOK_S, double(ended.duration_s)),
        ];
        for trigger in open.triggers {
            triples.push(triple(activity.clone(), STARTED_BY, trigger));
        }
        if let Some(parent) = open.parent {
            triples.push(triple(activity.clone(), PART_OF, parent));
        }
        for (said, kind, at) in open.generated {
            triples.push(triple(said.clone(), GENERATED_BY, activity.clone()));
            triples.push(triple(said.clone(), GENERATED_AT, instant(at)));
            if let Some(kind) = kind {
                triples.push(typed(said, kind));
            }
        }
        if let Err(e) = self.journal.record(&activity, triples, Some(open.began), false) {
            log::warn!("the journal refused an activity: {e}");
        }
    }
}

/// Keep every activity `watch` hears ended, in `journal`.
pub fn connect(watch: &Watch, journal: Arc<Journal>) {
    let keeper = Arc::new(Mutex::new(Keeper {
        journal,
        open: HashMap::new(),
    }));
    watch.connect(move |event, said| keeper.lock().unwrap().heard(event, said));
}

#[cfg(test)]
mod tests {
    use super::*;
    use orexis::activity::Activity;
    use orexis::events::mint;

    const PLANNING: &str = "http://example.org/orexis/planning#Planning";
    const SEARCHING: &str = "http://example.org/test#Searching";
    const REVISED: &str = "http://example.org/orexis/belief#Revised";

    fn at(text: &str) -> DateTime {
        orexis::clock::instant(text).unwrap()
    }

    struct Revised;
    impl Event for Revised {
        fn kind(&self) -> Option<&'static str> {
            Some(REVISED)
        }
    }

    fn journal() -> Arc<Journal> {
        Arc::new(Journal::new(None, 600.0, Arc::new(|| at("2026-01-01T12:00:00+00:00"))).unwrap())
    }

    fn rows(journal: &Journal, text: &str) -> Vec<String> {
        let body = String::from_utf8(crate::journal::answer(&journal.store, text).unwrap().1).unwrap();
        body.split("\"value\":\"")
            .skip(1)
            .map(|v| v.split('"').next().unwrap().to_string())
            .collect()
    }

    fn begin(watch: &Watch, kind: &'static str, triggers: &[NamedNode], when: &str) -> Activity {
        let activity = Activity::begin(kind);
        watch.emit(&Started {
            activity: activity.node.clone(),
            kind,
            triggers: triggers.to_vec(),
            at: at(when),
        });
        activity
    }

    fn end(watch: &Watch, activity: &Activity, when: &str) {
        watch.emit(&Ended {
            activity: activity.node.clone(),
            kind: activity.kind,
            at: at(when),
            duration_s: 0.25,
        });
    }

    /// An activity is one entry, written as it ends: its class, when it began and ended, how long it took, what
    /// started it, the activity it was begun inside, each event said while it was open and each graph it wrote.
    #[test]
    fn an_activity_ended_is_kept_with_what_started_it_and_what_it_generated() {
        let (watch, journal) = (Watch::default(), journal());
        connect(&watch, journal.clone());
        let trigger = mint();
        let planning = begin(
            &watch,
            PLANNING,
            std::slice::from_ref(&trigger),
            "2026-01-01T12:00:00+00:00",
        );
        let searching = begin(&watch, SEARCHING, &[], "2026-01-01T12:00:00+00:00");
        let revised = watch.emit(&Revised).unwrap();
        assert!(
            rows(
                &journal,
                "SELECT ?a WHERE { GRAPH ?a { ?a a <http://www.w3.org/ns/prov#Activity> } }"
            )
            .is_empty(),
            "nothing is kept of an activity still open"
        );
        end(&watch, &searching, "2026-01-01T12:00:01+00:00");
        end(&watch, &planning, "2026-01-01T12:00:02+00:00");
        watch.emit(&Wrote {
            by: planning.node.clone(),
            graphs: vec!["http://example.org/test#plan".to_string()],
        });
        let p = planning.node.as_str();
        let s = searching.node.as_str();
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?k WHERE {{ GRAPH <{p}> {{ <{p}> a ?k }} }} ORDER BY ?k")
            ),
            [PLANNING, ACTIVITY]
        );
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?t WHERE {{ GRAPH <{p}> {{ <{p}> <{STARTED_BY}> ?t }} }}")
            ),
            [trigger.as_str()]
        );
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?s WHERE {{ GRAPH <{p}> {{ <{p}> <{TOOK_S}> ?s }} }}")
            ),
            ["0.25"]
        );
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?o WHERE {{ GRAPH <{s}> {{ <{s}> <{PART_OF}> ?o }} }}")
            ),
            [p],
            "the search was begun inside the planning"
        );
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?e ?k WHERE {{ GRAPH <{s}> {{ ?e <{GENERATED_BY}> <{s}> ; a ?k }} }}")
            ),
            [revised.as_str(), REVISED],
            "an event is generated by the innermost activity open as it is said"
        );
        assert_eq!(
            rows(
                &journal,
                &format!("SELECT ?g WHERE {{ GRAPH <{p}> {{ ?g <{GENERATED_BY}> <{p}> }} }}")
            ),
            ["http://example.org/test#plan"],
            "and the graphs its turn wrote are said of it once it has ended"
        );
    }

    /// What caused what is a path: an activity started by something another generated.
    #[test]
    fn an_activity_started_by_what_another_generated_is_found_by_a_query() {
        let (watch, journal) = (Watch::default(), journal());
        connect(&watch, journal.clone());
        let first = begin(&watch, SEARCHING, &[], "2026-01-01T12:00:00+00:00");
        let revised = watch.emit(&Revised).unwrap();
        end(&watch, &first, "2026-01-01T12:00:00+00:00");
        let second = begin(
            &watch,
            PLANNING,
            std::slice::from_ref(&revised),
            "2026-01-01T12:00:00+00:00",
        );
        end(&watch, &second, "2026-01-01T12:00:00+00:00");
        assert_eq!(
            rows(
                &journal,
                &format!(
                    "SELECT ?a ?b WHERE {{ GRAPH ?b {{ ?b <{STARTED_BY}> ?x }} GRAPH ?a {{ ?x <{GENERATED_BY}> ?a }} }}"
                )
            ),
            [first.node.as_str(), second.node.as_str()]
        );
    }

    /// An activity is kept for the journal's window and swept after, as a log record is.
    #[test]
    fn an_activity_the_window_has_passed_is_swept() {
        let (watch, journal) = (Watch::default(), journal());
        connect(&watch, journal.clone());
        let planning = begin(&watch, PLANNING, &[], "2026-01-01T12:00:00+00:00");
        end(&watch, &planning, "2026-01-01T12:00:00+00:00");
        let kept = "SELECT ?a WHERE { GRAPH ?a { ?a a <http://www.w3.org/ns/prov#Activity> } }";
        assert_eq!(rows(&journal, kept).len(), 1);
        assert_eq!(journal.sweep(Some(at("2026-01-01T12:05:00+00:00"))).unwrap(), 0);
        assert_eq!(journal.sweep(Some(at("2026-01-01T12:11:00+00:00"))).unwrap(), 1);
        assert!(rows(&journal, kept).is_empty());
    }
}
