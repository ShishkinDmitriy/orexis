//! SENSING, in Rust: the translation row of the agent stack, and nothing above it — ported from `orexis-sensing/`
//! and held to what its suite asks.
//!
//! - [`received`]: a transport hands it the bytes it read for a sensor, and a percept is written per reading,
//!   linked to the one before it — or, for a sensor reading a series, a forecast per stretch ahead;
//! - [`pipeline`]: bytes to a document by the codec, to a number by the pointer;
//! - [`cadence`]: how often a sensor reports, which sensors are the agent's, and which have lapsed;
//! - [`missed`]: which sensors have gone silent, computed and never written;
//! - `observer`: the package's core, the observer the self plays, which asks after silence and hands each percept to
//!   belief;
//! - [`events`]: what it says happened — each observation, a point of the history, and the sensors silent and doubted;
//! - the start, below the modules, and nothing else: the observer made, and the task that wakes it.
//!
//! The Python copy's `account`, sensing's word of itself for a person, is read by nothing, and is not ported.

use orexis::task::{Every, Handed, Package, Woke, sooner};

use crate::observer::{ASK, HEARD, OBSERVE};
use crate::ontology::{OBSERVATION_GRAPH, OBSERVER, OBSERVING_TRIGGER};

pub mod cadence;
pub mod events;
pub mod missed;
mod observer;
pub mod ontology;
pub mod past;
pub mod pipeline;
pub mod received;

pub use observer::Observer;

inventory::submit! { Package { name: "sensing", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl", "rules.ttl");

/// SENSING'S START, which every package this binary holds is given: it joins where the self plays an observer and
/// declines otherwise; joined, its observer is made and what a restart finds unrevised queued for the first ask;
/// it says it booted, and checked it ends there; otherwise what follows is ITS TASK, which waits for what it
/// hears, an arrival or the instant it is next due, and once nothing more waits to be heard asks what has fallen due.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[OBSERVER])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let mut observer = Observer::new(&handed.store)?;
        observer.watch = handed.events.watch().clone();
        observer.unrevised()?;
        let mut hears = handed.events.hears();
        hears.graph(OBSERVATION_GRAPH, HEARD);
        hears.event(OBSERVING_TRIGGER, OBSERVE);
        let mut arrived = handed.arrived();
        //  HOW OFTEN IT ASKS WHAT HAS FALLEN DUE is the observer's role's to say (`sensing:askedEveryS`).
        let mut timers = vec![(Every::new(observer.asked_every_s), ASK)];
        if !handed.booted().await? {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            match heard.take() {
                Some(Woke::Event(tag, event)) => {
                    let wrote = observer.heard_event(tag, &event, &mut turn);
                    turn.done(wrote)?;
                }
                Some(Woke::Graphs(tag, graphs)) => {
                    let wrote = observer.heard(tag, &graphs, &mut turn);
                    turn.done(wrote)?;
                }
                _ => {}
            }
            if hears.is_empty() {
                for (every, tag) in &mut timers {
                    if every.due(turn.now) {
                        let wrote = observer.run(*tag, &mut turn);
                        turn.done(wrote)?;
                    }
                }
                due = timers
                    .iter()
                    .fold(turn.next(), |soonest, (every, _)| sooner(soonest, every.at()));
            }
            heard = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => match woke {
                    Some(woke) => Some(woke),
                    None => break,
                },
                _ = arrived.wait() => None,
                _ = handed.sleep_until(due) => None,
            };
        }
        Ok(())
    })
}
