//! WHAT A PACKAGE SAYS HAPPENED, as `agent/lifecycle.py`'s `Signal` carries it and `agent/metrics/model.py` marks it:
//! ONE EVENT, an instance of a type the package declares beside it, said whole, so whoever hears it asks nobody.
//!
//! A PART LINKS TO ANOTHER BY SHARING ITS OBJECT in Rust (the binary links the parts), so what one package acts on of
//! another's work is no event here; an event is what WATCHES the agent hears — the history part, which writes each
//! event that is a point to the series and each that states triples to the journal, and the metrics part, which
//! tallies each its type reports. Both hear every event, as the Python parts connect to every signal, so one `Watch`
//! per agent is what a Python signal's `connected` asked: an emitter whose event costs something to make asks
//! `connected` first and makes nothing where nobody watches.
//!
//! AN EVENT IS REPORTED WHERE IT NAMES A `metric` and marks its fields (`Mark`): a TAG, a string with few values by
//! which the window's tallies are kept apart — never an IRI, since a want is minted per instance; a VALUE, a number
//! aggregated as its sum, mean and max; a FLAG, a truth counted where raised; a LEVEL, a figure that IS the state now,
//! written as it last stood. An event marking values or flags, or tags alone, is COUNTED. A duration is real time,
//! never the agent's (`Laps`).

use std::any::Any;
use std::collections::BTreeMap;
use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use oxigraph::model::vocab::xsd;
use oxigraph::model::{Literal, NamedNode, NamedOrBlankNode, Term, Triple};
use oxsdatatypes::DateTime;

use crate::clock::isoformat;

pub const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// A figure that is the state now, in the type it was said in: a count an integer, a measure a float.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Number {
    Int(i64),
    Float(f64),
}

/// How a field of an event is reported, with what it holds.
#[derive(Clone, Debug, PartialEq)]
pub enum Mark {
    Tag(Option<String>),
    Value(Option<f64>),
    Flag(bool),
    Level(Option<Number>),
}

/// A field of a point, as the series store keeps it.
#[derive(Clone, Debug, PartialEq)]
pub enum Field {
    Float(f64),
    Int(i64),
    Bool(bool),
    Text(String),
}

/// A point of a series: its measurement, its tags, its fields and its instant.
#[derive(Clone, Debug, PartialEq)]
pub struct Point {
    pub measurement: String,
    pub tags: BTreeMap<String, String>,
    pub fields: BTreeMap<String, Field>,
    pub time: Option<DateTime>,
}

/// One thing a package says happened. Every method has its default, so an event says only what it is.
pub trait Event: Any {
    /// The measurement it is reported under, where it is reported.
    fn metric(&self) -> Option<&'static str> {
        None
    }

    /// Every field it reports, in field order, with how.
    fn marks(&self) -> Vec<(&'static str, Mark)> {
        Vec::new()
    }

    /// The triples it states in the journal of the entry `node`, where it is history.
    fn statements(&self, _node: &NamedNode) -> Option<Vec<Triple>> {
        None
    }

    /// The instant it happened at, where it says one.
    fn at(&self) -> Option<DateTime> {
        None
    }

    /// The class it is an instance of, for a part hearing events by class: None where nothing may hear it so.
    fn kind(&self) -> Option<&'static str> {
        None
    }

    /// The activity it starts or ends, and that activity's class, where it is a start or an end.
    fn activity(&self) -> Option<(&NamedNode, &'static str)> {
        None
    }

    /// What it is about, each under the predicate that says its part, in the words of whoever hears it: a plan
    /// published names the plan an intention would adopt and the want it pursues. Names, never facts to act on — a
    /// policy reads what holds now from the beliefs.
    fn about(&self) -> Vec<(&'static str, Term)> {
        Vec::new()
    }
}

