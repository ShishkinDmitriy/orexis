//! THE RUNTIME: one agent's process, a lifecycle container for its packages' parts, run pass by pass — as
//! `agent/runtime.py`'s `Runtime` runs them (a-package-starts-itself). A part is started, asks for what it waits for
//! — so far a timer, `every` so many seconds of the one timeline — and is run when that falls due; a pass runs every
//! part due, in the order of the pass, on the one thread, the mind. The run ends when nothing holds the agent, as the
//! last to let go said: `met`, `planned` or `unreachable`; or when the passes ran out, `unfinished`.
//!
//! A PART HEARS A KIND OF GRAPH WRITTEN (`on`), as Python's `runtime.on` offers it: every graph a job answers it
//! wrote is told to each part listening for a kind the catalogue says it is, and what that part writes in turn is
//! told the same way — how a package answers another's work with neither naming the other. And A PART QUEUES A JOB
//! (`submitted`), which runs after the jobs queued before it in the same drain, as Python's `submit` queues one.
//!
//! A TRANSPORT'S THREAD HANDS THE PASS WHAT ARRIVED through the member's inbox: what a client received waits there,
//! and the member's part queues a job per message when the runtime asks what it `submitted`, so a message is handled
//! on the one thread the store is written from. NOT YET PORTED: the wake — a pass that moved nothing waits the poll,
//! as the Python runtime does, where the decision record has the mind woken by its channel
//! (the-agent-moves-to-rust-one-package-at-a-time).

use std::collections::{BTreeMap, VecDeque};

use oxsdatatypes::DateTime;

use crate::Error;
use crate::clock::{Clock, seconds};
use crate::store::Store;

/// How a run ends.
pub const MET: &str = "met";
pub const PLANNED: &str = "planned";
pub const UNREACHABLE: &str = "unreachable";
pub const UNFINISHED: &str = "unfinished";

/// What a part asks for as it starts.
pub struct Starting<'c> {
    timers: Vec<(f64, usize)>,
    hears: Vec<(String, usize)>,
    clock: &'c dyn Clock,
}

impl Starting<'_> {
    /// The instant the part starts at, read off the one timeline — a tick in a test, so read only where needed.
    pub fn now(&self) -> DateTime {
        self.clock.now()
    }

    /// Run the part's `job` for every graph of `kind` written, handed the graph (`Part::heard`).
    pub fn on(&mut self, kind: &str, job: usize) {
        self.hears.push((kind.to_string(), job));
    }

    /// Run the part's `job` at the first pass and again every `seconds` of the one timeline after — every pass where
    /// `seconds` is nought.
    pub fn every(&mut self, seconds: f64, job: usize) {
        self.timers.push((seconds, job));
    }
}

/// What a part is handed when it runs: the instant the pass stands at, and the agent's life to keep or let go.
pub struct Pass<'r> {
    pub now: DateTime,
    pub agent: &'r str,
    held: &'r mut BTreeMap<String, ()>,
    outcome: &'r mut Option<String>,
    again: &'r mut bool,
}

impl Pass<'_> {
    /// `who` keeps the agent running.
    pub fn hold(&mut self, who: &str) {
        self.held.insert(who.to_string(), ());
    }

    /// `who` no longer keeps the agent running, and says how its part ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.held.remove(who);
        if let Some(outcome) = outcome {
            *self.outcome = Some(outcome.to_string());
        }
    }

    /// Pass once more at once, without waiting the poll.
    pub fn again(&mut self) {
        *self.again = true;
    }
}

/// A package's part: started once, run when what it asked for falls due, stopped at the end, the last first.
pub trait Part {
    fn start(&mut self, _starting: &mut Starting) -> Result<(), Error> {
        Ok(())
    }

    /// Run `job` at the pass; the graphs written.
    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error>;

