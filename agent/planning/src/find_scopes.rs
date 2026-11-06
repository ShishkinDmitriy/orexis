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
mod tests {
    //! Reading the store's scopes, held to what `test_find_scopes.py` holds the Python read to.

    use orexis::snapshots;

    use super::*;

    fn store() -> Store {
        let store = Store::new(snapshots::namespaces()).expect("an empty store");
        store
            .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph } }")
            .unwrap();
        store
    }

    fn set(members: &[&str]) -> BTreeSet<String> {
        members.iter().map(|m| m.to_string()).collect()
    }

    #[test]
    fn a_store_nobody_scoped_says_none_and_a_scoped_empty_store_says_nothing() {
        let store = store();
        assert_eq!(find_scopes(&store).unwrap(), None, "never scoped");
        store
            .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }")
            .unwrap();
        assert_eq!(
            find_scopes(&store).unwrap(),
            Some(Scopes::default()),
            "scoped, and empty"
        );
    }

    #[test]
    fn every_member_is_read_with_every_scope_it_is_in() {
        let store = store();
        store
            .update(
                "INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:s1> a planning:Scope . <urn:test:s2> a planning:Scope .
                            <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:fill> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:heat> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }",
            )
            .unwrap();
        let scopes = find_scopes(&store).unwrap().unwrap();
        let expected: BTreeMap<String, BTreeSet<String>> = [
            ("urn:test:level", set(&["urn:test:s1"])),
            ("urn:test:fill", set(&["urn:test:s1"])),
            ("urn:test:bed", set(&["urn:test:s1", "urn:test:s2"])),
            ("urn:test:heat", set(&["urn:test:s2"])),
        ]
        .into_iter()
        .map(|(k, v)| (k.to_string(), v))
        .collect();
        assert_eq!(scopes.0, expected);
        assert_eq!(scopes.all(), set(&["urn:test:s1", "urn:test:s2"]));
    }

    #[test]
    fn a_thing_is_placed_where_the_scopes_of_what_it_names_meet() {
        let store = store();
        store
            .update(
                "INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:temperature> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }",
            )
            .unwrap();
        let scopes = find_scopes(&store).unwrap().unwrap();
        assert_eq!(
            scopes.meet(["urn:test:bed", "urn:test:level", "urn:test:probe"]),
            set(&["urn:test:s1"])
        );
        assert_eq!(scopes.meet(["urn:test:bed"]), set(&["urn:test:s1", "urn:test:s2"]));
        assert_eq!(
            scopes.meet(["urn:test:level", "urn:test:temperature"]),
            set(&["urn:test:s1", "urn:test:s2"]),
            "held together by no scope, so every scope either is in"
        );
        assert_eq!(scopes.meet(["urn:test:probe"]), BTreeSet::new());
    }
}
