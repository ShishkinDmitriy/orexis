//! `scope_actions`: the actions the store holds, clustered into the scopes their effects join, written back to the
//! store — as `agent/planning/scope_actions.py` writes them, and held to its cases. The partition is computed from
//! what the rules do, over the atoms `footprint` reads off each filling of an action and the edges each loaded
//! derivation makes, never off namespaces; it runs at boot, once, and whenever the actions are rebuilt.

use std::collections::{BTreeMap, BTreeSet};

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, DERIVED, GRAPH_PREFIX};
use orexis::store::{Store, Within, iri};

use crate::find_scopes::STANDING_Q;
use crate::footprint::{Atom, Filling, Side, atoms_of, spelled, stored_edges};
use crate::ontology::{DERIVATION_GRAPH, WAIT};

const WAIT_Q: &str = "SELECT ?w WHERE { $wait a orexis:Action BIND($wait AS ?w) } LIMIT 1";

/// Cluster every action the store holds into scopes and write them, replacing what stood. An action is in every
/// scope a filling of it lies in, and a predicate or a term in every scope an atom of it falls in; an action
/// stating no effect, or with no filling here, is in none — save the wait, which is in every one (#920); one whose
/// effect cannot be read joins everything.
pub fn scope_actions(store: &Store, now: DateTime) -> Result<(), Error> {
    let atoms = atoms_of(store, now)?;
    let derivations = store.graphs_of(&[DERIVATION_GRAPH], &Within::default())?;
    let derivations: Vec<&str> = derivations.iter().map(String::as_str).collect();
    let edges = stored_edges(store, &derivations)?;
    let parts = partition(&atoms, &edges);
    let part_of: BTreeMap<&Atom, usize> = parts
        .iter()
        .enumerate()
        .flat_map(|(n, part)| part.iter().map(move |a| (a, n + 1)))
        .collect();
    let mut place: BTreeMap<(char, String), BTreeSet<usize>> = BTreeMap::new();
    for (n, part) in parts.iter().enumerate() {
        for (predicate, _) in part {
            place.entry(('p', predicate.clone())).or_default().insert(n + 1);
        }
    }
    for filling in atoms.values().flatten().flatten() {
        let mut scopes: BTreeSet<usize> = filling.atoms.iter().filter_map(|a| part_of.get(a).copied()).collect();
        if scopes.is_empty() {
            scopes = (1..=parts.len()).collect();
        }
        for term in &filling.terms {
            place.entry(('t', term.clone())).or_default().extend(&scopes);
        }
    }
    let actions = store.graphs_of(&[ACTION], &Within::at(now))?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let waits = !store
        .rows(&bind(WAIT_Q, &[("wait", Value::iri(WAIT))])?, &actions)?
        .is_empty();
    let mut written = Vec::new();
    for (n, part) in parts.iter().enumerate() {
        let mut members: BTreeSet<String> = place
            .iter()
            .filter(|(_, scopes)| scopes.contains(&(n + 1)))
            .map(|((_, m), _)| m.clone())
            .collect();
        members.extend(
            atoms
                .iter()
                .filter(|(_, fillings)| {
                    fillings
                        .as_ref()
                        .is_none_or(|fs| fs.iter().any(|f: &Filling| f.atoms.iter().any(|a| part.contains(a))))
                })
                .map(|(action, _)| action.clone()),
        );
        if waits {
            members.insert(WAIT.to_string());
        }
        written.push((scope_name(n + 1), members));
    }
    save(store, &written)?;
    log::info!("{} action(s) in {} scope(s)", atoms.len(), parts.len());
    Ok(())
}

/// THE STORE'S SCOPES: the graph this module replaces whole on every run, and nobody's.
pub const SCOPES_GRAPH: &str = "http://example.org/orexis/graph/scopes";

/// The nth scope of the partition, largest first.
fn scope_name(n: usize) -> String {
    format!("{GRAPH_PREFIX}scopes/{n}")
}

