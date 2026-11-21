//! WHAT BELIEF SAYS HAPPENED: a pass that revised, which whoever is above belief hears and the journal keeps, and
//! the revisions the belief base holds, which only the metrics hear. Said by the deliberator as a pass ends.

use oxigraph::model::{NamedNode, Term};

use orexis::events::{Event, Mark, Number};

use crate::ontology::{CHANGED, REVISED, REVISED_SOURCE};

/// A revision pass: the sources it revised or transitioned on, the agent's own state graphs the transitions they
/// triggered changed, how many it was handed, the rule executions it spent, how many it left cut short, and its
/// real seconds.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Revised {
    pub graphs: Vec<String>,
    pub changed: Vec<String>,
    pub sources: usize,
    pub executions: usize,
    pub cut: usize,
    pub duration_s: f64,
}

impl Event for Revised {
    fn metric(&self) -> Option<&'static str> {
        Some("revise")
    }

    fn kind(&self) -> Option<&'static str> {
        Some(REVISED)
    }

    /// Every source it revised or transitioned on (`belief:revised`) and every state of the agent's its transitions
    /// changed (`belief:changed`), in belief's own words: whoever hears it is above belief and reads them.
    fn about(&self) -> Vec<(&'static str, Term)> {
        let named = |p: &'static str, gs: &[String]| {
            gs.iter()
                .filter_map(|g| NamedNode::new(g.as_str()).ok())
                .map(move |n| (p, Term::NamedNode(n)))
                .collect::<Vec<_>>()
        };
        let mut about = named(REVISED_SOURCE, &self.graphs);
        about.extend(named(CHANGED, &self.changed));
        about
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("sources", Mark::Value(Some(self.sources as f64))),
            ("executions", Mark::Value(Some(self.executions as f64))),
            ("cut", Mark::Value(Some(self.cut as f64))),
            ("duration_s", Mark::Value(Some(self.duration_s))),
        ]
    }
}

/// The revisions the belief base holds, and how many a budget cut short — settled false, which the
/// next pass continues. A revision unsettled window after window is a rule set that never settles.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct RevisionsHeld {
    pub revisions: i64,
    pub unsettled: i64,
}

impl Event for RevisionsHeld {
    fn metric(&self) -> Option<&'static str> {
        Some("revisions")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("revisions", Mark::Level(Some(Number::Int(self.revisions)))),
            ("unsettled", Mark::Level(Some(Number::Int(self.unsettled)))),
        ]
    }
}
