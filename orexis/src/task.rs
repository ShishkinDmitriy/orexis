//! WHAT A PACKAGE'S TASK IS HANDED, AND WHERE PACKAGES MEET (a-package-is-a-task-that-awaits-its-events). A package
//! is one async function: it makes its core, and loops - it awaits what it hears (`Hears::next`), an arrival
//! (`Arrived::wait`), the clock (`Handed::sleep_until`) or the run's end (`Handed::stopped`), calls its core, and
//! says what happened. The kernel knows no package and no word of what one does: a package REGISTERS ITSELF, its
//! crate submitting its name and its start (`Package`) to a registry the linker collects, and whoever runs an agent
//! starts each one its roles load (`start`).
//!
//! WHAT IT IS HANDED (`Handed`) is plain: the store, the agent's id, the clock, THE EVENTS - where every package says
//! what happened and subscribes to what it hears, the one thing packages share - and what reaches OUTSIDE, the
//! connectors a deployment makes from its environment and a test hands in.
//!
//! A PACKAGE HEARS AN EVENT BY ITS CLASS (`Hears::event`), the class and every class the vocabulary puts beneath it,
//! and A KIND OF GRAPH WRITTEN (`Hears::graph`): every graph a package says it wrote (`Turn::done`) is sent to each
//! task hearing a kind the catalogue says it is. A task hears everything in the order it was said, each under the tag
//! it asked with. WHAT A TASK SAYS WHILE IT HANDLES WHAT WOKE IT IS HEARD WHEN IT NEXT WAITS, its graphs before its
//! events, so a hearer never starts on a sayer's half-written work.
//!
//! THE RUN ENDS WHEN NOTHING HOLDS THE AGENT (`Running::released`), as the last to let go said: `met`, `planned` or
//! `unreachable`; or when it is halted, `unfinished`.

use std::any::{Any, TypeId};
use std::cell::RefCell;
use std::collections::{BTreeMap, HashMap};
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};

use oxsdatatypes::DateTime;

use oxigraph::model::{NamedNode, Term};
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio::sync::{Notify, watch};

use crate::Error;
use crate::activity::{Activity, Ended, Started, Wrote};
use crate::clock::Clock;
use crate::events::{Event, Laps, Mark, Number, Watch, round6};
use crate::store::Store;

pub const MET: &str = "met";
pub const PLANNED: &str = "planned";
pub const UNREACHABLE: &str = "unreachable";
pub const UNFINISHED: &str = "unfinished";

pub const PASS_METRIC: &str = "pass";

/// A pass, or a stretch of the run with something busy, and how long it took: by part, where a part marked laps.
#[derive(Clone, Debug, PartialEq)]
pub struct Passed {
    pub duration_s: f64,
    pub laps: Vec<(String, f64)>,
    pub quads: Option<i64>,
    pub uptime_s: f64,
}

impl Event for Passed {
    fn metric(&self) -> Option<&'static str> {
        Some(PASS_METRIC)
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let lap = |part: &str| self.laps.iter().find(|(n, _)| n == part).map(|(_, s)| *s);
        vec![
            ("duration_s", Mark::Value(Some(self.duration_s))),
            ("plan_s", Mark::Value(lap("plan_s"))),
            ("execute_s", Mark::Value(lap("execute_s"))),
            ("quads", Mark::Level(self.quads.map(Number::Int))),
            ("uptime_s", Mark::Level(Some(Number::Float(self.uptime_s)))),
        ]
    }
}

fn started() -> std::time::Instant {
    static STARTED: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
    *STARTED.get_or_init(std::time::Instant::now)
}

/// An event as a package hears it: the name it was said under, its class, and the activity it starts or ends.
#[derive(Clone, Debug, PartialEq)]
pub struct Heard {
    pub node: NamedNode,
    pub kind: String,
    pub activity: Option<(NamedNode, String)>,
    /// What it is about, each under the predicate that says its part (`Event::about`).
    pub about: Vec<(String, Term)>,
}

impl Heard {
    /// The first thing it is about under `predicate`, where it names a node there.
    pub fn named(&self, predicate: &str) -> Option<&NamedNode> {
        self.about.iter().find_map(|(p, t)| match t {
            Term::NamedNode(n) if p == predicate => Some(n),
            _ => None,
        })
    }

    /// Every node it is about under `predicate`, in the order said.
    pub fn all(&self, predicate: &str) -> Vec<&NamedNode> {
        self.about
            .iter()
            .filter_map(|(p, t)| match t {
                Term::NamedNode(n) if p == predicate => Some(n),
                _ => None,
            })
            .collect()
    }
}

/// WHAT A TASK DOES EVERY SO MANY SECONDS of the one timeline: due when the run begins, and again that long after
/// each time it fell due.
pub struct Every {
    seconds: f64,
    at: Option<DateTime>,
}

impl Every {
    pub fn new(seconds: f64) -> Self {
        Every { seconds, at: None }
    }

    /// Whether it is due at `now`; if so, it is next due its seconds on.
    pub fn due(&mut self, now: DateTime) -> bool {
        if self.at.is_some_and(|at| now < at) {
            return false;
        }
        self.at = Some(
            now.checked_add_day_time_duration(crate::clock::seconds(self.seconds))
                .unwrap_or(now),
        );
        true
    }

    /// When it is next due; never by itself where its seconds are nought - it is done after whatever its task
    /// heard, and a wait until now would never be one.
    pub fn at(&self) -> Option<DateTime> {
        if self.seconds > 0.0 { self.at } else { None }
    }
}

/// The sooner of two instants, either of which may be none.
pub fn sooner(a: Option<DateTime>, b: Option<DateTime>) -> Option<DateTime> {
    match (a, b) {
        (Some(a), Some(b)) => Some(if b < a { b } else { a }),
        (a, b) => a.or(b),
    }
}

tokio::task_local! {
    /// WHAT A TASK SAID AND TOOK SINCE IT LAST WAITED: the events it said, told when it next waits, and how many
    /// things it took and is still busy with.
    static TURN: RefCell<Local>;
}

#[derive(Default)]
struct Local {
    said: Vec<Heard>,
    in_hand: usize,
}

