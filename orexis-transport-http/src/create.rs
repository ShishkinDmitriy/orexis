//! THE HTTP TRANSPORT'S PART, as `agent/transport/http/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it polls each sensor it reads — at once, then every frequency the sensor
//! states, once where it states none — and holds the agent running. A body a fetch's thread received waits in the
//! member's inbox and is handed to the one executing thread as a job that handles it.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Arrived, Every, Handed, Hears, Package, Task, Turn, Woke, sooner};
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

inventory::submit! { Package { name: "transport/http", start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    let member = handed
        .outside
        .take::<crate::driver::Http>()
        .unwrap_or_else(|| crate::driver::Http::new(&handed.store, &me, crate::driver::get()));
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
        //  THE WEB MEMBER HEARS NOTHING: whatever woke it, it does what has fallen due.
        let _: Option<Woke> = heard.take();
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
        for sensor in self.member.open()? {
            let job = HANDLE + 1 + self.polled.len();
            match cadence_of(self.member_beliefs(), &sensor)? {
                Some(every) => timers.push((Every::new(every), job)),
                None => self.once.push(job),
            }
            self.polled.push(sensor);
        }
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
