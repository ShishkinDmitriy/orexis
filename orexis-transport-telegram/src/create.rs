//! THE TELEGRAM TRANSPORT'S PART, as `agent/transport/telegram/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls the bot every `TELEGRAM_POLL_S` and holds the agent running; a message
//! a poll's thread received waits in the member's inbox and is handed to the one executing thread as a job that says
//! it as prose. The agent's own words for a channel it carries it hears said kept, beneath its trigger, and sends.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Arrived, Every, Handed, Heard, Hears, Package, Task, Turn, Woke, sooner};
use orexis::transport::Message;
use orexis_speech::prose::{ProseKept, carry, kept};

use crate::driver::Telegram;

const POLL: usize = 0;
const HANDLE: usize = 1;
const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/telegram#Carrying";
const CARRYING_TRIGGER: &str = "http://example.org/orexis/telegram#CarryingTrigger";
const HOLDER: &str = "transport/telegram";

/// The member's part: the member, shared, and the messages handed to the pass.
pub struct Transport {
    pub member: Telegram,
    pending: VecDeque<Message>,
}

impl Transport {
    pub fn new(member: Telegram) -> Self {
        Transport {
            member,
            pending: VecDeque::new(),
        }
    }
}

inventory::submit! { Package { name: "transport/telegram", documents: orexis::documents!("ontology.ttl"), start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    let member = match handed.outside.take::<crate::driver::Telegram>() {
        Some(member) => member,
        None => crate::driver::Telegram::connect(&handed.store, &me, &|name| std::env::var(name).ok())?,
    };
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
        timers.push((Every::new(self.member.every), POLL));
        hears.event(CARRYING_TRIGGER, CARRY);
        Ok(())
    }

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries, and the agent shown writing.
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
