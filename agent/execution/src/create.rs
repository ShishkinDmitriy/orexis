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
//! A HEAD ABOUT TO BE TAKEN IS ASKED where the executor `asks`: said `execution:HeadAsked`, and taken or failed when an
//! event beneath the walking trigger answers it (`execution:head`, `execution:blocked`), which planning says (#916).
//! Belief's revision pass is heard beneath the walking trigger too, in belief's words, and where it changed the present
//! a walk is queued, once, however many revisions say so before it runs. A STEP IS TAKEN order by order
//! (`taker`): each order's commands sized from the present, kept as an `execution:CommandGraph` and said
//! `execution:Commanded`, which a transport's ontology puts beneath its trigger and sends; and each document said,
//! kept by speech's `said` and said `execution:Told`, which execution's ontology puts beneath speech's speaking
//! trigger. A step whose command answers nothing is not taken (#869).

use std::cell::{Cell, RefCell};
use std::rc::Rc;
use std::sync::Arc;

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::Clock;
use orexis::document::Document;
use orexis::events::{Event, Watch, mint};
use orexis::ontology::RECORDED;
use orexis::runtime::{Heard, Part, Pass, Starting};
use orexis::store::Store;
use oxigraph::model::{GraphName, Literal, NamedNode, Quad, Term};

use serde_json::Value as Json;

use crate::command::command;
use crate::events::{BLOCKED, HEAD};
use crate::executor::Take;
use crate::implementation::operations;
use crate::ontology::{
    ACTUATOR, ADOPTING, ADOPTING_TRIGGER, ADOPTS, CHANGED, COMMAND, COMMAND_GRAPH, COMMANDED, COMMANDS, DERIVED_FROM,
    ENDS_AFTER, OUTCOME, PAYLOAD, PURSUES, RESOLVING, RESOLVING_TRIGGER, REVISED_SOURCE, SAYING, SPEECH_STATEMENT,
    SPEECH_TO, SUPERSEDING, SUPERSEDING_TRIGGER, TOLD, WALKING_TRIGGER,
};
use crate::says::says;
use crate::{Executor, Said};

/// The taker of an agent that carries out its steps, as Python's `_take` takes a step: the action's implementation,
/// order by order, each command sized from the present at the clock's instant, kept and said `execution:Commanded` where
/// the agent `commands` — has a transport to send it — and each document it says kept by speech and said
/// `execution:Told` where the agent `says`, the statements kept handed on through `said`. A step whose action carries no
/// command or saying reaches nothing; a command that answers nothing is a step NOT taken (#869), since the present held
/// nothing it sizes from and recording it taken would have the intention wait out its patience as though the device
/// had run.
pub fn taker(
    beliefs: Store,
    me: &str,
    clock: Arc<dyn Clock>,
    watch: Watch,
    commands: bool,
    says_to: bool,
    kept: Rc<RefCell<Vec<String>>>,
) -> Take {
    let me = me.to_string();
    Box::new(move |said: &Said, _intention: &str| {
        let beliefs = &beliefs;
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
            if commands && !sent.is_empty() {
                let graph = commanded(beliefs, &me, &sent)?;
                watch.emit(&Commanded { commands: graph });
            }
            if says_to {
                for (agents, document) in says(beliefs, said, Some(order), now)? {
                    let statements = orexis_speech::said::said(beliefs, &me, &document)?;
                    watch.emit(&Told {
                        statements: statements.clone(),
                        to: agents,
                    });
                    kept.borrow_mut().extend(statements);
                }
            }
        }
        Ok(true)
    })
}

/// THE COMMANDS ONE ORDER OF A STEP SENDS, kept as the agent's own act before any transport sends them: an
/// `execution:CommandGraph` of one node per command, its actuator and its payload; the graph's name.
pub fn commanded(store: &Store, me: &str, sent: &[(String, Json)]) -> Result<String, Error> {
    let tail = |n: &NamedNode| {
        n.as_str()
            .rsplit(['/', ':', '#'])
            .next()
            .unwrap_or_default()
            .to_string()
    };
    let local = me.rsplit(['/', '#']).next().unwrap_or(me);
    let graph = NamedNode::new(format!(
        "http://example.org/orexis/graph/command/{local}/{}",
        tail(&mint())
    ))
    .map_err(|e| Error::Evaluation(e.to_string()))?;
    let into = GraphName::NamedNode(graph.clone());
    let mut quads = vec![Quad::new(
        graph.clone(),
        NamedNode::new_unchecked(RDF_TYPE),
        NamedNode::new_unchecked(COMMAND_GRAPH),
        GraphName::DefaultGraph,
    )];
    for (actuator, payload) in sent {
        let node = NamedNode::new_unchecked(format!("{}#{}", graph.as_str(), tail(&mint())));
        let actuator = NamedNode::new(actuator.as_str()).map_err(|e| Error::Evaluation(e.to_string()))?;
        quads.push(Quad::new(
            node.clone(),
            NamedNode::new_unchecked(ACTUATOR),
            actuator,
            into.clone(),
        ));
        quads.push(Quad::new(
            node,
            NamedNode::new_unchecked(PAYLOAD),
            Literal::new_simple_literal(payload.to_string()),
            into.clone(),
        ));
    }
    store.put_document(&Document::of_quads(quads), Some(me), None, Some(RECORDED), true)?;
    Ok(graph.as_str().to_string())
}

