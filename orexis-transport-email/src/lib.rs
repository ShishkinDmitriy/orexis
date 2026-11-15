//! THE EMAIL TRANSPORT, in Rust: an agent's own mailbox over IMAP and SMTP — ported from `orexis-transport-email/` and
//! held to what its suite asks.
//!
//! - [`driver`]: polled for every unseen message, a chat's words said as prose, and told what the agent says;
//! - the start, below the modules: the member's part, polling as often as a role says (`email:polledEveryS`).

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Arrived, Every, Handed, Heard, Hears, Package, Task, Turn, Woke, sooner};
use orexis::transport::Message;
use orexis_speech::prose::{ProseKept, carry, kept};

use crate::driver::Email;

pub mod driver;

const POLL: usize = 0;
const HANDLE: usize = 1;
const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/email#Carrying";
const CARRYING_TRIGGER: &str = "http://example.org/orexis/email#CarryingTrigger";
const HOLDER: &str = "transport/email";

/// The member's part: the member, shared, and the messages handed to the pass.
pub struct Transport {
    pub member: Email,
    pending: VecDeque<Message>,
}

impl Transport {
    pub fn new(member: Email) -> Self {
        Transport {
            member,
            pending: VecDeque::new(),
        }
    }
}

inventory::submit! { Package { name: "transport/email", documents: orexis::documents!("ontology.ttl"), start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
/// A TRANSPORT IS NO ROLE: this member joins the agent where a role the self plays needs bytes and the world wires
/// them through it - each a role's class with what the world must state of the self, in words declared here.
const WIRED: &[(&str, &str)] = &[(
    "http://example.org/orexis/translation#Translator",
    "?chat speech:participant ?me ; speech:channel ?channel . ?channel schema:email ?address",
)];
const WORDS: &str = "PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX speech: <http://example.org/orexis/speech#> PREFIX schema: <https://schema.org/> ";

/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !orexis::boot::wired(&handed.store, WORDS, WIRED)? {
            return Ok(());
        }
        let task = make(&handed)?;
        handed.started("transport/email").await;
        match task {
            Some(task) if handed.checking().is_none() => task.await,
            _ => Ok(()),
        }
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    //  HANDED A MEMBER, by a test that plays the other side, it is that; deployed and handed none, it connects from
    //  the agent's environment, refused where that lacks what it needs; and otherwise, a check or a test that hands
    //  none, it is a member that reaches nothing, so every text it parses at its making is parsed and nothing is dialled.
    let member = match handed.outside.take::<crate::driver::Email>() {
        Some(member) => member,
        None if handed.outside.has::<orexis::task::Deployed>() => {
            crate::driver::Email::connect(&handed.store, &me, &|name| std::env::var(name).ok())?
        }
        None => crate::driver::Email::new(&handed.store, &me, std::sync::Arc::new(crate::driver::Unreachable)),
    };
    //  CHECKED, it says what a check asks of it: it listens, so it holds the agent for as long as its process runs.
    if let Some(checking) = handed.checking() {
        checking.holds("transport/email");
    }
    let mut part = Transport::new(member);
    let mut hears = handed.events.hears();
    let arrived = handed.arrived();
    let mut timers = Vec::new();
    part.start(handed, &mut hears, &arrived, &mut timers)?;
    Ok(Some(Box::pin(task(handed.clone(), part, hears, arrived, timers))))
}

/// THE PACKAGE'S TASK: it decides as the run begins, then waits for what it hears, an arrival or the instant it is
/// next due; once nothing more waits to be heard it does what it queued for itself and what has fallen due.
async fn task(
    handed: Handed,
    mut part: Transport,
    mut hears: Hears,
    mut arrived: Arrived,
    mut timers: Vec<(Every, usize)>,
) -> Result<(), Error> {
    let mut heard = None;
    let mut due = None;
    loop {
        let mut turn = handed.turn();
        if let Some(Woke::Event(tag, event)) = heard.take() {
            let wrote = part.heard_event(tag, &event, &mut turn);
            turn.done(wrote)?;
        }
        if hears.is_empty() {
            let wrote = part.queued(&mut turn);
            turn.done(wrote)?;
            for (every, tag) in &mut timers {
                if every.due(turn.now) {
                    let wrote = part.run(*tag, &mut turn);
                    turn.done(wrote)?;
                    let wrote = part.queued(&mut turn);
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
}

impl Transport {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        loop {
            let jobs = self.submitted();
            if jobs.is_empty() {
                return Ok(Vec::new());
            }
            for job in jobs {
                let wrote = self.run(job, pass)?;
                pass.told(wrote)?;
            }
        }
    }

    fn start(
        &mut self,
        handed: &Handed,
        hears: &mut Hears,
        arrived: &Arrived,
        timers: &mut Vec<(Every, usize)>,
    ) -> Result<(), Error> {
        let _ = (&handed, &hears, &arrived, &timers);
        self.member.inbox.wakes(arrived.wake());
        timers.push((Every::new(self.member.polled_every_s), POLL));
        hears.event(CARRYING_TRIGGER, CARRY);
        Ok(())
    }

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let store = self.member.beliefs().clone();
        carry(&store, &mut self.member, event, pass, CARRYING)?;
        Ok(Vec::new())
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        pass.hold(HOLDER);
        match job {
            POLL => {
                self.member.poll();
                Ok(Vec::new())
            }
            _ => {
                let Some(message) = self.pending.pop_front() else {
                    return Ok(Vec::new());
                };
                let prose = self
                    .member
                    .handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                let Some(prose) = prose else {
                    return Ok(Vec::new());
                };
                //  A PERSON'S WORDS are kept, and said kept, for whoever translates.
                let graph = {
                    let member = &self.member;
                    kept(member.beliefs(), &member.me, &prose)?
                };
                pass.emit(&ProseKept { prose: graph.clone() });
                Ok(vec![graph])
            }
        }
    }

    fn submitted(&mut self) -> Vec<usize> {
        let arrived = self.member.inbox.take();
        let n = arrived.len();
        self.pending.extend(arrived);
        vec![HANDLE; n]
    }
}
