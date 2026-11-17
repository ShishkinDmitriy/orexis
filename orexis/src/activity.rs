//! AN ACTIVITY: what a package does over a stretch of time, begun by its policy, and said as two events that are PROV's
//! own, its `prov:Start` and its `prov:End` (packages-meet-by-events-policies-and-activities). A start's TRIGGERS are
//! what PROV says they are, entities - the graph that changed, the step that fell due - and never the event heard, so
//! an event triggers no event. Where it runs is not its question; what it is, is a class its package declares beneath
//! `prov:Activity`.
//!
//! Neither event states journal triples: a planning begins and a walk every second, and kept for good they would be
//! most of a journal. They reach the watch, where `orexis-journal/` hears them and keeps each activity ended as one entry
//! for the journal's window. AND WHAT A TURN WROTE IS SAID OF THE ACTIVITY THAT WROTE IT (`Wrote`), since a graph
//! written is what starts whoever hears its kind, and nothing else says whose it was.

use std::time::Instant;

use oxigraph::model::{NamedNode, Term};
use oxsdatatypes::DateTime;

use crate::events::{Event, mint, round6};

/// An activity's start, an instant: PROV's.
pub const STARTED: &str = "http://www.w3.org/ns/prov#Start";
/// An activity's end, an instant: PROV's.
pub const ENDED: &str = "http://www.w3.org/ns/prov#End";

/// An activity begun and not yet ended: its name, its class, and when it began in real time.
#[derive(Debug)]
pub struct Activity {
    pub node: NamedNode,
    pub kind: &'static str,
    began: Instant,
}

impl Activity {
    /// An activity of `kind` beginning now, under a name of its own.
    pub fn begin(kind: &'static str) -> Self {
        Activity {
            node: mint(),
            kind,
            began: Instant::now(),
        }
    }

    /// The real seconds since it began.
    pub fn took(&self) -> f64 {
        round6(self.began.elapsed().as_secs_f64())
    }
}

/// AN ACTIVITY THAT LASTS ACROSS TURNS - the agent's booting, running and stopping, and each package's within them,
/// begun and ended by the kernel: the activity it is part of, what it is about, each under the predicate that says its
/// part, and when it began. Its start and its end each say it whole, so whoever hears only the end - the journal, made
/// inside the booting - keeps it all the same; and it is open beside a task's turns, never one a turn's activity is
/// begun inside.
#[derive(Clone, Debug, PartialEq)]
pub struct Lasting {
    pub part_of: Option<NamedNode>,
    pub about: Vec<(&'static str, Term)>,
    pub began: DateTime,
}

/// An activity started at `at`, by every entity in `triggers` (`prov:entity`).
#[derive(Clone, Debug, PartialEq)]
pub struct Started {
    pub activity: NamedNode,
    pub kind: &'static str,
    pub triggers: Vec<NamedNode>,
    pub at: DateTime,
    pub lasting: Option<Lasting>,
}

impl Event for Started {
    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(STARTED)
    }

    fn activity(&self) -> Option<(&NamedNode, &'static str)> {
        Some((&self.activity, self.kind))
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        self.lasting.as_ref().map(|l| l.about.clone()).unwrap_or_default()
    }
}

/// An activity ended at `at`, having taken `duration_s` real seconds.
#[derive(Clone, Debug, PartialEq)]
pub struct Ended {
    pub activity: NamedNode,
    pub kind: &'static str,
    pub at: DateTime,
    pub duration_s: f64,
    pub lasting: Option<Lasting>,
}

impl Event for Ended {
    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(ENDED)
    }

    fn activity(&self) -> Option<(&NamedNode, &'static str)> {
        Some((&self.activity, self.kind))
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        self.lasting.as_ref().map(|l| l.about.clone()).unwrap_or_default()
    }
}

/// The graphs a task's turn wrote, said of the activity it ended last: what generated them.
#[derive(Clone, Debug, PartialEq)]
pub struct Wrote {
    pub by: NamedNode,
    pub graphs: Vec<String>,
}

impl Event for Wrote {}
