//! `derive_wants`: every desire judged, and a want minted for every cluster of what its met-test reads unmet — as
//! `agent/planning/derive_wants.py` mints them, and held to its cases. NOTHING STANDS BETWEEN A DESIRE AND A WANT
//! but the weighings the Planner wrote: a desire is weighed in every ground, and read across the grounds in order
//! a violation has a stretch, from the first ground it holds in to the first later one it does not. A want is
//! minted per cluster of them — by scope, by instance and by stretch, and where a holder's constraint can make two
//! instances' plans collide, the two as one. **IT WITHDRAWS NOTHING**: the answer is every want the desires imply,
//! and `withdraw` is handed it.

mod clusters;
mod mint;
mod troubles;

use std::collections::{BTreeMap, BTreeSet, HashMap};

use clusters::clusters;
use mint::{mint, name_of, named};
use oxigraph::model::Term;
use oxsdatatypes::DateTime;
use troubles::troubles;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, RECORD};
use orexis::store::{Store, Within, iri, value};

use crate::couplings::{Couplings, couplings};
use crate::find_scopes::{Scopes, find_scopes};
use crate::memo::Memo;
use crate::ontology::{DESIRE, SHAPES, WANT};
use crate::shapes::Shapes;
use crate::terms::{SH, node};
use crate::withdraw::forget_one;

const MET_WHEN: &str = "http://example.org/orexis/planning#metWhen";

const UNMET_WHEN: &str = "http://example.org/orexis/planning#unmetWhen";

