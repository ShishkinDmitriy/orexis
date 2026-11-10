//! THE EXECUTION PACKAGE'S PART, as `agent/execution/create.py` makes it: its executor, walking what is due every
//! pass, after planning. A walk at the instant and over the intentions the last one stood at is skipped, since it
//! finds nothing new; a walk that took a step, or ended an intention, asks for the next pass at once.
//!
//! ITS POLICY HEARS ONE TRIGGER PER ACTIVITY, beneath which a higher package's ontology puts its events, reads what each
//! is about in execution's words, and starts that activity, its trigger the entity the event names: an adopting of a
//! plan (`execution:adopts`, pursuing `execution:pursues`, the want derived from `prov:wasDerivedFrom`), a superseding
//! after a step in flight (`execution:endsAfter`, replaced by a plan pursuing `execution:pursues`), or a resolving of a
//! want's unbegun intentions (`execution:pursues`, `execution:outcome`). Planning's plan published, plan superseded and
//! want reached are beneath the three, so planning and execution meet by events and the store.
//!
//! LINKED by whoever assembles the parts: planning answers `taking` (#916), until a hearer may hold a reader of the
//! store (#1119). Belief's revision pass is heard beneath the walking trigger, in belief's words, and where it changed
//! the present a walk is queued, once, however many revisions say so before it runs. A TRANSPORT, linked, is handed each command a
//! step's implementation sends, order by order (`taker`); a step whose command answers nothing is not taken (#869).
//! And speech, linked, is handed each document a step's implementation says, with the agents it is to.

use std::cell::{Cell, RefCell};
use std::rc::Rc;
use std::sync::Arc;

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::Clock;
use orexis::runtime::{Heard, Part, Pass, Starting};
use orexis::store::Store;

use serde_json::Value as Json;

use crate::command::command;
use crate::executor::Take;
use crate::implementation::operations;
use crate::ontology::{
    ADOPTING, ADOPTING_TRIGGER, ADOPTS, CHANGED, COMMAND, DERIVED_FROM, ENDS_AFTER, OUTCOME, PURSUES, RESOLVING,
    RESOLVING_TRIGGER, REVISED_SOURCE, SAYING, SUPERSEDING, SUPERSEDING_TRIGGER, WALKING_TRIGGER,
};
use crate::says::says;
use crate::{Executor, Said};

/// Whoever sends a step's command to the device: the actuator and the payload, as a transport's `command` takes them.
pub type Commands<'a> = Box<dyn FnMut(&str, &Json) -> Result<(), Error> + 'a>;

/// Whoever says a step's document to the agents it is to, as speech's `say` takes them.
pub type Sayings<'a> = Box<dyn FnMut(&[String], &orexis::document::Document) -> Result<(), Error> + 'a>;

/// The taker a transport links, as Python's `_take` takes a step: the action's implementation, order by order, each
/// command sized from the present at the clock's instant and handed to `send`. A step whose action carries no command
/// or saying reaches nothing and is said in the log; a command that answers nothing is a step NOT taken (#869),
/// since the present held nothing it sizes from and recording it taken would have the intention wait out its patience
/// as though the device had run.
pub fn taker<'a>(
    beliefs: &'a Store,
    clock: Arc<dyn Clock>,
    mut send: Option<Commands<'a>>,
    mut say: Option<Sayings<'a>>,
) -> Take<'a> {
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
            if let Some(send) = send.as_mut() {
                for (actuator, payload) in &sent {
                    send(actuator, payload)?;
                }
            }
            if let Some(say) = say.as_mut() {
                for (agents, document) in says(beliefs, said, Some(order), now)? {
                    say(&agents, &document)?;
                }
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
const ADOPT: usize = 2;
const SUPERSEDE: usize = 3;
const RESOLVE: usize = 4;
const REVISED: usize = 5;

/// Execution's part: its executor, shared with whoever links to it.
pub struct Execution<'a> {
    pub executor: Rc<RefCell<Executor<'a>>>,
    /// Raised by whoever saw the present change: a walk is queued.
    pub soon: Rc<Cell<bool>>,
    queued: bool,
    walked_at: Option<DateTime>,
    since: usize,
    resolved: usize,
    /// What whoever was linked wrote as a step was taken — the statements speech kept of what a step said — for the
    /// pass to hand on with what the executor wrote.
    pub said: Rc<RefCell<Vec<String>>>,
}

