//! What every world's test does of a running agent: its clock on Tokio's paused time, which runs ahead whenever every
//! task is idle, and the three waits a scenario is made of - until everything said was handled, until a stretch of
//! the agent's time has passed, and until nothing holds the agent.
#![allow(dead_code)]

use std::sync::Arc;
use std::time::Duration;

use oxsdatatypes::DateTime;

use orexis::clock::Elapsing;
use orexis::task::{Running, UNFINISHED};

/// The agent's clock from `at`, on Tokio's time.
pub fn clock(at: DateTime) -> Arc<Elapsing> {
    Arc::new(Elapsing::from(at))
}

/// Until everything said so far was heard and done with.
pub async fn settled(running: &Running) {
    running.settled().await.unwrap();
}

/// Let `seconds` of the agent's time pass, the agent doing whatever falls due in them.
pub async fn pass(running: &Running, seconds: f64) {
    tokio::time::sleep(Duration::from_secs_f64(seconds)).await;
    //  WHAT FALLS DUE AT THE VERY INSTANT THE STRETCH ENDS is the agent's to do before the test looks: its tasks'
    //  sleeps ended with this one, and each is let run.
    for _ in 0..8 {
        tokio::task::yield_now().await;
    }
    running.settled().await.unwrap();
}

/// Until every agent of a society has settled: what one tells another wakes it, so they are waited for in turn until
/// a round finds them all at rest.
pub async fn settled_all(society: &[Running]) {
    loop {
        let mut busy = false;
        for running in society {
            busy |= !running.idle();
            running.settled().await.unwrap();
        }
        if !busy {
            break;
        }
    }
}

/// Let `seconds` of the society's one time pass, each agent doing whatever falls due in them.
pub async fn pass_all(society: &[Running], seconds: f64) {
    tokio::time::sleep(Duration::from_secs_f64(seconds)).await;
    for _ in 0..8 {
        tokio::task::yield_now().await;
    }
    settled_all(society).await;
}

/// How the run ends within `seconds` of the agent's time: as the last to let go said, or `unfinished` where something
/// still holds it then.
pub async fn outcome(running: &Running, seconds: u64) -> String {
    match tokio::time::timeout(Duration::from_secs(seconds), running.released()).await {
        Ok(outcome) => outcome.unwrap(),
        Err(_) => UNFINISHED.to_string(),
    }
}

struct Stderr;

impl log::Log for Stderr {
    fn enabled(&self, _: &log::Metadata) -> bool {
        true
    }
    fn log(&self, record: &log::Record) {
        eprintln!("LOG {} {}", record.level(), record.args());
    }
    fn flush(&self) {}
}

/// Say what the agent logs on stderr, for a test being looked into.
pub fn logged() {
    static LOGGER: Stderr = Stderr;
    let _ = log::set_logger(&LOGGER);
    log::set_max_level(log::LevelFilter::Debug);
}

/// THE SELF PLAYS A METER, said in its self graph: a world whose agent plays none is metered by a test that hands it a
/// window, and the metrics run where the self plays their role, as every package does.
#[allow(dead_code)]
pub fn metered(store: &orexis::store::Store) {
    let selves = store
        .graphs_of(&[orexis::ontology::SELF_GRAPH], &orexis::store::Within::default())
        .unwrap();
    store
        .update(&format!(
            "PREFIX metrics: <http://example.org/orexis/metrics#>
             PREFIX orexis: <http://example.org/orexis#>
             INSERT {{ GRAPH <{g}> {{ ?me orexis:plays [ a metrics:Meter ] }} }} \
             WHERE {{ GRAPH <{g}> {{ ?me a orexis:Self }} }}",
            g = selves[0]
        ))
        .unwrap();
}