/// WHAT A DESIRE SAYS, from the graphs of desires and wants: its met-test, its estimate, what it is about, its label.
const SAID_Q: &str = "
SELECT ?p ?o WHERE {
  GRAPH ?g { $desire ?p ?o
    FILTER(?p IN (planning:metWhen, planning:unmetWhen, planning:estimates, planning:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { planning:DesireGraph planning:WantGraph } } }";

/// WHAT THIS DERIVATION HAS MINTED UNDER ONE DESIRE, across all time: existence is not an instant question.
const STANDING_Q: &str = "
SELECT ?w WHERE {
  GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom $desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }
ORDER BY ?w";

/// EVERY GRAPH OF WANTS THE DERIVATION WROTE THAT HOLDS ONE WANT, and how many wants each holds.
const HOMES_Q: &str = "
SELECT ?g (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a planning:Want . ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }
GROUP BY ?g";

const DESIRES_Q: &str = "
SELECT DISTINCT ?holder ?desire WHERE {
  GRAPH ?g { ?holder planning:holds ?desire . ?desire a planning:Desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:DesireGraph } }
ORDER BY ?holder ?desire";

/// THE TIMELINE: every ground, earliest first.
const GROUNDS_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start";

/// One way a desire is failing, and the stretch it fails over: `at` the start of the earliest ground it reads unmet
/// in, `until` the start of the first later ground it reads met in.
#[derive(Clone, Debug)]
struct Witness {
    instance: String,
    constraint: String,
    about: Option<String>,
    key: Vec<String>,
    at: DateTime,
    until: Option<DateTime>,
    /// The key terms that placed it in its scope, where what it is about placed it nowhere.
    placed: Vec<String>,
}

/// What a desire says, `(predicate, the engine's own term)`, sorted by predicate and the term's spelling.
type Said = Vec<(String, Term)>;

/// Mint a want under every desire for every cluster of what its met-test reads unmet, and answer with EVERY want
/// those desires imply — minted here or standing under the same name. `walking` is every want an intention walks,
/// with the instant its step in flight lands; `reopen` the walking wants the Planner reopened (#921).
pub fn derive_wants(
    store: &Store,
    now: DateTime,
    walking: &BTreeMap<String, DateTime>,
    reopen: &BTreeSet<String>,
) -> Result<BTreeSet<String>, Error> {
    let mut memo = Memo::default();
    let shapes = Shapes::of(
        store,
        &store.graphs_of(&[DESIRE, WANT, RECORD, SHAPES], &Within::default())?,
    )?;
    let scopes = find_scopes(store)?;
    let grounds: Vec<String> = store.rows(GROUNDS_Q, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let Some(present) = grounds.first() else {
        return Err(Error::Evaluation(
            "the store holds no ground — lay_ground has not run".into(),
        ));
    };
    let mut coupled: HashMap<String, Option<Couplings>> = HashMap::new();
    let mut wanted = BTreeSet::new();
    for (holder, desire) in desires_in(store)? {
        let Some(found) = troubles(store, &desire, scopes.as_ref(), &holder)? else {
            //  NOT JUDGED IS NOT MET: what stands under it is what it implies.
            wanted.extend(standing_under(store, &desire)?);
            continue;
        };
        if !coupled.contains_key(&holder) {
            let read = couplings(store, &holder, present, now, &mut memo)?;
            coupled.insert(holder.clone(), read);
        }
        let joins = coupled[&holder].as_ref();
        derive_under(
            store,
            &shapes,
            scopes.as_ref(),
            &holder,
            &desire,
            &found,
            now,
            joins,
            walking,
            reopen,
        )?;
        let said = said(store, &desire)?;
        let standing = standing_under(store, &desire)?;
        wanted.extend(named(
            &shapes,
            scopes.as_ref(),
            &desire,
            &said,
            &found,
            joins,
            &standing,
        )?);
    }
    Ok(wanted)
}

fn standing_under(store: &Store, desire: &str) -> Result<BTreeSet<String>, Error> {
    Ok(store
        .rows(&bind(STANDING_Q, &[("desire", Value::iri(desire))])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "w"))
        .collect())
}

#[allow(clippy::too_many_arguments)]
fn derive_under(
    store: &Store,
    shapes: &Shapes,
    scopes: Option<&Scopes>,
    holder: &str,
    desire: &str,
    found: &[Witness],
    now: DateTime,
    coupled: Option<&Couplings>,
    walking: &BTreeMap<String, DateTime>,
    reopen: &BTreeSet<String>,
) -> Result<Vec<String>, Error> {
    let standing = standing_under(store, desire)?;
    let said = said(store, desire)?;
    let clusters = clusters(scopes, found, coupled)?;
    let mut minted = Vec::new();
    for cluster in clusters {
        let about: Vec<String> = cluster
            .iter()
            .filter_map(|w| w.about.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instances: Vec<String> = cluster
            .iter()
            .map(|w| w.instance.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instance = (instances.len() == 1).then(|| instances[0].as_str());
        let keys = keys_of(&cluster);
        let child = name_of(shapes, desire, &said, &about, instance, &keys);
        let mut at = cluster
            .iter()
            .map(|w| w.at)
            .reduce(|a, b| if b < a { b } else { a })
            .unwrap_or(now);
        let until = if cluster.is_empty() || cluster.iter().any(|w| w.until.is_none()) {
            None
        } else {
            cluster
                .iter()
                .filter_map(|w| w.until)
                .reduce(|a, b| if b > a { b } else { a })
        };
        //  A WANT ALREADY STANDING FOR THIS CLUSTER IS LEFT ALONE, unless a belief arriving reopened it.
        if standing.contains(&child) && !reopen.contains(&child) {
            continue;
        }
        //  AND SO IS A WANT ALREADY ABOUT EVERY INSTANCE OF IT, unless reopened.
        let covering = if standing.contains(&child) {
            None
        } else {
            covering(shapes, &standing, &instances, &about)
        };
        if let Some(covering) = &covering
            && !reopen.contains(covering)
        {
            log::debug!("{child} is still pursued by {covering}, which is about every instance of it");
            continue;
        }
        let (reopened, why) = if standing.contains(&child) {
            unhome(store, &child)?;
            (vec![child.clone()], "the Planner reopened its untaken steps")
        } else if let Some(covering) = covering {
            (vec![covering], "the Planner reopened its untaken steps")
        } else {
            let walked: BTreeSet<String> = standing.iter().filter(|w| walking.contains_key(*w)).cloned().collect();
            let reopened = if coupled.is_some() {
                reopened(shapes, &walked, &instances, &about)
            } else {
                Vec::new()
            };
            (reopened, "a want a constraint couples to it has arrived")
        };
        if !reopened.is_empty() {
            let opens = reopened
                .iter()
                .map(|w| walking.get(w).copied().unwrap_or(now))
                .fold(at, |a, b| if b > a { b } else { a });
            if until.is_none_or(|u| u > opens) {
                at = opens;
            }
            log::info!("{child} reopens {}: {why}", reopened.join(", "));
        }
        if let Some(child) = mint(
            store, shapes, holder, desire, now, at, until, &said, &about, &instances, &keys, &reopened,
        )? {
            minted.push(child);
        }
    }
    Ok(minted)
}

/// Take `want` out of the graph of the stretch it was minted over: the graph goes where it held this want alone.
fn unhome(store: &Store, want: &str) -> Result<(), Error> {
    for r in store.rows(&bind(HOMES_Q, &[("want", Value::iri(want))])?, &[])? {
        let (Some(g), Some(n)) = (iri(&r, "g"), value(&r, "wants")) else {
            continue;
        };
        if n == "1" {
            store.forget_graph(&g, Some(BELIEF))?;
        } else {
            forget_one(store, &g, want)?;
        }
    }
    Ok(())
}

fn keys_of(cluster: &[Witness]) -> Vec<String> {
    cluster
        .iter()
        .flat_map(|w| w.placed.iter().cloned())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

fn subset(a: &[String], b: &[String]) -> bool {
    a.iter().all(|x| b.contains(x))
}

/// The standing want whose met-test targets every instance of a cluster about those instances themselves.
fn covering(shapes: &Shapes, standing: &BTreeSet<String>, instances: &[String], about: &[String]) -> Option<String> {
    if instances.is_empty() || !subset(about, instances) {
        return None;
    }
    standing
        .iter()
        .find(|want| {
            let held = targets(shapes, want);
            instances.iter().all(|i| held.contains(i))
        })
        .cloned()
}

/// The walking wants a cluster about `instances` reopens: each targeting fewer than all of them, and only those.
fn reopened(shapes: &Shapes, walking: &BTreeSet<String>, instances: &[String], about: &[String]) -> Vec<String> {
    if instances.len() < 2 || !subset(about, instances) {
        return Vec::new();
    }
    let wanted: BTreeSet<&String> = instances.iter().collect();
    walking
        .iter()
        .filter(|w| {
            let held = targets(shapes, w);
            !held.is_empty() && held.len() < wanted.len() && held.iter().all(|h| wanted.contains(h))
        })
        .cloned()
        .collect()
}

/// The instances a want is about, off the `sh:targetNode`s of the shape or avoided state it carries.
fn targets(shapes: &Shapes, want: &str) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for polarity in [MET_WHEN, UNMET_WHEN] {
        if let Some(shape) = shapes.value(&node(want), polarity) {
            for t in shapes.objects(&shape, &format!("{SH}targetNode")) {
                out.insert(spelled(&t));
            }
        }
    }
    out
}

/// A term's value as Python's `str(term)` of an rdflib term is: the IRI, the lexical form, a blank node's id.
fn spelled(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => n.as_str().to_string(),
        Term::Literal(l) => l.value().to_string(),
        Term::BlankNode(b) => b.as_str().to_string(),
        #[allow(unreachable_patterns)]
        other => other.to_string(),
    }
}

/// What the desire says, sorted by predicate and the term's spelling.
fn said(store: &Store, desire: &str) -> Result<Said, Error> {
    let mut out: Said = store
        .rows(&bind(SAID_Q, &[("desire", Value::iri(desire))])?, &[])?
        .into_iter()
        .filter_map(|r| Some((iri(&r, "p")?, r.get("o")?.clone())))
        .collect();
    out.sort_by_cached_key(|(p, o)| (p.clone(), o.to_string()));
    Ok(out)
}

fn desires_in(store: &Store) -> Result<Vec<(String, String)>, Error> {
    Ok(store
        .rows(DESIRES_Q, &[])?
        .iter()
        .filter_map(|r| Some((iri(r, "holder")?, iri(r, "desire")?)))
        .collect())
}

#[cfg(test)]
mod tests {
    //! `derive_wants`, held to `crates/orexis-planning/tests/derive_wants/`'s cases as `test_derive_wants.py` holds the Python
    //! act: a pass as a pass stands — the grounds laid, every desire weighed in every ground, the derivation, and
    //! `withdraw` handed its answer with what is walked.

    use std::path::PathBuf;

    use oxsdatatypes::DayTimeDuration;

    use orexis::snapshots;

    use super::*;
    use crate::lay_ground::{Laying, lay_ground};
    use crate::unweighed::unweighed;
    use crate::weigh::weigh;
    use crate::withdraw::withdraw;
    use crate::world_at::lexical;

    fn cases() -> PathBuf {
        snapshots::tree().join("orexis-planning/tests/derive_wants")
    }

    /// What the intentions walk, as the executor's `walking` reads it: every want an unresolved intention pursues.
    const WALKING_Q: &str = "
SELECT DISTINCT ?want WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
ORDER BY ?want";

    fn laid_and_weighed(case: &std::path::Path) -> Store {
        let store = snapshots::stand_in(case);
        lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
        weigh_all(&store, None);
        store
    }

    fn weigh_all(store: &Store, for_: Option<&str>) {
        let mut memo = Memo::default();
        for pair in unweighed(store, for_, None, &mut memo).unwrap() {
            weigh(
                store,
                &iri(&pair, "for").unwrap(),
                &iri(&pair, "about").unwrap(),
                &mut memo,
            )
            .unwrap();
        }
    }

    #[test]
    fn derive_wants_leaves_the_store_as_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = laid_and_weighed(&case);
            let walking: BTreeSet<String> = store
                .rows(WALKING_Q, &[])
                .unwrap()
                .iter()
                .filter_map(|r| iri(r, "want"))
                .collect();
            let at: BTreeMap<String, DateTime> = walking.iter().map(|w| (w.clone(), snapshots::now())).collect();
            let mut wanted = derive_wants(&store, snapshots::now(), &at, &BTreeSet::new())
                .unwrap_or_else(|e| panic!("{}: {e}", case.display()));
            wanted.extend(walking);
            withdraw(&store, Some(&wanted), &BTreeSet::new(), &BTreeSet::new()).unwrap();
            snapshots::held_to_diff(&case, &store, "derive_wants");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 14);
    }

    const HOMES: &str = "
SELECT ?w ?g ?start ?reopens WHERE {
  GRAPH ?g { ?w a planning:Want . OPTIONAL { ?w planning:reopens ?reopens } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph .
               OPTIONAL { ?g dcterms:temporal/orexis:start ?start } } }";

    #[test]
    fn a_walking_want_a_belief_reopened_is_minted_again_where_its_step_in_flight_lands() {
        for reopened in [false, true] {
            let store = laid_and_weighed(&cases().join("a_standing_want_is_left_alone.trig"));
            let want = "http://example.org/test#keeper.in_range.pursued.tank1.level";
            let lands = snapshots::now()
                .checked_add_day_time_duration(DayTimeDuration::new(30))
                .unwrap();
            let before: BTreeMap<String, String> = store
                .rows(HOMES, &[])
                .unwrap()
                .iter()
                .filter_map(|r| Some((iri(r, "w")?, iri(r, "g")?)))
                .collect();
            let reopen: BTreeSet<String> = if reopened {
                [want.to_string()].into()
            } else {
                BTreeSet::new()
            };
            let wanted = derive_wants(&store, snapshots::now(), &[(want.to_string(), lands)].into(), &reopen).unwrap();
            let homes: Vec<_> = store
                .rows(HOMES, &[])
                .unwrap()
                .into_iter()
                .filter(|r| iri(r, "w").as_deref() == Some(want))
                .collect();
            assert!(wanted.contains(want) && homes.len() == 1, "{homes:?}");
            let (graph, reopens) = (iri(&homes[0], "g").unwrap(), iri(&homes[0], "reopens"));
            if !reopened {
                assert_eq!(
                    (graph, reopens),
                    (before[want].clone(), None),
                    "a walking want nothing reopened stands where it was"
                );
                continue;
            }
            assert_eq!(
                lexical(&homes[0]["start"]).unwrap(),
                lands,
                "minted again where its step in flight lands"
            );
            assert_eq!(reopens.as_deref(), Some(want), "reopening itself");
            assert!(
                graph != before[want] && store.quads(&before[want]).unwrap().is_empty(),
                "the old graph goes"
            );
        }
    }

    const REMAINING_Q: &str = "
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ; planning:remaining ?left .
               ?g a planning:GroundGraph } }";

    #[test]
    fn two_wants_under_one_desire_read_two_estimates() {
        let store = laid_and_weighed(&cases().join("two_parcels_two_estimates.trig"));
        let wants = derive_wants(&store, snapshots::now(), &BTreeMap::new(), &BTreeSet::new()).unwrap();
        assert_eq!(wants.len(), 2, "{wants:?}");
        for want in &wants {
            weigh_all(&store, Some(want));
        }
        let left: BTreeMap<String, f64> = store
            .rows(REMAINING_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| {
                let for_ = iri(r, "for")?;
                Some((for_.rsplit('.').next()?.to_string(), value(r, "left")?.parse().ok()?))
            })
            .collect();
        assert_eq!(
            left,
            [("parcel_a".to_string(), 3.0), ("parcel_b".to_string(), 2.0)].into()
        );
    }
}