/// Run `work`, a computation of seconds, so the tasks beside it keep their workers: where the runtime has several,
/// this worker hands its other tasks on and `work` runs in place; on one thread it simply runs.
pub fn long<T>(work: impl FnOnce() -> T) -> T {
    match tokio::runtime::Handle::try_current().map(|h| h.runtime_flavor()) {
        Ok(tokio::runtime::RuntimeFlavor::MultiThread) => tokio::task::block_in_place(work),
        _ => work(),
    }
}

/// HOW MANY THINGS ARE SENT AND NOT YET DONE WITH, across every task: nought is idle.
#[derive(Clone)]
struct Busy(Arc<watch::Sender<usize>>, Arc<Mutex<std::time::Instant>>);

impl Busy {
    fn new() -> Self {
        Busy(
            Arc::new(watch::channel(0).0),
            Arc::new(Mutex::new(std::time::Instant::now())),
        )
    }

    fn up(&self) {
        self.0.send_modify(|n| {
            if *n == 0 {
                *self.1.lock().expect("an instant nobody poisoned") = std::time::Instant::now();
            }
            *n += 1;
        });
    }

    /// When the stretch with something busy began: the last time anything was, after nothing had been.
    fn began(&self) -> std::time::Instant {
        *self.1.lock().expect("an instant nobody poisoned")
    }

    fn down(&self) {
        self.0.send_modify(|n| *n = n.saturating_sub(1));
    }
}

/// What a task hears, under the tag it asked with.
#[derive(Clone, Debug, PartialEq)]
pub enum Woke {
    /// An event of a class it hears was said.
    Event(usize, Heard),
    /// Graphs of a kind it hears were written, together: what one turn wrote of that kind.
    Graphs(usize, Vec<String>),
}

struct Bus {
    beliefs: Store,
    watch: Watch,
    /// Who hears what: each task's sender, the classes of event and the kinds of graph it hears, each with its tag.
    hearers: RwLock<Vec<Hearer>>,
    /// Every class each class said is beneath, asked once.
    closed: Mutex<HashMap<String, Vec<String>>>,
    busy: Busy,
    /// Whether the watch is heard: connected when the first task asks to hear an event.
    listening: AtomicBool,
    held: Mutex<BTreeMap<String, ()>>,
    outcome: Mutex<Option<String>>,
    laps: Mutex<Option<Laps>>,
    error: Mutex<Option<Error>>,
}

struct Hearer {
    to: UnboundedSender<Woke>,
    events: Vec<(String, usize)>,
    graphs: Vec<(String, usize)>,
}

/// THE EVENTS OF ONE AGENT: where its packages say what happened and subscribe to what they hear. A clone is the same
/// events.
#[derive(Clone)]
pub struct Events(Arc<Bus>);

impl Events {
    /// The events of an agent over `beliefs`, whose vocabulary says which class is beneath which.
    pub fn new(beliefs: &Store) -> Self {
        let bus = Arc::new(Bus {
            beliefs: beliefs.clone(),
            watch: Watch::default(),
            hearers: RwLock::new(Vec::new()),
            closed: Mutex::new(HashMap::new()),
            busy: Busy::new(),
            listening: AtomicBool::new(false),
            held: Mutex::new(BTreeMap::new()),
            outcome: Mutex::new(None),
            laps: Mutex::new(None),
            error: Mutex::new(None),
        });
        Events(bus)
    }

    /// A turn at `now`, for whoever calls a package's core with no task around it: a unit test.
    pub fn turn<'a>(&'a self, now: DateTime, agent: &'a str) -> Turn<'a> {
        Turn {
            now,
            agent,
            events: self,
            next: None,
            last: None,
        }
    }

    /// THE WATCH EVERY PACKAGE SAYS ITS EVENTS TO, and whoever watches the agent hears them on.
    pub fn watch(&self) -> &Watch {
        &self.0.watch
    }

    /// What a task hears, empty until it says: it asks by `event` and `graph`, and awaits `next`.
    pub fn hears(&self) -> Hears {
        let (to, inbox) = unbounded_channel();
        let index = {
            let mut hearers = self.0.hearers.write().expect("hearers nobody poisoned");
            hearers.push(Hearer {
                to,
                events: Vec::new(),
                graphs: Vec::new(),
            });
            hearers.len() - 1
        };
        Hears {
            events: self.clone(),
            index,
            inbox,
        }
    }

    /// Whether any task hears events of `class`: whoever would say one asks first, where saying it is work.
    pub fn heard(&self, class: &str) -> bool {
        let Ok(classes) = self.closure(class) else {
            return false;
        };
        let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
        hearers
            .iter()
            .any(|h| h.events.iter().any(|(c, _)| classes.contains(c)))
    }

    /// Hear the watch, once somebody hears events: what is said on it is told to the tasks that hear its class.
    fn listen(&self) {
        if self.0.listening.swap(true, Ordering::SeqCst) {
            return;
        }
        let weak = Arc::downgrade(&self.0);
        self.0.watch.connect(move |event, named| {
            if let (Some(kind), Some(bus)) = (event.kind(), weak.upgrade()) {
                let heard = Heard {
                    node: named.clone(),
                    kind: kind.to_string(),
                    activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
                    about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
                };
                let held = TURN.try_with(|turn| turn.borrow_mut().said.push(heard.clone())).is_ok();
                if !held {
                    Events(bus).tell(heard);
                }
            }
        });
    }

    /// Every class `class` is beneath, itself among them.
    fn closure(&self, class: &str) -> Result<Vec<String>, Error> {
        let mut closed = self.0.closed.lock().expect("a closure nobody poisoned");
        if let Some(classes) = closed.get(class) {
            return Ok(classes.clone());
        }
        let classes = self.0.beliefs.closed(class)?;
        closed.insert(class.to_string(), classes.clone());
        Ok(classes)
    }

    fn send(&self, to: &UnboundedSender<Woke>, woke: Woke) {
        self.0.busy.up();
        if to.send(woke).is_err() {
            self.0.busy.down();
        }
    }

