//! AN ACTIVITY: what a package does over a stretch of time, begun by its policy, and said as two events that are PROV's
//! own, its `prov:Start` and its `prov:End` (packages-meet-by-events-policies-and-activities). A start's TRIGGERS are
//! what started it: the entities the event heard was about - the graph that changed, the step that fell due - and
//! that event, so every activity is traced to the process's start (`ProcessStarted`); an event triggers no event.
//! Where it runs is not its question; what it is, is a class its package declares beneath
//! `prov:Activity`.
//!
//! Neither event states journal triples: a planning begins and a walk every second, and kept for good they would be
//! most of a journal. They reach the watch, where `orexis-journal/` hears them and keeps each activity ended as one entry
//! for the journal's window. AND WHAT A TURN WROTE IS SAID OF THE ACTIVITY THAT WROTE IT (`Wrote`), since a graph
//! written is what starts whoever hears its kind, and nothing else says whose it was.

use std::time::Instant;

use oxigraph::model::{NamedNode, Term};
use oxsdatatypes::DateTime;

use crate::events::Event;

use crate::rdf::{mint, round6};

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
        Self::named(mint(), kind)
    }

    /// An activity of `kind` beginning now, under the name `node` it was given before it began.
    pub fn named(node: NamedNode, kind: &'static str) -> Self {
        Activity {
            node,
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
/// begun and ended by the kernel: the activity it is part of, and what it is about, each under the predicate that says
/// its part. It is open beside a task's turns, never one a turn's activity is begun inside, so it names its own.
#[derive(Clone, Debug, PartialEq)]
pub struct Lasting {
    pub part_of: Option<NamedNode>,
    pub about: Vec<(&'static str, Term)>,
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

/// THE PROCESS STARTED: the one event nothing in the agent caused, said by the kernel before anything else, and what
/// the agent's booting is started by - so every activity the agent ever does is reached from it, through what each
/// was started by and what each is part of.
#[derive(Clone, Debug, PartialEq)]
pub struct ProcessStarted {
    pub at: DateTime,
}

/// The process's start, an event of the kernel's.
pub const PROCESS_STARTED: &str = "http://example.org/orexis#ProcessStarted";

impl Event for ProcessStarted {
    fn statements(&self, node: &NamedNode) -> Option<Vec<oxigraph::model::Triple>> {
        Some(vec![crate::rdf::typed(node.clone(), PROCESS_STARTED)])
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(PROCESS_STARTED)
    }
}

/// The graphs a task's turn wrote, said of the activity it ended last: what generated them.
#[derive(Clone, Debug, PartialEq)]
pub struct Wrote {
    pub by: NamedNode,
    pub graphs: Vec<String>,
}

impl Event for Wrote {}
