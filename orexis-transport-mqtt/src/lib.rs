//! THE MQTT TRANSPORT, in Rust, ported from `orexis-transport-mqtt/`: the agent's side of the bus, in MQTT4SSN's
//! words, answering what the container needs of a transport.
//!
//! - [`driver`]: what the agent subscribes to, whose a message is, where a command goes and as what, MQTT's own
//!   filter matching, and the client per broker the environment names;
//! - `transport`: the member's part, which hands each message to sensing, asks after missing readings and tells and
//!   commands what the agent says and does;
//! - the start, below the modules, and nothing else: the member made and listening, and the task that holds the agent.
//!
//! A CHAT ON A TOPIC is carried too: a person's prose heard there is kept for translation, which the part hands it to,
//! and words said back are published as `{"from": the agent, "text": …}`.

use orexis::task::{Every, Handed, Package, Woke, sooner};

use crate::transport::{ACTUATE, ACTUATING_TRIGGER, CARRY, CARRYING_TRIGGER, NUDGE, TELL, TELLING_TRIGGER};
use orexis_transport::Jobs;

pub mod driver;
pub mod figures;
mod transport;

pub use transport::Transport;

inventory::submit! { Package { name: "transport/mqtt", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl");

/// A TRANSPORT IS NO ROLE: this member joins the agent where a role the self plays needs bytes and the world wires
/// them through it - each a role's class with what the world must state of the self, in words declared here.
const WIRED: &[(&str, &str)] = &[
    (
        "http://example.org/orexis/sensing#Observer",
        "?me orexis:plays/sensing:attends/sensing:sensor ?sensor . ?sensor mqtt4ssn:observesTopic ?topic",
    ),
    (
        "http://example.org/orexis/speech#Speaker",
        "?me mqtt4ssn:listensToTopic ?topic",
    ),
    (
        "http://example.org/orexis/translation#Translator",
        "?chat speech:participant ?me ; speech:channel ?channel . ?channel a mqtt4ssn:Topic",
    ),
];
const WORDS: &str = "PREFIX sensing: <http://example.org/orexis/sensing#>
    PREFIX speech: <http://example.org/orexis/speech#>
    PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
    ";

/// ITS START, which every package this binary holds is given: it joins where a role the self plays needs what it
/// carries and the world wires it, and declines otherwise; joined, its member is made and listens; checked, it says
/// it holds the agent and ends there as it boots; otherwise what follows is ITS TASK, which waits for
/// an event beneath its triggers, an arrival or the instant a reading next falls due, and once nothing more waits to
/// be heard hands on what arrived; and it stops the member as it ends.
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
        //  HANDED A MEMBER, by a test that plays the other side, it is that; deployed and handed none, it connects from
        //  the agent's environment, refused where that lacks what it needs; and otherwise, a check or a test that hands
        //  none, it is a member that reaches nothing, so every text it parses at its making is parsed and nothing is dialled.
        let member = match handed.provided.take::<crate::driver::Mqtt>() {
            Some(member) => member,
            None if handed.provided.has::<orexis::task::Deployed>() => {
                crate::driver::connect(&handed.store, &me, &|name| std::env::var(name).ok())?
            }
            None => crate::driver::Mqtt::new(&handed.store, &me, Vec::new()),
        };
        //  CHECKED, it says what a check asks of it: it listens, so it holds the agent for as long as its process runs.
        if let Some(checking) = handed.checking() {
            checking.holds("transport/mqtt");
        }
        let mut transport = Transport::new(member);
        let mut hears = handed.events.hears();
        let mut arrived = handed.arrived();
        transport.listen(&arrived)?;
        let mut timers = vec![(Every::new(0.0), NUDGE)];
        hears.event(CARRYING_TRIGGER, CARRY);
        hears.event(TELLING_TRIGGER, TELL);
        hears.event(ACTUATING_TRIGGER, ACTUATE);
        if !handed.booted().await? {
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
        transport.stop();
        Ok(())
    })
}
