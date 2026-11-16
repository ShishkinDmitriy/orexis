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
use std::collections::{BTreeMap, BTreeSet, HashMap};
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
    /// When the task's start began, whether it has decided whether its package runs, and whether it has said it
    /// made its core.
    began: Option<DateTime>,
    decided: bool,
    made: bool,
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
/// When the stretch with something busy began, and how long the last one took, said AS IT ENDED: a task waking before
/// whoever says the stretch looks begins the next, and the length is never read off its beginning.
struct Busy(
    Arc<watch::Sender<usize>>,
    Arc<Mutex<std::time::Instant>>,
    Arc<Mutex<f64>>,
);

impl Busy {
    fn new() -> Self {
        Busy(
            Arc::new(watch::channel(0).0),
            Arc::new(Mutex::new(std::time::Instant::now())),
            Arc::new(Mutex::new(0.0)),
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
        self.0.send_modify(|n| {
            *n = n.saturating_sub(1);
            if *n == 0 {
                *self.2.lock().expect("a length nobody poisoned") = self.began().elapsed().as_secs_f64();
            }
        });
    }

    /// How long the stretch took: the last, as it ended, or where something is busy still, so far.
    fn took(&self) -> f64 {
        if *self.0.borrow() == 0 {
            *self.2.lock().expect("a length nobody poisoned")
        } else {
            self.began().elapsed().as_secs_f64()
        }
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

    /// WHAT THE TASK SAID IS TOLD, and it stays busy: what a start waiting on the other starts does, its sayings heard
    /// as when it rests, while it is still counted as starting.
    fn spoke(&self) {
        let said = TURN.try_with(|turn| std::mem::take(&mut turn.borrow_mut().said));
        for heard in said.unwrap_or_default() {
            self.tell(heard);
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

    /// `thing` handed, and what is handed: for whoever runs the agent, handing several in one expression.
    #[must_use]
    pub fn with<T: Any + Send>(self, thing: T) -> Self {
        self.hand(thing);
        self
    }

    /// What was handed of type `T` changed by `change`, a default one handed first where nothing was: for what several
    /// packages each add to, whichever starts first, so no package's addition is lost to another's.
    pub fn alter<T: Any + Send + Default>(&self, change: impl FnOnce(&mut T)) {
        let mut held = self.0.lock().expect("an outside nobody poisoned");
        let thing = held.entry(TypeId::of::<T>()).or_insert_with(|| Box::new(T::default()));
        if let Some(thing) = thing.downcast_mut::<T>() {
            change(thing);
        }
    }

    /// Whether anything of type `T` is handed, taking nothing.
    pub fn has<T: Any + Send>(&self) -> bool {
        self.0
            .lock()
            .expect("an outside nobody poisoned")
            .contains_key(&TypeId::of::<T>())
    }

    /// What was handed of type `T`, read and left where it is.
    pub fn read<T: Any + Send + Clone>(&self) -> Option<T> {
        self.0
            .lock()
            .expect("an outside nobody poisoned")
            .get(&TypeId::of::<T>())
            .and_then(|thing| thing.downcast_ref::<T>())
            .cloned()
    }

    /// What was handed of type `T`, shared: read and left where it is, and where nothing was handed, a default one
    /// handed now. For what several packages each add to or read, whichever starts first.
    pub fn share<T: Any + Send + Clone + Default>(&self) -> T {
        let mut held = self.0.lock().expect("an outside nobody poisoned");
        if let Some(thing) = held.get(&TypeId::of::<T>()).and_then(|thing| thing.downcast_ref::<T>()) {
            return thing.clone();
        }
        let thing = T::default();
        held.insert(TypeId::of::<T>(), Box::new(thing.clone()));
        thing
    }

    /// Take what was handed of type `T`, where anything was: it is the taker's from now on.
    pub fn take<T: Any + Send>(&self) -> Option<T> {
        let mut held = self.0.lock().expect("an outside nobody poisoned");
        held.remove(&TypeId::of::<T>())
            .and_then(|thing| thing.downcast().ok())
            .map(|thing| *thing)
    }
}

/// THE AGENT IS DEPLOYED: handed outside by whoever runs it for good, and by no check and no test. Where it is
/// handed, a package makes for itself what it was not handed, from what the world says: its journal, its archive.
/// Where it is not, a package handed nothing has nothing, so a check reaches no disk and no port. It says the one
/// thing whoever runs the agent knows and no document states: the name of the world's directory, which its buckets
/// and its metrics' points go by.
#[derive(Clone, Default)]
pub struct Deployed {
    pub world: String,
}

/// THE AGENT IS BEING CHECKED: handed outside by whoever checks an agent before anything is granted, and by no run
/// and no test of a run. A package handed it says, as it makes its core, the two things a check asks of every
/// package and no document states alone: that it HOLDS the agent, which then runs for as long as its process
/// does, and why it REFUSES the world as posed. The kernel knows neither reason; whoever checks reads what was found.
#[derive(Clone, Default)]
pub struct Checking(Arc<Mutex<Found>>);

/// What the packages of a checked agent said: which hold it, and each reason one refuses the world as posed.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Found {
    pub held: Vec<String>,
    pub refused: Vec<String>,
}

impl Checking {
    /// The package `who` holds the agent: it does not finish while this stands.
    pub fn holds(&self, who: &str) {
        self.0.lock().unwrap().held.push(who.to_string());
    }

    /// The world as posed is refused, and `why`, in the saying package's words.
    pub fn refuses(&self, why: String) {
        self.0.lock().unwrap().refused.push(why);
    }

    /// What was said so far.
    pub fn found(&self) -> Found {
        self.0.lock().unwrap().clone()
    }
}

/// What keeps a line of the process's log: its logger, its level and its message.
pub type Remark = Box<dyn Fn(&str, log::Level, &str) + Send + Sync>;

/// THE PROCESS'S LOG, for whoever keeps it: handed outside by whoever owns the log, and called once by the package
/// that keeps it, with how each line is kept. What was said before is kept first.
pub struct Said(pub Box<dyn FnOnce(Remark) + Send>);

/// WHERE THE AGENT'S JOURNAL LIES, said by whoever keeps it whenever that starts, and asked by a reader when it
/// reads: so no reader waits for a keeper's start, and no order between them is kept. What archives the journal
/// says the archive, after the journal it waits for said itself.
#[derive(Clone, Default)]
pub struct Journaled(Arc<Mutex<Option<oxigraph::store::Store>>>);

impl Journaled {
    /// The journal lies in `store` from now on.
    pub fn lies_in(&self, store: oxigraph::store::Store) {
        *self.0.lock().unwrap() = Some(store);
    }

    /// Where it lies now, or None where nobody keeps one.
    pub fn now(&self) -> Option<oxigraph::store::Store> {
        self.0.lock().unwrap().clone()
    }
}

/// WHAT THE AGENT KEEPS OF WHAT HAPPENED, as a chat reads it: its journal where it lies, and its two series. Each
/// package that keeps any of it says so outside as it makes its core (`Outside::alter`), the journal's where it lies
/// and each series' package the sink it writes, and a reader reads it once every core is made.
#[derive(Clone, Default)]
pub struct Reads {
    pub journal: Journaled,
    pub history: Option<crate::series::Reader>,
    pub metrics: Option<crate::series::Reader>,
}

/// WHAT A PACKAGE'S TASK IS HANDED: the agent's services, and nothing of its own - its store, its id, the clock, the
/// events, what reaches outside, and the run it is part of. Every package is handed the same.
#[derive(Clone)]
pub struct Handed {
    pub store: Store,
    pub id: String,
    pub clock: Arc<dyn Clock>,
    pub events: Events,
    pub outside: Outside,
    run: Run,
}

/// THE RUN THE PACKAGES ARE PART OF, a service each is handed: the signal that stops it, HOW MANY STARTS ARE STILL
/// MAKING THEIR CORE, which every package waits on before it goes on so each listens before any speaks, the packages
/// that said they started, in the order they did, and what is owed once every task has ended. It names no package
/// but as one says it started.
#[derive(Clone)]
struct Run {
    stop: watch::Receiver<bool>,
    making: Arc<Gate<usize>>,
    started: Arc<Mutex<Vec<String>>>,
    ending: Arc<Mutex<Vec<Ending>>>,
    boot: Arc<Mutex<Boot>>,
    finished: Arc<Gate<bool>>,
    cores: Arc<Gate<BTreeSet<String>>>,
}

/// THE BOOT AS THE STARTS FINISH IT: what is begun and not yet finished, where the agent was booted by `boot`; how many
/// starts have not yet decided whether their package runs; the packages that joined and brought their documents; each
/// role class the self plays by the package that serves it, its own documents declaring it, once the boot is
/// finished; and why the boot was refused as it finished.
#[derive(Default)]
struct Boot {
    begun: Option<crate::boot::Begun>,
    deciding: usize,
    joined: Vec<String>,
    serving: BTreeMap<String, String>,
    refused: Option<String>,
}

/// What a package owes once every task has ended.
type Ending = Box<dyn FnOnce() + Send>;

/// A VALUE THE STARTS WAIT ON, WAKING THEM IN THE ORDER THEY CAME: a `watch` spreads its waiters over notifiers picked
/// at random, so starts waiting on one went on in an order no two runs shared, and a test's paused run was no longer
/// one run. One `Notify` wakes its waiters as they queued.
struct Gate<T> {
    value: Mutex<T>,
    changed: Notify,
}

impl<T> Gate<T> {
    fn new(value: T) -> Self {
        Gate {
            value: Mutex::new(value),
            changed: Notify::new(),
        }
    }

    /// Change the value, and wake whoever waits on it.
    fn modify(&self, change: impl FnOnce(&mut T)) {
        change(&mut self.value.lock().expect("a gate nobody poisoned"));
        self.changed.notify_waiters();
    }

    /// The value, as it stands.
    fn read<R>(&self, look: impl FnOnce(&T) -> R) -> R {
        look(&self.value.lock().expect("a gate nobody poisoned"))
    }

    /// Wait until `open` holds of the value.
    async fn wait_for(&self, open: impl Fn(&T) -> bool) {
        loop {
            let changed = self.changed.notified();
            tokio::pin!(changed);
            changed.as_mut().enable();
            if self.read(&open) {
                return;
            }
            changed.await;
        }
    }
}

impl Run {
    fn new(stop: watch::Receiver<bool>) -> Self {
        Run {
            stop,
            making: Arc::new(Gate::new(0)),
            started: Arc::default(),
            ending: Arc::default(),
            boot: Arc::default(),
            finished: Arc::new(Gate::new(false)),
            cores: Arc::new(Gate::new(BTreeSet::new())),
        }
    }

    /// A START HAS DECIDED whether its package runs, once: the last to decide finishes the boot, before anyone waiting
    /// on it hears it is finished.
    fn decided(&self, store: &Store) {
        let first = TURN
            .try_with(|turn| !std::mem::replace(&mut turn.borrow_mut().decided, true))
            .unwrap_or(true);
        if !first {
            return;
        }
        let mut boot = self.boot.lock().expect("a boot nobody poisoned");
        boot.deciding = boot.deciding.saturating_sub(1);
        if boot.deciding > 0 {
            return;
        }
        if let Some(begun) = boot.begun.take() {
            let joined = boot.joined.clone();
            if let Err(e) = begun.finish(store, &joined) {
                boot.refused = Some(e.to_string());
            }
        }
        match serving(store, &boot.joined) {
            Ok(serving) => boot.serving = serving,
            Err(e) => boot.refused = boot.refused.take().or(Some(e.to_string())),
        }
        drop(boot);
        self.finished.modify(|f| *f = true);
    }

    /// `package`'s start is done waiting on: its core is made, or its start ended without one, so no start waiting
    /// for it waits for ever.
    fn done(&self, package: &str) {
        self.cores.modify(|made| {
            made.insert(package.to_string());
        });
    }

    /// A start is done making its core: `package` started, or the start ended with nothing to run.
    fn made(&self, package: Option<&str>) {
        if let Some(package) = package {
            self.started
                .lock()
                .expect("starts nobody poisoned")
                .push(package.to_string());
            self.done(package);
        }
        self.making.modify(|n| *n = n.saturating_sub(1));
    }
}

/// A PACKAGE STARTING, or STARTED: the two events of a package's lifecycle, said by the kernel to whoever watches
/// the agent as a package's start begins and as it ends, so the journal keeps which packages run and a package
/// that needs another's core waits until every package has made its own (`Handed::started`).
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
    /// DO `last` ONCE EVERY TASK HAS ENDED, as the run stops: what a package owes after the others' last word, as
    /// what archives the journal takes what they said while stopping.
    pub fn finally(&self, last: impl FnOnce() + Send + 'static) {
        self.run
            .ending
            .lock()
            .expect("endings nobody poisoned")
            .push(Box::new(last));
    }

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

    /// WHETHER THE SELF PLAYS A ROLE of one of `roles`, the package's own classes, by the vocabulary the store holds:
    /// what a package asks first, deciding for itself whether it runs. No package's role is beneath another
    /// package's, so its own class decides before any package has brought its documents, and a domain's role class
    /// beneath it is the world's to say, put in as the boot began.
    pub fn plays(&self, roles: &[&str]) -> Result<bool, Error> {
        crate::boot::plays(&self.store, roles)
    }

    /// `package` JOINS THE AGENT, AND WAITS FOR WHAT ITS ROLES DEPEND ON: its documents are brought
    /// (`Package::documents`), put in, and every graph of the world passed over until now offered again, and its start
    /// has decided; then, once every start has decided and the boot is finished, it waits until every package serving
    /// a role its roles depend on (`orexis:dependsOn`) has made its core - a role depending on nothing waiting on
    /// nobody. What a package does once it has
    /// decided it runs and before it makes its core, which may then read what those packages brought and made. The
    /// order is the vocabulary's: the package names no other. Over a store booted already, with every package's
    /// documents in, nothing is brought.
    pub async fn joins(&self, package: &str) -> Result<(), Error> {
        {
            let mut boot = self.run.boot.lock().expect("a boot nobody poisoned");
            if let Some(begun) = boot.begun.as_mut() {
                begun.bring(&self.store, package)?;
            }
            boot.joined.push(package.to_string());
        }
        self.run.decided(&self.store);
        //  A START JOINING IS STILL MAKING ITS CORE, so it waits busy: the run is not over, and no stretch ends, while
        //  it waits for the boot to finish and for what its roles depend on; what it said is told as it waits.
        self.events.spoke();
        self.run.finished.wait_for(|f| *f).await;
        let needs = self.needs(package)?;
        self.run
            .cores
            .wait_for(|made| needs.iter().all(|n| made.contains(n)))
            .await;
        Ok(())
    }

    /// THE PACKAGES `package` WAITS FOR: each serving a role that a role it serves and the self plays depends on, once
    /// the boot is finished, refused where the boot was. A role depended on that the self plays none of is waited for
    /// by nobody: that the self plays it is onboarding's to hold (`onboarding/requirements.ttl`), not the boot's.
    fn needs(&self, package: &str) -> Result<BTreeSet<String>, Error> {
        let boot = self.run.boot.lock().expect("a boot nobody poisoned");
        if let Some(why) = boot.refused.clone() {
            return Err(Error::Evaluation(why));
        }
        let mut needs = BTreeSet::new();
        for (role, serving) in &boot.serving {
            if serving != package {
                continue;
            }
            for needed in crate::boot::depended(&self.store, role)? {
                if let Some(other) = boot.serving.get(&needed).filter(|other| *other != package) {
                    needs.insert(other.clone());
                }
            }
        }
        Ok(needs)
    }

    /// `package` HAS STARTED: its core is made. Said by the package itself, once, as its making ends, and it WAITS
    /// HERE UNTIL EVERY PACKAGE OF THE AGENT HAS MADE ITS CORE OR ENDED, so each is listening before any goes on to
    /// speak; then it says `orexis:PackageStarting` and `orexis:PackageStarted`, at the instants it began and made
    /// its core, which the journal, made by then, keeps. A start that ends without saying it has nothing to run.
    pub async fn started(&self, package: &str) {
        let now = self.clock.now();
        let (began, first) = TURN
            .try_with(|turn| {
                let mut turn = turn.borrow_mut();
                (turn.began, !std::mem::replace(&mut turn.made, true))
            })
            .unwrap_or((None, true));
        self.run.decided(&self.store);
        if first {
            self.run.made(Some(package));
        }
        //  A START WAITING FOR THE OTHERS TO MAKE THEIR CORES IS STILL STARTING, so it waits busy: woken as the last
        //  is made, every start goes on counted, and no stretch ends while one is still to be polled; what it said is
        //  told as it waits, as it is when a task rests.
        self.events.spoke();
        self.run.making.wait_for(|n| *n == 0).await;
        for (started, at) in [(false, began.unwrap_or(now)), (true, now)] {
            self.events.0.watch.emit(&Lifecycle {
                package: package.to_string(),
                started,
                at,
            });
        }
    }

    /// WHETHER THE AGENT IS BEING CHECKED, and where to say what the check asks: handed outside by whoever checks an
    /// agent before anything is granted. A package being checked says what it found as it makes its core - that it
    /// holds the agent, why it refuses the world as posed - and ENDS ITS START THERE, its core made and nothing run:
    /// each package checks its own, and the kernel knows nothing of checks.
    pub fn checking(&self) -> Option<Checking> {
        self.outside.read::<Checking>()
    }

    /// Wait until the run is over: the task stops itself.
    pub async fn stopped(&self) {
        self.events.rest();
        let mut stop = self.run.stop.clone();
        let _ = stop.wait_for(|stopped| *stopped).await;
    }
}

/// A task: what a package runs once it has started, where a package keeps that apart from its making.
pub type Task = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A package's start, running: the whole of what the package does, from deciding whether it runs to the end of its
/// task. It says when it has started (`Handed::started`), and ends where it has nothing more to do.
pub type Starting = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A PACKAGE, AS IT REGISTERS ITSELF: its name, THE DOCUMENTS IT BRINGS - its ontology, its rules, its actions, each
/// a file of its crate compiled into the binary (`documents!`) and put in the store as it joins - and ITS START. THE
/// AGENT STARTS EVERY PACKAGE IT HOLDS, and each is responsible for its own: it decides whether it runs
/// (`Handed::plays`, or a reason of its own), and declined, it ends; it joins (`Handed::joins`), bringing its
/// documents and waiting until the packages serving the roles its own depend on have made their cores; it makes its core,
/// says it started (`Handed::started`), and checked, ends there; otherwise it goes on as its task. Nothing decides
/// for a package, knows which run, or keeps an order between two.
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

/// THE PACKAGES A TEST NAMES, handed outside by whoever starts the agent for a test (`start`): a test's member runs
/// where it is named, as a package runs where the self plays its role.
#[derive(Clone, Default)]
pub struct Named(pub Vec<String>);

/// THE START OF A TEST'S MEMBER, which no role loads: it runs where whoever starts the agent names `name`, and its
/// core is what `make` makes.
pub fn named(handed: Handed, name: &'static str, make: fn(&Handed) -> Result<Option<Task>, Error>) -> Starting {
    Box::pin(async move {
        if !handed
            .outside
            .read::<Named>()
            .is_some_and(|named| named.0.iter().any(|n| n == name))
        {
            return Ok(());
        }
        let task = make(&handed)?;
        handed.started(name).await;
        match task {
            Some(task) if handed.checking().is_none() => task.await,
            _ => Ok(()),
        }
    })
}

/// EACH ROLE CLASS THE SELF PLAYS BY THE PACKAGE THAT SERVES IT, of the packages `joined`, each read off its own
/// documents; refused where the roles depend on each other round a cycle, which no start could wait out.
fn serving(store: &Store, joined: &[String]) -> Result<BTreeMap<String, String>, Error> {
    let mut serving = BTreeMap::new();
    for package in joined {
        for class in crate::boot::served(store, package)? {
            if crate::boot::plays(store, &[&class])? {
                serving.insert(class, package.clone());
            }
        }
    }
    let mut edges: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    let depended: Vec<(String, Vec<String>)> = serving
        .keys()
        .map(|role| crate::boot::depended(store, role).map(|d| (role.clone(), d)))
        .collect::<Result<_, _>>()?;
    for (role, needed) in &depended {
        for n in needed {
            if let Some(other) = serving.get(n) {
                edges.entry(serving[role].as_str()).or_default().insert(other.as_str());
            }
        }
    }
    fn round(at: &str, edges: &BTreeMap<&str, BTreeSet<&str>>, path: &mut Vec<String>) -> Option<Vec<String>> {
        if let Some(i) = path.iter().position(|p| p == at) {
            return Some(path[i..].to_vec());
        }
        path.push(at.to_string());
        for next in edges.get(at).into_iter().flatten() {
            if let Some(cycle) = round(next, edges, path) {
                return Some(cycle);
            }
        }
        path.pop();
        None
    }
    for start in edges.keys() {
        if let Some(cycle) = round(start, &edges, &mut Vec::new()) {
            return Err(Error::Evaluation(format!(
                "the roles of {} depend on each other round a cycle, so none could start",
                cycle.join(", ")
            )));
        }
    }
    Ok(serving)
}

/// Every package this binary holds, by its name.
fn every() -> Vec<String> {
    crate::boot::every_package()
}

/// What every package of an agent is handed.
fn handed(store: &Store, id: &str, clock: Arc<dyn Clock>, outside: Outside, stop: watch::Receiver<bool>) -> Handed {
    Handed {
        store: store.clone(),
        id: id.to_string(),
        clock,
        events: Events::new(store),
        outside,
        run: Run::new(stop),
    }
}

/// AN AGENT BOOTED AND NOT YET STARTED: its boot begun, the world's documents and the self in, and no package's.
pub struct Booted {
    handed: Handed,
    stop: watch::Sender<bool>,
}

/// BEGIN TO BOOT `booting.agent` INTO `store`: the kernel's vocabulary, the world's documents and the self. The
/// starts finish it: each package that joins brings its documents (`Handed::joins`), and once every start has decided
/// the boot is finished, refused where the self plays a role no package of this binary declares.
pub fn boot(
    store: &Store,
    booting: &crate::boot::Booting<'_>,
    clock: Arc<dyn Clock>,
    outside: Outside,
) -> Result<Booted, Error> {
    let begun = crate::boot::begin(store, booting)?;
    let (stop, stopped) = watch::channel(false);
    let handed = handed(store, booting.agent, clock, outside, stopped);
    handed.run.boot.lock().expect("a boot nobody poisoned").begun = Some(begun);
    Ok(Booted { handed, stop })
}

impl Booted {
    /// START THE AGENT, on the Tokio runtime this is called in: every package this binary holds is started, each
    /// deciding for itself whether it runs, and this ends once every one has made its core or ended - refused where
    /// one could not be made.
    pub async fn start(self) -> Result<Running, Error> {
        started();
        spawn(self.handed, self.stop, every()).made().await
    }
}

/// START THE AGENT `id` over `store`, booted already, for a test: every package this binary holds is started, those
/// `names` names first and in that order, and a test's member runs where it is named (`Named`). A name no package
/// registered under is an error: its crate was not built in.
pub async fn start(
    store: &Store,
    id: &str,
    clock: Arc<dyn Clock>,
    outside: Outside,
    names: &[String],
) -> Result<Running, Error> {
    started();
    let every = every();
    if let Some(name) = names.iter().find(|n| !every.contains(n)) {
        return Err(Error::Evaluation(format!(
            "no package registered itself as {name}: this binary was built without it"
        )));
    }
    outside.hand(Named(names.to_vec()));
    let (stop, stopped) = watch::channel(false);
    let mut order = names.to_vec();
    order.extend(every.into_iter().filter(|n| !names.contains(n)));
    spawn(handed(store, id, clock, outside, stopped), stop, order)
        .made()
        .await
}

/// EVERY START IS SPAWNED AS A TASK, in `order`: each is the whole of its package's life. A start that ends without
/// saying it started is done making its core all the same, so nobody waits for it.
fn spawn(handed: Handed, stop: watch::Sender<bool>, order: Vec<String>) -> Running {
    let mut running = Running {
        handed: handed.clone(),
        names: Vec::new(),
        joins: Vec::new(),
        stop,
        halt: None,
        halted: Arc::new(Notify::new()),
    };
    handed.run.making.modify(|n| *n += order.len());
    handed.run.boot.lock().expect("a boot nobody poisoned").deciding += order.len();
    if order.is_empty() {
        handed.run.finished.modify(|f| *f = true);
    }
    for name in order {
        let package = inventory::iter::<Package>()
            .find(|p| p.name == name)
            .expect("a package found is registered");
        let start = (package.start)(handed.clone());
        let (events, run, at, store) = (
            handed.events.clone(),
            handed.run.clone(),
            handed.clock.now(),
            handed.store.clone(),
        );
        let ending = name.clone();
        //  A TASK IS BUSY FROM ITS START until it first waits: the run is not over before every policy decided once.
        events.0.busy.up();
        let scoped = TURN.scope(
            RefCell::new(Local {
                said: Vec::new(),
                in_hand: 1,
                began: Some(at),
                decided: false,
                made: false,
            }),
            async move {
                let ended = start.await;
                run.decided(&store);
                if !TURN.with(|turn| turn.borrow().made) {
                    run.made(None);
                    run.done(&ending);
                }
                if let Err(e) = ended {
                    events.failed(e);
                }
                events.rest();
            },
        );
        running.names.push(name);
        running.joins.push(tokio::spawn(scoped));
    }
    running
}

impl Running {
    /// The packages that said they started, in the order they did.
    pub fn parts(&self) -> Vec<String> {
        self.handed.run.started.lock().expect("starts nobody poisoned").clone()
    }

    /// The run once every package has made its core, or ended: refused where one could not be made.
    async fn made(self) -> Result<Self, Error> {
        self.handed.run.making.wait_for(|n| *n == 0).await;
        if let Some(why) = self
            .handed
            .run
            .boot
            .lock()
            .expect("a boot nobody poisoned")
            .refused
            .clone()
        {
            return Err(Error::Evaluation(why));
        }
        self.checked()?;
        Ok(self)
    }

    /// The packages whose starts have not ended: what goes on running.
    pub fn going_on(&self) -> Vec<String> {
        self.names
            .iter()
            .zip(&self.joins)
            .filter(|(_, join)| !join.is_finished())
            .map(|(name, _)| name.clone())
            .collect()
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
        self.passed(bus.busy.took())
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
            self.passed(bus.busy.took())?;
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
        //  AND WHAT WAS ASKED FOR ONCE THEY HAVE ALL ENDED, in the order asked.
        let ending = std::mem::take(&mut *self.handed.run.ending.lock().expect("endings nobody poisoned"));
        for last in ending {
            last();
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

    async fn running(names: &[&str], seen: &Seen) -> Running {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let outside = Outside::default();
        outside.hand(seen.clone());
        let names: Vec<String> = names.iter().map(|n| n.to_string()).collect();
        start(&store, "urn:test:me", Arc::new(Elapsing::from(noon())), outside, &names)
            .await
            .unwrap()
    }

    fn seen_by(handed: &Handed) -> Seen {
        handed
            .outside
            .take::<Seen>()
            .inspect(|s| handed.outside.hand(s.clone()))
            .unwrap()
    }

    //  BEGINS AND ENDS AN ACTIVITY as the run begins, writes down that it did, and then that it waited.
    inventory::submit! { Package { name: "test/begins", documents: &[], start: |handed| named(handed, "test/begins", |handed| {
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
    inventory::submit! { Package { name: "test/hears", documents: &[], start: |handed| named(handed, "test/hears", |handed| {
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
    inventory::submit! { Package { name: "test/holds", documents: &[], start: |handed| named(handed, "test/holds", |handed| {
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
    inventory::submit! { Package { name: "test/arrives", documents: &[], start: |handed| named(handed, "test/arrives", |handed| {
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
        let running = running(&["test/begins", "test/hears"], &seen).await;
        running.settled().await.unwrap();
        assert_eq!(*seen.lock().unwrap(), ["begun", &format!("heard 7 {STEP}")]);
        assert_eq!(running.parts(), ["test/begins", "test/hears"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn nobody_hearing_connects_nothing() {
        let seen = Seen::default();
        let running = running(&["test/begins"], &seen).await;
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
        let running = running(&["test/holds"], &seen).await;
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
        let running = running(&["test/arrives"], &seen).await;
        assert_eq!(running.released().await.unwrap(), MET);
        assert_eq!(*seen.lock().unwrap(), ["arrived"]);
        running.stop().await;
    }

    #[tokio::test(start_paused = true)]
    async fn a_halt_ends_the_run_unfinished() {
        let seen = Seen::default();
        let mut running = running(&["test/holds"], &seen).await;
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

    #[tokio::test]
    async fn a_package_nobody_registered_is_refused() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Arc::new(crate::clock::Manual::at(noon()));
        let refused = start(
            &store,
            "urn:test:me",
            clock,
            Outside::default(),
            &["test/absent".to_string()],
        )
        .await;
        assert!(refused.is_err());
    }
}
