//! A ROLE THE SELF PLAYS, READ AS ONE THING. A role is an instance the agent `orexis:plays`, in its self graph
//! (knowledge/domain/kernel/role.md), and what it says is how its package is configured: a figure, a word, and a
//! link to a service the world is connected to, whose address the world's deployment graph states
//! (knowledge/decisions/the-world-says-what-it-is-connected-to.md). A package reads its role once, as it starts,
//! into a type of its own whose `Default` is the package's constants, and fills in what the role says: so what a
//! package can be told is the fields of one struct, and what holds where the role says nothing is one `impl`.
//!
//! The kernel names no role and no property: a package hands the class it serves and asks by the properties it
//! declares.

use std::collections::BTreeMap;

use crate::Error;
use crate::ontology::{DEPLOYMENT, SELF_GRAPH};
use crate::store::{Store, Within, value};

/// EVERYTHING THE SELF'S ROLES SAY, a row per statement, with the address the world's deployment states of what
/// the statement names where it names a service.
const SAID_Q: &str = "SELECT ?role ?kind ?property ?said ?url WHERE { \
?me a orexis:Self ; orexis:plays ?role . ?role a ?kind ; ?property ?said . \
OPTIONAL { ?said <https://schema.org/url> ?url } } ORDER BY ?role ?property ?said ?url";

/// What the self's roles of one class say: each property with what is said of it, in the order stated, and the
/// address of each service a property names. Several roles of the class are read as one.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Played {
    said: BTreeMap<String, Vec<String>>,
    answers: BTreeMap<String, String>,
}

impl Played {
    /// Everything said by `property`, as its lexical values.
    pub fn words(&self, property: &str) -> &[String] {
        self.said.get(property).map_or(&[], Vec::as_slice)
    }

    /// What is said by `property`, the first where several are.
    pub fn word(&self, property: &str) -> Option<&str> {
        self.words(property).first().map(String::as_str)
    }

    /// The figure said by `property`: a number above nought, or None, and the package's own then holds.
    pub fn figure(&self, property: &str) -> Option<f64> {
        self.words(property)
            .iter()
            .filter_map(|said| said.parse::<f64>().ok())
            .find(|figure| *figure > 0.0)
    }

    /// Where the service `property` names answers, as the world's deployment graph states it: None where the role
    /// names none, or the world says nothing of the one named.
    pub fn answers(&self, property: &str) -> Option<&str> {
        self.answers.get(property).map(String::as_str)
    }
}

/// WHAT THE SELF'S ROLES OF `class` SAY, read off its self graph and the world's deployment graph: None where the
/// self plays no role of the class or of one beneath it.
pub fn played(store: &Store, class: &str) -> Result<Option<Played>, Error> {
    let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    let rows = store.rows(SAID_Q, &known)?;
    //  THE ROLES OF THE CLASS: each whose kind is the class or beneath it, by the closure the store holds.
    let mut of_class: BTreeMap<String, bool> = BTreeMap::new();
    for row in &rows {
        let (Some(role), Some(kind)) = (value(row, "role"), value(row, "kind")) else {
            continue;
        };
        let is = store.closed(&kind)?.iter().any(|c| c == class);
        *of_class.entry(role).or_default() |= is;
    }
    if !of_class.values().any(|is| *is) {
        return Ok(None);
    }
    let mut played = Played::default();
    for row in &rows {
        let (Some(role), Some(property), Some(said)) = (value(row, "role"), value(row, "property"), value(row, "said"))
        else {
            continue;
        };
        if !of_class.get(&role).copied().unwrap_or(false) {
            continue;
        }
        let all = played.said.entry(property.clone()).or_default();
        if !all.contains(&said) {
            all.push(said);
        }
        if let Some(url) = value(row, "url").filter(|url| !url.is_empty()) {
            played.answers.entry(property).or_insert(url);
        }
    }
    Ok(Some(played))
}
