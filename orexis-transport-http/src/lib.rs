//! THE HTTP TRANSPORT, in Rust: how an agent reaches a service over the web, in the words of the W3C Web of Things
//! Thing Description, adopted as it stands — ported from `orexis-transport-http/` and held to what its suite asks.
//!
//! - [`driver`]: which sensors are the member's, where each is read, a fetch on a thread of its own, and the body handed
//!   to sensing;
//! - `transport`: the member's part, a poll job per sensor and the bodies it handed on;
//! - the start, below the modules, and nothing else: the member made, and the task that polls each of its sensors at
//!   the frequency the sensor states.

use orexis::task::{Handed, Package, Woke, sooner};
use orexis_transport::Jobs;

pub mod driver;
pub mod figures;
mod transport;

pub use transport::Transport;

inventory::submit! { Package { name: "transport/http", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// A TRANSPORT IS NO ROLE: this member joins the agent where a role the self plays needs bytes and the world wires
/// them through it - each a role's class with what the world must state of the self, in words declared here.
const WIRED: &[(&str, &str)] = &[(
    "http://example.org/orexis/sensing#Observer",
    "?me orexis:plays/sensing:attends/sensing:sensor ?sensor . ?sensor td:hasForm ?form",
)];
const WORDS: &str = "PREFIX sensing: <http://example.org/orexis/sensing#>
    PREFIX speech: <http://example.org/orexis/speech#>
    PREFIX td: <https://www.w3.org/2019/wot/td#>
    ";

/// ITS START, which every package this binary holds is given: it joins where a role the self plays needs what it
/// reads and the world wires it, and declines otherwise; joined, its member is made and each sensor opened; checked,
/// it ends there as it boots; otherwise what follows is ITS TASK, which hears nothing and waits for an
/// arrival or the instant a sensor is next polled, and once nothing more waits does what has fallen due.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !orexis_transport::wired(&handed, WORDS, WIRED)? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        let me = orexis::boot::selves(&handed.store)?
            .into_iter()
            .next()
            .unwrap_or_default();
        //  HANDED A MEMBER, by a test that plays the other side, it is that; deployed and handed none, it fetches
        //  over the web; and otherwise, a check or a test that hands none, it is a member that reaches nothing, so
        //  every text it parses at its making is parsed and nothing is dialled.
        let member = match handed.provided.take::<crate::driver::Http>() {
            Some(member) => member,
            None if handed.provided.has::<orexis::task::Deployed>() => crate::driver::Http::new(
                &handed.store,
                &me,
                crate::driver::get(crate::figures::figure_of(
                    &handed.store,
                    crate::driver::FETCHED_WITHIN_S,
                )?),
            ),
            None => crate::driver::Http::new(
                &handed.store,
                &me,
                std::sync::Arc::new(|_: &str| Err("an agent that is not deployed reaches no web".to_string())),
            ),
        };
        let mut transport = Transport::new(member);
        let mut hears = handed.events.hears();
        let mut arrived = handed.arrived();
        transport.member.inbox.wakes(arrived.wake());
        let mut timers = transport.open()?;
        if !handed.booted().await? {
            return Ok(());
        }
        let mut heard = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            //  THE WEB MEMBER HEARS NOTHING: whatever woke it, it does what has fallen due.
            let _: Option<Woke> = heard.take();
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
