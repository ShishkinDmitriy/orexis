//! SPEECH, in Rust, ported from `orexis-speech/`: what a peer says and what the agent says, each kept as what was said
//! — a statement, a kind no reader of the mind is handed — and what the agent believes of it, extracted.
//!
//! - [`heard`]: a peer's document, kept as what was said, or refused whole;
//! - [`said`]: what this agent told a peer, kept as it was said;
//! - [`statements`]: a document as what was said, each graph a statement whatever kind it says, and read back;
//! - [`extract`]: what every extraction the agent holds concludes of one statement, one belief derived from it;
//! - `speaker`: the package's core, the speaker the self plays, which extracts from every statement written and says
//!   what a step says;
//! - [`events`]: every statement said and heard, history in speech's words;
//! - the start, below the modules, and nothing else: the speaker made, and the task that wakes it.

use orexis::task::{Handed, Package, Woke};

use crate::ontology::{SPEAKING_TRIGGER, STATEMENT_GRAPH};
use crate::speaker::{SPEAK, STATED};

pub mod events;
pub mod extract;
pub mod heard;
pub mod ontology;
pub mod prose;
pub mod said;
mod speaker;
pub mod statements;

pub use speaker::Speaker;
pub use statements::document_of;

inventory::submit! { Package { name: "speech", documents: orexis::documents!("ontology.ttl"), start } }

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/speech#Speaker";

/// SPEECH'S START, which every package this binary holds is given: it joins where the self plays a speaker and
/// declines otherwise; joined, its speaker is made and what a restart finds unextracted extracted; checked, it ends
/// there; otherwise it says it has started, and what follows is ITS TASK, which waits for a statement written or an
/// event beneath its trigger, and once nothing more waits to be heard hands on what it queued for itself.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        let mut speaker = Speaker::new(&handed.store)?;
        speaker.watch = handed.events.watch().clone();
        speaker.unextracted()?;
        let mut hears = handed.events.hears();
        hears.graph(STATEMENT_GRAPH, STATED);
        hears.event(SPEAKING_TRIGGER, SPEAK);
        let mut arrived = handed.arrived();
        handed.started("speech").await;
        if handed.checking().is_some() {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            match heard.take() {
                Some(Woke::Event(tag, event)) => {
                    let wrote = speaker.heard_event(tag, &event, &mut turn);
                    turn.done(wrote)?;
                }
                Some(Woke::Graphs(tag, graphs)) => {
                    let wrote = speaker.heard(tag, &graphs, &mut turn);
                    turn.done(wrote)?;
                }
                _ => {}
            }
            if hears.is_empty() {
                let wrote = speaker.queued(&mut turn);
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
                _ = arrived.wait() => None,
                _ = handed.sleep_until(due) => None,
            };
        }
        Ok(())
    })
}
