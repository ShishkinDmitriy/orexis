//! THE PLANNING PACKAGE'S PART, as `agent/planning/create.py` makes it: its Planner, planning every pass once
//! started, and after each pass holding the agent or letting it go, saying how the wanting ended — `met` where no
//! want stands and nothing walks, `planned` where every want has a plan published and no part walks one,
//! `unreachable` where some stand that nothing this agent holds reaches. A desire held keeps it holding, since a
//! desire asks at every instant.
//!
//! LINKED by whoever assembles the parts, as `link` connects the Python part's signals: the Planner is shared, so the
//! executor can ask it of a head about to be taken, and `heard` is told of each pass before its holding is decided —
//! what it published, reached and reconsidered — as the executor adopts, ends and supersedes by them.

use std::cell::RefCell;
use std::rc::Rc;

use orexis::Error;
use orexis::runtime::{MET, PLANNED, Part, Pass, Starting, UNREACHABLE};
use orexis::store::Store;

use crate::Planner;
use crate::admit::local_of;
use crate::ontology::PLANNING_ACTIVITY;

const PLAN: usize = 0;

/// Whoever hears what a pass did, handed the Planner after it: the graphs it wrote in answer.
pub type Heard<'a> = Box<dyn FnMut(&Planner<'a>) -> Result<Vec<String>, Error> + 'a>;

/// Planning's part: its Planner, shared with whoever links to it, whether any part walks what it publishes, and who
/// hears each pass.
pub struct Planning<'a> {
    pub planner: Rc<RefCell<Planner<'a>>>,
    pub walked: bool,
    pub heard: Option<Heard<'a>>,
}

impl<'a> Planning<'a> {
    /// The part, its budget the agent's stance unless the caller sizes one.
    pub fn new(beliefs: &'a Store, agent: &str, budget: Option<usize>) -> Result<Self, Error> {
        Ok(Planning {
            planner: Rc::new(RefCell::new(Planner::new(beliefs, agent, budget)?)),
            walked: false,
            heard: None,
        })
    }

    /// Hold the agent, or let it go and say how the wanting ended.
    fn keep(&self, pass: &mut Pass<'_>) -> Result<(), Error> {
        let who = "planning";
        let planner = self.planner.borrow();
        let standing = planner.standing(pass.now)?;
        let walking = planner.walking()?;
        let desire = planner.holds_a_desire()?;
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
        if planner.exhausted()? {
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
        let unplanned: Vec<String> = unplanned.into_iter().cloned().collect();
        planner.unreachable(&unplanned, pass.now)?;
        settle(pass, UNREACHABLE);
        Ok(())
    }
}

impl Part for Planning<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        starting.every(0.0, PLAN);
        Ok(())
    }

    fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        //  EVERY PASS FOR NOW, TRIGGERED BY NOTHING: a policy deciding when to plan is #1119's sixth step.
        let activity = pass.begin(PLANNING_ACTIVITY, &[]);
        let mut written = self.planner.borrow_mut().plan(pass.now)?;
        if let Some(heard) = self.heard.as_mut() {
            written.extend(heard(&self.planner.borrow())?);
        }
        self.keep(pass)?;
        pass.lap("plan");
        pass.end(activity);
        Ok(written)
    }
}