    /// Send `event` to every task hearing a class it is beneath.
    fn tell(&self, event: Heard) {
        let classes = match self.closure(&event.kind) {
            Ok(classes) => classes,
            Err(e) => return self.failed(e),
        };
        let to: Vec<(UnboundedSender<Woke>, usize)> = {
            let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
            hearers
                .iter()
                .flat_map(|h| {
                    h.events
                        .iter()
                        .filter(|(class, _)| classes.contains(class))
                        .map(|(_, tag)| (h.to.clone(), *tag))
                })
                .collect()
        };
        for (to, tag) in to {
            self.send(&to, Woke::Event(tag, event.clone()));
        }
    }

    /// Say that `graphs` were written, to every task hearing a kind the catalogue says any of them is: WHAT ONE
    /// TURN WROTE OF A KIND IS TOLD AS ONE THING, the graphs of it together in the order they were written. One
    /// message of several readings is several percepts, and told one by one each was said and revised apart, so
    /// whoever heard the first revision decided before the rest was believed.
    pub fn wrote(&self, graphs: Vec<String>) -> Result<(), Error> {
        let asked: Vec<(UnboundedSender<Woke>, String, usize)> = {
            let hearers = self.0.hearers.read().expect("hearers nobody poisoned");
            hearers
                .iter()
                .flat_map(|h| h.graphs.iter().map(|(kind, tag)| (h.to.clone(), kind.clone(), *tag)))
                .collect()
        };
        if asked.is_empty() || graphs.is_empty() {
            return Ok(());
        }
        let mut kinds = Vec::new();
        for graph in &graphs {
            kinds.push(self.kinds(graph)?);
        }
        for (to, kind, tag) in asked {
            let of_kind: Vec<String> = graphs
                .iter()
                .zip(&kinds)
                .filter(|(_, kinds)| kinds.contains(&kind))
                .map(|(graph, _)| graph.clone())
                .collect();
            if !of_kind.is_empty() {
                self.send(&to, Woke::Graphs(tag, of_kind));
            }
        }
        Ok(())
    }

    /// Every kind the catalogue says `graph` is.
    fn kinds(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(cat) = self.0.beliefs.catalogue()? else {
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
            .0
            .beliefs
            .rows(&text, &[])?
            .iter()
            .filter_map(|r| crate::store::iri(r, "k"))
            .collect())
    }

    /// A task failed: the run's error, the first one kept.
    pub fn failed(&self, error: Error) {
        let mut kept = self.0.error.lock().expect("an error nobody poisoned");
        if kept.is_none() {
            *kept = Some(error);
        }
    }

    /// THE TASK WAITS: what it said since it last waited is told, and what it took it is done with.
    fn rest(&self) {
        let rested = TURN.try_with(|turn| {
            let mut turn = turn.borrow_mut();
            (std::mem::take(&mut turn.said), std::mem::take(&mut turn.in_hand))
        });
        if let Ok((said, in_hand)) = rested {
            for heard in said {
                self.tell(heard);
            }
            for _ in 0..in_hand {
                self.0.busy.down();
            }
        }
    }

    /// The task took something it was sent, counted busy since it was sent: it is in hand until the task next waits.
    /// Whoever is no task of the agent's is done with it at once.
    fn took(&self) {
        if TURN.try_with(|turn| turn.borrow_mut().in_hand += 1).is_err() {
            self.0.busy.down();
        }
    }

    /// The task woke by itself - the clock, or the run began: busy until it next waits.
    fn woke(&self) {
        self.0.busy.up();
        self.took();
    }

    /// Mark the end of a part of a stretch with something busy, for the stretch's event, where anybody watches.
    pub fn lap(&self, part: &str) {
        if self.0.watch.connected() {
            let mut laps = self.0.laps.lock().expect("laps nobody poisoned");
            laps.get_or_insert_with(|| Laps::since(self.0.busy.began())).lap(part);
        }
    }
}

/// WHAT A TASK HEARS: the events and graphs it asked for, in the order they were said.
pub struct Hears {
    events: Events,
    index: usize,
    inbox: UnboundedReceiver<Woke>,
}

impl Hears {
    /// Hear every event of `class` said, or of a class the vocabulary puts beneath it, with `tag`.
    pub fn event(&mut self, class: &str, tag: usize) {
        self.events.listen();
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].events.push((class.to_string(), tag));
    }

    /// Hear every graph of `kind` written, with `tag`.
    pub fn graph(&mut self, kind: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].graphs.push((kind.to_string(), tag));
    }

    /// Whether nothing more waits to be heard.
    pub fn is_empty(&self) -> bool {
        self.inbox.is_empty()
    }

    /// WAIT FOR WHAT IS HEARD NEXT; nothing once nobody can say anything more.
    pub async fn next(&mut self) -> Option<Woke> {
        self.events.rest();
        let woke = self.inbox.recv().await?;
        self.events.took();
        Some(woke)
    }
}

impl Drop for Hears {
    /// A task that ended holds nothing busy: nothing it was sent and never took.
    fn drop(&mut self) {
        self.inbox.close();
        while self.inbox.try_recv().is_ok() {
            self.events.0.busy.down();
        }
    }
}

struct Ring {
    notify: Notify,
    /// Whether it rang and the task has not yet woken for it.
    rung: AtomicBool,
    /// Whether the task that waits for it is gone.
    gone: AtomicBool,
    busy: Busy,
}

/// What ends a task's wait when something arrived for it from outside - or the run's, for whoever halts it.
#[derive(Clone, Default)]
pub struct Wake {
    ring: Option<Arc<Ring>>,
    halt: Option<Arc<Notify>>,
}

impl Wake {
    /// Something arrived.
    pub fn ring(&self) {
        if let Some(ring) = &self.ring
            && !ring.gone.load(Ordering::SeqCst)
            && !ring.rung.swap(true, Ordering::SeqCst)
        {
            ring.busy.up();
            ring.notify.notify_one();
        }
        if let Some(halt) = &self.halt {
            halt.notify_one();
        }
    }
}

/// Where a task waits for what arrives from outside.
pub struct Arrived {
    ring: Arc<Ring>,
    events: Events,
}

impl Arrived {
    /// What whoever hands the task an arrival rings.
    pub fn wake(&self) -> Wake {
        Wake {
            ring: Some(self.ring.clone()),
            halt: None,
        }
    }

    /// Wait until something arrived.
    pub async fn wait(&mut self) {
        self.events.rest();
        self.ring.notify.notified().await;
        self.ring.rung.store(false, Ordering::SeqCst);
        self.events.took();
    }
}

