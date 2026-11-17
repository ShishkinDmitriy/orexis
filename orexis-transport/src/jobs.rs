//! WHAT A MEMBER'S CORE RUNS: the messages its member handed on, queued for a turn to handle one by one, and the jobs
//! they and the member's own work make, run until none is left.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::Turn;

use crate::inbox::{Inbox, Message};

/// The messages a member handed on, oldest first, each handled by a job of its own.
#[derive(Default)]
pub struct Pending(VecDeque<Message>);

impl Pending {
    /// Take what arrived in `inbox` since the last take: how many there were, a job to handle each.
    pub fn arrived(&mut self, inbox: &Inbox) -> usize {
        let arrived = inbox.take();
        let n = arrived.len();
        self.0.extend(arrived);
        n
    }

    /// The oldest message not yet handled.
    pub fn oldest(&mut self) -> Option<Message> {
        self.0.pop_front()
    }
}

/// A MEMBER'S CORE, as its task calls it: the jobs it queued for itself, each run in turn.
pub trait Jobs {
    /// What it queued for itself since it was last asked, as the tags its `run` answers.
    fn submitted(&mut self) -> Vec<usize>;

    /// Run one job, in `pass`: the graphs it wrote.
    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error>;

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
}
