//! THE PLANNING PACKAGE'S PART, as `agent/planning/create.py` makes it: its Planner, planning every pass once
//! started, and after each pass holding the agent or letting it go, saying how the wanting ended — `met` where no
//! want stands and nothing walks, `planned` where every want has a plan published and no part walks one,
//! `unreachable` where some stand that nothing this agent holds reaches. A desire held keeps it holding, since a
//! desire asks at every instant.
//!
//! WHAT A PASS DID IS SAID, not handed: a plan published, a want reached and a plan superseded are events beneath
//! execution's trigger, which execution's policy hears once the pass's job is done. Whether anything walks what it
//! publishes is the agent's roles' to say — one beneath `execution:Executor` — and the Planner is shared only so the
//! executor can ask it of a head about to be taken, until a hearer may hold a reader of the store (#1119).

use std::cell::RefCell;
use std::rc::Rc;

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::runtime::{Heard, MET, PLANNED, Part, Pass, Starting, UNREACHABLE};
use orexis::store::{Store, Within, iri};

use crate::Planner;
use crate::admit::local_of;
use crate::ontology::{PLANNING_ACTIVITY, PLANNING_TRIGGER, REOPENS};

const PLAN: usize = 0;
const REOPEN: usize = 1;

/// Whoever walks what planning publishes: a role of this class, or one beneath it.
const EXECUTOR: &str = "http://example.org/orexis/execution#Executor";
const ROLES_Q: &str = "SELECT DISTINCT ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }";

/// Planning's part: its Planner, and whether any part walks what it publishes.
pub struct Planning {
    pub planner: Rc<RefCell<Planner>>,
    pub walked: bool,
}

impl Planning {
    /// The part, its budget the agent's stance unless the caller sizes one.
    pub fn new(beliefs: &Store, agent: &str, budget: Option<usize>) -> Result<Self, Error> {
        Ok(Planning {
            planner: Rc::new(RefCell::new(Planner::new(beliefs, agent, budget)?)),
            walked: walks(beliefs)?,
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

/// Whether the self plays a role beneath `execution:Executor`, read off its self graph: what it publishes is walked.
fn walks(beliefs: &Store) -> Result<bool, Error> {
    let selves = beliefs.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    for row in beliefs.rows(ROLES_Q, &selves)? {
        if let Some(kind) = iri(&row, "kind")
            && beliefs.closed(&kind)?.iter().any(|c| c == EXECUTOR)
        {
            return Ok(true);
        }
    }
    Ok(false)
}

impl Part for Planning {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        starting.every(0.0, PLAN);
        starting.hears(PLANNING_TRIGGER, REOPEN);
        Ok(())
    }

    /// What planning's policy does of a trigger: keep the walking wants it names to search again, and ask for a pass.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let wants: Vec<String> = event.all(REOPENS).iter().map(|w| w.as_str().to_string()).collect();
        if !wants.is_empty() {
            self.planner.borrow_mut().reopen(wants);
            pass.again();
        }
        Ok(Vec::new())
    }

    fn watch(&self) -> Option<orexis::events::Watch> {
        Some(self.planner.borrow().watch.clone())
    }

    fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        //  EVERY PASS FOR NOW, TRIGGERED BY NOTHING: a policy deciding when to plan is #1119's sixth step.
        let activity = pass.begin(PLANNING_ACTIVITY, &[]);
        let written = self.planner.borrow_mut().plan(pass.now)?;
        self.keep(pass)?;
        pass.lap("plan");
        pass.end(activity);
        Ok(written)
    }
}
