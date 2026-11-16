//! EXECUTION, in Rust: the intentions this agent is committed to, and what carries a commitment out — ported from
//! `orexis-execution/` and held to what its suite asks.
//!
//! - `executor`: the package's core, the executor the self plays: the intentions, adopted by reference from a plan
//!   published, walked step by step, each step held to what it predicts, and ended by the doors planning knocks at;
//! - `taker`: what carries a step out, its commands kept for a transport and its documents for speech;
//! - `implementation`: the operations taking a step does, read off the action's row;
//! - `events`: what it says happened — a step taken and answered, an intention resolved — to whoever watches;
//! - the start, below the modules, and nothing else: the executor made, and the task that wakes it.

use orexis::task::{Handed, Package, Woke};

use crate::events::HEAD_ASKED;
use crate::executor::{ADOPT, PASS, RESOLVE, REVISED, SUPERSEDE};
use crate::ontology::{ADOPTING_TRIGGER, COMMANDED, RESOLVING_TRIGGER, SUPERSEDING_TRIGGER, TOLD, WALKING_TRIGGER};

pub mod command;
pub mod events;
mod executor;
mod implementation;
pub mod ontology;
pub mod says;
mod taker;

pub use executor::{Executor, Said, Standing, Take};
pub use taker::{commanded, taker};

inventory::submit! { Package { name: "execution", documents: orexis::documents!("ontology.ttl"), start } }

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/execution#Executor";

/// EXECUTION'S START, which every package this binary holds is given: it joins where the self plays an executor and
/// declines otherwise; joined, its executor is made; checked, it ends there; otherwise it says it has started, and
/// what follows is ITS TASK, which asks who hears what it would say, then waits for an event beneath one of its
/// triggers or the instant it is next due, and once nothing more waits to be heard does the walk it queued, once,
/// and decides.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        let mut executor = Executor::new(&handed.store, &handed.id, None, None, handed.clock.clone())?;
        executor.watch = handed.events.watch().clone();
        let mut hears = handed.events.hears();
        hears.event(ADOPTING_TRIGGER, ADOPT);
        hears.event(SUPERSEDING_TRIGGER, SUPERSEDE);
        hears.event(RESOLVING_TRIGGER, RESOLVE);
        hears.event(WALKING_TRIGGER, REVISED);
        handed.started("execution").await;
        if handed.checking().is_some() {
            return Ok(());
        }
        //  WHO HEARS WHAT IT WOULD SAY, asked as the run begins, every package having started: a head is asked where
        //  somebody answers, a command kept and said where somebody sends it, a document where somebody says it.
        let events = &handed.events;
        executor.asks = events.heard(HEAD_ASKED);
        let (commands, says) = (events.heard(COMMANDED), events.heard(TOLD));
        if commands || says {
            let me = orexis::boot::selves(&handed.store)?
                .into_iter()
                .next()
                .unwrap_or_default();
            executor.take = Some(taker(
                handed.store.clone(),
                &me,
                handed.clock.clone(),
                events.watch().clone(),
                commands,
                says,
            ));
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            if let Some(Woke::Event(tag, event)) = heard.take() {
                let wrote = executor.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            if hears.is_empty() {
                let wrote = executor.queued(&mut turn);
                turn.done(wrote)?;
                let wrote = executor.run(PASS, &mut turn);
                turn.done(wrote)?;
                let wrote = executor.queued(&mut turn);
                turn.done(wrote)?;
                due = turn.next();
            }
            heard = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => match woke {
                    Some(woke) => Some(woke),
                    None => break,
                },
                _ = handed.sleep_until(due) => None,
            };
        }
        Ok(())
    })
}
