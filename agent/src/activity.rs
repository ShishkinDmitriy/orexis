//! AN ACTIVITY: what a package does over a stretch of time, begun by its policy for the events that triggered it, and
//! said as two events of the kernel's, its start and its end (packages-meet-by-events-policies-and-activities). Where it
//! runs is not its question; what it is, is a class its package declares beneath `prov:Activity`.
//!
//! Neither event states journal triples yet: a pass begins planning and a walk every second, and kept for good they
//! would be most of a journal. They reach the watch, where a tracer hears them as spans (#1119).

use std::time::Instant;

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use crate::events::{Event, mint, round6};

/// An activity's start, an instant: the event `orexis:Started`.
pub const STARTED: &str = "http://example.org/orexis#Started";
/// An activity's end, an instant: the event `orexis:Ended`.
pub const ENDED: &str = "http://example.org/orexis#Ended";

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

/// An activity started at `at`, by every event in `triggered_by`.
#[derive(Clone, Debug, PartialEq)]
pub struct Started {
    pub activity: NamedNode,
    pub kind: &'static str,
    pub triggered_by: Vec<NamedNode>,
    pub at: DateTime,
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
}

/// An activity ended at `at`, having taken `duration_s` real seconds.
#[derive(Clone, Debug, PartialEq)]
pub struct Ended {
    pub activity: NamedNode,
    pub kind: &'static str,
    pub at: DateTime,
    pub duration_s: f64,
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
}
