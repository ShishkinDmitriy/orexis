//! BELIEF, in Rust, ported from `orexis-belief/`:
//!
//! - [`transition`]: rules that change a state rather than conclude of it, and the one machine that applies them,
//!   which planning applies an action's effect by;
//! - `revise`: what the rules conclude of one graph, its revisions;
//! - `trigger`: the transitions an arrival of testimony triggers, applied to the agent's own state;
//! - `deliberator`: the package's core, the pass that sequences the two over what was written, within a budget, and
//!   what it revises as the package starts and on what it hears;
//! - the start, below the modules, and nothing else: the deliberator made, and the task that wakes it.

use orexis::Error;
use orexis::ontology::BELIEF;
use orexis::task::{Handed, Hears, Package, Task, Woke};

use crate::ontology::REVISING_TRIGGER;

mod deliberator;
pub mod ontology;
mod revise;
pub mod transition;
mod trigger;

pub use deliberator::{Deliberator, Revised};

const HEARD: usize = 0;
const REVISE: usize = 1;

inventory::submit! { Package { name: "belief", documents: orexis::documents!("ontology.ttl"), start } }

/// BELIEF'S START: its deliberator made, what the world authored as the agent's state revised, once, and its task,
/// which hears a belief written and its trigger's events.
/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[crate::ontology::DELIBERATOR]).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    let mut belief = Deliberator::new(&handed.store, &handed.id, None)?;
    belief.watch = handed.events.watch().clone();
    belief.unrevised(handed.clock.now())?;
    let mut hears = handed.events.hears();
    hears.graph(BELIEF, HEARD);
    hears.event(REVISING_TRIGGER, REVISE);
    Ok(Some(Box::pin(task(handed.clone(), belief, hears))))
}

/// BELIEF'S TASK: it waits for a belief written, or an event beneath its trigger, and revises.
async fn task(handed: Handed, mut belief: Deliberator, mut hears: Hears) -> Result<(), Error> {
    loop {
        let woke = tokio::select! {
            biased;
            _ = handed.stopped() => break,
            woke = hears.next() => woke,
        };
        let Some(woke) = woke else { break };
        let mut turn = handed.turn();
        let wrote = match woke {
            Woke::Graphs(_, graphs) => belief.revising(&graphs, BELIEF, &mut turn).map(|()| Vec::new()),
            Woke::Event(_, event) => belief.heard_event(&event, &mut turn),
        };
        turn.done(wrote)?;
    }
    Ok(())
}
