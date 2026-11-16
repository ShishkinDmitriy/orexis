//! TRANSLATION, in Rust: the agent's chats with people, heard and answered through a language model at a run-time
//! edge, never in a pass — ported from `orexis-translation/` and held to what its suite asks.
//!
//! - [`chat`]: the chats an agent is in, each its channel, its people, its agents, what its model may read and state;
//! - [`briefing`]: what the model is handed before a person's words;
//! - [`readable`]: what a chat may read of the agent, copied, and the two tools that read it;
//! - [`stated`]: what a person may state in a chat, held to its words' bounds, and believed as the world's word;
//! - [`past`]: what happened to the agent — its journal, its series, its metrics — and the tools that read them;
//! - [`model`]: the model client, the one place a language model is asked;
//! - [`events`]: what translation says happened — the model used, and each conversation;
//! - `conversation`: one conversation with the model, what it is told and offered, and what comes of it;
//! - `translator`: the package's core, the translator the self plays, which hears a person's words and phrases what
//!   the agent says to one;
//! - the start, below the modules, and nothing else: the translator made, handed its model and what a chat reads, and
//!   the task that wakes it.

use std::sync::Arc;

use orexis::series::Reader;
use orexis::task::{Every, Handed, Package, Reads, Woke, sooner};

use crate::translator::{PHRASE, PHRASING_TRIGGER, STILL, TRANSLATE, TRANSLATING_TRIGGER};

pub mod briefing;
pub mod chat;
mod conversation;
pub mod events;
pub mod figures;
pub mod model;
pub mod past;
pub mod readable;
pub mod stated;
mod translator;

pub use conversation::{CONVERSE_SYSTEM, SAY_SYSTEM, SILENT, UNADDRESSED, WRITING_S};
pub use translator::{Inline, Translator};

inventory::submit! { Package { name: "translation", documents: orexis::documents!("ontology.ttl"), start } }

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/translation#Translator";

/// TRANSLATION'S START, which every package this binary holds is given: it joins where the self plays a translator
/// and declines otherwise; joined, its translator is made, handed the model a test answers for or, deployed, the one
/// its role names, and what a chat reads of what happened; checked, it ends there; otherwise it says it has started,
/// and what follows is ITS TASK, which waits for an event beneath its triggers, an arrival or the instant it is next
/// due, and once nothing more waits to be heard does what the model's threads handed back.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        let mut translator = Translator::new(&handed.store)?;
        //  HANDED A MODEL, by a test that answers for it, it is that; deployed and handed none, the one its role
        //  names (`translation:translatedBy`), where the world's deployment says that answers, under the name and key
        //  the agent's environment holds; and otherwise none, so a check calls no model.
        translator.model = handed.outside.take::<Arc<dyn crate::model::Model>>();
        if translator.model.is_none() && handed.outside.has::<orexis::task::Deployed>() {
            //  CALLED AS THE TRANSLATOR'S ROLE SAYS: where, how long a call may take, and how often it is asked again.
            translator.model = match &translator.translated_by {
                Some(url) => crate::model::Anthropic::from_environ(url, &|name| std::env::var(name).ok()).map(|m| {
                    Arc::new(m.paced(translator.called_within_s, translator.retries)) as Arc<dyn crate::model::Model>
                }),
                None => {
                    log::warn!(
                        "no model: the translator's role names none the world says where to reach (translation:translatedBy)"
                    );
                    None
                }
            };
        }
        translator.inline = handed.outside.take::<Inline>().is_some();
        //  WHAT A CHAT READS OF WHAT HAPPENED: the journal where what keeps it said where it lies, and the two series —
        //  handed, by a test that answers for them, or, where the agent is deployed, read through a sink of its own
        //  wherever the world names a store that serves the purpose.
        let mut reads = handed.outside.share::<Reads>();
        if handed.outside.has::<orexis::task::Deployed>() {
            let own = |purpose: &'static str| -> Result<Option<Reader>, orexis::Error> {
                Ok(
                    orexis::series::Sink::deployed(&handed.store, purpose, &orexis::series::environment)?
                        .map(|(sink, _)| sink.reader()),
                )
            };
            if reads.history.is_none() {
                reads.history = own(orexis::series::HISTORY)?;
            }
            if reads.metrics.is_none() {
                reads.metrics = own(orexis::series::METRICS)?;
            }
        }
        (translator.journaled, translator.history, translator.metrics) = (reads.journal, reads.history, reads.metrics);
        translator.watch = handed.events.watch().clone();
        let mut hears = handed.events.hears();
        hears.event(TRANSLATING_TRIGGER, TRANSLATE);
        hears.event(PHRASING_TRIGGER, PHRASE);
        let mut arrived = handed.arrived();
        let mut timers = vec![(Every::new(WRITING_S), STILL)];
        handed.started("translation").await;
        if handed.checking().is_some() {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            if let Some(Woke::Event(tag, event)) = heard.take() {
                let wrote = translator.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            if hears.is_empty() {
                let wrote = translator.queued(&mut turn);
                turn.done(wrote)?;
                for (every, tag) in &mut timers {
                    if every.due(turn.now) {
                        let wrote = translator.run(*tag, &mut turn);
                        turn.done(wrote)?;
                        let wrote = translator.queued(&mut turn);
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
