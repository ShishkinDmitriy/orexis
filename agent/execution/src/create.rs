//! THE EXECUTION PACKAGE'S PART, as `agent/execution/create.py` makes it: its executor, walking what is due every
//! pass, after planning. A walk at the instant and over the intentions the last one stood at is skipped, since it
//! finds nothing new; a walk that took a step, or ended an intention, asks for the next pass at once.
//!
//! LINKED by whoever assembles the parts: planning hands it what a pass published, reached and reconsidered, and
//! answers `taking` (#916); belief, where the agent deliberates, raises `soon` where a pass revised the present, and
//! a walk is queued, once, however many revisions say so before it runs. A TRANSPORT, linked, is handed each command a
//! step's implementation sends, order by order (`taker`); a step whose command answers nothing is not taken (#869).
//! NOT PORTED: the sayings an implementation makes, which wait for speech.

use std::cell::{Cell, RefCell};
use std::rc::Rc;

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::Clock;
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::Store;

use serde_json::Value as Json;

use crate::command::command;
use crate::executor::Take;
use crate::implementation::operations;
use crate::ontology::{COMMAND, SAYING};
use crate::{Executor, Said};

/// Whoever sends a step's command to the device: the actuator and the payload, as a transport's `command` takes them.
pub type Commands<'a> = Box<dyn FnMut(&str, &Json) -> Result<(), Error> + 'a>;

/// The taker a transport links, as Python's `_take` takes a step: the action's implementation, order by order, each
/// command sized from the present at the clock's instant and handed to `send`. A step whose action carries no command
/// or saying reaches nothing and is said in the log; a command that answers nothing is a step NOT taken (#869),
/// since the present held nothing it sizes from and recording it taken would have the intention wait out its patience
/// as though the device had run.
pub fn taker<'a>(beliefs: &'a Store, clock: &'a dyn Clock, mut send: Commands<'a>) -> Take<'a> {
    Box::new(move |said: &Said, _intention: &str| {
        let action = said.get("fills").cloned().unwrap_or_default();
        let ops = operations(beliefs, &action)?;
        let mut orders: Vec<f64> = ops
            .iter()
            .filter(|op| op.kind == COMMAND || op.kind == SAYING)
            .map(|op| op.order)
            .collect();
        orders.sort_by(f64::total_cmp);
        orders.dedup();
        if orders.is_empty() {
            return Ok(false);
        }
        let now = clock.now();
        for order in orders {
            let sent = command(beliefs, said, Some(order), now)?;
            if sent.is_empty() && ops.iter().any(|op| op.kind == COMMAND && op.order == order) {
                return Err(Error::Evaluation(format!(
                    "{}'s command answered nothing in the present",
                    orexis::ontology::local_of(&action)
                )));
            }
            for (actuator, payload) in &sent {
                send(actuator, payload)?;
            }
            if ops.iter().any(|op| op.kind == SAYING && op.order == order) {
                log::warn!(
                    "{}: a saying is not ported, so nothing is said",
                    orexis::ontology::local_of(&action)
                );
            }
        }
        Ok(true)
    })
}

/// WHETHER ANY OF SOME GRAPHS IS THE PRESENT: a belief of the agent's, by the catalogue.
const PRESENT_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { VALUES ?g { $revised } ?g a orexis:BeliefGraph .
                               FILTER NOT EXISTS { ?g a execution:CommittedStepGraph }
                               ?g orexis:ownedBy ?owner . } } LIMIT 1";

const PASS: usize = 0;
const WALK: usize = 1;

/// Execution's part: its executor, shared with whoever links to it.
pub struct Execution<'a> {
    pub executor: Rc<RefCell<Executor<'a>>>,
    /// Raised by whoever saw the present change: a walk is queued.
    pub soon: Rc<Cell<bool>>,
    queued: bool,
    walked_at: Option<DateTime>,
    since: usize,
    resolved: usize,
}

impl<'a> Execution<'a> {
    pub fn new(beliefs: &'a Store, agent: &str, clock: &'a dyn Clock) -> Result<Self, Error> {
        Ok(Execution {
            executor: Rc::new(RefCell::new(Executor::new(beliefs, agent, None, None, clock)?)),
            soon: Rc::new(Cell::new(false)),
            queued: false,
            walked_at: None,
            since: usize::MAX,
            resolved: 0,
        })
    }
}

/// Whether a revision pass changed the present, which alone answers a step: the transitions it applied changed a
/// state, or a source it revised is a belief of the agent's — no world's document, and no committed step the
/// executor wrote itself, since a walk on those would read the clock for nothing.
pub fn present(beliefs: &Store, revised: &[String], changed: &[String]) -> Result<bool, Error> {
    if !changed.is_empty() {
        return Ok(true);
    }
    let Some(cat) = beliefs.catalogue()? else {
        return Ok(false);
    };
    if revised.is_empty() {
        return Ok(false);
    }
    let graphs = revised.iter().map(|g| format!("<{g}>")).collect::<Vec<_>>().join(" ");
    let text = bind(PRESENT_Q, &[("cat", Value::iri(cat)), ("revised", Value::Raw(graphs))])?;
    Ok(!beliefs.rows(&text, &[])?.is_empty())
}

impl Execution<'_> {
    fn walk(&mut self, pass: &mut Pass<'_>) -> Result<(), Error> {
        self.queued = false;
        let mut executor = self.executor.borrow_mut();
        if executor.walk(pass.now)? > 0 {
            pass.again();
        }
        self.walked_at = Some(pass.now);
        self.since = executor.standing()?.len();
        Ok(())
    }
}

impl Part for Execution<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        starting.every(0.0, PASS);
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        if job == WALK {
            self.walk(pass)?;
        } else {
            let standing = self.executor.borrow().standing()?.len();
            if self.walked_at != Some(pass.now) || self.since != standing {
                self.walk(pass)?;
            }
        }
        let mut executor = self.executor.borrow_mut();
        if executor.resolved != self.resolved {
            self.resolved = executor.resolved;
            pass.again();
        }
        Ok(std::mem::take(&mut executor.written))
    }

    fn submitted(&mut self) -> Vec<usize> {
        if !self.soon.replace(false) || self.queued {
            return Vec::new();
        }
        self.queued = true;
        vec![WALK]
    }
}
