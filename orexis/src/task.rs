//! WHAT A PACKAGE'S TASK IS HANDED, AND WHERE PACKAGES MEET (a-package-is-a-task-that-awaits-its-events). A package
//! is one async function: it makes its core, and loops - it awaits what it hears (`Hears::next`), an arrival
//! (`Arrived::wait`), the clock (`Handed::sleep_until`) or the run's end (`Handed::stopped`), calls its core, and
//! says what happened. The kernel knows no package and no word of what one does: a package REGISTERS ITSELF, its
//! crate submitting its name and its start (`Package`) to a registry the linker collects, and whoever runs an agent
//! starts each one (`Booted::start`), inside the agent's booting: a package decides whether it runs, joins bringing its
//! documents, says it booted, and goes on as its task - THE LIFECYCLE, activities of the kernel's the packages hear on
//! the events as they hear any other (the-lifecycle-is-activities-the-packages-hear).
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

use oxigraph::model::{Literal, NamedNode, Term};
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio::sync::{Notify, watch};

use crate::Error;
use crate::activity::{Activity, Ended, Lasting, Started, Wrote};
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
    /// Each class of event heard, with the class of activity it must start or end where it is an activity's, and
    /// its tag.
    events: Vec<(String, Option<String>, usize)>,
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
            .any(|h| h.events.iter().any(|(c, _, _)| classes.contains(c)))
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

    /// SAY `event` TO WHOEVER WATCHES AND TO EVERY TASK HEARING ITS CLASS, connecting nothing: what the kernel says of
    /// the lifecycle, which every package hears, so the watch is still told no where nothing else watches it. Where the
    /// tasks already hear the watch, it tells them; otherwise it is told them here, held until the sayer next waits.
    fn say(&self, event: &dyn Event) {
        let named = self.0.watch.emit(event);
        if self.0.listening.load(Ordering::SeqCst) {
            return;
        }
        let Some(kind) = event.kind() else {
            return;
        };
        let heard = Heard {
            node: named.unwrap_or_else(crate::events::mint),
            kind: kind.to_string(),
            activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
            about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
        };
        if let Err(heard) = TURN
            .try_with(|turn| turn.borrow_mut().said.push(heard.clone()))
            .map_err(|_| heard)
        {
            self.tell(heard);
        }
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
                        .filter(|(class, of, _)| {
                            classes.contains(class)
                                && of
                                    .as_ref()
                                    .is_none_or(|of| event.activity.as_ref().is_some_and(|(_, k)| k == of))
                        })
                        .map(|(_, _, tag)| (h.to.clone(), *tag))
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
        hearers[self.index].events.push((class.to_string(), None, tag));
    }

    /// Hear every event of `class` the kernel says (`Events::say`), with `tag`, connecting nothing.
    fn said(&mut self, class: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index].events.push((class.to_string(), None, tag));
    }

    /// Hear every start or end - `phase`, `activity::STARTED` or `activity::ENDED` - of an activity of `kind`, with
    /// `tag`: what a package hears of another's lifecycle, and of the agent's.
    pub fn activity(&mut self, phase: &str, kind: &str, tag: usize) {
        let mut hearers = self.events.0.hearers.write().expect("hearers nobody poisoned");
        hearers[self.index]
            .events
            .push((phase.to_string(), Some(kind.to_string()), tag));
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

    /// WAIT FOR WHAT IS HEARD NEXT AND STAY BUSY: what a package booting waits with, what it said told as it waits,
    /// while it is still counted as booting - so no stretch ends, and the run is not over, while a booting waits on
    /// the others.
    async fn next_busy(&mut self) -> Option<Woke> {
        self.events.spoke();
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
                lasting: None,
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
                lasting: None,
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

/// WHAT THE AGENT IS PROVIDED, by its type, by whoever runs it - the binary, a check or a test: the connectors a test
/// makes, a bus, a web, a bot, a model, a sink, and the word that the agent is deployed or checked; and what one
/// package provides another, the journal it keeps. A package takes the one it knows, where one was provided, and one
/// value of a type is provided at a time.
#[derive(Clone, Default)]
pub struct Provided(Arc<Mutex<HashMap<TypeId, Box<dyn Any + Send>>>>);

impl Provided {
    /// Provide `thing` to whichever package takes its type.
    pub fn provide<T: Any + Send>(&self, thing: T) {
        let mut held = self.0.lock().expect("what is provided, poisoned by nobody");
        held.insert(TypeId::of::<T>(), Box::new(thing));
    }

    /// `thing` provided, and what is provided: for whoever runs the agent, providing several in one expression.
    #[must_use]
    pub fn with<T: Any + Send>(self, thing: T) -> Self {
        self.provide(thing);
        self
    }

    /// What was handed of type `T` changed by `change`, a default one handed first where nothing was: for what several
    /// packages each add to, whichever starts first, so no package's addition is lost to another's.
    pub fn alter<T: Any + Send + Default>(&self, change: impl FnOnce(&mut T)) {
        let mut held = self.0.lock().expect("what is provided, poisoned by nobody");
        let thing = held.entry(TypeId::of::<T>()).or_insert_with(|| Box::new(T::default()));
        if let Some(thing) = thing.downcast_mut::<T>() {
            change(thing);
        }
    }

    /// Whether anything of type `T` is handed, taking nothing.
    pub fn has<T: Any + Send>(&self) -> bool {
        self.0
            .lock()
            .expect("what is provided, poisoned by nobody")
            .contains_key(&TypeId::of::<T>())
    }

    /// What was handed of type `T`, read and left where it is.
    pub fn read<T: Any + Send + Clone>(&self) -> Option<T> {
        self.0
            .lock()
            .expect("what is provided, poisoned by nobody")
            .get(&TypeId::of::<T>())
            .and_then(|thing| thing.downcast_ref::<T>())
            .cloned()
    }

    /// What was handed of type `T`, shared: read and left where it is, and where nothing was handed, a default one
    /// handed now. For what several packages each add to or read, whichever starts first.
    pub fn share<T: Any + Send + Clone + Default>(&self) -> T {
        let mut held = self.0.lock().expect("what is provided, poisoned by nobody");
        if let Some(thing) = held.get(&TypeId::of::<T>()).and_then(|thing| thing.downcast_ref::<T>()) {
            return thing.clone();
        }
        let thing = T::default();
        held.insert(TypeId::of::<T>(), Box::new(thing.clone()));
        thing
    }

    /// Take what was handed of type `T`, where anything was: it is the taker's from now on.
    pub fn take<T: Any + Send>(&self) -> Option<T> {
        let mut held = self.0.lock().expect("what is provided, poisoned by nobody");
        held.remove(&TypeId::of::<T>())
            .and_then(|thing| thing.downcast().ok())
            .map(|thing| *thing)
    }
}

/// THE AGENT IS DEPLOYED: provided by whoever runs it for good, and by no check and no test. Where it is
/// handed, a package makes for itself what it was not handed, from what the world says: its journal, its archive.
/// Where it is not, a package handed nothing has nothing, so a check reaches no disk and no port. It says the one
/// thing whoever runs the agent knows and no document states: the name of the world's directory, which its buckets
/// and its metrics' points go by.
#[derive(Clone, Default)]
pub struct Deployed {
    pub world: String,
}

/// THE AGENT IS BEING CHECKED: provided by whoever checks an agent before anything is granted, and by no run
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

/// THE PROCESS'S LOG, for whoever keeps it: provided by whoever owns the log, and called once by the package
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
/// package that keeps any of it says so as it makes its core (`Provided::alter`), the journal's where it lies
/// and each series' package the sink it writes, and a reader reads it once every core is made.
#[derive(Clone, Default)]
pub struct Reads {
    pub journal: Journaled,
    pub history: Option<crate::series::Reader>,
    pub metrics: Option<crate::series::Reader>,
}

/// WHAT A PACKAGE'S TASK IS HANDED: the agent's services, and nothing of its own - its store, its id, the clock, the
/// events, what is provided, and the run it is part of; and, handed to a package's start, THE PACKAGE'S LIFECYCLE,
/// which the kernel begins and the package goes on with: it joins (`joins`), says it booted (`booted`) and, where it
/// has work left once the agent's running ends, stops (`stopping`).
#[derive(Clone)]
pub struct Handed {
    pub store: Store,
    pub id: String,
    pub clock: Arc<dyn Clock>,
    pub events: Events,
    pub provided: Provided,
    run: Run,
    life: Option<Arc<tokio::sync::Mutex<Life>>>,
}

/// THE AGENT'S LIFECYCLE AND EACH PACKAGE'S, as activities of the kernel's classes, each said by one start and one end
/// (`activity::Lasting`): the agent's booting holds every package's, its running every running package's, its stopping
/// every package's that stops - and a check is the agent's booting alone.
pub const AGENT_BOOTING: &str = "http://example.org/orexis#AgentBooting";
pub const AGENT_RUNNING: &str = "http://example.org/orexis#AgentRunning";
pub const AGENT_STOPPING: &str = "http://example.org/orexis#AgentStopping";
pub const PACKAGE_BOOTING: &str = "http://example.org/orexis#PackageBooting";
pub const PACKAGE_RUNNING: &str = "http://example.org/orexis#PackageRunning";
pub const PACKAGE_STOPPING: &str = "http://example.org/orexis#PackageStopping";
/// A package joined the agent, its documents brought: said inside its booting.
pub const PACKAGE_JOINED: &str = "http://example.org/orexis#PackageJoined";
const PACKAGE: &str = "http://example.org/orexis#package";
const SERVES: &str = "http://example.org/orexis#serves";
const RUNS: &str = "http://example.org/orexis#runs";

/// What a lifecycle is told under: a package's booting ended, a package joined, the agent's booting ended, the agent's
/// running ended, and a package's running ended.
const BOOTED: usize = 0;
const JOINED: usize = 1;
const AGENT_BOOTED: usize = 2;
const AGENT_RAN: usize = 3;
const RAN: usize = 4;

/// THE RUN THE PACKAGES ARE PART OF, a service each is handed: the signal that stops it, whether the packages run
/// once booted - not where the agent is checked or booted without starting - how many packages boot, the packages
/// that booted with a core, in the order they did, the boot the bootings finish, and the agent's own activities,
/// named as the run begins so each package's is said part of its.
#[derive(Clone)]
struct Run {
    stop: watch::Receiver<bool>,
    runs: bool,
    packages: usize,
    started: Arc<Mutex<Vec<String>>>,
    boot: Arc<Mutex<Boot>>,
    booting: NamedNode,
    running: NamedNode,
    stopping: Arc<Mutex<Option<Span>>>,
}

/// THE BOOT AS THE BOOTINGS FINISH IT: what is begun and not yet finished, where the agent was booted by `boot`; the
/// packages that joined and brought their documents, each with its crate; and why the boot was refused as it finished.
#[derive(Default)]
struct Boot {
    begun: Option<crate::boot::Begun>,
    joined: Vec<(String, &'static str)>,
    refused: Option<String>,
}

impl Run {
    fn new(stop: watch::Receiver<bool>) -> Self {
        Run {
            stop,
            runs: true,
            packages: 0,
            started: Arc::default(),
            boot: Arc::default(),
            booting: crate::events::mint(),
            running: crate::events::mint(),
            stopping: Arc::default(),
        }
    }

    fn refused(&self) -> Option<String> {
        self.boot.lock().expect("a boot nobody poisoned").refused.clone()
    }
}

/// AN ACTIVITY OF THE LIFECYCLE, OPEN: said whole as it begins and again as it ends (`activity::Lasting`).
struct Span {
    node: NamedNode,
    kind: &'static str,
    part_of: Option<NamedNode>,
    about: Vec<(&'static str, Term)>,
    began: DateTime,
    real: std::time::Instant,
}

impl Span {
    fn begin(
        events: &Events,
        kind: &'static str,
        node: NamedNode,
        part_of: Option<NamedNode>,
        about: Vec<(&'static str, Term)>,
        at: DateTime,
    ) -> Span {
        events.say(&Started {
            activity: node.clone(),
            kind,
            triggers: Vec::new(),
            at,
            lasting: Some(Lasting {
                part_of: part_of.clone(),
                about: about.clone(),
                began: at,
            }),
        });
        Span {
            node,
            kind,
            part_of,
            about,
            began: at,
            real: std::time::Instant::now(),
        }
    }

    /// End it at `at`, saying `more` of it besides what it began saying.
    fn end(self, events: &Events, at: DateTime, more: Vec<(&'static str, Term)>) {
        let mut about = self.about;
        about.extend(more);
        events.say(&Ended {
            activity: self.node,
            kind: self.kind,
            at,
            duration_s: round6(self.real.elapsed().as_secs_f64()),
            lasting: Some(Lasting {
                part_of: self.part_of,
                about,
                began: self.began,
            }),
        });
    }
}

/// A PACKAGE'S LIFECYCLE: which package, what it hears of the others' and of the agent's, which of its activities is
/// open, and the crate whose documents it brought.
struct Life {
    package: String,
    hears: Hears,
    booting: Option<Span>,
    running: Option<Span>,
    stopping: Option<Span>,
    krate: Option<&'static str>,
}

impl Life {
    /// End whichever of its activities is open, as its start ends: a booting that never said it booted ends having
    /// made no core.
    fn end(&mut self, events: &Events, at: DateTime) {
        if let Some(booting) = self.booting.take() {
            booting.end(events, at, vec![(RUNS, Literal::from(false).into())]);
        }
        for span in [self.running.take(), self.stopping.take()].into_iter().flatten() {
            span.end(events, at, Vec::new());
        }
    }
}

/// WHAT A PACKAGE JOINING HAS HEARD OF THE OTHERS: which have joined or ended their booting, which have ended it,
/// and the roles those that ended serve.
#[derive(Default)]
struct Settling {
    settled: BTreeSet<String>,
    ended: BTreeSet<String>,
    served: BTreeSet<String>,
}

impl Settling {
    fn hear(&mut self, woke: Woke) {
        if let Woke::Event(tag, heard) = woke
            && let Some(package) = package_of(&heard)
        {
            if tag == BOOTED {
                self.served
                    .extend(heard.all(SERVES).into_iter().map(|c| c.as_str().to_string()));
                self.ended.insert(package.clone());
            }
            if tag == BOOTED || tag == JOINED {
                self.settled.insert(package);
            }
        }
    }
}

/// The name of the package a lifecycle event says it is of.
fn package_of(heard: &Heard) -> Option<String> {
    heard.about.iter().find_map(|(p, t)| match t {
        Term::Literal(l) if p == PACKAGE => Some(l.value().to_string()),
        _ => None,
    })
}

/// Whether a booting ended having made the package's core, which then runs.
fn runs(heard: &Heard) -> bool {
    heard
        .about
        .iter()
        .any(|(p, t)| p == RUNS && *t == Term::from(Literal::from(true)))
}

/// A PACKAGE JOINED THE AGENT: its documents brought, said inside its booting, so a package that waits on another's
/// knows when every package's vocabulary is in.
pub struct Joined {
    pub package: String,
    pub at: DateTime,
}

impl Event for Joined {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<oxigraph::model::Triple>> {
        Some(vec![
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                NamedNode::new_unchecked(PACKAGE_JOINED),
            ),
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked(PACKAGE),
                Literal::new_simple_literal(&self.package),
            ),
        ])
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(PACKAGE_JOINED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        vec![(PACKAGE, Literal::new_simple_literal(&self.package).into())]
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

    /// WHETHER THE SELF PLAYS A ROLE of one of `roles`, the package's own classes, by the vocabulary the store holds:
    /// what a package asks first, deciding for itself whether it runs. No package's role is beneath another
    /// package's, so its own class decides before any package has brought its documents, and a domain's role class
    /// beneath it is the world's to say, put in as the boot began.
    pub fn plays(&self, roles: &[&str]) -> Result<bool, Error> {
        crate::boot::plays(&self.store, roles)
    }

    fn life(&self) -> Result<Arc<tokio::sync::Mutex<Life>>, Error> {
        self.life.clone().ok_or_else(|| {
            Error::Evaluation("nothing was handed a lifecycle: only a package's start joins, boots and stops".into())
        })
    }

    /// THE PACKAGE JOINS THE AGENT, BRINGING `documents`, AND WAITS FOR WHAT ITS ROLES DEPEND ON, inside its booting:
    /// its documents, which it names in the order it wants them, are put in and every graph of the world passed over
    /// until now offered again, and it says it joined (`orexis:PackageJoined`); then, once every package has joined or
    /// ended its booting, so the vocabulary is whole, it waits to hear the end of the booting of each package serving
    /// a role its roles depend on (`orexis:dependsOn`) - a role depending on nothing waiting on nobody, and none
    /// waiting once every other booting has ended. The order is the vocabulary's: the package names no other.
    pub async fn joins(&self, documents: &Documents) -> Result<(), Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        {
            let mut boot = self.run.boot.lock().expect("a boot nobody poisoned");
            if let Some(begun) = boot.begun.as_mut() {
                begun.bring(&self.store, documents)?;
            }
            boot.joined.push((life.package.clone(), documents.krate));
        }
        life.krate = Some(documents.krate);
        self.events.say(&Joined {
            package: life.package.clone(),
            at: self.clock.now(),
        });
        let mut heard = Settling::default();
        heard.settled.insert(life.package.clone());
        while heard.settled.len() < self.run.packages {
            let Some(woke) = life.hears.next_busy().await else {
                break;
            };
            heard.hear(woke);
        }
        let needs = self.needs(documents.krate)?;
        while !needs.iter().all(|n| heard.served.contains(n)) && heard.ended.len() + 1 < self.run.packages {
            let Some(woke) = life.hears.next_busy().await else {
                break;
            };
            heard.hear(woke);
        }
        Ok(())
    }

    /// THE ROLES THE PACKAGE OF `krate` WAITS FOR: each a role it serves and the self plays depends on, that the self
    /// plays and it does not serve; refused where they depend back on its own round a cycle, which no booting could
    /// wait out. A role depended on that the self plays none of is waited for by nobody: that the self plays it is
    /// onboarding's to hold (`onboarding/requirements.ttl`), not the boot's.
    fn needs(&self, krate: &str) -> Result<BTreeSet<String>, Error> {
        let played = |role: &str| crate::boot::plays(&self.store, &[role]);
        let mut mine = Vec::new();
        for role in crate::boot::served(&self.store, krate)? {
            if played(&role)? {
                mine.push(role);
            }
        }
        let mut needs = BTreeSet::new();
        for role in &mine {
            for needed in crate::boot::depended(&self.store, role)? {
                if !mine.contains(&needed) && played(&needed)? {
                    needs.insert(needed);
                }
            }
        }
        let (mut seen, mut frontier): (BTreeSet<String>, Vec<String>) =
            (needs.clone(), needs.iter().cloned().collect());
        while let Some(role) = frontier.pop() {
            for needed in crate::boot::depended(&self.store, &role)? {
                if mine.contains(&needed) {
                    return Err(Error::Evaluation(format!(
                        "the roles of {krate} depend on each other round a cycle through {role}, so none could boot"
                    )));
                }
                if played(&needed)? && seen.insert(needed.clone()) {
                    frontier.push(needed);
                }
            }
        }
        Ok(needs)
    }

    /// THE PACKAGE HAS BOOTED: its core is made, and its booting ends, saying the roles it serves. It WAITS HERE UNTIL
    /// THE AGENT'S BOOTING HAS ENDED - every package booted or declined, and the boot finished - so each is listening
    /// before any speaks; then, where the agent runs, its running begins, and it goes on as its task. False where the
    /// agent does not run - it is checked, or booted without starting - and the package ends there; refused where the
    /// boot was.
    pub async fn booted(&self) -> Result<bool, Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        let mut serves = Vec::new();
        if let Some(krate) = life.krate {
            for role in crate::boot::served(&self.store, krate)? {
                if crate::boot::plays(&self.store, &[&role])? {
                    serves.push(role);
                }
            }
        }
        self.run
            .started
            .lock()
            .expect("starts nobody poisoned")
            .push(life.package.clone());
        if let Some(booting) = life.booting.take() {
            let mut more: Vec<(&'static str, Term)> = vec![(RUNS, Literal::from(true).into())];
            more.extend(serves.iter().map(|c| (SERVES, NamedNode::new_unchecked(c).into())));
            booting.end(&self.events, self.clock.now(), more);
        }
        while let Some(woke) = life.hears.next_busy().await {
            if matches!(woke, Woke::Event(AGENT_BOOTED, _)) {
                break;
            }
        }
        if let Some(why) = self.run.refused() {
            return Err(Error::Evaluation(why));
        }
        if !self.run.runs {
            return Ok(false);
        }
        let about = vec![(PACKAGE, Literal::new_simple_literal(&life.package).into())];
        life.running = Some(Span::begin(
            &self.events,
            PACKAGE_RUNNING,
            crate::events::mint(),
            Some(self.run.running.clone()),
            about,
            self.clock.now(),
        ));
        Ok(true)
    }

    /// THE PACKAGE STOPS: its running ends, and it WAITS UNTIL THE AGENT'S RUNNING HAS ENDED - every running package's
    /// ended - so what it does next comes after the others' last word, inside its stopping, which ends with its start:
    /// what archives the journal takes what they said while they stopped.
    pub async fn stopping(&self) -> Result<(), Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        if let Some(running) = life.running.take() {
            running.end(&self.events, self.clock.now(), Vec::new());
        }
        while let Some(woke) = life.hears.next_busy().await {
            if matches!(woke, Woke::Event(AGENT_RAN, _)) {
                break;
            }
        }
        let about = vec![(PACKAGE, Literal::new_simple_literal(&life.package).into())];
        let stopping = self.run.stopping.lock().expect("a stopping nobody poisoned");
        let part_of = stopping.as_ref().map(|s| s.node.clone());
        drop(stopping);
        life.stopping = Some(Span::begin(
            &self.events,
            PACKAGE_STOPPING,
            crate::events::mint(),
            part_of,
            about,
            self.clock.now(),
        ));
        Ok(())
    }

    /// WHETHER THE AGENT IS BEING CHECKED, and where to say what the check asks: provided by whoever checks an
    /// agent before anything is granted. A package being checked says what it found as it makes its core - that it
    /// holds the agent, why it refuses the world as posed; a check is the agent's booting alone, so nothing runs.
    pub fn checking(&self) -> Option<Checking> {
        self.provided.read::<Checking>()
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
/// task - its booting, its running and its stopping.
pub type Starting = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A PACKAGE, AS IT REGISTERS ITSELF: its name and ITS START. THE AGENT STARTS EVERY PACKAGE IT HOLDS, each inside a
/// booting of its own, and each is responsible for its own: it decides whether it runs (`Handed::plays`, or a reason of
/// its own), and declined, it ends; it joins (`Handed::joins`), bringing its documents and waiting until the packages
/// serving the roles its own depend on have booted; it makes its core, says it booted (`Handed::booted`), and where the
/// agent does not run, ends there; otherwise it goes on as its task, its running. Nothing decides for a package,
/// knows which run, or keeps an order between two.
pub struct Package {
    pub name: &'static str,
    pub start: fn(Handed) -> Starting,
}

inventory::collect!(Package);

/// THE DOCUMENTS A PACKAGE BRINGS as it joins, of its crate, each named as the file it is, in the order the package
/// wants them put in: read as the crate is compiled, so a binary holds the documents of the packages built into it
/// and of no other, and the boot reads no tree.
pub struct Documents {
    pub krate: &'static str,
    pub files: &'static [(&'static str, &'static str)],
}

/// THE DOCUMENTS OF THE CRATE THIS IS WRITTEN IN, each a file of it: `documents!("ontology.ttl", "rules.ttl")`.
#[macro_export]
macro_rules! documents {
    ($($name:literal),* $(,)?) => {
        $crate::task::Documents {
            krate: env!("CARGO_PKG_NAME"),
            files: &[$(($name, include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/", $name)))),*],
        }
    };
}

/// An agent's tasks, running.
pub struct Running {
    pub handed: Handed,
    names: Vec<String>,
    joins: Vec<tokio::task::JoinHandle<()>>,
    agent: Option<tokio::task::JoinHandle<()>>,
    stop: watch::Sender<bool>,
    /// RAISED TO STOP THE RUN, by a signal the process was sent.
    pub halt: Option<Arc<AtomicBool>>,
    halted: Arc<Notify>,
}

/// THE PACKAGES A TEST NAMES, provided by whoever starts the agent for a test (`Booted::first`): a test's member runs
/// where it is named, as a package runs where the self plays its role.
#[derive(Clone, Default)]
pub struct Named(pub Vec<String>);

/// THE START OF A TEST'S MEMBER, which no role loads: it runs where whoever starts the agent names `name`, and its
/// core is what `make` makes.
pub fn named(handed: Handed, name: &'static str, make: fn(&Handed) -> Result<Option<Task>, Error>) -> Starting {
    Box::pin(async move {
        if !handed
            .provided
            .read::<Named>()
            .is_some_and(|named| named.0.iter().any(|n| n == name))
        {
            return Ok(());
        }
        let task = make(&handed)?;
        if !handed.booted().await? {
            return Ok(());
        }
        match task {
            Some(task) => task.await,
            None => Ok(()),
        }
    })
}

/// Every package this binary holds, by its name.
fn every() -> Vec<String> {
    crate::boot::every_package()
}

/// What every package of an agent is handed.
fn handed(store: &Store, id: &str, clock: Arc<dyn Clock>, provided: Provided, stop: watch::Receiver<bool>) -> Handed {
    Handed {
        store: store.clone(),
        id: id.to_string(),
        clock,
        events: Events::new(store),
        provided,
        run: Run::new(stop),
        life: None,
    }
}

/// AN AGENT BOOTED AND NOT YET STARTED: its boot begun, the world's documents and the self in, and no package's. Its
/// packages' bootings finish the boot, which is why booting is the tasks' and not the boot's alone: which packages'
/// documents an agent holds is what each booting decides (`Handed::joins`), and a role no package declares is refused
/// once every booting has ended.
pub struct Booted {
    handed: Handed,
    stop: watch::Sender<bool>,
    first: Vec<String>,
}

/// BEGIN TO BOOT `agent` of `world` INTO `store`, handed `provided`: the kernel's vocabulary, the world's documents and
/// the self. Nothing runs until `Booted::start`.
pub fn boot(
    store: &Store,
    world: &std::path::Path,
    agent: &str,
    clock: Arc<dyn Clock>,
    provided: Provided,
) -> Result<Booted, Error> {
    let begun = crate::boot::begin(store, &crate::boot::Booting { world, agent })?;
    let (stop, stopped) = watch::channel(false);
    let handed = handed(store, agent, clock, provided, stopped);
    handed.run.boot.lock().expect("a boot nobody poisoned").begun = Some(begun);
    Ok(Booted {
        handed,
        stop,
        first: Vec::new(),
    })
}

impl Booted {
    /// THOSE `names` NAMES START FIRST, and in that order, the rest after them, and a test's member runs where it is
    /// named (`Named`): for a test, which holds a run the same whichever package hears first. A name no package
    /// registered under is an error: its crate was not built in.
    pub fn first(mut self, names: &[String]) -> Result<Self, Error> {
        let every = every();
        if let Some(name) = names.iter().find(|n| !every.contains(n)) {
            return Err(Error::Evaluation(format!(
                "no package registered itself as {name}: this binary was built without it"
            )));
        }
        self.handed.provided.provide(Named(names.to_vec()));
        self.first = names.to_vec();
        Ok(self)
    }

    /// START THE AGENT, on the Tokio runtime this is called in: its booting, every package this binary holds booting
    /// inside it, each deciding for itself whether it runs, and then its running. This ends once the booting has -
    /// refused where a package could not boot, or where the boot it finished was.
    pub async fn start(self) -> Result<Running, Error> {
        self.go(true).await
    }

    /// BOOT THE AGENT AND START NOTHING: its booting alone, every package booting inside it and ending there, its core
    /// made and nothing run. What a check does, and a test that calls a package's core itself.
    pub async fn without_starting(self) -> Result<Running, Error> {
        self.go(false).await
    }

    async fn go(mut self, runs: bool) -> Result<Running, Error> {
        started();
        let rest: Vec<String> = every().into_iter().filter(|n| !self.first.contains(n)).collect();
        let order = [std::mem::take(&mut self.first), rest].concat();
        self.handed.run.runs = runs;
        self.handed.run.packages = order.len();
        let (said, booted) = tokio::sync::oneshot::channel();
        let running = spawn(self.handed, self.stop, order, said);
        let _ = booted.await;
        running.booted()
    }
}

/// THE AGENT'S OWN TASK: it hears every package's booting end, finishes the boot once all have and ends its booting -
/// telling whoever started it - and where the agent runs, begins its running, hears every running package's running
/// end, and ends its running as its stopping begins.
async fn agent(handed: Handed, mut hears: Hears, booting: Span, said: tokio::sync::oneshot::Sender<()>) {
    let run = &handed.run;
    let (mut bootings, mut running) = (0, 0);
    while bootings < run.packages {
        match hears.next().await {
            Some(Woke::Event(BOOTED, heard)) => {
                bootings += 1;
                if runs(&heard) {
                    running += 1;
                }
            }
            Some(_) => {}
            None => break,
        }
    }
    {
        let mut boot = run.boot.lock().expect("a boot nobody poisoned");
        if let Some(begun) = boot.begun.take() {
            let joined: Vec<String> = boot.joined.iter().map(|(p, _)| p.clone()).collect();
            if let Err(e) = begun.finish(&handed.store, &joined) {
                boot.refused = Some(e.to_string());
            }
        }
    }
    booting.end(&handed.events, handed.clock.now(), Vec::new());
    let runs = run.runs && run.refused().is_none();
    let agent_running = runs.then(|| {
        Span::begin(
            &handed.events,
            AGENT_RUNNING,
            run.running.clone(),
            None,
            Vec::new(),
            handed.clock.now(),
        )
    });
    handed.events.spoke();
    let _ = said.send(());
    let Some(agent_running) = agent_running else {
        handed.events.rest();
        return;
    };
    let mut ran = 0;
    while ran < running {
        match hears.next().await {
            Some(Woke::Event(RAN, _)) => ran += 1,
            Some(_) => {}
            None => break,
        }
    }
    agent_running.end(&handed.events, handed.clock.now(), Vec::new());
    *run.stopping.lock().expect("a stopping nobody poisoned") = Some(Span::begin(
        &handed.events,
        AGENT_STOPPING,
        crate::events::mint(),
        None,
        Vec::new(),
        handed.clock.now(),
    ));
    handed.events.rest();
}

/// EVERY START IS SPAWNED AS A TASK, in `order`, inside a booting of its own the kernel begins: each is the whole of
/// its package's life. What every lifecycle hears is asked before any task runs, so none misses what another says
/// first; and a start that ends with its booting, running or stopping open ends it.
fn spawn(
    handed: Handed,
    stop: watch::Sender<bool>,
    order: Vec<String>,
    said: tokio::sync::oneshot::Sender<()>,
) -> Running {
    let events = handed.events.clone();
    let mut hears = events.hears();
    hears.activity(crate::activity::ENDED, PACKAGE_BOOTING, BOOTED);
    hears.activity(crate::activity::ENDED, PACKAGE_RUNNING, RAN);
    let lives: Vec<Arc<tokio::sync::Mutex<Life>>> = order
        .iter()
        .map(|name| {
            let mut hears = events.hears();
            hears.activity(crate::activity::ENDED, PACKAGE_BOOTING, BOOTED);
            hears.said(PACKAGE_JOINED, JOINED);
            hears.activity(crate::activity::ENDED, AGENT_BOOTING, AGENT_BOOTED);
            hears.activity(crate::activity::ENDED, AGENT_RUNNING, AGENT_RAN);
            Arc::new(tokio::sync::Mutex::new(Life {
                package: name.clone(),
                hears,
                booting: None,
                running: None,
                stopping: None,
                krate: None,
            }))
        })
        .collect();
    let booting = Span::begin(
        &events,
        AGENT_BOOTING,
        handed.run.booting.clone(),
        None,
        Vec::new(),
        handed.clock.now(),
    );
    let mut running = Running {
        handed: handed.clone(),
        names: Vec::new(),
        joins: Vec::new(),
        agent: None,
        stop,
        halt: None,
        halted: Arc::new(Notify::new()),
    };
    events.0.busy.up();
    running.agent = Some(tokio::spawn(TURN.scope(
        RefCell::new(Local {
            said: Vec::new(),
            in_hand: 1,
        }),
        agent(handed.clone(), hears, booting, said),
    )));
    for (name, life) in order.into_iter().zip(lives) {
        let package = inventory::iter::<Package>()
            .find(|p| p.name == name)
            .expect("a package found is registered");
        let mut own = handed.clone();
        own.life = Some(life.clone());
        let start = (package.start)(own);
        let (events, clock, part_of) = (handed.events.clone(), handed.clock.clone(), handed.run.booting.clone());
        //  A TASK IS BUSY FROM ITS START until it first waits: the run is not over before every policy decided once.
        events.0.busy.up();
        let named = name.clone();
        let scoped = TURN.scope(
            RefCell::new(Local {
                said: Vec::new(),
                in_hand: 1,
            }),
            async move {
                let about = vec![(PACKAGE, Literal::new_simple_literal(&named).into())];
                life.lock().await.booting = Some(Span::begin(
                    &events,
                    PACKAGE_BOOTING,
                    crate::events::mint(),
                    Some(part_of),
                    about,
                    clock.now(),
                ));
                let ended = start.await;
                life.lock().await.end(&events, clock.now());
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
    /// The packages that booted with a core, in the order they did.
    pub fn parts(&self) -> Vec<String> {
        self.handed.run.started.lock().expect("starts nobody poisoned").clone()
    }

    /// The run once the agent's booting has ended: refused where a package could not boot, or the boot was.
    fn booted(self) -> Result<Self, Error> {
        if let Some(why) = self.handed.run.refused() {
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

    /// STOP EVERY TASK, each stopping itself where it waits, and wait for them to end: every package's running ends,
    /// then the agent's, and what stops does so inside the agent's stopping, which ends as the last task does.
    pub async fn stop(self) {
        let _ = self.stop.send(true);
        for join in self.joins {
            let _ = join.await;
        }
        if let Some(agent) = self.agent {
            let _ = agent.await;
        }
        let stopping = self
            .handed
            .run
            .stopping
            .lock()
            .expect("a stopping nobody poisoned")
            .take();
        if let Some(stopping) = stopping {
            stopping.end(&self.handed.events, self.handed.clock.now(), Vec::new());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::{Elapsing, seconds};

    const STEP: &str = "http://example.org/test#Stepping";

    /// What a test's packages write down, provided.
    type Seen = Arc<Mutex<Vec<String>>>;

    fn noon() -> DateTime {
        "2026-11-12T12:00:00Z".parse().unwrap()
    }

    /// An agent over `store` with no world, so no boot is begun: what the kernel's own cases start.
    fn booted(store: &Store, clock: Arc<dyn Clock>, provided: Provided) -> Booted {
        let (stop, stopped) = watch::channel(false);
        Booted {
            handed: handed(store, "urn:test:me", clock, provided, stopped),
            stop,
            first: Vec::new(),
        }
    }

    async fn running(names: &[&str], seen: &Seen) -> Running {
        let store = Store::new().unwrap();
        let provided = Provided::default();
        provided.provide(seen.clone());
        let names: Vec<String> = names.iter().map(|n| n.to_string()).collect();
        booted(&store, Arc::new(Elapsing::from(noon())), provided)
            .first(&names)
            .unwrap()
            .start()
            .await
            .unwrap()
    }

    fn seen_by(handed: &Handed) -> Seen {
        handed
            .provided
            .take::<Seen>()
            .inspect(|s| handed.provided.provide(s.clone()))
            .unwrap()
    }

    //  BEGINS AND ENDS AN ACTIVITY as the run begins, writes down that it did, and then that it waited.
    inventory::submit! { Package { name: "test/begins", start: |handed| named(handed, "test/begins", |handed| {
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

    //  HEARS EVERY START said, and writes each down but the lifecycle's, which the kernel says of every package.
    inventory::submit! { Package { name: "test/hears", start: |handed| named(handed, "test/hears", |handed| {
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
                        if !kind.starts_with("http://example.org/orexis#") {
                            seen.lock().unwrap().push(format!("heard {tag} {kind}"));
                        }
                    }
                    _ => break,
                }
            }
            Ok(())
        })))
    }) } }

    //  HOLDS THE AGENT, and lets it go an hour on by the clock.
    inventory::submit! { Package { name: "test/holds", start: |handed| named(handed, "test/holds", |handed| {
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
    inventory::submit! { Package { name: "test/arrives", start: |handed| named(handed, "test/arrives", |handed| {
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
        let store = Store::new().unwrap();
        store
            .update(&format!(
                "PREFIX orexis: <http://example.org/orexis#>
                 INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . \
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
        let store = Store::new().unwrap();
        let clock = Arc::new(crate::clock::Manual::at(noon()));
        let refused = booted(&store, clock, Provided::default()).first(&["test/absent".to_string()]);
        assert!(refused.is_err());
    }
}
