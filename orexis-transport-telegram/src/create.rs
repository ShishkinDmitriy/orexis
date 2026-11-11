//! THE TELEGRAM TRANSPORT'S PART, as `agent/transport/telegram/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls the bot every `TELEGRAM_POLL_S` and holds the agent running; a message
//! a poll's thread received waits in the member's inbox and is handed to the one executing thread as a job that says
//! it as prose. The agent's own words for a channel it carries it hears said kept, beneath its trigger, and sends.

use std::collections::VecDeque;

use orexis::Error;
use orexis::runtime::{Heard, Part, Pass, Starting};
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

impl Part for Transport {
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
