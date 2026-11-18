//! THE ARCHIVE: a triplestore of what the journal kept for good, and what archives - the journal read, the archive
//! written, and how often.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

use oxigraph::model::NamedNode;
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;

use orexis::Error;
use orexis_journal::Journal;
use orexis_journal::journal::{ACTIVITY, KEPT_BY, LOGGED};

fn engine(e: impl std::fmt::Display) -> Error {
    Error::Evaluation(e.to_string())
}

/// One agent's archive: a triplestore of what its journal kept for good, and how much of each entry the journal
/// still holds it took.
pub struct Archive {
    pub store: Engine,
    taken: Mutex<BTreeMap<String, usize>>,
}

impl Archive {
    /// An archive over `store`, or one in memory.
    pub fn new(store: Option<Engine>) -> Result<Self, Error> {
        Ok(Archive {
            store: match store {
                Some(store) => store,
                None => Engine::new().map_err(engine)?,
            },
            taken: Mutex::new(BTreeMap::new()),
        })
    }

    /// The archive on disk at `path`, tidied of what a journal once kept there for its window alone.
    #[cfg(feature = "volume")]
    pub fn open(path: &std::path::Path) -> Result<Self, Error> {
        let archive = Archive::new(Some(Engine::open(path).map_err(engine)?))?;
        let gone = archive.tidy()?;
        if gone > 0 {
            log::info!(
                "the archive at {} is tidied of {gone} entries no incident kept",
                path.display()
            );
        }
        Ok(archive)
    }

    /// Take out every line logged and activity no incident kept: a journal on disk held them there for its window,
    /// and an archive holds what lasts. How many.
    pub fn tidy(&self) -> Result<usize, Error> {
        let text = format!(
            "SELECT DISTINCT ?r WHERE {{ VALUES ?c {{ <{LOGGED}> <{ACTIVITY}> }} GRAPH ?r {{ ?r a ?c }} \
             FILTER NOT EXISTS {{ GRAPH ?r {{ ?r <{KEPT_BY}> ?any }} }} }}"
        );
        let mut gone = Vec::new();
        if let QueryResults::Solutions(solutions) = SparqlEvaluator::new()
            .parse_query(&text)
            .map_err(engine)?
            .on_store(&self.store)
            .execute()
            .map_err(engine)?
        {
            for solution in solutions {
                if let Some(oxigraph::model::Term::NamedNode(r)) = solution.map_err(engine)?.get("r") {
                    gone.push(r.clone());
                }
            }
        }
        for graph in &gone {
            self.store.remove_named_graph(graph).map_err(engine)?;
        }
        Ok(gone.len())
    }

    /// TAKE WHAT LASTS out of `journal`: each entry not yet taken as it stands is written here, whole, and each the
    /// journal needs no more is forgotten there. How many were written.
    pub fn take(&self, journal: &Journal) -> Result<usize, Error> {
        let mut taken = self.taken.lock().unwrap();
        let mut wrote = 0;
        for lasting in journal.lasting()? {
            let name = lasting.entry.as_str().to_string();
            let before = taken.get(&name).copied();
            if before != Some(lasting.quads.len()) {
                if before.is_some() {
                    self.store.remove_named_graph(&lasting.entry).map_err(engine)?;
                }
                let size = lasting.quads.len();
                self.store.extend(lasting.quads).map_err(engine)?;
                taken.insert(name.clone(), size);
                wrote += 1;
            }
            if !lasting.needed {
                journal.forget(&lasting.entry)?;
                taken.remove(&name);
            }
        }
        Ok(wrote)
    }

    /// Whether the archive holds the entry `entry`.
    pub fn holds(&self, entry: &NamedNode) -> bool {
        self.store.contains_named_graph(entry).unwrap_or(false)
    }

    /// What is written reaches the disk, where the store is on one.
    pub fn flush(&self) {
        #[cfg(feature = "volume")]
        let _ = self.store.flush();
    }
}

/// What archives: the archive written and how often, the journal read being the one the journal's package keeps.
/// Provided by a test that reads it; a deployed agent is handed none and the package opens its own.
pub struct Archives {
    pub archive: Arc<Archive>,
    /// How often, in the agent's seconds: none, and as often as the recorder's role says.
    pub every_s: Option<f64>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use orexis::rdf::{mint, node, text, typed};
    use oxigraph::model::Triple;
    use oxsdatatypes::DateTime;

