//! THE PLANNING PACKAGE'S PART, as `agent/planning/create.py` makes it: its Planner, planning every pass once
//! started, and after each pass holding the agent or letting it go, saying how the wanting ended — `met` where no
//! want stands and nothing walks, `planned` where every want has a plan published and no part walks one,
//! `unreachable` where some stand that nothing this agent holds reaches. A desire held keeps it holding, since a
//! desire asks at every instant.

use orexis::Error;
use orexis::runtime::{MET, PLANNED, Part, Pass, Starting, UNREACHABLE};
use orexis::store::Store;

use crate::Planner;
use crate::admit::local_of;

const PLAN: usize = 0;

/// Planning's part: its Planner, and whether any part walks what it publishes.
pub struct Planning<'a> {
    pub planner: Planner<'a>,
    pub walked: bool,
}

impl<'a> Planning<'a> {
    /// The part, its budget the agent's stance unless the caller sizes one.
    pub fn new(beliefs: &'a Store, agent: &str, budget: Option<usize>) -> Result<Self, Error> {
        Ok(Planning {
            planner: Planner::new(beliefs, agent, budget)?,
            walked: false,
        })
    }

    /// Hold the agent, or let it go and say how the wanting ended.
    fn keep(&self, pass: &mut Pass<'_>) -> Result<(), Error> {
        let who = "planning";
        let standing = self.planner.standing(pass.now)?;
        let walking = self.planner.walking()?;
        let desire = self.planner.holds_a_desire()?;
        let settle = |pass: &mut Pass<'_>, outcome: &str| {
            if desire {
                pass.hold(who);
            } else {
                pass.release(who, Some(outcome));
            }
        };
        if standing.is_empty() && walking.is_empty() {
            settle(pass, MET);
            return Ok(());
        }
        if !walking.is_empty() && self.walked {
            pass.hold(who);
            return Ok(());
        }
        let unplanned: Vec<&String> = standing.iter().filter(|w| !walking.contains(*w)).collect();
        if unplanned.is_empty() {
            settle(pass, PLANNED);
            return Ok(());
        }
        if self.planner.exhausted()? {
            pass.again();
            pass.hold(who);
            return Ok(());
        }
        log::error!(
            "{}: {} want(s) stand and nothing this agent holds reaches them: {}",
            pass.agent,
            unplanned.len(),
            unplanned.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
        );
        settle(pass, UNREACHABLE);
        Ok(())
    }
}

impl Part for Planning<'_> {
    fn start(&mut self, starting: &mut Starting) {
        starting.every(0.0, PLAN);
    }

    fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let written = self.planner.plan(pass.now)?;
        self.keep(pass)?;
        Ok(written)
    }
}