impl<'a> Execution<'a> {
    pub fn new(beliefs: &Store, agent: &str, clock: Arc<dyn Clock>) -> Result<Self, Error> {
        Ok(Execution {
            executor: Rc::new(RefCell::new(Executor::new(beliefs, agent, None, None, clock)?)),
            soon: Rc::new(Cell::new(false)),
            queued: false,
            walked_at: None,
            since: usize::MAX,
            resolved: 0,
            said: Rc::new(RefCell::new(Vec::new())),
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
        let activity = pass.begin(crate::ontology::WALKING, &[]);
        let mut executor = self.executor.borrow_mut();
        if executor.walk(pass.now)? > 0 {
            pass.again();
        }
        pass.end(activity);
        self.walked_at = Some(pass.now);
        self.since = executor.intentions.len()?;
        Ok(())
    }
}

impl Part for Execution<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        starting.every(0.0, PASS);
        starting.hears(ADOPTING_TRIGGER, ADOPT);
        starting.hears(SUPERSEDING_TRIGGER, SUPERSEDE);
        starting.hears(RESOLVING_TRIGGER, RESOLVE);
        starting.hears(WALKING_TRIGGER, REVISED);
        Ok(())
    }

    /// What execution's policy does of a trigger: the activity it is the trigger of, begun with the entity the event
    /// names as what triggered it, and ended once done. An event naming less than its activity needs starts nothing.
    fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        //  A WALK IS QUEUED where what was heard changed the present, which alone answers a step: the walk is the
        //  activity, started when it runs.
        if job == REVISED {
            let names = |p: &str| {
                event
                    .all(p)
                    .into_iter()
                    .map(|n| n.as_str().to_string())
                    .collect::<Vec<_>>()
            };
            let beliefs = self.executor.borrow().beliefs.clone();
            if present(&beliefs, &names(REVISED_SOURCE), &names(CHANGED))? {
                self.soon.set(true);
            }
            return Ok(Vec::new());
        }
        let want = event.named(PURSUES).cloned();
        let (kind, trigger) = match job {
            ADOPT => (ADOPTING, event.named(ADOPTS)),
            SUPERSEDE => (SUPERSEDING, event.named(ENDS_AFTER)),
            RESOLVE => (RESOLVING, want.as_ref()),
            _ => return Ok(Vec::new()),
        };
        let Some(trigger) = trigger.cloned() else {
            return Ok(Vec::new());
        };
        let outcome = event.about.iter().find_map(|(p, t)| match t {
            oxigraph::model::Term::Literal(l) if p == OUTCOME => Some(l.value().to_string()),
            _ => None,
        });
        let activity = pass.begin(kind, std::slice::from_ref(&trigger));
        let mut executor = self.executor.borrow_mut();
        let want = want.map(|w| w.as_str().to_string());
        let wrote = match (job, want) {
            (ADOPT, Some(want)) => {
                if let Some(desire) = event.named(DERIVED_FROM) {
                    executor
                        .desires
                        .insert(want.clone(), orexis::ontology::local_of(desire.as_str()));
                }
                executor.adopt(trigger.as_str(), &want)
            }
            (SUPERSEDE, want) => executor.supersede_after(trigger.as_str(), want.as_deref()),
            (RESOLVE, Some(want)) => match outcome {
                Some(outcome) => executor.end_for(&want, &outcome),
                None => Ok(Vec::new()),
            },
            _ => Ok(Vec::new()),
        };
        drop(executor);
        pass.end(activity);
        wrote
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        if job == WALK {
            self.walk(pass)?;
        } else {
            //  OVER THE INTENTIONS THE LAST WALK STOOD AT: nothing written to them since, as Python reads it off the
            //  store's length — a plan that replaced another leaves as many standing, and is walked at once.
            let held = self.executor.borrow().intentions.len()?;
            if self.walked_at != Some(pass.now) || self.since != held {
                self.walk(pass)?;
            }
            //  THE PASS'S LAP IS MARKED HERE AND ONLY HERE: a walk a revision queued, run among the drain's jobs,
            //  would mark `execute` over the sensing and revision before it.
            pass.lap("execute");
        }
        let mut executor = self.executor.borrow_mut();
        if executor.resolved != self.resolved {
            self.resolved = executor.resolved;
            pass.again();
        }
        let mut written = std::mem::take(&mut executor.written);
        written.append(&mut self.said.borrow_mut());
        Ok(written)
    }

    fn watch(&self) -> Option<orexis::events::Watch> {
        Some(self.executor.borrow().watch.clone())
    }

    fn submitted(&mut self) -> Vec<usize> {
        if !self.soon.replace(false) || self.queued {
            return Vec::new();
        }
        self.queued = true;
        vec![WALK]
    }
}