/// A step's commands at one order were kept: the command graph, for the transport that sends them.
#[derive(Clone, Debug, PartialEq)]
pub struct Commanded {
    pub commands: String,
}

impl Event for Commanded {
    fn kind(&self) -> Option<&'static str> {
        Some(COMMANDED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        NamedNode::new(self.commands.as_str())
            .map(|g| vec![(COMMANDS, Term::NamedNode(g))])
            .unwrap_or_default()
    }
}

/// A step said statements the agent now believes it said, to the agents named: in speech's words, for speech to tell.
#[derive(Clone, Debug, PartialEq)]
pub struct Told {
    pub statements: Vec<String>,
    pub to: Vec<String>,
}

impl Event for Told {
    fn kind(&self) -> Option<&'static str> {
        Some(TOLD)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        let named = |p: &'static str, iri: &str| NamedNode::new(iri).ok().map(|n| (p, Term::NamedNode(n)));
        self.statements
            .iter()
            .filter_map(|s| named(SPEECH_STATEMENT, s))
            .chain(self.to.iter().filter_map(|a| named(SPEECH_TO, a)))
            .collect()
    }
}

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

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
pub struct Execution {
    pub executor: Rc<RefCell<Executor>>,
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

impl Execution {
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

impl Execution {
    /// What the executor and the taker wrote since the runtime was last handed it.
    fn handed(&mut self) -> Vec<String> {
        let mut written = std::mem::take(&mut self.executor.borrow_mut().written);
        written.append(&mut self.said.borrow_mut());
        written
    }

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

impl Part for Execution {
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
            //  A HEAD ASKED IS ANSWERED beneath the same trigger: taken or failed now, and walked on from, since a
            //  fictive step taken is answered at once.
            if let Some(head) = event.named(HEAD) {
                let blocked = event.about.iter().any(|(p, t)| {
                    p == BLOCKED && matches!(t, oxigraph::model::Term::Literal(l) if l.value() == "true")
                });
                let activity = pass.begin(crate::ontology::WALKING, std::slice::from_ref(&event.node));
                if self.executor.borrow_mut().judged(head.as_str(), blocked)? {
                    pass.again();
                }
                pass.end(activity);
                self.soon.set(true);
                return Ok(self.handed());
            }
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
            //  EXECUTION'S POLICY AT THE PASS: walk where the instant the last walk said is due has come — a head
            //  due, a landing to look at, a patience run out — or the intentions were written since it, as Python
            //  read it off the store's length, a plan that replaced another leaving as many standing; and otherwise
            //  nothing, since what else answers a step is a revision of the present, which queues a walk of its own.
            //  THE DUE INSTANT IS HELD TO THE CLOCK, not to the pass's instant: a walk reads the clock as it goes, so
            //  a landing may have come since the pass began.
            let (held, due) = {
                let executor = self.executor.borrow();
                let due = match executor.next_due {
                    Some(d) => d <= pass.now || d <= executor.clock.now(),
                    None => false,
                };
                (executor.intentions.len()?, due)
            };
            if self.walked_at.is_none() || self.since != held || due {
                self.walk(pass)?;
            }
            if let Some(due) = self.executor.borrow().next_due {
                pass.wake_at(due);
            }
            //  THE PASS'S LAP IS MARKED HERE AND ONLY HERE: a walk a revision queued, run among the drain's jobs,
            //  would mark `execute` over the sensing and revision before it.
            pass.lap("execute");
        }
        if self.executor.borrow().resolved != self.resolved {
            self.resolved = self.executor.borrow().resolved;
            pass.again();
        }
        Ok(self.handed())
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