impl Drop for Arrived {
    fn drop(&mut self) {
        self.ring.gone.store(true, Ordering::SeqCst);
        if self.ring.rung.swap(false, Ordering::SeqCst) {
            self.ring.busy.down();
        }
    }
}

/// WHAT A TASK IS HANDED WITH WHAT WOKE IT: the instant it stands at, where it says what it did, and the agent's
/// life to keep or let go.
pub struct Turn<'a> {
    pub now: DateTime,
    pub agent: &'a str,
    events: &'a Events,
    next: Option<DateTime>,
    /// The activity this turn ended last: what the graphs it wrote are said of.
    last: Option<NamedNode>,
}

impl Turn<'_> {
    /// WHAT THE TASK DID OF WHAT WOKE IT: the graphs it wrote, told to whoever hears their kinds, before the events
    /// it said are.
    pub fn done(&mut self, wrote: Result<Vec<String>, Error>) -> Result<(), Error> {
        let wrote = wrote?;
        self.wrote(&wrote);
        self.events.wrote(wrote)
    }

    /// Say whose `graphs` are, where anybody watches and an activity of this turn wrote them.
    fn wrote(&self, graphs: &[String]) {
        if let Some(by) = &self.last
            && !graphs.is_empty()
            && self.events.0.watch.connected()
        {
            self.events.0.watch.emit(&Wrote {
                by: by.clone(),
                graphs: graphs.to_vec(),
            });
        }
    }

    /// One thing done of several in this turn - what a package queued for itself, each in turn: the graphs it wrote
    /// told, then the events it said, before the next is done.
    pub fn told(&mut self, wrote: Vec<String>) -> Result<(), Error> {
        self.wrote(&wrote);
        let told = self.events.wrote(wrote);
        let said = TURN
            .try_with(|turn| std::mem::take(&mut turn.borrow_mut().said))
            .unwrap_or_default();
        for heard in said {
            self.events.tell(heard);
        }
        told
    }

    /// The task is next due at `at`, with nothing heard: it waits no longer than that.
    pub fn wake_at(&mut self, at: DateTime) {
        if self.next.is_none_or(|s| at < s) {
            self.next = Some(at);
        }
    }

    /// When the task said it is next due.
    pub fn next(&self) -> Option<DateTime> {
        self.next
    }

    /// The task's policy decides again at once, with nothing heard: it is due at the next instant, a millisecond on,
    /// since two decisions never stand at one instant - a search cut short is continued from where the clock then
    /// reads, and where a test pauses the clock nothing else would move it.
    pub fn again(&mut self) {
        let next = self
            .now
            .checked_add_day_time_duration(crate::clock::microseconds(0.001));
        self.wake_at(next.unwrap_or(self.now));
    }

    /// Begin an activity of `kind`, triggered by the entities `triggers` names - what the events heard were about -
    /// and say that it started.
    pub fn begin(&mut self, kind: &'static str, triggers: &[NamedNode]) -> Activity {
        let activity = Activity::begin(kind);
        if self.events.0.watch.connected() {
            self.events.0.watch.emit(&Started {
                activity: activity.node.clone(),
                kind,
                triggers: triggers.to_vec(),
                at: self.now,
            });
        }
        activity
    }

    /// Say `event` happened, to whoever watches the agent.
    pub fn emit(&self, event: &dyn Event) {
        self.events.0.watch.emit(event);
    }

    /// End `activity`, and say that it ended.
    pub fn end(&mut self, activity: Activity) {
        self.last = Some(activity.node.clone());
        if self.events.0.watch.connected() {
            self.events.0.watch.emit(&Ended {
                activity: activity.node.clone(),
                kind: activity.kind,
                at: self.now,
                duration_s: activity.took(),
            });
        }
    }

    /// Mark the end of a part of the stretch, for its event, where anybody watches.
    pub fn lap(&mut self, part: &str) {
        self.events.lap(part);
    }

    /// `who` keeps the agent running.
    pub fn hold(&mut self, who: &str) {
        let mut held = self.events.0.held.lock().expect("holders nobody poisoned");
        held.insert(who.to_string(), ());
    }

    /// `who` no longer keeps the agent running, and says how it ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.events.0.held.lock().expect("holders nobody poisoned").remove(who);
        if let Some(outcome) = outcome {
            *self.events.0.outcome.lock().expect("an outcome nobody poisoned") = Some(outcome.to_string());
        }
    }
}

/// WHAT REACHES OUTSIDE THE AGENT, by its type: the connectors a deployment makes from its environment, and a test
/// hands in - a bus, a web, a bot, a model, a sink. A package takes the one it knows, where one was handed.
#[derive(Clone, Default)]
pub struct Outside(Arc<Mutex<HashMap<TypeId, Box<dyn Any + Send>>>>);

impl Outside {
    /// Hand `thing` to whichever package takes its type.
    pub fn hand<T: Any + Send>(&self, thing: T) {
        let mut held = self.0.lock().expect("an outside nobody poisoned");
        held.insert(TypeId::of::<T>(), Box::new(thing));
    }

    /// Take what was handed of type `T`, where anything was: it is the taker's from now on.
    pub fn take<T: Any + Send>(&self) -> Option<T> {
        let mut held = self.0.lock().expect("an outside nobody poisoned");
        held.remove(&TypeId::of::<T>())
            .and_then(|thing| thing.downcast().ok())
            .map(|thing| *thing)
    }
}

/// WHAT THE AGENT KEEPS OF WHAT HAPPENED, as a chat reads it: its journal where it lies, and its two series. Handed
/// outside by whoever runs the agent, where it keeps any.
#[derive(Default)]
pub struct Reads {
    pub journal: Option<oxigraph::store::Store>,
    pub history: Option<crate::series::Reader>,
    pub metrics: Option<crate::series::Reader>,
}

/// WHAT A PACKAGE'S TASK IS HANDED, plain: the agent's store, its id, the clock, the events, what reaches outside,
/// and the packages the agent loads.
#[derive(Clone)]
pub struct Handed {
    pub store: Store,
    pub id: String,
    pub clock: Arc<dyn Clock>,
    pub events: Events,
    pub outside: Outside,
    pub loaded: Arc<Vec<String>>,
    stop: watch::Receiver<bool>,
    /// The package this was handed to, and the lifecycle it starts in.
    me: String,
    life: Arc<Mutex<Life>>,
}

