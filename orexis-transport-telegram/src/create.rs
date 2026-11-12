//! THE TELEGRAM TRANSPORT'S PART, as `agent/transport/telegram/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls the bot every `TELEGRAM_POLL_S` and holds the agent running; a message
//! a poll's thread received waits in the member's inbox and is handed to the one executing thread as a job that says
//! it as prose. The agent's own words for a channel it carries it hears said kept, beneath its trigger, and sends.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use orexis::Error;
use orexis::runtime::{Heard, Pass, Registers, Runtime, Seat, Starting, Woke};
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

impl Transport {
    /// THE TELEGRAM MEMBER REGISTERING ITSELF on a runtime, lent: whoever keeps the part reads it between runs.
    pub fn registers(part: &Arc<Mutex<Self>>) -> Registers {
        let part = part.clone();
        Box::new(move |runtime| register(runtime, part))
    }
}

/// Started, it says what it waits for, and hands the runtime its task.
fn register(runtime: &mut Runtime, part: Arc<Mutex<Transport>>) -> Result<(), Error> {
    let mut starting = runtime.starting("transport/telegram");
    part.lock().expect("a part nobody poisoned").start(&mut starting)?;
    runtime.register(starting, move |seat| policy(part, seat));
    Ok(())
}

/// THE TELEGRAM MEMBER'S TASK: it waits for its poll falling due, an event beneath its trigger, or a message a poll
/// received, and does what its policy says of each.
async fn policy(part: Arc<Mutex<Transport>>, mut seat: Seat) {
    while let Some((woke, mut pass)) = seat.next().await {
        let mut transport = part.lock().expect("a part nobody poisoned");
        let wrote = match woke {
            Woke::Due(tag) => transport.run(tag, &mut pass),
            Woke::Event(tag, event) => transport.heard_event(tag, &event, &mut pass),
            Woke::Arrived => transport.queued(&mut pass),
            _ => Ok(Vec::new()),
        };
        pass.done(wrote);
    }
}

impl Transport {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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

    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.member.inbox.wakes(starting.wake());
        starting.every(self.member.every, POLL);
        starting.hears(CARRYING_TRIGGER, CARRY);
        Ok(())
    }

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries, and the agent shown writing.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let store = self.member.beliefs().clone();
        carry(&store, &mut self.member, event, pass, CARRYING)?;
        Ok(Vec::new())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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
