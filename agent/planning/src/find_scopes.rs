//! READING THE STORE'S SCOPES — every scope each predicate, each term and each action is in, as
//! `agent/planning/find_scopes.py` reads them. `scope_actions` writes the partition; this reads it back, asking the
//! scope graphs by class. A store holding none at all answers None, which is a store nobody scoped; a scoped store
//! with nothing in it answers an empty map.

use std::collections::{BTreeMap, BTreeSet};

use orexis::Error;
use orexis::store::{Store, iri};

const SCOPES_Q: &str = "SELECT ?member ?scope WHERE { ?member planning:inScope ?scope }";

/// EVERY STANDING SCOPE GRAPH, asked of the catalogue by class.
pub(crate) const STANDING_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } }
ORDER BY ?g";

/// The partition as read: every member — predicate, term or action — to the SET of scopes it is in, and the one
/// question a reader asks of it, where a thing naming several members is.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Scopes(pub BTreeMap<String, BTreeSet<String>>);

impl Scopes {
    /// Every scope the store has.
    pub fn all(&self) -> BTreeSet<String> {
        self.0.values().flatten().cloned().collect()
    }

    /// The scope `member` is in where that is exactly one, else None — a word two scopes' keys both hold tells
    /// nothing on its own.
    pub fn one(&self, member: &str) -> Option<&str> {
        match self.0.get(member) {
            Some(held) if held.len() == 1 => held.iter().next().map(String::as_str),
            _ => None,
        }
    }

    /// The scopes a thing naming `names` is of: the scopes every one of its named members is in, and where no scope
    /// holds them all, every scope any of them is in; nothing where it names no member at all, which is a thing
    /// every scope holds.
    pub fn meet<'a>(&self, names: impl IntoIterator<Item = &'a str>) -> BTreeSet<String> {
        let sets: Vec<&BTreeSet<String>> = names.into_iter().filter_map(|n| self.0.get(n)).collect();
        let Some((first, rest)) = sets.split_first() else {
            return BTreeSet::new();
        };
        let together: BTreeSet<String> = first
            .iter()
            .filter(|s| rest.iter().all(|other| other.contains(*s)))
            .cloned()
            .collect();
        if together.is_empty() {
            sets.into_iter().flatten().cloned().collect()
        } else {
            together
        }
    }
}

/// Every member's scopes, from the scope graphs asked by class — or None where the store holds none at all.
pub fn find_scopes(store: &Store) -> Result<Option<Scopes>, Error> {
    let graphs: Vec<String> = store
        .rows(STANDING_Q, &[])?
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect();
    if graphs.is_empty() {
        return Ok(None);
    }
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for r in store.rows(SCOPES_Q, &graphs)? {
        if let (Some(member), Some(scope)) = (iri(&r, "member"), iri(&r, "scope")) {
            out.entry(member).or_default().insert(scope);
        }
    }
    Ok(Some(Scopes(out)))
}

#[cfg(test)]
mod tests;
