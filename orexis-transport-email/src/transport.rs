//! THE MEMBER'S PART: the member, and the messages it handed on for a turn to handle - each a person's words kept as
//! prose - polled as often as a role says, and what the agent says carried.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Heard, Turn};
use orexis::transport::Message;
use orexis_speech::prose::{ProseKept, carry, kept};

use crate::driver::Email;

pub(crate) const POLL: usize = 0;
const HANDLE: usize = 1;
pub(crate) const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/email#Carrying";
pub(crate) const CARRYING_TRIGGER: &str = "http://example.org/orexis/email#CarryingTrigger";
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

    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    pub(crate) fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries.
    pub(crate) fn heard_event(
        &mut self,
        _job: usize,
        event: &Heard,
        pass: &mut Turn<'_>,
    ) -> Result<Vec<String>, Error> {
        let store = self.member.beliefs().clone();
        carry(&store, &mut self.member, event, pass, CARRYING)?;
        Ok(Vec::new())
    }

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