/// THE LIFECYCLE THE PACKAGES START IN, shared by every package's start. While the boot is `deciding`, each package
/// decides whether it joins, and `begun` is the boot its documents are brought into; a package still asking when a
/// round of asking changed nothing is told the asking has `settled`, and declines. Once every package has decided
/// the boot is finished, and the starts go on to make their cores, each `started` as its start ends.
#[derive(Default)]
struct Life {
    deciding: bool,
    settled: bool,
    decided: BTreeMap<String, bool>,
    started: BTreeMap<String, bool>,
    begun: Option<crate::boot::Begun>,
    moved: u64,
}

/// A PACKAGE STARTING, or STARTED: the two events of a package's lifecycle, said by the kernel to whoever watches
/// the agent as a package's start begins and as it ends, so the journal keeps which packages run and a package
/// that needs another started may wait for it (`Handed::started`).
pub struct Lifecycle {
    pub package: String,
    pub started: bool,
    pub at: DateTime,
}

pub const PACKAGE_STARTING: &str = "http://example.org/orexis#PackageStarting";
pub const PACKAGE_STARTED: &str = "http://example.org/orexis#PackageStarted";
const PACKAGE: &str = "http://example.org/orexis#package";

impl Event for Lifecycle {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<oxigraph::model::Triple>> {
        let class = if self.started {
            PACKAGE_STARTED
        } else {
            PACKAGE_STARTING
        };
        Some(vec![
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                NamedNode::new_unchecked(class),
            ),
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked(PACKAGE),
                oxigraph::model::Literal::new_simple_literal(&self.package),
            ),
        ])
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(if self.started {
            PACKAGE_STARTED
        } else {
            PACKAGE_STARTING
        })
    }
}

impl Handed {
    /// A turn at the instant the clock reads.
    pub fn turn(&self) -> Turn<'_> {
        Turn {
            now: self.clock.now(),
            agent: &self.id,
            events: &self.events,
            next: None,
            last: None,
        }
    }

    /// Where the task waits for what arrives from outside, and what rings it.
    pub fn arrived(&self) -> Arrived {
        Arrived {
            ring: Arc::new(Ring {
                notify: Notify::new(),
                rung: AtomicBool::new(false),
                gone: AtomicBool::new(false),
                busy: self.events.0.busy.clone(),
            }),
            events: self.events.clone(),
        }
    }

    /// Wait until the clock reads `at`, at its pace; for ever where no instant is given.
    pub async fn sleep_until(&self, at: Option<DateTime>) {
        self.events.rest();
        let Some(at) = at else {
            return std::future::pending().await;
        };
        let ahead = at.checked_sub(self.clock.now()).map_or(0.0, crate::clock::seconds_of);
        tokio::time::sleep(self.clock.real_delay(ahead.max(0.0))).await;
        self.events.woke();
    }

    /// DECIDE WHETHER THIS PACKAGE JOINS THE AGENT, and wait until every package has: the first thing a package's
    /// start does. `needed` is the package's own reason - the role the self plays, what the world wires - asked of
    /// the store as it stands, and asked again whenever another package joined, since a package that joins brings
    /// the ontology that may put a role beneath this one's. Joined, its documents are brought into the boot
    /// (`boot::Begun::bring`); still not needed when the asking has settled, it declines, and its start ends there.
    pub async fn joins(&self, needed: impl Fn(&Handed) -> Result<bool, Error>) -> Result<bool, Error> {
        let joined = std::future::poll_fn(|_| self.decide(&needed)).await?;
        if joined {
            std::future::poll_fn(|_| {
                if self.life().deciding {
                    std::task::Poll::Pending
                } else {
                    std::task::Poll::Ready(())
                }
            })
            .await;
        }
        Ok(joined)
    }

    fn life(&self) -> std::sync::MutexGuard<'_, Life> {
        self.life.lock().expect("a lifecycle nobody poisoned")
    }

    fn decide(&self, needed: &impl Fn(&Handed) -> Result<bool, Error>) -> std::task::Poll<Result<bool, Error>> {
        use std::task::Poll;
        if let Some(decided) = self.life().decided.get(&self.me) {
            return Poll::Ready(Ok(*decided));
        }
        match needed(self) {
            Err(e) => Poll::Ready(Err(e)),
            Ok(true) => {
                let mut life = self.life();
                if let Some(begun) = life.begun.as_mut()
                    && let Err(e) = begun.bring(&self.store, &self.me)
                {
                    return Poll::Ready(Err(e));
                }
                life.decided.insert(self.me.clone(), true);
                life.moved += 1;
                Poll::Ready(Ok(true))
            }
            Ok(false) => {
                let mut life = self.life();
                if life.settled {
                    life.decided.insert(self.me.clone(), false);
                    life.moved += 1;
                    Poll::Ready(Ok(false))
                } else {
                    Poll::Pending
                }
            }
        }
    }

    /// Join where the self plays a role of one of `roles`, the package's own classes (`joins`).
    pub async fn plays(&self, roles: &[&str]) -> Result<bool, Error> {
        self.joins(|handed| crate::boot::plays(&handed.store, roles)).await
    }

    /// Join where `package` has (`joins`): what keeps house for another package runs where that one does.
    pub async fn beside(&self, package: &str) -> Result<bool, Error> {
        self.joins(|handed| Ok(handed.joined(package))).await
    }

    /// Whether `package` has joined, as far as is decided.
    pub fn joined(&self, package: &str) -> bool {
        self.life().decided.get(package).copied().unwrap_or(false)
    }

    /// WAIT UNTIL `package` HAS STARTED - its start ended, its core made - and answer whether it runs: false where
    /// it declined, or is no package of this binary. For a package whose own start needs what another's made.
    pub async fn started(&self, package: &str) -> bool {
        std::future::poll_fn(|_| {
            let life = self.life();
            match (life.started.get(package), life.decided.get(package)) {
                (Some(started), _) => std::task::Poll::Ready(*started),
                (None, Some(false)) => std::task::Poll::Ready(false),
                (None, None) if !life.deciding => std::task::Poll::Ready(false),
                _ => std::task::Poll::Pending,
            }
        })
        .await
    }

    /// Wait until the run is over: the task stops itself.
    pub async fn stopped(&self) {
        self.events.rest();
        let mut stop = self.stop.clone();
        let _ = stop.wait_for(|stopped| *stopped).await;
    }
}

