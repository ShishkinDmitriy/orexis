//! THE HTTP TRANSPORT'S PART, as `agent/transport/http/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls each sensor it reads — at once, then every frequency the sensor
//! states, once where it states none — and holds the agent running. A body a fetch's thread received waits in the
//! member's inbox and is handed to the one executing thread as a job that handles it.

use std::collections::VecDeque;

use orexis::Error;
use orexis::runtime::{Part, Pass, Starting};
use orexis::transport::Message;
use orexis_sensing::cadence::cadence_of;

use crate::driver::Http;

const HANDLE: usize = 0;
const HOLDER: &str = "transport/http";

/// The member's part: the member, a poll job per sensor, and the bodies handed to the pass.
pub struct Transport {
    pub member: Http,
    /// Each poll job's sensor, its job the index after `HANDLE`.
    polled: Vec<String>,
    once: Vec<usize>,
    pending: VecDeque<Message>,
}

impl Transport {
    pub fn new(member: Http) -> Self {
        Transport {
            member,
            polled: Vec::new(),
            once: Vec::new(),
            pending: VecDeque::new(),
        }
    }
}

impl Part for Transport {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.member.inbox.wakes(starting.wake());
        for sensor in self.member.open()? {
            let job = HANDLE + 1 + self.polled.len();
            match cadence_of(self.member_beliefs(), &sensor)? {
                Some(every) => starting.every(every, job),
                None => self.once.push(job),
            }
            self.polled.push(sensor);
        }
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        //  A MEMBER KEEPS THE AGENT RUNNING: what it senses goes on arriving whatever is wanted.
        pass.hold(HOLDER);
        if job == HANDLE {
            let Some(message) = self.pending.pop_front() else {
                return Ok(Vec::new());
            };
            let written = self
                .member
                .handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
            return Ok(written.into_iter().map(|(_, graph)| graph).collect());
        }
        if let Some(sensor) = self.polled.get(job - HANDLE - 1) {
            self.member.sense_now(sensor)?;
        }
        Ok(Vec::new())
    }

    fn submitted(&mut self) -> Vec<usize> {
        let mut jobs = std::mem::take(&mut self.once);
        let arrived = self.member.inbox.take();
        jobs.extend(std::iter::repeat_n(HANDLE, arrived.len()));
        self.pending.extend(arrived);
        jobs
    }
}

impl Transport {
    fn member_beliefs(&self) -> &orexis::store::Store {
        self.member.beliefs()
    }
}
