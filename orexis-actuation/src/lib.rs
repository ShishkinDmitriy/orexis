//! ACTUATION: the translation row's acting side, the mirror of sensing — a step's command turned into what a device
//! is told, and sent through the transport member that reaches it, in SOSA's words for acting
//! (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop).
//!
//! - `operator`: the package's core, the operator the self plays, which sends each command of a step's order and
//!   keeps the acts it made, and tells a board whose reading is due to sense;
//! - `encode`: what a device is sent, each setting's value written at its property's pointer;
//! - the start, below the modules, and nothing else: the operator made, and the task that hears a step's commands.

use orexis::task::{Handed, Package, Woke};
use orexis_transport::Members;

use crate::operator::{ACTUATE, NUDGE};

pub mod encode;
mod operator;

pub use operator::Operator;

inventory::submit! { Package { name: "actuation", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/actuation#Operator";
/// What starts its actuating: execution's `execution:Commanded`, beneath it in this package's ontology.
const ACTUATING_TRIGGER: &str = "http://example.org/orexis/actuation#ActuatingTrigger";
/// What starts its nudging: sensing's `sensing:ReadingLapsed`, beneath it in this package's ontology.
const NUDGING_TRIGGER: &str = "http://example.org/orexis/actuation#NudgingTrigger";

/// ACTUATION'S START, which every package this binary holds is given: it joins where the self plays an operator and
/// declines otherwise; it says it booted, and checked it ends there; otherwise what follows is ITS TASK, which reads
/// the agent's members once every core is made, sends each command of each step's order it hears, and tells the board
/// of each sensor sensing says is due to sense.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let mut hears = handed.events.hears();
        hears.event(ACTUATING_TRIGGER, ACTUATE);
        hears.event(NUDGING_TRIGGER, NUDGE);
        if !handed.booted().await? {
            return Ok(());
        }
        let mut operator = Operator::new(&handed.store, handed.provided.share::<Members>())?;
        loop {
            let woke = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => match woke {
                    Some(woke) => woke,
                    None => break,
                },
            };
            if let Woke::Event(tag, event) = woke {
                let mut turn = handed.turn();
                let wrote = operator.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
        }
        Ok(())
    })
}
