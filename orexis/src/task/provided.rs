//! WHAT THE AGENT IS PROVIDED, by its type, by whoever runs it, and the few things packages hand each other
//! through it because neither may import the other.

use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// WHAT THE AGENT IS PROVIDED, by its type, by whoever runs it - the binary, a check or a test: the connectors a test
/// makes, a bus, a web, a bot, a model, a sink, and the word that the agent is deployed or checked; and what one
/// package provides another, the journal it keeps. A package takes the one it knows, where one was provided, and one
/// value of a type is provided at a time.
#[derive(Clone, Default)]
pub struct Provided(pub(super) Arc<Mutex<HashMap<TypeId, Box<dyn Any + Send>>>>);

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
pub struct Checking(pub(super) Arc<Mutex<Found>>);

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
pub struct Journaled(pub(super) Arc<Mutex<Option<oxigraph::store::Store>>>);

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
