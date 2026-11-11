//! WHAT A DESIRE READS UNMET: its witnesses in every ground, each a violation the met-test says, placed where the
//! scopes of what it names meet and keyed by what it offends.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Store, iri, value};

use super::{Witness, spelled};
use crate::find_scopes::Scopes;
use crate::memo::Memo;
use crate::world_at::{Asking, lexical, world_at};

/// WHAT ONE DESIRE'S WEIGHINGS SAY, ground by ground.
const TROUBLES_Q: &str = "
SELECT ?start ?g ?met ?instance ?constraint ?about ?offending WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $desire ; planning:weighs ?g .
    ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
    OPTIONAL { ?x planning:met ?met }
    OPTIONAL { ?x planning:violation ?v . ?v planning:instance ?instance .
               OPTIONAL { ?v planning:constraint ?constraint }
               OPTIONAL { ?v planning:about ?about }
               OPTIONAL { ?v planning:offending ?offending FILTER(isIRI(?offending)) } } } }
ORDER BY ?start ?instance ?constraint ?offending";

/// WHAT A NODE NAMES IN A GROUND, as the objects of its own facts.
const NAMES_Q: &str = "SELECT DISTINCT ?o WHERE { $node ?p ?o FILTER(isIRI(?o)) }";

/// A way of failing: the instance, the constraint, and the key.
type Way = (String, String, Vec<String>);

/// Every way `desire` is failing, each with the stretch it fails over — or None where any ground was not judged,
/// which is not the same as met. The key is what the offending value is keyed by in the ground it offended in: the
/// scope members among what it names, less what the violation is about, a member of every scope and the holder.
pub(super) fn troubles(
    store: &Store,
    desire: &str,
    scopes: Option<&Scopes>,
    holder: &str,
) -> Result<Option<Vec<Witness>>, Error> {
    let found = store.rows(&bind(TROUBLES_Q, &[("desire", Value::iri(desire))])?, &[])?;
    if found.is_empty() || found.iter().any(|r| !r.contains_key("met")) {
        return Ok(None);
    }
    let mut read = Memo::default();
    let everywhere = scopes.map(Scopes::all).unwrap_or_default();
    let mut by_ground: BTreeMap<String, Vec<&orexis::store::Row>> = BTreeMap::new();
    for r in &found {
        if let Some(start) = value(r, "start") {
            by_ground.entry(start).or_default().push(r);
        }
    }
    let mut seen: Vec<(Way, Witness)> = Vec::new();
    let mut lifted: HashMap<Way, DateTime> = HashMap::new();
    let mut names: HashMap<(String, String), Vec<String>> = HashMap::new();
    for group in by_ground.values() {
        let at = lexical(&group[0]["start"])?;
        let mut unmet = BTreeSet::new();
        for r in group {
            let Some(instance) = iri(r, "instance") else { continue };
            let about = r.get("about").map(spelled);
            let constraint = r.get("constraint").map(spelled).unwrap_or_default();
            let mut keyed = Vec::new();
            if let (Some(scopes), Some(offending), Some(g)) = (scopes, iri(r, "offending"), iri(r, "g")) {
                let cached = names.get(&(g.clone(), offending.clone())).cloned();
                keyed = match cached {
                    Some(k) => k,
                    None => {
                        let world = world_at(store, Some(&g), &Asking::default(), &mut read)?;
                        let world: Vec<&str> = world.iter().map(String::as_str).collect();
                        let text = bind(NAMES_Q, &[("node", Value::iri(offending.as_str()))])?;
                        let mut named: BTreeSet<String> =
                            store.rows(&text, &world)?.iter().filter_map(|n| iri(n, "o")).collect();
                        named.insert(offending.clone());
                        let k: Vec<String> = named
                            .into_iter()
                            .filter(|o| {
                                scopes.0.get(o).is_some_and(|s| *s != everywhere)
                                    && Some(o) != about.as_ref()
                                    && o != holder
                            })
                            .collect();
                        names.insert((g, offending), k.clone());
                        k
                    }
                };
            }
            let key = (instance.clone(), constraint.clone(), keyed.clone());
            unmet.insert(key.clone());
            if !seen.iter().any(|(k, _)| *k == key) {
                seen.push((
                    key,
                    Witness {
                        instance,
                        constraint,
                        about,
                        key: keyed,
                        at,
                        until: None,
                        placed: Vec::new(),
                    },
                ));
            }
        }
        for (key, _) in &seen {
            if !unmet.contains(key) {
                lifted.entry(key.clone()).or_insert(at);
            }
        }
    }
    let mut out: Vec<Witness> = seen
        .into_iter()
        .map(|(k, mut w)| {
            w.until = lifted.get(&k).copied();
            w
        })
        .collect();
    out.sort_by(|a, b| {
        (a.at, &a.instance, &a.constraint, &a.key)
            .partial_cmp(&(b.at, &b.instance, &b.constraint, &b.key))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    Ok(Some(out))
}