    fn at(s: &str) -> DateTime {
        orexis::clock::instant(s).unwrap()
    }

    fn journal(now: &'static str) -> Journal {
        Journal::new(600.0, Arc::new(move || at(now))).unwrap()
    }

    fn graphs(store: &Engine) -> usize {
        store.named_graphs().count()
    }

    const HAPPENED: &str = "http://example.org/test#Happened";

    /// An event is the archive's once taken, and the journal's no more; a log no incident kept is never taken.
    #[test]
    fn an_event_is_taken_and_forgotten_and_the_log_no_incident_kept_stays_the_journals() {
        let journal = journal("2026-01-01T12:00:00+00:00");
        let archive = Archive::new(None).unwrap();
        let event = mint();
        journal
            .record(&event, vec![typed(event.clone(), HAPPENED)], None, false)
            .unwrap();
        let said = journal.remark("planning", log::Level::Info, "a plan", None).unwrap();
        assert_eq!(archive.take(&journal).unwrap(), 1);
        assert!(archive.holds(&event) && !archive.holds(&said));
        assert!(
            !journal.store.contains_named_graph(&event).unwrap(),
            "the journal forgot the event"
        );
        assert!(journal.store.contains_named_graph(&said).unwrap(), "and keeps its log");
        assert_eq!(archive.take(&journal).unwrap(), 0, "nothing is taken twice");
        assert_eq!(graphs(&archive.store), 1);
    }

    /// What an incident kept is taken while the journal still needs it, taken again whole where it changed, and
    /// forgotten by the journal once the window has passed it.
    #[test]
    fn what_an_incident_kept_is_taken_at_once_again_where_it_changed_and_forgotten_past_the_window() {
        let journal = journal("2026-01-01T12:00:00+00:00");
        let archive = Archive::new(None).unwrap();
        let before = journal
            .remark(
                "planning",
                log::Level::Info,
                "just before",
                Some(at("2026-01-01T11:58:00+00:00")),
            )
            .unwrap();
        let failed = journal
            .remark(
                "execution",
                log::Level::Warn,
                "a step did not land",
                Some(at("2026-01-01T11:59:00+00:00")),
            )
            .unwrap();
        assert_eq!(archive.take(&journal).unwrap(), 2);
        assert!(archive.holds(&before) && archive.holds(&failed));
        assert!(
            journal.store.contains_named_graph(&before).unwrap(),
            "inside the window the journal keeps it"
        );
        journal
            .add(
                &before,
                vec![Triple::new(
                    before.clone(),
                    node("http://example.org/test#noted"),
                    text("later"),
                )],
            )
            .unwrap();
        assert_eq!(archive.take(&journal).unwrap(), 1, "the one that changed");
        let size = |store: &Engine| {
            store
                .quads_for_pattern(None, None, None, Some((&before).into()))
                .count()
        };
        assert_eq!(size(&archive.store), size(&journal.store), "whole, and once");

        //  The window passes: a journal standing an hour on needs neither any more.
        let later = Journal::new(600.0, Arc::new(|| at("2026-01-01T13:00:00+00:00"))).unwrap();
        for quad in journal.store.iter().map(Result::unwrap) {
            later.store.insert(&quad).unwrap();
        }
        archive.take(&later).unwrap();
        assert_eq!(graphs(&later.store), 0, "the journal forgot what the archive holds");
        assert_eq!(graphs(&archive.store), 2);
    }

    /// An archive opened over what a journal once kept on disk is tidied of the log no incident kept.
    #[test]
    fn an_archive_is_tidied_of_the_log_no_incident_kept() {
        let journal = journal("2026-01-01T12:00:00+00:00");
        let event = mint();
        journal
            .record(&event, vec![typed(event.clone(), HAPPENED)], None, false)
            .unwrap();
        journal.remark("planning", log::Level::Info, "a plan", None).unwrap();
        journal
            .remark("execution", log::Level::Warn, "a step did not land", None)
            .unwrap();
        let archive = Archive::new(Some(journal.store.clone())).unwrap();
        assert_eq!(archive.tidy().unwrap(), 0, "the incident kept the log before it");
        journal.remark("planning", log::Level::Info, "after", None).unwrap();
        assert_eq!(archive.tidy().unwrap(), 1);
        assert_eq!(graphs(&archive.store), 3);
    }
}