/// THE TRACE FROM THE PROCESS'S START, read off a journal: which activities it keeps are not reached from the one
/// event nothing in the agent caused, and which classes of event were said within a package's running for want of
/// an activity of their own. An activity is reached where something that started it is - an event or a graph a
/// reached activity generated, or the end of one - and, WHERE IT NAMES NOTHING THAT STARTED IT, where the activity it
/// is part of is: begun by the clock or with its package, it is its part and no more. One that names what started it
/// and is reached through none of it has a cause the journal does not know.
#[allow(dead_code)]
pub fn traced(journal: &oxigraph::store::Store) -> (Vec<String>, Vec<String>) {
    use std::collections::{BTreeMap, BTreeSet};
    const TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
    const ACTIVITY: &str = "http://www.w3.org/ns/prov#Activity";
    const STARTED_BY: &str = "http://www.w3.org/ns/prov#wasStartedBy";
    const GENERATED_BY: &str = "http://www.w3.org/ns/prov#wasGeneratedBy";
    const QUALIFIED_END: &str = "http://www.w3.org/ns/prov#qualifiedEnd";
    const PART_OF: &str = "http://purl.org/dc/terms/isPartOf";
    const STARTED: &str = "http://example.org/orexis#ProcessStarted";
    const RUNNING: &str = "http://example.org/orexis#PackageRunning";
    let mut kinds: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut from: Vec<(String, String)> = Vec::new();
    let mut generated: Vec<(String, String)> = Vec::new();
    let mut parts: Vec<(String, String)> = Vec::new();
    let mut triggered: BTreeSet<String> = BTreeSet::new();
    for quad in journal.quads_for_pattern(None, None, None, None) {
        let quad = quad.unwrap();
        let (oxigraph::model::NamedOrBlankNode::NamedNode(s), oxigraph::model::Term::NamedNode(o)) =
            (&quad.subject, &quad.object)
        else {
            continue;
        };
        let (s, o) = (s.as_str().to_string(), o.as_str().to_string());
        match quad.predicate.as_str() {
            TYPE => {
                kinds.entry(s).or_default().insert(o);
            }
            //  WHAT REACHES WHAT: the second is reached where the first is.
            STARTED_BY => {
                triggered.insert(s.clone());
                from.push((o, s));
            }
            PART_OF => parts.push((o, s)),
            GENERATED_BY => {
                generated.push((s.clone(), o.clone()));
                from.push((o, s));
            }
            QUALIFIED_END => from.push((s, o)),
            _ => {}
        }
    }
    from.extend(parts.into_iter().filter(|(_, part)| !triggered.contains(part)));
    let is = |node: &str, kind: &str| kinds.get(node).is_some_and(|k| k.contains(kind));
    let mut reached: BTreeSet<String> = kinds.keys().filter(|n| is(n, STARTED)).cloned().collect();
    loop {
        let more: Vec<String> = from
            .iter()
            .filter(|(a, b)| reached.contains(a) && !reached.contains(b))
            .map(|(_, b)| b.clone())
            .collect();
        if more.is_empty() {
            break;
        }
        reached.extend(more);
    }
    let named = |node: &str| {
        let kind = kinds[node].iter().find(|k| k.as_str() != ACTIVITY).cloned();
        kind.unwrap_or_else(|| node.to_string())
    };
    //  AN ACTIVITY UNREACHED IS SAID WITH WHAT IT NAMES AS HAVING STARTED IT, each by its class where it has one.
    let unreached: BTreeSet<String> = kinds
        .keys()
        .filter(|n| is(n, ACTIVITY) && !reached.contains(*n))
        .map(|n| {
            let by: BTreeSet<String> = from
                .iter()
                .filter(|(_, b)| b == n)
                .map(|(a, _)| if kinds.contains_key(a) { named(a) } else { a.clone() })
                .collect();
            format!(
                "{} started by {}",
                named(n),
                by.into_iter().collect::<Vec<_>>().join(", ")
            )
        })
        .collect();
    let fell_back: BTreeSet<String> = generated
        .iter()
        .filter(|(said, by)| is(by, RUNNING) && kinds.contains_key(said))
        .map(|(said, _)| named(said))
        .collect();
    (unreached.into_iter().collect(), fell_back.into_iter().collect())
}

/// A journal for a walk held to its trace: nothing is swept from it while the walk lasts.
#[allow(dead_code)]
pub fn journal(now: impl Fn() -> DateTime + Send + Sync + 'static) -> Arc<orexis_journal::journal::Journal> {
    Arc::new(orexis_journal::journal::Journal::new(1.0e9, Arc::new(now)).unwrap())
}

/// EVERY ACTIVITY THE JOURNAL KEEPS IS TRACED TO THE PROCESS'S START, and nothing was said within a package's running
/// for want of an activity of its own: what a walk of `who` is held to.
#[allow(dead_code)]
pub fn traced_whole(journal: &orexis_journal::journal::Journal, who: &str) {
    let (unreached, fell_back) = traced(&journal.store);
    assert!(
        unreached.is_empty(),
        "{who}: activities whose cause the journal does not know: {unreached:#?}"
    );
    assert!(
        fell_back.is_empty(),
        "{who}: said within a package's running, for want of an activity of its own: {fell_back:#?}"
    );
}
