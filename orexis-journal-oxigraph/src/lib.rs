//! THE JOURNAL'S ARCHIVE: the half of the pair that keeps house. `orexis-journal/` writes what happens into the
//! journal, in memory, as it is said; this takes what the journal keeps for good out of it into a triplestore on
//! disk, on a timer, and has the journal forget what it took. One crate does a thing and another keeps house, as
//! `orexis-sensing-influxdb/` does for sensing's readings and `orexis-journal-otlp/` for the activities.
//!
//! WHAT IS TAKEN is what lasts (`Journal::lasting`): each event, and each log record and activity an incident kept.
//! An entry is a named graph in the archive as it is in the journal, so a text reads either alike. The log and the
//! activities no incident kept are never taken: the journal sweeps them past its window.
//!
//! WHAT THE JOURNAL THEN FORGETS is an event at once, and a kept log record or activity once the window has passed
//! it: until then a later incident keeps it again, and what ships the activities reads it there. One that changes
//! after it was taken, an activity told the graphs it wrote, is taken again whole.
//!
//! WHEN: every `JOURNAL_ARCHIVE_INTERVAL_S` of the agent's seconds, two where the environment says nothing, where
//! anything was written; at once as an incident is kept; and once more as the run ends. So an agent killed outright
//! loses what it said in its last stretch, and one that stops, nothing.
//!
//! THE ARCHIVE IS WHAT A READER OF THE PAST IS HANDED: the endpoint's `/sparql`, a chat's journal tool and a stopped
//! agent's store opened read-only all read it, a stretch behind the journal at most.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

use oxigraph::model::NamedNode;
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;

use orexis::Error;
use orexis::task::{Handed, Package, Task};
use orexis_journal::Journal;
use orexis_journal::journal::{ACTIVITY, KEPT_BY, LOG_RECORD};

/// How often what lasts is archived, in the agent's seconds: the environment's to say.
pub const INTERVAL: &str = "JOURNAL_ARCHIVE_INTERVAL_S";
/// How often where the environment says nothing.
pub const INTERVAL_S: f64 = 2.0;

/// How often what lasts is archived: `JOURNAL_ARCHIVE_INTERVAL_S`, or two seconds.
pub fn interval(env: &dyn Fn(&str) -> Option<String>) -> f64 {
    env(INTERVAL)
        .and_then(|s| s.parse::<f64>().ok())
        .filter(|s| *s > 0.0)
        .unwrap_or(INTERVAL_S)
}

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

    /// Take out every log record and activity no incident kept: a journal on disk held them there for its window,
    /// and an archive holds what lasts. How many.
    pub fn tidy(&self) -> Result<usize, Error> {
        let text = format!(
            "SELECT DISTINCT ?r WHERE {{ VALUES ?c {{ <{LOG_RECORD}> <{ACTIVITY}> }} GRAPH ?r {{ ?r a ?c }} \
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

/// What archives: the journal read, the archive written and how often, handed outside by whoever runs the agent
/// where the deployment keeps an archive.
pub struct Archives {
    pub journal: Arc<Journal>,
    pub archive: Arc<Archive>,
    pub every_s: f64,
}

inventory::submit! { Package { name: "journal-oxigraph", documents: &[], start } }

/// WHERE THE RECORDER'S ARCHIVE IS: the path of the archive its role names (`journal:archivedIn`), as the world's
/// deployment states it, a `file:` url, or None where the role names none or the world says nothing of the one
/// named. The role says that there is one and the world where; no flag does.
pub fn archive(store: &orexis::store::Store) -> Result<Option<std::path::PathBuf>, Error> {
    Ok(orexis::boot::connected(store, WORDS, ARCHIVED_IN)?
        .and_then(|url| url.strip_prefix("file://").map(std::path::PathBuf::from)))
}

const WORDS: &str = "PREFIX journal: <http://example.org/orexis/journal#> ";
const ARCHIVED_IN: &str = "?role journal:archivedIn ?service . ?service a journal:Archive .";

/// ITS START, which every package this binary holds is given: it keeps house for the journal, so it joins where the
/// journal did AND THE RECORDER'S ROLE NAMES AN ARCHIVE the world says where to find, and where the role names none
/// its start ends there, and what lasts stays in the journal. Joined, it waits for the journal's start; handed a
/// journal and an archive, its task.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        let archived = |handed: &Handed| Ok(handed.joined("journal") && archive(&handed.store)?.is_some());
        if !handed.joins(archived).await? || !handed.started("journal").await {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    let Some(archives) = handed.outside.take::<Archives>() else {
        return Ok(None);
    };
    Ok(Some(Box::pin(task(handed.clone(), archives))))
}

/// THE ARCHIVER'S TASK: every stretch of the agent's time, or as an incident is kept, it takes what lasts where
/// anything was written, off the agent's threads, and once more as the run ends.
async fn task(handed: Handed, archives: Archives) -> Result<(), Error> {
    loop {
        let at = handed
            .clock
            .now()
            .checked_add_day_time_duration(orexis::clock::seconds(archives.every_s));
        let over = tokio::select! {
            biased;
            _ = handed.stopped() => true,
            _ = archives.journal.incident.notified() => false,
            _ = handed.sleep_until(at) => false,
        };
        if archives.journal.news() || over {
            let (journal, archive) = (archives.journal.clone(), archives.archive.clone());
            let took = tokio::task::spawn_blocking(move || archive.take(&journal)).await;
            match took {
                Ok(Ok(wrote)) => log::debug!("{}: {wrote} journal entries archived", handed.id),
                Ok(Err(e)) => {
                    archives.journal.renew();
                    log::warn!(
                        "{}: the archive refused the journal's entries, and they stay: {e}",
                        handed.id
                    );
                }
                Err(e) => {
                    archives.journal.renew();
                    log::warn!("{}: archiving the journal did not finish: {e}", handed.id);
                }
            }
        }
        if over {
            break;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use orexis::events::{mint, node, text, typed};
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

    #[test]
    fn the_interval_is_the_environments_and_two_seconds_where_it_says_nothing() {
        assert_eq!(interval(&|k| (k == INTERVAL).then(|| "30".to_string())), 30.0);
        assert_eq!(interval(&|_| None), INTERVAL_S);
        assert_eq!(interval(&|_| Some("nought".to_string())), INTERVAL_S);
    }
}