/// A task: what a package's start answers, to be spawned.
pub type Task = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A package's start, running: it ends in the package's task, or in nothing.
pub type Starting = Pin<Box<dyn Future<Output = Result<Option<Task>, Error>> + Send>>;

/// A PACKAGE, AS IT REGISTERS ITSELF: its name, THE DOCUMENTS IT BRINGS - its ontology, its rules, its actions, each
/// a file of its crate compiled into the binary (`documents!`) and put in the store as the package joins - and ITS
/// START, which every package this binary holds is given. A start first decides whether the agent runs the package
/// (`Handed::joins`, `plays`, `beside`), by a reason the package knows and the kernel does not; declined, it ends
/// in nothing; joined, it waits for what it needs started (`Handed::started`), makes its core from what it is
/// handed and answers its task - or nothing, where what it is handed gives it nothing to do. A START DOES NOTHING
/// BEFORE IT HAS JOINED: the boot runs every start as far as its decision and no further (`decide`).
pub struct Package {
    pub name: &'static str,
    pub documents: &'static [(&'static str, &'static str)],
    pub start: fn(Handed) -> Starting,
}

inventory::collect!(Package);

/// THE DOCUMENTS A PACKAGE BRINGS, each named as the file of its crate it is: `documents!("ontology.ttl", "rules.ttl")`
/// is each file's name with its text, read as the crate is compiled. So a binary holds the documents of the packages
/// built into it and of no other, and the boot reads no tree.
#[macro_export]
macro_rules! documents {
    ($($name:literal),* $(,)?) => {
        &[$(($name, include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/", $name)))),*]
    };
}

/// An agent's tasks, running.
pub struct Running {
    pub handed: Handed,
    names: Vec<String>,
    joins: Vec<tokio::task::JoinHandle<()>>,
    stop: watch::Sender<bool>,
    /// RAISED TO STOP THE RUN, by a signal the process was sent.
    pub halt: Option<Arc<AtomicBool>>,
    halted: Arc<Notify>,
}

/// THE START OF A PACKAGE THAT JOINS NO AGENT OF ITSELF: it declines as a boot asks, and where whoever starts the
/// agent names it, it is made by `make`. A test's member, which no role loads.
pub fn named(handed: Handed, make: fn(&Handed) -> Result<Option<Task>, Error>) -> Starting {
    Box::pin(async move {
        if !handed.joins(|_| Ok(false)).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

/// Every package this binary holds, in the order they start.
fn every() -> Vec<String> {
    crate::boot::every_package()
}

/// DECIDE WHICH PACKAGES `agent` RUNS, over a boot `begun`: every package this binary holds is given its start, and
/// each start is run as far as its decision (`Handed::joins`) and no further. They are asked in the order they
/// start, round after round, since one that joins brings the ontology another's role may be beneath; a round in
/// which nothing changed settles the asking, and those still asking decline. Then the boot is finished, and the
/// packages that joined are answered. The starts are dropped where they wait: no core is made and nothing runs.
pub fn decide(store: &Store, agent: &str, begun: crate::boot::Begun) -> Result<Vec<String>, Error> {
    let (_stop, stopped) = watch::channel(false);
    let life = Arc::new(Mutex::new(Life {
        deciding: true,
        begun: Some(begun),
        ..Life::default()
    }));
    let handed = Handed {
        store: store.clone(),
        id: agent.to_string(),
        clock: Arc::new(crate::clock::Manual::at(DateTime::now())),
        events: Events::new(store),
        outside: Outside(Arc::new(Mutex::new(HashMap::new()))),
        loaded: Arc::new(Vec::new()),
        stop: stopped,
        me: String::new(),
        life: life.clone(),
    };
    let names = every();
    let mut starting: Vec<(String, Option<Starting>)> = Vec::new();
    for name in &names {
        let package = inventory::iter::<Package>()
            .find(|p| p.name == name)
            .expect("a package found is registered");
        starting.push((
            name.clone(),
            Some((package.start)(Handed {
                me: name.clone(),
                ..handed.clone()
            })),
        ));
    }
    let mut context = std::task::Context::from_waker(std::task::Waker::noop());
    loop {
        let before = handed.life().moved;
        for (name, start) in starting.iter_mut() {
            if handed.life().decided.contains_key(name) {
                continue;
            }
            let Some(running) = start.as_mut() else { continue };
            if let std::task::Poll::Ready(ended) = running.as_mut().poll(&mut context) {
                //  A START THAT ENDED BEFORE THE BOOT DID declined, or failed.
                ended?;
                *start = None;
                let mut life = handed.life();
                life.decided.entry(name.clone()).or_insert(false);
                life.moved += 1;
            }
        }
        let mut life = handed.life();
        if names.iter().all(|n| life.decided.contains_key(n)) {
            break;
        }
        if life.moved == before {
            if life.settled {
                return Err(Error::Evaluation(
                    "a package's start waits, before it has decided, for what never comes".into(),
                ));
            }
            life.settled = true;
        }
    }
    let loaded: Vec<String> = {
        let life = handed.life();
        names.iter().filter(|n| life.decided[*n]).cloned().collect()
    };
    let begun = handed.life().begun.take().expect("the boot it was begun with");
    drop(starting);
    begun.finish(store, &loaded)?;
    Ok(loaded)
}

/// START THE AGENT `id` over `store`: each package of `names` that registered itself is started, in that order, and
/// its task spawned on the Tokio runtime this is called in. A name no package registered under is an error: its
/// crate was not built in.
pub fn start(
    store: &Store,
    id: &str,
    clock: Arc<dyn Clock>,
    outside: Outside,
    names: &[String],
) -> Result<Running, Error> {
    started();
    let (stop, stopped) = watch::channel(false);
    let handed = Handed {
        store: store.clone(),
        id: id.to_string(),
        clock,
        events: Events::new(store),
        outside,
        loaded: Arc::new(names.to_vec()),
        stop: stopped,
        me: String::new(),
        life: Arc::new(Mutex::new(Life {
            decided: every().into_iter().map(|p| (p.clone(), names.contains(&p))).collect(),
            ..Life::default()
        })),
    };
    let mut running = Running {
        handed: handed.clone(),
        names: Vec::new(),
        joins: Vec::new(),
        stop,
        halt: None,
        halted: Arc::new(Notify::new()),
    };
    for name in names {
        let Some(package) = inventory::iter::<Package>().find(|p| p.name == name) else {
            return Err(Error::Evaluation(format!(
                "no package registered itself as {name}: this binary was built without it"
            )));
        };
        //  ITS START, run to its end here: joined already, it waits only for a package started before it.
        handed.events.0.watch.emit(&Lifecycle {
            package: name.clone(),
            started: false,
            at: handed.clock.now(),
        });
        let mut starting = (package.start)(Handed {
            me: name.clone(),
            ..handed.clone()
        });
        let ended = match starting
            .as_mut()
            .poll(&mut std::task::Context::from_waker(std::task::Waker::noop()))
        {
            std::task::Poll::Ready(ended) => ended?,
            std::task::Poll::Pending => {
                return Err(Error::Evaluation(format!(
                    "{name} waits, as it starts, for a package that starts after it or for what never comes"
                )));
            }
        };
        handed.life().started.insert(name.clone(), true);
        handed.events.0.watch.emit(&Lifecycle {
            package: name.clone(),
            started: true,
            at: handed.clock.now(),
        });
        let Some(task) = ended else {
            continue;
        };
        let events = handed.events.clone();
        //  A TASK IS BUSY FROM ITS START until it first waits: the run is not over before every policy decided once.
        events.0.busy.up();
        let scoped = TURN.scope(
            RefCell::new(Local {
                said: Vec::new(),
                in_hand: 1,
            }),
            async move {
                if let Err(e) = task.await {
                    events.failed(e);
                }
                events.rest();
            },
        );
        running.names.push(name.clone());
        running.joins.push(tokio::spawn(scoped));
    }
    Ok(running)
}

impl Running {
    /// The packages whose tasks run, in the order they started.
    pub fn parts(&self) -> Vec<&str> {
        self.names.iter().map(String::as_str).collect()
    }

    /// Whoever watches the agent: what a test or a tool connects to, to hear everything its packages say.
    pub fn watch(&self) -> &Watch {
        self.handed.events.watch()
    }

    /// What ends the run's wait, for whoever halts the run from outside it.
    pub fn wake(&self) -> Wake {
        Wake {
            ring: None,
            halt: Some(self.halted.clone()),
        }
    }

    fn halted(&self) -> bool {
        self.halt.as_ref().is_some_and(|h| h.load(Ordering::Relaxed))
    }

    fn checked(&self) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        match bus.error.lock().expect("an error nobody poisoned").take() {
            Some(e) => Err(e),
            None => Ok(()),
        }
    }

    /// Whether no task is busy now.
    pub fn idle(&self) -> bool {
        *self.handed.events.0.busy.0.borrow() == 0
    }

    /// Wait until no task is busy: everything said was heard and done with, and the stretch said where anybody
    /// watches. A task's failure is the run's.
    pub async fn settled(&self) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        let mut seen = bus.busy.0.subscribe();
        let _ = seen.wait_for(|n| *n == 0).await;
        self.checked()?;
        self.passed(bus.busy.began().elapsed().as_secs_f64())
    }

    /// UNTIL NOTHING HOLDS THE AGENT, ending as the last to let go said, or it is halted, `unfinished`. Each stretch
    /// with something busy is said as it ends, where anybody watches.
    pub async fn released(&self) -> Result<String, Error> {
        let bus = &self.handed.events.0;
        let mut seen = bus.busy.0.subscribe();
        loop {
            //  UNTIL NOTHING IS BUSY, OR THE RUN IS HALTED WHILE SOMETHING STILL IS: a signal stops an agent that
            //  never comes to rest.
            tokio::select! {
                _ = seen.wait_for(|n| *n == 0) => {}
                _ = self.halted.notified() => {}
            }
            self.checked()?;
            self.passed(bus.busy.began().elapsed().as_secs_f64())?;
            if self.halted() {
                log::info!("{}: stopped", self.handed.id);
                return Ok(UNFINISHED.to_string());
            }
            if bus.held.lock().expect("holders nobody poisoned").is_empty() {
                log::info!("{}: nothing holds it", self.handed.id);
                let outcome = bus.outcome.lock().expect("an outcome nobody poisoned").clone();
                return Ok(outcome.unwrap_or_else(|| MET.to_string()));
            }
            //  ANY CHANGE, so a task that woke and was done between two looks is still a stretch it sees.
            tokio::select! {
                _ = seen.changed() => {}
                _ = self.halted.notified() => {}
            }
            if self.halted() {
                log::info!("{}: stopped", self.handed.id);
                return Ok(UNFINISHED.to_string());
            }
        }
    }

    /// Say the stretch, where anybody watches.
    fn passed(&self, took: f64) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        if !bus.watch.connected() {
            return Ok(());
        }
        let laps = bus
            .laps
            .lock()
            .expect("laps nobody poisoned")
            .take()
            .unwrap_or_default();
        let quads = i64::try_from(self.handed.store.len()?).ok();
        bus.watch.emit(&Passed {
            duration_s: round6(took),
            laps: laps.spent,
            quads,
            uptime_s: (started().elapsed().as_secs_f64() * 1000.0).round() / 1000.0,
        });
        Ok(())
    }

    /// Stop every task, each stopping itself where it waits, and wait for them to end.
    pub async fn stop(self) {
        let _ = self.stop.send(true);
        for join in self.joins {
            let _ = join.await;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::{Elapsing, seconds};

    const STEP: &str = "http://example.org/test#Stepping";

    /// What a test's packages write down, handed outside.
    type Seen = Arc<Mutex<Vec<String>>>;

    fn noon() -> DateTime {
        "2026-11-12T12:00:00Z".parse().unwrap()
    }

    fn running(names: &[&str], seen: &Seen) -> Running {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let outside = Outside::default();
        outside.hand(seen.clone());
        let names: Vec<String> = names.iter().map(|n| n.to_string()).collect();
        start(&store, "urn:test:me", Arc::new(Elapsing::from(noon())), outside, &names).unwrap()
    }

    fn seen_by(handed: &Handed) -> Seen {
        handed
            .outside
            .take::<Seen>()
            .inspect(|s| handed.outside.hand(s.clone()))
            .unwrap()
    }

    //  BEGINS AND ENDS AN ACTIVITY as the run begins, writes down that it did, and then that it waited.
    inventory::submit! { Package { name: "test/begins", documents: &[], start: |handed| named(handed, |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        Ok(Some(Box::pin(async move {
            let mut turn = handed.turn();
            let activity = turn.begin(STEP, &[]);
            turn.end(activity);
            seen.lock().unwrap().push("begun".into());
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    //  HEARS EVERY START said, and writes each down.
    inventory::submit! { Package { name: "test/hears", documents: &[], start: |handed| named(handed, |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        let mut hears = handed.events.hears();
        hears.event(crate::activity::STARTED, 7);
        Ok(Some(Box::pin(async move {
            loop {
                let woke = tokio::select! {
                    biased;
                    _ = handed.stopped() => break,
                    woke = hears.next() => woke,
                };
                match woke {
                    Some(Woke::Event(tag, event)) => {
                        let kind = event.activity.map(|(_, k)| k).unwrap_or_default();
                        seen.lock().unwrap().push(format!("heard {tag} {kind}"));
                    }
                    _ => break,
                }
            }
            Ok(())
        })))
    }) } }

    //  HOLDS THE AGENT, and lets it go an hour on by the clock.
    inventory::submit! { Package { name: "test/holds", documents: &[], start: |handed| named(handed, |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        Ok(Some(Box::pin(async move {
            let mut turn = handed.turn();
            turn.hold("holds");
            let at = turn.now.checked_add_day_time_duration(seconds(3600.0)).unwrap();
            handed.sleep_until(Some(at)).await;
            let mut turn = handed.turn();
            seen.lock().unwrap().push(crate::clock::isoformat(turn.now));
            turn.release("holds", Some(PLANNED));
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    //  WAITS FOR AN ARRIVAL, rung from outside the agent a moment after the run begins, and holds until then.
    inventory::submit! { Package { name: "test/arrives", documents: &[], start: |handed| named(handed, |handed| {
        let (handed, seen) = (handed.clone(), seen_by(handed));
        let mut arrived = handed.arrived();
        let wake = arrived.wake();
        tokio::spawn(async move {
            tokio::time::sleep(std::time::Duration::from_secs(5)).await;
            wake.ring();
        });
        Ok(Some(Box::pin(async move {
            handed.turn().hold("arrives");
            arrived.wait().await;
            seen.lock().unwrap().push("arrived".into());
            handed.turn().release("arrives", None);
            handed.stopped().await;
            Ok(())
        })))
    }) } }

    #[tokio::test(start_paused = true)]
    async fn an_activitys_start_is_heard_by_class_once_its_sayer_waits() {
        let seen = Seen::default();
        let running = running(&["test/begins", "test/hears"], &seen);
        running.settled().await.unwrap();
        assert_eq!(*seen.lock().unwrap(), ["begun", &format!("heard 7 {STEP}")]);
        assert_eq!(running.parts(), ["test/begins", "test/hears"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn nobody_hearing_connects_nothing() {
        let seen = Seen::default();
        let running = running(&["test/begins"], &seen);
        running.settled().await.unwrap();
        assert!(
            !running.handed.events.watch().connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn the_run_ends_when_nothing_holds_the_agent_as_the_last_to_let_go_said() {
        let seen = Seen::default();
        let running = running(&["test/holds"], &seen);
        let began = std::time::Instant::now();
        assert_eq!(running.released().await.unwrap(), PLANNED);
        assert_eq!(
            *seen.lock().unwrap(),
            ["2026-11-12T13:00:00+00:00"],
            "an hour on, by the clock"
        );
        assert!(
            began.elapsed() < std::time::Duration::from_secs(5),
            "and no hour waited"
        );
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn an_arrival_from_outside_ends_the_tasks_wait() {
        let seen = Seen::default();
        let running = running(&["test/arrives"], &seen);
        assert_eq!(running.released().await.unwrap(), MET);
        assert_eq!(*seen.lock().unwrap(), ["arrived"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn a_halt_ends_the_run_unfinished() {
        let seen = Seen::default();
        let mut running = running(&["test/holds"], &seen);
        let halt = Arc::new(AtomicBool::new(true));
        running.halt = Some(halt);
        running.wake().ring();
        assert_eq!(running.released().await.unwrap(), UNFINISHED);
        running.stop().await;
    }

    /// Three graphs written in one turn, two of a kind a task hears and one of another: the task is told the two
    /// together, once, in the order they were written, and nothing of the third.
    #[test]
    fn what_one_turn_wrote_of_a_kind_is_told_as_one_thing() {
        use crate::ontology::{BELIEF, CATALOGUE_GRAPH};
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . \
                 <urn:test:one> a orexis:BeliefGraph . <urn:test:other> a orexis:ActionGraph . \
                 <urn:test:two> a orexis:BeliefGraph }} }}"
            ))
            .unwrap();
        let events = Events::new(&store);
        let mut hears = events.hears();
        hears.graph(BELIEF, 3);
        let written = ["urn:test:one", "urn:test:other", "urn:test:two"];
        events.wrote(written.iter().map(|g| g.to_string()).collect()).unwrap();
        assert_eq!(
            hears.inbox.try_recv().ok(),
            Some(Woke::Graphs(
                3,
                vec!["urn:test:one".to_string(), "urn:test:two".to_string()]
            ))
        );
        assert!(hears.inbox.try_recv().is_err(), "told once");
    }

    #[test]
    fn a_package_nobody_registered_is_refused() {
        let tasks = tokio::runtime::Builder::new_current_thread().build().unwrap();
        let _entered = tasks.enter();
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Arc::new(crate::clock::Manual::at(noon()));
        let refused = start(
            &store,
            "urn:test:me",
            clock,
            Outside::default(),
            &["test/absent".to_string()],
        );
        assert!(refused.is_err());
    }
}
