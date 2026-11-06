//! THE RUNTIME: one agent's process, a lifecycle container for its packages' parts, run pass by pass — as
//! `agent/runtime.py`'s `Runtime` runs them (a-package-starts-itself). A part is started, asks for what it waits for
//! — so far a timer, `every` so many seconds of the one timeline — and is run when that falls due; a pass runs every
//! part due, in the order of the pass, on the one thread, the mind. The run ends when nothing holds the agent, as the
//! last to let go said: `met`, `planned` or `unreachable`; or when the passes ran out, `unfinished`.
//!
//! NOT YET PORTED: the jobs a transport submits from its own thread and the graphs-written signal a package hears
//! another's work by; they come with the first package that needs them, and with them the Tokio tasks the decision
//! record says what waits is (the-agent-moves-to-rust-one-package-at-a-time).

use std::collections::BTreeMap;

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
#[derive(Default)]
pub struct Starting {
    timers: Vec<(f64, usize)>,
}

impl Starting {
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
    fn start(&mut self, _starting: &mut Starting) {}

    /// Run `job` at the pass; the graphs written.
    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error>;

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
    held: BTreeMap<String, ()>,
    outcome: Option<String>,
    again: bool,
}

impl<'p> Runtime<'p> {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, its parts each started.
    pub fn new(beliefs: &'p Store, id: &str, clock: &'p dyn Clock, parts: Vec<(String, &'p mut dyn Part)>) -> Self {
        let mut runtime = Runtime {
            beliefs,
            id: id.to_string(),
            clock,
            parts,
            timers: Vec::new(),
            held: BTreeMap::new(),
            outcome: None,
            again: false,
        };
        for (i, (_, part)) in runtime.parts.iter_mut().enumerate() {
            let mut starting = Starting::default();
            part.start(&mut starting);
            runtime
                .timers
                .extend(starting.timers.into_iter().map(|(seconds, job)| Timer {
                    seconds,
                    due: None,
                    part: i,
                    job,
                }));
        }
        runtime
    }

    /// The packages whose parts run, in the order a pass runs them.
    pub fn parts(&self) -> Vec<&str> {
        self.parts.iter().map(|(p, _)| p.as_str()).collect()
    }

    /// Run every part due at `now`, in the order they asked: the graphs written.
    pub fn drain(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        for timer in &mut self.timers {
            if timer.due.is_some_and(|due| now < due) {
                continue;
            }
            timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
            let mut pass = Pass {
                now,
                agent: &self.id,
                held: &mut self.held,
                outcome: &mut self.outcome,
                again: &mut self.again,
            };
            written.extend(self.parts[timer.part].1.run(timer.job, &mut pass)?);
        }
        Ok(written)
    }

    /// Pass after pass until nobody holds the agent, ending as the last to let go said, or `passes` ran out. A pass
    /// that moved nothing waits the poll, unless a part asked to go again.
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
                std::thread::sleep(self.clock.real_delay(poll_s));
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
