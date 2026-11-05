//! WHAT ONLY A WRITE CAN CHANGE, computed once a pass, as `agent/store.py`'s `Memo` keeps it for the acts: the
//! catalogue's name, the actions, the grounds by hash, the graphs per instant, the mint counter. Typed fields
//! where the Python keeps a dictionary keyed by tuples, since each act names what it keeps.
//!
//! A FRESH MEMO IS NO MEMO: every act computes what it does not find, so a caller that keeps nothing across
//! calls hands a new one and gets fresh answers.

use std::collections::{HashMap, HashSet};

use oxigraph::model::Term;
use oxsdatatypes::DateTime;

/// One action as the store declares it: its precondition and the parameters it takes, sorted.
#[derive(Clone, Debug)]
pub struct Declared {
    pub action: String,
    pub precondition: String,
    pub takes: Vec<String>,
}

/// What a filling is: the parameter, the value's text, and the term itself.
pub type Filling = Vec<(String, String, Term)>;

/// What a candidate's row says: the world it is taken in and when that world is, what it fills, its mint number,
/// what reaching the world spent, and every parameter it is filled with — the parameter and the value's text.
#[derive(Clone, Debug)]
pub struct Binding {
    pub from: String,
    pub start: DateTime,
    pub end: DateTime,
    pub action: String,
    pub minted: u64,
    pub spent: f64,
    pub filled: Vec<(String, String)>,
    pub subject: String,
}

/// What an action carries for a search: its landing and cost texts, and its effect's rules in order.
#[derive(Clone, Debug)]
pub struct Carried {
    pub lands: Option<String>,
    pub costs: Option<String>,
    pub rules: Vec<orexis_belief::transition::Rule>,
}

#[derive(Default)]
pub struct Memo {
    pub catalogue: Option<String>,
    pub spoken_for: Option<HashSet<String>>,
    pub knowable: HashMap<String, Vec<String>>,
    pub when: HashMap<String, Option<(DateTime, Option<DateTime>)>>,
    pub actions: Option<Vec<Declared>>,
    pub waits: Option<bool>,
    pub minted: Option<u64>,
    pub grounds: Option<Vec<(DateTime, String)>>,
    pub next_ground: HashMap<String, Option<DateTime>>,
    pub bindings: HashMap<String, Binding>,
    pub carried: HashMap<String, Option<Carried>>,
    pub acts_for: Option<Option<String>>,
    pub ground_set: Option<HashSet<String>>,
    pub ground_at: HashMap<String, Option<String>>,
    pub closed: HashMap<String, Vec<String>>,
}
