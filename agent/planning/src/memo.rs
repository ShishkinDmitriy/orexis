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
}