/// Replace the store's scopes with these, classified even when empty: a store with no scope graph has never been
/// scoped. One update: every standing scope graph dropped with its row, then the graph and its row together.
fn save(store: &Store, scopes: &[(String, BTreeSet<String>)]) -> Result<(), Error> {
    let standing: Vec<String> = store
        .rows(STANDING_Q, &[])?
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect();
    let blocks: Vec<String> = scopes
        .iter()
        .map(|(scope, members)| {
            let members: Vec<String> = members
                .iter()
                .map(|m| format!("<{m}> planning:inScope <{scope}> ."))
                .collect();
            format!("  <{scope}> a planning:Scope .\n  {}", members.join(" "))
        })
        .collect();
    let dropped: String = standing
        .iter()
        .map(|g| {
            format!(
                "DROP SILENT GRAPH <{g}> ;\nDELETE {{ GRAPH ?cat {{ <{g}> ?p ?o }} }} WHERE {{ GRAPH ?cat {{ ?cat a \
                 orexis:CatalogueGraph . <{g}> ?p ?o }} }} ;\n"
            )
        })
        .collect();
    store.update(&format!(
        "{dropped}
INSERT {{
  GRAPH <{SCOPES_GRAPH}> {{
{}
  }}
  GRAPH ?cat {{ <{SCOPES_GRAPH}> a planning:ScopeGraph ; orexis:arrivedBy <{DERIVED}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{SCOPES_GRAPH}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ planning:ScopeGraph rdfs:subClassOf ?kind }} }}",
        blocks.join("\n")
    ))
}

/// The SCOPES of a vocabulary: atoms joined wherever one filling of one action reads or writes both, and separate
/// where nothing does; a derivation's edges are predicates and join every key of theirs, an unreadable action or
/// edge joins everything, and an atom keyed by nothing is every atom of its predicate. Largest first.
pub fn partition(atoms: &BTreeMap<String, Option<Vec<Filling>>>, rules: &[(Side, Side)]) -> Vec<BTreeSet<Atom>> {
    let edges: Vec<&BTreeSet<Atom>> = atoms.values().flatten().flatten().map(|f| &f.atoms).collect();
    let mut known: BTreeSet<Atom> = edges.iter().flat_map(|e| e.iter().cloned()).collect();
    for (reads, writes) in rules {
        for side in [reads, writes].into_iter().flatten() {
            known.extend(side.iter().map(|p| (p.clone(), None)));
        }
    }
    let by_index: Vec<&Atom> = known.iter().collect();
    let index: BTreeMap<&Atom, usize> = by_index.iter().enumerate().map(|(i, a)| (*a, i)).collect();
    let mut parent: Vec<usize> = (0..known.len()).collect();
    fn find(parent: &mut [usize], mut x: usize) -> usize {
        while parent[x] != x {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        x
    }
    let mut join = |items: &[usize]| {
        if let Some((first, rest)) = items.split_first() {
            for other in rest {
                let (a, b) = (find(&mut parent, *first), find(&mut parent, *other));
                if a != b {
                    parent[a] = b;
                }
            }
        }
    };
    let every: Vec<usize> = (0..known.len()).collect();
    if atoms.values().any(Option::is_none) {
        join(&every);
    }
    for edge in &edges {
        join(&edge.iter().map(|a| index[a]).collect::<Vec<_>>());
    }
    for (reads, writes) in rules {
        match (reads, writes) {
            (Some(reads), Some(writes)) => {
                let side: Vec<usize> = reads.union(writes).map(|p| index[&(p.clone(), None)]).collect();
                join(&side);
            }
            _ => join(&every),
        }
    }
    let mut by_predicate: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for (i, (predicate, _)) in by_index.iter().enumerate() {
        by_predicate.entry(predicate).or_default().push(i);
    }
    for members in by_predicate.values() {
        if members
            .iter()
            .any(|&i| known.iter().nth(i).is_some_and(|a| a.1.is_none()))
        {
            join(members);
        }
    }
    let mut out: BTreeMap<usize, BTreeSet<Atom>> = BTreeMap::new();
    for (i, atom) in by_index.iter().enumerate() {
        let root = find(&mut parent, i);
        out.entry(root).or_default().insert((*atom).clone());
    }
    let mut parts: Vec<BTreeSet<Atom>> = out.into_values().collect();
    parts.sort_by_cached_key(|part| {
        let mut names: Vec<String> = part.iter().map(spelled).collect();
        names.sort();
        (std::cmp::Reverse(part.len()), names)
    });
    parts
}

#[cfg(test)]
mod tests {
    //! `scope_actions`, held to `agent/planning/tests/scope_actions/`'s cases as `test_scope_actions.py` holds the
    //! Python act.

    use std::path::PathBuf;

    use orexis::snapshots;

    use super::*;

    fn cases() -> PathBuf {
        snapshots::tree().join("planning/tests/scope_actions")
    }

    #[test]
    fn scope_actions_leaves_the_store_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            scope_actions(&store, snapshots::now()).unwrap();
            snapshots::held_to_diff(&case, &store, "scope_actions");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 5);
    }
}
