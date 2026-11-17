//! THE TELEGRAM TRANSPORT, in Rust: an agent's own bot over the Bot API — ported from `orexis-transport-telegram/` and
//! held to what its suite asks.
//!
//! - [`driver`]: polled for what is written to the bot, a chat's words said as prose, and told what the agent says;
//! - `transport`: the member's part, the member and the messages it handed on;
//! - the start, below the modules, and nothing else: the member made, and the task that polls it as often as a role
//!   says (`telegram:polledEveryS`).

use orexis::task::{Every, Handed, Package, Woke, sooner};

use crate::transport::{CARRY, CARRYING_TRIGGER, POLL};

pub mod driver;
mod transport;

pub use transport::Transport;

inventory::submit! { Package { name: "transport/telegram", documents: orexis::documents!("ontology.ttl"), start } }

/// A TRANSPORT IS NO ROLE: this member joins the agent where a role the self plays needs bytes and the world wires
/// them through it - each a role's class with what the world must state of the self, in words declared here.
const WIRED: &[(&str, &str)] = &[(
    "http://example.org/orexis/translation#Translator",
    "?me telegram:hasBot ?bot",
)];
const WORDS: &str = "PREFIX telegram: <http://example.org/orexis/telegram#> ";

/// ITS START, which every package this binary holds is given: it joins where a role the self plays needs what it
/// carries and the world wires it, and declines otherwise; joined, its member is made; checked, it says it holds the
/// agent and ends there; otherwise it says it has started, and what follows is ITS TASK, which waits for an event
/// beneath its trigger, an arrival or the instant it next polls, and once nothing more waits to be heard handles what
/// the member handed on.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !orexis::boot::wired(&handed.store, WORDS, WIRED)? {
            return Ok(());
        }
        handed.joins("transport/telegram").await?;
        let me = orexis::boot::selves(&handed.store)?
            .into_iter()
            .next()
            .unwrap_or_default();
        //  HANDED A MEMBER, by a test that plays the other side, it is that; deployed and handed none, it connects from
        //  the agent's environment, refused where that lacks what it needs; and otherwise, a check or a test that hands
        //  none, it is a member that reaches nothing, so every text it parses at its making is parsed and nothing is dialled.
        let member = match handed.provided.take::<crate::driver::Telegram>() {
            Some(member) => member,
            None if handed.provided.has::<orexis::task::Deployed>() => {
                crate::driver::Telegram::connect(&handed.store, &me, &|name| std::env::var(name).ok())?
            }
            None => crate::driver::Telegram::unreachable(&handed.store, &me),
        };
        //  CHECKED, it says what a check asks of it: it listens, so it holds the agent for as long as its process runs.
        if let Some(checking) = handed.checking() {
            checking.holds("transport/telegram");
        }
        let mut transport = Transport::new(member);
        let mut hears = handed.events.hears();
        let mut arrived = handed.arrived();
        transport.member.inbox.wakes(arrived.wake());
        let mut timers = vec![(Every::new(transport.member.polled_every_s), POLL)];
        hears.event(CARRYING_TRIGGER, CARRY);
        handed.started("transport/telegram").await;
        if handed.checking().is_some() {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            if let Some(Woke::Event(tag, event)) = heard.take() {
                let wrote = transport.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            if hears.is_empty() {
                let wrote = transport.queued(&mut turn);
                turn.done(wrote)?;
                for (every, tag) in &mut timers {
                    if every.due(turn.now) {
                        let wrote = transport.run(*tag, &mut turn);
                        turn.done(wrote)?;
                        let wrote = transport.queued(&mut turn);
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
