//! WHAT THE EXECUTOR SAYS HAPPENED, as `agent/execution/events.py` declares it, to whoever watches the agent.
//!
//! A STEP IS HISTORY TWICE, each an event in the journal in execution's words: `execution:StepTaken` when the executor
//! records the act, and `execution:StepAnswered` at the landing verdict, `execution:landed` true where the present came
//! to hold what the step predicted, false where the patience ran out or the want it was kept below ended undone — and
//! then an `execution:StepFailed` too, beneath `orexis:Incident`. AN INTENTION ENDED is history too,
//! `execution:IntentionResolved`, and an `execution:IntentionFailed`, an incident, where it failed. A step's event names
//! the act (`execution:act`), an intention's the intention (`execution:intention`), and each carries what the agent
//! holds of them as it stands, copied, so the journal is read without the beliefs. On the metrics, a want's name is on
//! no point: the desire it was derived under is.

use oxigraph::model::vocab::xsd;
use oxigraph::model::{Literal, NamedNode, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::events::{Event, Mark, Number, boolean, node, triple, typed};

use crate::ontology::EXECUTION;

/// An intention ended, and a step recorded taken: each heard by whoever is above execution, by its class.
pub const INTENTION_RESOLVED: &str = "http://example.org/orexis/execution#IntentionResolved";
pub const STEP_TAKEN: &str = "http://example.org/orexis/execution#StepTaken";
/// A head about to be taken, asked of whoever is above execution: the head, and the instant it is taken at.
pub const TAKING: &str = "http://example.org/orexis/execution#Taking";
pub const HEAD: &str = "http://example.org/orexis/execution#head";
/// What an answer to a head asked says of it, beneath execution's walking trigger: blocked, or not.
pub const BLOCKED: &str = "http://example.org/orexis/execution#blocked";
pub const AT_TIME: &str = "http://www.w3.org/ns/prov#atTime";
const INTENTION_OF: &str = "http://example.org/orexis/execution#intention";
const ACT_OF: &str = "http://example.org/orexis/execution#act";

/// `iri` as what an event is about under `predicate`, where it is one.
fn named(predicate: &'static str, iri: Option<&String>) -> Vec<(&'static str, Term)> {
    iri.and_then(|i| NamedNode::new(i.as_str()).ok())
        .map(|n| (predicate, Term::NamedNode(n)))
        .into_iter()
        .collect()
}

fn term(name: &str) -> String {
    format!("{EXECUTION}{name}")
}

/// An intention ended: the want it pursued and how, by the desire the want was derived under.
#[derive(Clone, Debug, PartialEq)]
pub struct IntentionResolved {
    pub intention: String,
    pub want: Option<String>,
    pub outcome: String,
    pub desire: Option<String>,
    pub at: Option<DateTime>,
    pub said: Vec<Triple>,
}

impl Event for IntentionResolved {
    fn metric(&self) -> Option<&'static str> {
        Some("intention")
    }

    fn kind(&self) -> Option<&'static str> {
        Some(INTENTION_RESOLVED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        named(INTENTION_OF, Some(&self.intention))
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("outcome", Mark::Tag(Some(self.outcome.clone()))),
            ("desire", Mark::Tag(self.desire.clone())),
        ]
    }

    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![
            typed(entry.clone(), &term("IntentionResolved")),
            triple(entry.clone(), &term("intention"), node(&self.intention)),
        ];
        out.extend(self.said.iter().cloned());
        if self.outcome == "failed" {
            out.push(typed(entry.clone(), &term("IntentionFailed")));
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }
}

/// What a step's event carries of the step: its want, its desire, the action it fills and the act recorded of it,
/// with the triples the journal keeps.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct About {
    pub want: Option<String>,
    pub desire: Option<String>,
    pub action: Option<String>,
    pub act: Option<String>,
    pub said: Vec<Triple>,
}

fn about(entry: &NamedNode, about: &About) -> Vec<Triple> {
    let mut out: Vec<Triple> = about
        .act
        .iter()
        .map(|act| triple(entry.clone(), &term("act"), node(act)))
        .collect();
    out.extend(about.said.iter().cloned());
    out
}

/// A step taken — or not, where its taker failed — at `at`, recorded as an act.
#[derive(Clone, Debug, PartialEq)]
pub struct StepTaken {
    pub step: String,
    pub at: DateTime,
    pub taken: bool,
    pub about: About,
}

impl Event for StepTaken {
    fn metric(&self) -> Option<&'static str> {
        Some("act")
    }

    fn kind(&self) -> Option<&'static str> {
        Some(STEP_TAKEN)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        named(ACT_OF, self.about.act.as_ref())
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("action", Mark::Tag(self.about.action.clone())),
            ("desire", Mark::Tag(self.about.desire.clone())),
            ("taken", Mark::Flag(self.taken)),
        ]
    }

    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![typed(entry.clone(), &term("StepTaken"))];
        out.extend(about(entry, &self.about));
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// A head about to be taken at `at`, asked: no history, since what is kept is the act it becomes or the failure it
/// ends in, and heard by whoever judges a head by its class.
#[derive(Clone, Debug, PartialEq)]
pub struct Taking {
    pub step: String,
    pub at: DateTime,
}

impl Event for Taking {
    fn kind(&self) -> Option<&'static str> {
        Some(TAKING)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        let mut out = named(HEAD, Some(&self.step));
        out.push((
            AT_TIME,
            Term::Literal(Literal::new_typed_literal(self.at.to_string(), xsd::DATE_TIME)),
        ));
        out
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// The verdict on a taken step at `at`: landed or not, how late the world answered it in the agent's seconds, and
/// whether the patience ran out on it.
#[derive(Clone, Debug, PartialEq)]
pub struct StepAnswered {
    pub step: String,
    pub at: DateTime,
    pub landed: bool,
    pub late_s: Option<f64>,
    pub timed_out: bool,
    pub about: About,
}

impl Event for StepAnswered {
    fn metric(&self) -> Option<&'static str> {
        Some("landing")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("action", Mark::Tag(self.about.action.clone())),
            ("desire", Mark::Tag(self.about.desire.clone())),
            ("landed", Mark::Flag(self.landed)),
            ("late_s", Mark::Value(self.late_s)),
            ("timed_out", Mark::Flag(self.timed_out)),
        ]
    }

    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![
            typed(entry.clone(), &term("StepAnswered")),
            triple(entry.clone(), &term("landed"), boolean(self.landed)),
        ];
        out.extend(about(entry, &self.about));
        if !self.landed {
            out.push(typed(entry.clone(), &term("StepFailed")));
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// How many intentions stand after a walk.
#[derive(Clone, Debug, PartialEq)]
pub struct Walked {
    pub standing: Option<i64>,
}

impl Event for Walked {
    fn metric(&self) -> Option<&'static str> {
        Some("intentions")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![("standing", Mark::Level(self.standing.map(Number::Int)))]
    }
}
