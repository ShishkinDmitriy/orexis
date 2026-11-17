//! COORDINATION, in Rust, ported from `orexis-coordination/`: two agents that want one resource ask each other what
//! their constraint reads, and a draw decides which goes first
//! (two-agents-that-want-one-resource-ask-each-other-and-draw-lots-for-it).
//!
//! - [`holdings`]: what the agent says of its own future under one constraint, read off its walking intentions;
//! - [`ask`]: the questions it says to the peers it believes in range; [`answer`]: what it says back, under a
//!   constraint it holds too, of what meets;
//! - [`conclude`]: what it concludes of its conflicts, and who won each draw, as the world's outcomes say;
//! - [`lay`]: what it lays of a peer's holdings as forecasts, as the draw says it yields;
//! - [`mint`]: the secret its draws' numbers come from;
//! - `coordinator`: the package's core, the coordinator the self plays and what it does of what it hears;
//! - the start, below the modules, and nothing else: the coordinator made, and the task that wakes it.
//!
//! - [`events`]: what it says happened — the holdings asked with, said and foreseen, and the conflicts concluded.
//!
//! It imports no code of planning, execution or speech, and meets them at the store and through whoever links them.

use orexis::task::{Every, Handed, Package, Woke, sooner};

use crate::coordinator::{ANSWERED, PASS, QUESTIONED};
use crate::ontology::{ANSWER_GRAPH, COORDINATING_TRIGGER, QUESTION_GRAPH};

pub mod answer;
pub mod ask;
pub mod conclude;
mod coordinator;
pub mod events;
pub mod holdings;
pub mod lay;
pub mod mint;
pub mod ontology;

pub use coordinator::Coordinator;

inventory::submit! { Package { name: "coordination", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/coordination#Coordinator";

/// COORDINATION'S START, which every package this binary holds is given: it joins where the self plays a coordinator
/// and declines otherwise; joined, its coordinator is made and its secret minted; it says it booted, and checked it ends there; otherwise
///  what follows is ITS TASK, which waits for what it hears, an arrival or the instant it is
/// next due, and once nothing more waits to be heard does what it queued for itself and what has fallen due.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let mut coordinator = Coordinator::new(&handed.store)?;
        coordinator.watch = handed.events.watch().clone();
        coordinator.mint()?;
        let mut hears = handed.events.hears();
        hears.graph(QUESTION_GRAPH, QUESTIONED);
        hears.graph(ANSWER_GRAPH, ANSWERED);
        hears.event(COORDINATING_TRIGGER, PASS);
        let mut arrived = handed.arrived();
        let mut timers = vec![(Every::new(0.0), PASS)];
        if !handed.booted().await? {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            match heard.take() {
                Some(Woke::Event(tag, event)) => {
                    let wrote = coordinator.heard_event(tag, &event, &mut turn);
                    turn.done(wrote)?;
                }
                Some(Woke::Graphs(tag, graphs)) => {
                    let wrote = coordinator.heard(tag, &graphs, &mut turn);
                    turn.done(wrote)?;
                }
                _ => {}
            }
            if hears.is_empty() {
                let wrote = coordinator.queued(&mut turn);
                turn.done(wrote)?;
                for (every, tag) in &mut timers {
                    if every.due(turn.now) {
                        let wrote = coordinator.run(*tag, &mut turn);
                        turn.done(wrote)?;
                        let wrote = coordinator.queued(&mut turn);
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
