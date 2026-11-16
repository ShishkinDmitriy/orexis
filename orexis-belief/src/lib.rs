//! BELIEF, in Rust, ported from `orexis-belief/`:
//!
//! - [`transition`]: rules that change a state rather than conclude of it, and the one machine that applies them,
//!   which planning applies an action's effect by;
//! - `revise`: what the rules conclude of one graph, its revisions;
//! - `trigger`: the transitions an arrival of testimony triggers, applied to the agent's own state;
//! - `deliberator`: the package's core, the pass that sequences the two over what was written, within a budget, and
//!   what it revises as the package starts and on what it hears;
//! - `events`: what belief says happened, a pass that revised and the revisions held;
//! - the start, below the modules, and nothing else: the deliberator made, and the task that wakes it.

use orexis::ontology::BELIEF;
use orexis::task::{Handed, Package, Woke};

use crate::ontology::REVISING_TRIGGER;

mod deliberator;
mod events;
pub mod ontology;
mod revise;
pub mod transition;
mod trigger;

pub use deliberator::Deliberator;
pub use events::Revised;

const HEARD: usize = 0;
const REVISE: usize = 1;

inventory::submit! { Package { name: "belief", documents: orexis::documents!("ontology.ttl"), start } }

/// BELIEF'S START, which every package this binary holds is given: it joins where the self plays a deliberator and
/// declines otherwise; joined, its deliberator is made and what the world authored as the agent's state revised,
/// once; checked, it ends there; otherwise it says it has started, and what follows is ITS TASK, which waits for a belief written or an event beneath
/// its trigger, and revises.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[crate::ontology::DELIBERATOR]).await? {
            return Ok(());
        }
        let mut deliberator = Deliberator::new(&handed.store)?;
        deliberator.watch = handed.events.watch().clone();
        deliberator.unrevised(handed.clock.now())?;
        let mut hears = handed.events.hears();
        hears.graph(BELIEF, HEARD);
        hears.event(REVISING_TRIGGER, REVISE);
        if handed.checking().is_some() {
            return Ok(());
        }
        handed.started().await;
        loop {
            let woke = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => woke,
            };
            let Some(woke) = woke else { break };
            let mut turn = handed.turn();
            let wrote = match woke {
                Woke::Graphs(_, graphs) => deliberator.revising(&graphs, BELIEF, &mut turn).map(|()| Vec::new()),
                Woke::Event(_, event) => deliberator.heard_event(&event, &mut turn),
            };
            turn.done(wrote)?;
        }
        Ok(())
    })
}
