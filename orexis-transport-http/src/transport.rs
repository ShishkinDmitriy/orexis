//! THE MEMBER'S PART: the member, a poll job per sensor, and the bodies it handed on for a turn to hand to sensing.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Every, Turn};
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

    /// Every sensor the member reads, opened: a poll job each, timed at the frequency the sensor states, or polled
    /// once where it states none. The timers.
    pub(crate) fn open(&mut self) -> Result<Vec<(Every, usize)>, Error> {
        let mut timers = Vec::new();
        for sensor in self.member.open()? {
            let job = HANDLE + 1 + self.polled.len();
            match cadence_of(self.member.beliefs(), &sensor)? {
                Some(every) => timers.push((Every::new(every), job)),
                None => self.once.push(job),
            }
            self.polled.push(sensor);
        }
        Ok(timers)
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

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