/// Whether an event marking `marks` is counted: it marks values or flags, or tags alone.
pub fn counted(marks: &[(&'static str, Mark)]) -> bool {
    let valued = marks.iter().any(|(_, m)| matches!(m, Mark::Value(_) | Mark::Flag(_)));
    let tags = !marks.is_empty() && marks.iter().all(|(_, m)| matches!(m, Mark::Tag(_)));
    valued || tags
}

type Hearer = Arc<dyn Fn(&dyn Event, &NamedNode) + Send + Sync>;

/// Whoever watches one agent: every event its parts say, named as it is said and heard by each hearer connected, at
/// once, on the thread of the part that said it, so the journal keeps it and a later event names it by one IRI —
/// and the instant the pass stands at, which the runtime says as each pass begins, for an event said by a part that
/// is handed no pass, so nothing reads the clock for it.
#[derive(Clone, Default)]
pub struct Watch(Arc<Mutex<Vec<Hearer>>>, Arc<Mutex<Option<DateTime>>>);

impl Watch {
    /// The instant the pass in progress stands at.
    pub fn at(&self) -> Option<DateTime> {
        *self.1.lock().expect("an instant nobody poisoned")
    }

    /// Say the instant the pass stands at.
    pub fn stand(&self, at: DateTime) {
        *self.1.lock().expect("an instant nobody poisoned") = Some(at);
    }

    /// Call `hearer` with every event said from here on, and the name it was said under.
    pub fn connect(&self, hearer: impl Fn(&dyn Event, &NamedNode) + Send + Sync + 'static) {
        self.0.lock().expect("hearers nobody poisoned").push(Arc::new(hearer));
    }

    /// Whether anybody watches.
    pub fn connected(&self) -> bool {
        !self.0.lock().expect("hearers nobody poisoned").is_empty()
    }

    /// Say `event` to every hearer, under a name minted for it: the name, where anybody heard.
    pub fn emit(&self, event: &dyn Event) -> Option<NamedNode> {
        let hearers: Vec<Hearer> = self.0.lock().expect("hearers nobody poisoned").clone();
        if hearers.is_empty() {
            return None;
        }
        let named = mint();
        for hearer in hearers {
            hearer(event, &named);
        }
        Some(named)
    }
}

impl std::fmt::Debug for Watch {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Watch({} connected)", self.0.lock().map(|h| h.len()).unwrap_or(0))
    }
}

/// Real seconds spent per part of something, each lap from the last, as `<part>_s` — by the process's monotonic clock
/// and never the agent's, which may run fast or tick per read.
#[derive(Clone, Debug)]
pub struct Laps {
    pub spent: Vec<(String, f64)>,
    mark: Instant,
}

impl Default for Laps {
    fn default() -> Self {
        Laps {
            spent: Vec::new(),
            mark: Instant::now(),
        }
    }
}

impl Laps {
    /// Laps from `mark`, where what they are of began before they were asked for.
    pub fn since(mark: Instant) -> Self {
        Laps {
            spent: Vec::new(),
            mark,
        }
    }

    /// The end of `part`: the seconds since the last mark added to it.
    pub fn lap(&mut self, part: &str) {
        let now = Instant::now();
        let took = now.duration_since(self.mark).as_secs_f64();
        let name = format!("{part}_s");
        match self.spent.iter_mut().find(|(n, _)| *n == name) {
            Some((_, s)) => *s = round6(*s + took),
            None => self.spent.push((name, round6(took))),
        }
        self.mark = now;
    }

    /// The seconds spent on `part`, where it was marked.
    pub fn of(&self, part: &str) -> Option<f64> {
        let name = format!("{part}_s");
        self.spent.iter().find(|(n, _)| *n == name).map(|(_, s)| *s)
    }
}

/// A figure rounded to six places, as every derived number here is written.
pub fn round6(x: f64) -> f64 {
    (x * 1e6).round() / 1e6
}

/// A name for a journal entry: a UUID's URN, unique across every agent's journal.
pub fn mint() -> NamedNode {
    static COUNT: AtomicU64 = AtomicU64::new(0);
    let state = RandomState::new();
    let mut high = state.build_hasher();
    high.write_u64(COUNT.fetch_add(1, Ordering::Relaxed));
    let mut low = RandomState::new().build_hasher();
    low.write_u128(Instant::now().elapsed().as_nanos() ^ u128::from(high.finish()));
    let (a, b) = (high.finish(), low.finish());
    //  A VERSION-4 UUID's shape: the version nibble 4 and the variant bits 10.
    let a = (a & 0xffff_ffff_ffff_0fff) | 0x0000_0000_0000_4000;
    let b = (b & 0x3fff_ffff_ffff_ffff) | 0x8000_0000_0000_0000;
    NamedNode::new_unchecked(format!(
        "urn:uuid:{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        a >> 32,
        (a >> 16) & 0xffff,
        a & 0xffff,
        b >> 48,
        b & 0xffff_ffff_ffff
    ))
}

/// An IRI as a node.
pub fn node(iri: &str) -> NamedNode {
    NamedNode::new_unchecked(iri)
}

/// A triple of `subject`, `predicate` and `object`.
pub fn triple(subject: impl Into<NamedOrBlankNode>, predicate: &str, object: impl Into<Term>) -> Triple {
    Triple::new(subject, node(predicate), object)
}

/// `subject` a `class`.
pub fn typed(subject: impl Into<NamedOrBlankNode>, class: &str) -> Triple {
    triple(subject, RDF_TYPE, node(class))
}

/// An instant as the journal writes it: an `xsd:dateTime`, with its zone, spelled as the Python kernel spells it.
pub fn instant(at: DateTime) -> Literal {
    Literal::new_typed_literal(isoformat(at), xsd::DATE_TIME)
}

/// A truth as the literal it is.
pub fn boolean(value: bool) -> Literal {
    Literal::new_typed_literal(if value { "true" } else { "false" }, xsd::BOOLEAN)
}

/// An integer as the literal it is.
pub fn integer(value: i64) -> Literal {
    Literal::new_typed_literal(value.to_string(), xsd::INTEGER)
}

/// A text as the literal it is.
pub fn text(value: &str) -> Literal {
    Literal::new_simple_literal(value)
}

/// A float spelled as Python's `repr` spells it: `3.0` and not `3`, `0.1` and not `0.1000…`.
pub fn repr(value: f64) -> String {
    if value.is_finite() && value == value.trunc() && value.abs() < 1e16 {
        format!("{value:.1}")
    } else {
        format!("{value}")
    }
}

/// A double as the literal it is.
pub fn double(value: f64) -> Literal {
    Literal::new_typed_literal(repr(value), xsd::DOUBLE)
}

/// A downcast of `event` to the type it is, for a test reading what was said.
pub fn as_of<T: Event>(event: &dyn Event) -> Option<&T> {
    (event as &dyn Any).downcast_ref::<T>()
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Counted;
    impl Event for Counted {
        fn metric(&self) -> Option<&'static str> {
            Some("counted")
        }
        fn marks(&self) -> Vec<(&'static str, Mark)> {
            vec![("desire", Mark::Tag(None)), ("spent", Mark::Value(Some(2.0)))]
        }
    }

    #[test]
    fn an_event_marking_values_or_tags_alone_is_counted_and_a_report_of_state_is_not() {
        assert!(counted(&Counted.marks()));
        assert!(counted(&[("outcome", Mark::Tag(None))]));
        assert!(!counted(&[("scope", Mark::Tag(None)), ("worlds", Mark::Level(None))]));
        assert!(!counted(&[]));
    }

    #[test]
    fn a_watch_hears_what_is_said_where_anybody_connected_and_says_so() {
        let watch = Watch::default();
        assert!(!watch.connected());
        let heard = Arc::new(Mutex::new(Vec::new()));
        let kept = heard.clone();
        watch.connect(move |e, named| kept.lock().unwrap().push((e.metric(), named.clone())));
        assert!(watch.connected());
        let named = watch.emit(&Counted).expect("somebody heard");
        assert_eq!(*heard.lock().unwrap(), [(Some("counted"), named)]);
        assert!(as_of::<Counted>(&Counted).is_some());
    }

    #[test]
    fn an_entry_is_named_by_a_uuid_urn_and_never_twice() {
        let (a, b) = (mint(), mint());
        assert_ne!(a, b);
        let re = regex::Regex::new("^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
            .unwrap();
        assert!(re.is_match(a.as_str()), "{a}");
    }

    #[test]
    fn a_literal_is_spelled_as_the_python_journal_spells_it() {
        assert_eq!(double(3.0).value(), "3.0");
        assert_eq!(double(0.25).value(), "0.25");
        assert_eq!(integer(7).value(), "7");
        assert_eq!(boolean(false).value(), "false");
    }

    #[test]
    fn a_lap_is_from_the_last_mark_and_adds_to_its_part() {
        let mut laps = Laps::default();
        laps.lap("drain");
        laps.lap("plan");
        laps.lap("drain");
        assert_eq!(
            laps.spent.iter().map(|(n, _)| n.as_str()).collect::<Vec<_>>(),
            ["drain_s", "plan_s"]
        );
        assert!(laps.of("drain").is_some() && laps.of("execute").is_none());
    }
}