    /// Run `job` for `graph`, written and of a kind the part listens for; the graphs written in turn.
    fn heard(&mut self, _job: usize, _graph: &str, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    /// The jobs the part queued since it was last asked, to run in this drain after those queued before them.
    fn submitted(&mut self) -> Vec<usize> {
        Vec::new()
    }

    fn stop(&mut self) {}
}

struct Timer {
    seconds: f64,
    due: Option<DateTime>,
    part: usize,
    job: usize,
}

/// One agent's process over its beliefs, its parts lent to it in the order a pass runs them.
pub struct Runtime<'p> {
    pub beliefs: &'p Store,
    pub id: String,
    clock: &'p dyn Clock,
    parts: Vec<(String, &'p mut dyn Part)>,
    timers: Vec<Timer>,
    /// (part, kind, job): who hears a kind of graph written, in the order they asked.
    hears: Vec<(usize, String, usize)>,
    jobs: VecDeque<(usize, usize)>,
    held: BTreeMap<String, ()>,
    outcome: Option<String>,
    again: bool,
}

impl<'p> Runtime<'p> {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, its parts each started.
    pub fn new(
        beliefs: &'p Store,
        id: &str,
        clock: &'p dyn Clock,
        parts: Vec<(String, &'p mut dyn Part)>,
    ) -> Result<Self, Error> {
        let mut runtime = Runtime {
            beliefs,
            id: id.to_string(),
            clock,
            parts,
            timers: Vec::new(),
            hears: Vec::new(),
            jobs: VecDeque::new(),
            held: BTreeMap::new(),
            outcome: None,
            again: false,
        };
        for (i, (_, part)) in runtime.parts.iter_mut().enumerate() {
            let mut starting = Starting {
                timers: Vec::new(),
                hears: Vec::new(),
                clock,
            };
            part.start(&mut starting)?;
            runtime
                .hears
                .extend(starting.hears.into_iter().map(|(kind, job)| (i, kind, job)));
            runtime
                .timers
                .extend(starting.timers.into_iter().map(|(seconds, job)| Timer {
                    seconds,
                    due: None,
                    part: i,
                    job,
                }));
        }
        Ok(runtime)
    }

    /// The packages whose parts run, in the order a pass runs them.
    pub fn parts(&self) -> Vec<&str> {
        self.parts.iter().map(|(p, _)| p.as_str()).collect()
    }

    /// Run every job queued, and what their writes set off, until none is left; then every part due at `now`, in
    /// the order they asked, the same way: the graphs written.
    pub fn drain(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        self.queue_submitted();
        self.run_jobs(now, &mut written)?;
        for timer in &mut self.timers {
            if timer.due.is_some_and(|due| now < due) {
                continue;
            }
            timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
            self.jobs.push_back((timer.part, timer.job));
        }
        self.run_jobs(now, &mut written)?;
        Ok(written)
    }

    fn run_jobs(&mut self, now: DateTime, written: &mut Vec<String>) -> Result<(), Error> {
        while let Some((part, job)) = self.jobs.pop_front() {
            let mut pass = Pass {
                now,
                agent: &self.id,
                held: &mut self.held,
                outcome: &mut self.outcome,
                again: &mut self.again,
            };
            let wrote = self.parts[part].1.run(job, &mut pass)?;
            self.queue_submitted();
            self.wrote(now, wrote, written)?;
        }
        Ok(())
    }

    /// Say that `graphs` were written, so whoever listens for their kinds hears it now, and what they write in turn.
    fn wrote(&mut self, now: DateTime, graphs: Vec<String>, written: &mut Vec<String>) -> Result<(), Error> {
        for graph in graphs {
            let mut answered = Vec::new();
            if !self.hears.is_empty() {
                let kinds = self.kinds(&graph)?;
                for h in 0..self.hears.len() {
                    let (part, kind, job) = self.hears[h].clone();
                    if !kinds.contains(&kind) {
                        continue;
                    }
                    let mut pass = Pass {
                        now,
                        agent: &self.id,
                        held: &mut self.held,
                        outcome: &mut self.outcome,
                        again: &mut self.again,
                    };
                    answered.extend(self.parts[part].1.heard(job, &graph, &mut pass)?);
                    self.queue_submitted();
                }
            }
            written.push(graph);
            self.wrote(now, answered, written)?;
        }
        Ok(())
    }

    /// Every kind the catalogue says `graph` is.
    fn kinds(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(Vec::new());
        };
        let text = crate::bind::bind(
            "SELECT ?k WHERE { GRAPH $cat { $g a ?k } }",
            &[
                ("cat", crate::bind::Value::iri(cat)),
                ("g", crate::bind::Value::iri(graph)),
            ],
        )?;
        Ok(self
            .beliefs
            .rows(&text, &[])?
            .iter()
            .filter_map(|r| crate::store::iri(r, "k"))
            .collect())
    }

    fn queue_submitted(&mut self) {
        for (i, (_, part)) in self.parts.iter_mut().enumerate() {
            self.jobs.extend(part.submitted().into_iter().map(|job| (i, job)));
        }
    }

    /// Pass after pass until nobody holds the agent, ending as the last to let go said, or `passes` ran out. A pass
    /// that moved nothing waits the poll, unless a part asked to go again. THE POLL IS REAL SECONDS, as the Python
    /// runtime sleeps it: divided by a fast clock's pace, a courier at pace 30 passed 119 times where it passes 14.
    pub fn run(&mut self, passes: Option<usize>, poll_s: f64) -> Result<String, Error> {
        let mut n = 0;
        while passes.is_none_or(|p| n < p) {
            n += 1;
            let now = self.clock.now();
            self.again = false;
            self.drain(now)?;
            if self.held.is_empty() {
                log::info!("{}: nothing holds it, after {n} pass(es)", self.id);
                return Ok(self.outcome.clone().unwrap_or_else(|| MET.to_string()));
            }
            if !self.again {
                std::thread::sleep(std::time::Duration::from_secs_f64(poll_s));
            }
        }
        Ok(UNFINISHED.to_string())
    }

    /// Stop every part, the last first.
    pub fn stop(&mut self) {
        for (_, part) in self.parts.iter_mut().rev() {
            part.stop();
        }
    }
}
