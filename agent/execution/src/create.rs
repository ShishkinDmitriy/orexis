//! THE EXECUTION PACKAGE'S PART, as `agent/execution/create.py` makes it: its executor, walking what is due every
//! pass, after planning. A walk at the instant and over the intentions the last one stood at is skipped, since it
//! finds nothing new; a walk that took a step, or ended an intention, asks for the next pass at once.
//!
//! LINKED by whoever assembles the parts: planning hands it what a pass published, reached and reconsidered, and
//! answers `taking` (#916). NOT PORTED: hearing belief's revisions, since no Rust package revises yet, and the
//! commands and sayings an implementation makes, since no transport and no speech are ported; a step is said in
//! the log, or taken fictively.

use std::cell::RefCell;
use std::rc::Rc;

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::Clock;
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::Store;

use crate::Executor;

const WALK: usize = 0;

/// Execution's part: its executor, shared with whoever links to it.
pub struct Execution<'a> {
    pub executor: Rc<RefCell<Executor<'a>>>,
    walked_at: Option<DateTime>,
    since: usize,
    resolved: usize,
}

impl<'a> Execution<'a> {
    pub fn new(beliefs: &'a Store, agent: &str, clock: &'a dyn Clock) -> Result<Self, Error> {
        Ok(Execution {
            executor: Rc::new(RefCell::new(Executor::new(beliefs, agent, None, None, clock)?)),
            walked_at: None,
            since: usize::MAX,
            resolved: 0,
        })
    }
}

impl Part for Execution<'_> {
    fn start(&mut self, starting: &mut Starting) {
        starting.every(0.0, WALK);
    }

    fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let mut executor = self.executor.borrow_mut();
        let standing = executor.standing()?.len();
        if self.walked_at != Some(pass.now) || self.since != standing {
            if executor.walk(pass.now)? > 0 {
                pass.again();
            }
            self.walked_at = Some(pass.now);
            self.since = executor.standing()?.len();
        }
        if executor.resolved != self.resolved {
            self.resolved = executor.resolved;
            pass.again();
        }
        Ok(std::mem::take(&mut executor.written))
    }
}
