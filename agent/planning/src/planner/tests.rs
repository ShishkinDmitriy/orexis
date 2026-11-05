//! The Planner, held to what the Python suites hold it to: `plans/`'s cases (the imaginarium a pass leaves),
//! `expand/`'s (one iteration), and the tests of `test_planner.py`, `test_search.py`, `test_extract_plan.py` and
//! `test_publish_plan.py` that need no executor. Those that walk steps through an executor wait for execution: a
//! plan published and adopted by nobody is walked, as `walking` reads it, which is what the rest stand on.

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use oxigraph::model::Literal;

use orexis::ontology::FORECAST;
use orexis::snapshots;

use super::*;
use crate::footprint::changeable;
use crate::ontology::POSSIBLE_GRAPH;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/plans")
}

fn bench(name: &str) -> PathBuf {
    snapshots::tree().join(format!("planning/tests/bench/{name}.trig"))
}

fn minutes(n: i64) -> DateTime {
    snapshots::now()
        .checked_add_day_time_duration(DayTimeDuration::new(60 * n))
        .unwrap()
}

fn imagined<'p>(planner: &'p Planner<'_>) -> &'p Store {
    assert_eq!(planner.imaginaria.len(), 1, "one scope");
    planner.imaginaria.values().next().unwrap()
}

#[test]
fn the_pass_leaves_the_imaginarium_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = snapshots::stand_in(&case);
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner
            .plan(snapshots::now())
            .unwrap_or_else(|e| panic!("{}: {e}", case.display()));
        snapshots::held_to_diff(&case, imagined(&planner), "planner");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    for dir in [cases(), snapshots::tree().join("planning/tests/expand")] {
        assert!(snapshots::cases_in(&dir).len() >= 3);
        assert!(snapshots::orphans_in(&dir).is_empty());
    }
}

const OPEN_Q: &str = "
SELECT DISTINCT ?want WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for ?want ; planning:open true } }
ORDER BY ?want";

#[test]
fn one_iteration_adds_the_layer_the_diff_says() {
    for case in snapshots::cases_in(&snapshots::tree().join("planning/tests/expand")) {
        let store = snapshots::stand_in(&case);
        let planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        let wants: Vec<String> = store
            .rows(OPEN_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "want"))
            .collect();
        assert!(!wants.is_empty(), "{} has nothing to expand", case.display());
        let none = BTreeSet::new();
        let scoped = Searching {
            only: None,
            elsewhere: &none,
            within: None,
            at: snapshots::now(),
        };
        for want in wants {
            planner
                .expand(&store, &want, BUDGET, &scoped, &mut Memo::default())
                .unwrap();
        }
        snapshots::held_to_diff(&case, &store, "expand");
    }
}

// --- what a world is made of (#953) ----------------------------------------------------------------------------------

fn world_cases() -> Vec<PathBuf> {
    let mut out = snapshots::cases_in(&cases());
    out.push(bench("two_disk_hanoi"));
    out
}

/// What the writers of a one-scope imaginarium can write: predicates any object of which may be written, and
/// `(predicate, object)` pairs written with a fixed object.
fn writes(store: &Store) -> (BTreeSet<String>, HashSet<(String, Term)>) {
    let mut anything = BTreeSet::new();
    let mut fixed = HashSet::new();
    for p in changeable(store, None, snapshots::now())
        .unwrap()
        .expect("every writer reads")
    {
        match p.object {
            Some(o) => {
                fixed.insert((p.predicate, o));
            }
            None => {
                anything.insert(p.predicate);
            }
        }
    }
    let predictions = store.graphs_of(&[FORECAST], &Within::default()).unwrap();
    let mut graphs = predictions.clone();
    graphs.extend(store.revisions_of(&strs(&predictions), BELIEF).unwrap());
    for g in graphs {
        for t in store.triples(&g).unwrap() {
            anything.insert(t.predicate.as_str().to_string());
        }
    }
    (anything, fixed)
}

fn written_by(t: &Triple, anything: &BTreeSet<String>, fixed: &HashSet<(String, Term)>) -> bool {
    anything.contains(t.predicate.as_str()) || fixed.contains(&(t.predicate.as_str().to_string(), t.object.clone()))
}

fn worlds_of(store: &Store) -> Vec<String> {
    let mut out = store.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap();
    out.extend(store.graphs_of(&[POSSIBLE_GRAPH], &Within::default()).unwrap());
    out
}

#[test]
fn nothing_read_beside_a_world_is_what_a_step_can_write_and_everything_in_one_is() {
    for case in world_cases() {
        let store = snapshots::stand_in(&case);
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        for im in planner.imaginaria.values() {
            let (anything, fixed) = writes(im);
            let worlds = worlds_of(im);
            assert!(!worlds.is_empty(), "{}", case.display());
            for world in &worlds {
                for t in im.triples(world).unwrap() {
                    assert!(
                        written_by(&t, &anything, &fixed),
                        "{}: {world} holds {t}",
                        case.display()
                    );
                }
                for graph in world_at(im, Some(world), &Asking::default(), &mut Memo::default()).unwrap() {
                    if graph == *world {
                        continue;
                    }
                    for t in im.triples(&graph).unwrap() {
                        assert!(
                            !written_by(&t, &anything, &fixed),
                            "{}: {graph} beside {world} holds {t}",
                            case.display()
                        );
                    }
                }
            }
        }
    }
}

// --- reruns: the imaginarium outlives the pass ----------------------------------------------------------------------

const STEPS_Q: &str =
    "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?p { ?p a planning:Plan . ?s a execution:Step ; execution:partOf ?p } }";
const ROOTS_Q: &str = "
SELECT DISTINCT ?root WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph ; (planning:by/planning:from)+ ?root .
               ?root a planning:GroundGraph } }";
const WEIGHED_Q: &str = "
SELECT (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:weighs ?w .
               FILTER NOT EXISTS { ?w a planning:GroundGraph } } }";
const OUTCOME_Q: &str = "SELECT ?o WHERE { GRAPH ?p { ?p a planning:Plan ; planning:outcome ?o } }";

fn count(store: &Store, text: &str) -> usize {
    value(&store.rows(text, &[]).unwrap()[0], "n").unwrap().parse().unwrap()
}

fn possible(planner: &Planner<'_>) -> BTreeSet<String> {
    imagined(planner)
        .graphs_of(&[POSSIBLE_GRAPH], &Within::default())
        .unwrap()
        .into_iter()
        .collect()
}

fn steps(planner: &Planner<'_>) -> usize {
    count(imagined(planner), STEPS_Q)
}

fn outcome(planner: &Planner<'_>) -> String {
    local_of(&iri(&imagined(planner).rows(OUTCOME_Q, &[]).unwrap()[0], "o").unwrap())
}

/// The world moves a disk: its `hanoi:on` row replaced in the belief graph holding it.
fn move_disk(store: &Store, disk: &str, onto: &str) {
    let found = store
        .rows(
            &format!(
                "SELECT ?d ?p ?o ?g WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }}
        GRAPH ?g {{ ?d ?p ?o }} FILTER(STRENDS(STR(?d), \"{disk}\") && STRENDS(STR(?p), \"#on\")) }}"
            ),
            &[],
        )
        .unwrap();
    let r = &found[0];
    let (d, p, o, g) = (
        iri(r, "d").unwrap(),
        iri(r, "p").unwrap(),
        r["o"].to_string(),
        iri(r, "g").unwrap(),
    );
    store
        .update(&format!(
            "DELETE DATA {{ GRAPH <{g}> {{ <{d}> <{p}> {o} }} }} ; INSERT DATA {{ GRAPH <{g}> {{ <{d}> <{p}> <{onto}> }} }}"
        ))
        .unwrap();
}

/// Forget every plan handed down, as if nobody took it up and nothing walks it.
fn forget_handed(store: &Store) {
    for handed in store.graphs_of(&[orexis::ontology::PLAN], &Within::default()).unwrap() {
        store.forget_graph(&handed, Some(BELIEF)).unwrap();
    }
}

#[test]
fn a_pass_a_minute_later_hands_down_nothing_again_and_forks_nothing() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    assert_eq!(planner.plan(snapshots::now()).unwrap().len(), 1);
    assert_eq!(planner.walking().unwrap().len(), 1, "the plan handed down is walked");
    let (worlds, made) = (possible(&planner), steps(&planner));
    assert_eq!(made, 3);
    assert!(
        planner.plan(minutes(1)).unwrap().is_empty(),
        "and not handed down again"
    );
    assert_eq!(possible(&planner), worlds, "nothing forked for a want being walked");
}

#[test]
fn nothing_happened_and_the_next_pass_forks_nothing() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    forget_handed(&store);
    let worlds = possible(&planner);
    assert_eq!(steps(&planner), 3);
    planner.plan(minutes(1)).unwrap();
    assert_eq!((possible(&planner), steps(&planner)), (worlds, 3));
}

fn stamp(store: &Store, disk: &str, at: &str) {
    let found = store
        .rows(
            &format!(
                "SELECT ?d ?g WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }}
        GRAPH ?g {{ ?d ?p ?o }} FILTER(STRENDS(STR(?d), \"{disk}\") && STRENDS(STR(?p), \"#on\")) }}"
            ),
            &[],
        )
        .unwrap();
    let (d, g) = (iri(&found[0], "d").unwrap(), iri(&found[0], "g").unwrap());
    store
        .update(&format!(
            "DELETE WHERE {{ GRAPH <{g}> {{ <{d}> <http://www.w3.org/ns/sosa/resultTime> ?t }} }} ; \
             INSERT DATA {{ GRAPH <{g}> {{ <{d}> <http://www.w3.org/ns/sosa/resultTime> \"{at}\" }} }}"
        ))
        .unwrap();
}

#[test]
fn a_reading_re_stamped_with_its_instant_is_no_surprise() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    stamp(&store, "disk_1", "2026-01-01T12:00:00Z");
    planner.plan(snapshots::now()).unwrap();
    forget_handed(&store);
    let worlds = possible(&planner);
    stamp(&store, "disk_1", "2026-01-01T12:01:00Z");
    planner.plan(minutes(1)).unwrap();
    assert_eq!((possible(&planner), steps(&planner)), (worlds, 3));
}

#[test]
fn a_surprise_starts_the_search_afresh() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    forget_handed(&store);
    let old: BTreeSet<String> = imagined(&planner)
        .graphs_of(&[GROUND_GRAPH], &Within::default())
        .unwrap()
        .into_iter()
        .collect();
    assert!(!old.is_empty() && !possible(&planner).is_empty());
    let found = store
        .rows(
            "SELECT ?d WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d ?p ?o } \
             FILTER(STRENDS(STR(?d), \"disk_1\") && STRENDS(STR(?p), \"#on\")) }",
            &[],
        )
        .unwrap();
    let disk_1 = iri(&found[0], "d").unwrap();
    move_disk(&store, "disk_1", "http://example.org/orexis/hanoi#PegB");
    move_disk(&store, "disk_2", &disk_1);
    planner.plan(minutes(1)).unwrap();
    let im = imagined(&planner);
    let new: BTreeSet<String> = im
        .graphs_of(&[GROUND_GRAPH], &Within::default())
        .unwrap()
        .into_iter()
        .collect();
    assert!(
        !new.is_empty() && old.is_disjoint(&new),
        "the ground the last pass stood in went"
    );
    let roots: BTreeSet<String> = im
        .rows(ROOTS_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "root"))
        .collect();
    assert!(
        !roots.is_empty() && roots.is_subset(&new),
        "every world standing was forked from the new ground"
    );
    assert_eq!(steps(&planner), 2, "disk 2 to C, disk 1 to C");
}

/// Hanoi planned once: candidates weighed, and the plan's steps.
fn weighed(case: &Path, budget: usize, estimate: bool) -> (usize, usize) {
    let store = snapshots::stand_in(case);
    if !estimate {
        store
            .update(
                "DELETE { GRAPH ?g { ?d <http://example.org/orexis/planning#estimates> ?e } } \
                 WHERE { GRAPH ?g { ?d <http://example.org/orexis/planning#estimates> ?e } }",
            )
            .unwrap();
    }
    let mut planner = Planner::new(&store, snapshots::AGENT, Some(budget)).unwrap();
    planner.plan(snapshots::now()).unwrap();
    (count(imagined(&planner), WEIGHED_Q), steps(&planner))
}

#[test]
fn an_estimate_refuses_forks_a_uniform_cost_search_pays_for() {
    let with_it = weighed(&bench("three_disk_hanoi"), 128, true);
    let without = weighed(&bench("three_disk_hanoi"), 128, false);
    assert!(with_it.1 == 7 && without.1 == 7, "the same optimal plan either way");
    assert!(
        with_it.0 < without.0,
        "fewer candidates weighed: {} against {}",
        with_it.0,
        without.0
    );
}

#[test]
fn a_search_the_budget_cuts_short_is_finished_by_the_passes_after() {
    let (whole, _) = weighed(&bench("three_disk_hanoi"), 128, true);
    let store = snapshots::stand_in(&bench("three_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, Some(20)).unwrap();
    let mut passes = Vec::new();
    for i in 0..3 {
        planner.plan(minutes(i)).unwrap();
        assert_eq!(
            planner.standing(minutes(i)).unwrap().len(),
            1,
            "the want stands until its desire reads met"
        );
        assert_eq!(planner.exhausted().unwrap(), i < 2, "cut short twice, then satisfied");
        passes.push((outcome(&planner), planner.walking().unwrap().len()));
    }
    let expected: Vec<(String, usize)> = [("Exhausted", 0), ("Exhausted", 0), ("Satisfied", 1)]
        .iter()
        .map(|(o, n)| (o.to_string(), *n))
        .collect();
    assert_eq!(passes, expected);
    assert_eq!(steps(&planner), 7);
    assert_eq!(
        count(imagined(&planner), WEIGHED_Q),
        whole,
        "no candidate weighed twice, and none skipped"
    );
}

#[test]
fn the_budget_is_the_agents_stance_where_its_self_graph_states_one() {
    let store = snapshots::stand_in(&bench("three_disk_hanoi"));
    assert_eq!(Planner::new(&store, snapshots::AGENT, None).unwrap().budget, BUDGET);
    let cat = store.catalogue().unwrap().unwrap();
    let (me, own) = (snapshots::ME, "http://example.org/test#self");
    store
        .update(&format!(
            "INSERT DATA {{ GRAPH <{own}> {{ <{me}> a orexis:Self ; <{BUDGET_TERM}> 20 }}
  GRAPH <{cat}> {{ <{own}> a orexis:SelfGraph , orexis:BeliefGraph , orexis:Graph ; orexis:ownedBy <{me}> }} }}"
        ))
        .unwrap();
    assert_eq!(Planner::new(&store, snapshots::AGENT, Some(64)).unwrap().budget, 64);
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    assert_eq!(planner.budget, 20);
    planner.plan(snapshots::now()).unwrap();
    assert_eq!(
        (outcome(&planner), count(imagined(&planner), WEIGHED_Q)),
        ("Exhausted".to_string(), 20)
    );
}

#[test]
fn scope_is_the_boots_act_and_writes_what_a_pass_reads() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let scopes = "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a <http://example.org/orexis/planning#Scope> } }";
    store
        .update("DELETE WHERE { GRAPH ?g { ?s ?p <http://example.org/orexis/planning#Scope> } }")
        .unwrap();
    assert_eq!(count(&store, scopes), 0);
    Planner::scope(&store, snapshots::now()).unwrap();
    assert!(
        count(&store, scopes) >= 1,
        "the scopes are written again, from the actions"
    );
    Planner::new(&store, snapshots::AGENT, None)
        .unwrap()
        .plan(snapshots::now())
        .unwrap();
}

#[test]
fn a_candidate_a_cut_left_untaken_is_taken_by_the_next_pass() {
    let (whole, made) = weighed(&bench("courier_corner"), 128, true);
    assert_eq!(made, 8);
    let store = snapshots::stand_in(&bench("courier_corner"));
    let mut planner = Planner::new(&store, snapshots::AGENT, Some(16)).unwrap();
    let mut outcomes = Vec::new();
    for i in 0..8 {
        planner.plan(minutes(i)).unwrap();
        outcomes.push(outcome(&planner));
        if outcomes.last().map(String::as_str) == Some("Satisfied") {
            break;
        }
    }
    assert!(
        outcomes.last().map(String::as_str) == Some("Satisfied") && outcomes.len() > 1,
        "{outcomes:?}"
    );
    assert_eq!(steps(&planner), 8);
    assert_eq!(
        count(imagined(&planner), WEIGHED_Q),
        whole,
        "no candidate weighed twice, and none skipped"
    );
}

#[test]
fn a_want_the_world_meets_before_the_plan_begins_is_reached() {
    let store = snapshots::stand_in(&bench("two_disk_hanoi"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    let walked = planner.walking().unwrap();
    let found = store
        .rows(
            "SELECT ?d WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d ?p ?o } \
             FILTER(STRENDS(STR(?d), \"disk_2\") && STRENDS(STR(?p), \"#on\")) }",
            &[],
        )
        .unwrap();
    let disk_2 = iri(&found[0], "d").unwrap();
    move_disk(&store, "disk_2", "http://example.org/orexis/hanoi#PegC");
    move_disk(&store, "disk_1", &disk_2);
    planner.plan(minutes(1)).unwrap();
    assert_eq!(planner.reached, walked);
}

const PREDICTED_Q: &str = "
SELECT DISTINCT ?side ?s ?o WHERE {
  GRAPH ?p { ?step a execution:Step ; ?side ?g . VALUES ?side { execution:adds execution:retracts } }
  GRAPH ?g { ?s ?pred ?o } }";

#[test]
fn a_step_landing_across_a_prediction_predicts_its_own_effect_alone() {
    let store = snapshots::stand_in(&cases().join("a_step_lands_across_a_prediction_it_does_not_touch.trig"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    let predicted: BTreeSet<(String, String, String)> = store
        .rows(PREDICTED_Q, &[])
        .unwrap()
        .iter()
        .map(|r| {
            (
                local_of(&iri(r, "side").unwrap()),
                local_of(&iri(r, "s").unwrap()),
                value(r, "o").unwrap(),
            )
        })
        .collect();
    let expected: BTreeSet<(String, String, String)> = [("adds", "tank1", "11"), ("retracts", "tank1", "6")]
        .iter()
        .map(|(a, b, c)| (a.to_string(), b.to_string(), c.to_string()))
        .collect();
    assert_eq!(
        predicted, expected,
        "the fill's own change, and nothing of the tank the prediction drains"
    );
}

const CHANGES_Q: &str = "
SELECT ?g ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  ?g prov:wasDerivedFrom ?w ; a ?side . VALUES ?side { execution:AddsGraph execution:RetractsGraph } } }";

#[test]
fn a_world_the_re_root_drops_takes_what_its_step_changed_with_it() {
    let t = "http://example.org/test#";
    let store = snapshots::stand_in(&cases().join("a_step_lands_across_a_prediction_it_does_not_touch.trig"));
    let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    let first: Vec<String> = imagined(&planner)
        .rows(CHANGES_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect();
    assert_eq!(first.len(), 2, "the fill's world was forked in the later ground");
    store
        .update(&format!(
            "DELETE DATA {{ GRAPH <{t}sensed> {{ <{t}tank1> <{t}level> 6 }} }} ; INSERT DATA {{ GRAPH <{t}sensed> {{ <{t}tank1> <{t}level> 7 }} }}"
        ))
        .unwrap();
    planner.plan(minutes(1)).unwrap();
    let im = imagined(&planner);
    assert!(
        im.rows(CHANGES_Q, &[]).unwrap().is_empty(),
        "no graph of what a step changed outlives its world"
    );
    for g in first {
        assert!(im.quads(&g).unwrap().is_empty(), "{g}");
    }
}

fn top(
    late: i64,
    lands: Option<&str>,
    spent: &str,
    best: Option<&str>,
    best_late: i64,
    best_lands: Option<&str>,
) -> orexis::store::Row {
    let mut row = orexis::store::Row::new();
    let int =
        |n: i64| -> Term { Literal::new_typed_literal(n.to_string(), oxigraph::model::vocab::xsd::INTEGER).into() };
    let dec = |s: &str| -> Term { Literal::new_typed_literal(s, oxigraph::model::vocab::xsd::DECIMAL).into() };
    let at = |s: &str| -> Term { Literal::new_typed_literal(s, oxigraph::model::vocab::xsd::DATE_TIME).into() };
    row.insert("late".into(), int(late));
    row.insert("spent".into(), dec(spent));
    row.insert("remaining".into(), dec("0"));
    row.insert("bestLate".into(), int(best_late));
    if let Some(l) = lands {
        row.insert("lands".into(), at(l));
    }
    if let Some(b) = best {
        row.insert("best".into(), dec(b));
    }
    if let Some(b) = best_lands {
        row.insert("bestLands".into(), at(b));
    }
    row
}

#[test]
fn the_bound_ranks_on_time_before_late_and_a_late_world_soonest_first() {
    let (at, sooner) = (Some("2026-01-01T12:40:00+00:00"), Some("2026-01-01T12:35:00+00:00"));
    let b = |r| beaten(&r).unwrap();
    assert!(!b(top(0, None, "1", None, 0, None)), "no achiever yet refuses nothing");
    assert!(
        b(top(1, at, "0", Some("5"), 0, None)),
        "an on-time achiever refuses a late world"
    );
    assert!(b(top(0, None, "5", Some("5"), 0, None)) && !b(top(0, None, "4", Some("5"), 0, None)));
    assert!(
        !b(top(0, None, "9", Some("1"), 1, at)),
        "a late achiever refuses nothing on time"
    );
    assert!(
        !b(top(1, sooner, "9", Some("1"), 1, at)),
        "nor a late world landing sooner"
    );
    assert!(b(top(1, at, "0", Some("1"), 1, sooner)));
    assert!(b(top(1, at, "1", Some("1"), 1, at)) && !b(top(1, at, "0", Some("1"), 1, at)));
}

// --- one want's search ------------------------------------------------------------------------------------------------

const MADE_Q: &str = "
SELECT (COUNT(DISTINCT ?w) AS ?worlds) (COUNT(DISTINCT ?x) AS ?weighings) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    { ?w a planning:PossibleGraph } UNION { ?x a planning:Weighing ; planning:for $want } } }";
const PLAN_Q: &str = "
SELECT ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?g { ?g a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?g } } }
GROUP BY ?outcome";

/// The low tank's imaginarium with its want derived — the store `search` is handed.
fn derived_into(beliefs: &Store) -> (Store, String) {
    let store = Store::new(snapshots::namespaces()).unwrap();
    prepare_ground(beliefs, &store, None, None).unwrap();
    lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
    let mut memo = Memo::default();
    for pair in unweighed(&store, None, None, &mut memo).unwrap() {
        weigh(
            &store,
            &iri(&pair, "for").unwrap(),
            &iri(&pair, "about").unwrap(),
            &mut memo,
        )
        .unwrap();
    }
    derive_wants(&store, snapshots::now(), &BTreeMap::new(), &BTreeSet::new()).unwrap();
    let wants = find_wants(&store, snapshots::now(), &Finding::default()).unwrap();
    assert_eq!(wants.len(), 1);
    let want = wants[0].clone();
    (store, want)
}

fn made(store: &Store, want: &str) -> (usize, usize) {
    let r = &store
        .rows(&bind(MADE_Q, &[("want", Value::iri(want))]).unwrap(), &[])
        .unwrap()[0];
    (
        value(r, "worlds").unwrap().parse().unwrap(),
        value(r, "weighings").unwrap().parse().unwrap(),
    )
}

fn plan_of(store: &Store, want: &str) -> (String, usize) {
    let r = &store
        .rows(&bind(PLAN_Q, &[("want", Value::iri(want))]).unwrap(), &[])
        .unwrap()[0];
    (iri(r, "outcome").unwrap(), value(r, "steps").unwrap().parse().unwrap())
}

#[test]
fn a_search_the_budget_cut_short_is_finished_by_the_next_call() {
    let beliefs = snapshots::stand_in(&snapshots::cases_in(&cases())[0]);
    let (store, want) = derived_into(&beliefs);
    let planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
    let none = BTreeSet::new();
    let scoped = Searching {
        only: None,
        elsewhere: &none,
        within: None,
        at: snapshots::now(),
    };
    planner.search(&store, &want, 1, &scoped, &mut Memo::default()).unwrap();
    assert_eq!(plan_of(&store, &want), (EXHAUSTED.to_string(), 0));
    assert_eq!(
        made(&store, &want),
        (1, 2),
        "the ground weighed, and one world forked and weighed"
    );
    planner
        .search(&store, &want, 32, &scoped, &mut Memo::default())
        .unwrap();
    assert_eq!(plan_of(&store, &want), (SATISFIED.to_string(), 2));
    assert_eq!(
        made(&store, &want),
        (2, 3),
        "one more world, on top of the first — not beside it"
    );
}

#[test]
fn a_finished_search_asked_again_makes_nothing_new() {
    let beliefs = snapshots::stand_in(&snapshots::cases_in(&cases())[0]);
    let (store, want) = derived_into(&beliefs);
    let planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
    let none = BTreeSet::new();
    let scoped = Searching {
        only: None,
        elsewhere: &none,
        within: None,
        at: snapshots::now(),
    };
    planner
        .search(&store, &want, BUDGET, &scoped, &mut Memo::default())
        .unwrap();
    let held = |s: &Store| -> BTreeSet<String> { s.engine().iter().map(|q| q.unwrap().to_string()).collect() };
    let before = held(&store);
    planner
        .search(&store, &want, BUDGET, &scoped, &mut Memo::default())
        .unwrap();
    assert_eq!(held(&store), before, "not one quad differs");
    assert_eq!(plan_of(&store, &want), (SATISFIED.to_string(), 2));
}

// --- the plan read out, and handed down --------------------------------------------------------------------------------

const CHAIN_STEPS_Q: &str = "
SELECT ?step ?fills ?of (COUNT(?before) AS ?n) WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?fills ; planning:of ?of .
                OPTIONAL { ?before execution:then+ ?step } } }
GROUP BY ?step ?fills ?of ORDER BY ?n";

fn walked(beliefs: &Store) -> Planner<'_> {
    let mut planner = Planner::new(beliefs, snapshots::AGENT, None).unwrap();
    planner.plan(snapshots::now()).unwrap();
    planner
}

fn plan_steps(store: &Store, graph: &str) -> Vec<orexis::store::Row> {
    store
        .rows(&bind(CHAIN_STEPS_Q, &[("plan", Value::iri(graph))]).unwrap(), &[])
        .unwrap()
}

#[test]
fn every_step_names_the_candidate_it_was_minted_from_and_the_chain_is_the_worlds_ancestry() {
    let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
    let planner = walked(&beliefs);
    let im = imagined(&planner);
    let graphs = im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap();
    let steps = plan_steps(im, &graphs[0]);
    assert_eq!(steps.len(), 2);
    let cat = im.catalogue().unwrap().unwrap();
    for step in &steps {
        let of = iri(step, "of").unwrap();
        let found = im
            .rows(
                &format!("SELECT ?a WHERE {{ GRAPH <{cat}> {{ <{of}> a planning:Candidate ; planning:fills ?a }} }}"),
                &[],
            )
            .unwrap();
        assert_eq!(
            iri(&found[0], "a"),
            iri(step, "fills"),
            "a step fills what its candidate filled"
        );
    }
    let by_chain: Vec<String> = steps.iter().filter_map(|s| iri(s, "of")).collect();
    let deepest = im
        .rows(
            &format!(
                "SELECT ?w (COUNT(?above) AS ?depth) WHERE {{ GRAPH <{cat}> {{ ?w a planning:PossibleGraph ; (planning:by/planning:from)+ ?above }} }}
                 GROUP BY ?w ORDER BY DESC(?depth) LIMIT 1"
            ),
            &[],
        )
        .unwrap();
    let (mut ancestry, mut world) = (Vec::new(), iri(&deepest[0], "w").unwrap());
    loop {
        let found = im
            .rows(&format!("SELECT ?parent ?by WHERE {{ GRAPH <{cat}> {{ <{world}> planning:by ?by . ?by planning:from ?parent }} }}"), &[])
            .unwrap();
        let Some(r) = found.first() else { break };
        ancestry.push(iri(r, "by").unwrap());
        world = iri(r, "parent").unwrap();
    }
    ancestry.reverse();
    assert_eq!(ancestry, by_chain, "root first, and the same candidates");
}

#[test]
fn extracting_again_leaves_the_same_plan() {
    let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
    let planner = walked(&beliefs);
    let im = imagined(&planner);
    let graph = im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap()[0].clone();
    let before = plan_steps(im, &graph);
    let found = im
        .rows(
            &format!("SELECT ?w WHERE {{ GRAPH <{graph}> {{ <{graph}> planning:for ?w }} }}"),
            &[],
        )
        .unwrap();
    assert_eq!(extract_plan(im, &iri(&found[0], "w").unwrap()).unwrap(), graph);
    assert_eq!(plan_steps(im, &graph), before);
    let outcome = im
        .rows(
            &format!("SELECT ?o WHERE {{ GRAPH <{graph}> {{ <{graph}> planning:outcome ?o }} }}"),
            &[],
        )
        .unwrap();
    assert_eq!(iri(&outcome[0], "o").as_deref(), Some(SATISFIED));
}

#[test]
fn a_plan_handed_down_is_walked_and_not_handed_down_again() {
    let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
    let mut planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
    let written = planner.plan(snapshots::now()).unwrap();
    let handed = beliefs
        .graphs_of(&[orexis::ontology::PLAN], &Within::default())
        .unwrap();
    assert_eq!(handed, written);
    assert_eq!(written.len(), 1);
    let pursues = beliefs
        .rows(
            &format!(
                "SELECT ?w WHERE {{ GRAPH <{0}> {{ <{0}> execution:pursues ?w }} }}",
                written[0]
            ),
            &[],
        )
        .unwrap();
    let want = iri(&pursues[0], "w").unwrap();
    assert!(want.ends_with("keeper.in_range.pursued.tank1"), "{want}");
    assert_eq!(planner.walking().unwrap(), BTreeSet::from([want]));
    assert!(planner.plan(snapshots::now()).unwrap().is_empty());
}

#[test]
fn an_answer_is_not_handed_down() {
    let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
    beliefs
        .update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
        .unwrap();
    scope_actions(&beliefs, snapshots::now()).unwrap();
    let mut planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
    assert!(planner.plan(snapshots::now()).unwrap().is_empty());
    assert!(
        planner
            .imaginaria
            .values()
            .any(|im| !im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap().is_empty()),
        "the pass still wrote down what it concluded"
    );
    assert!(
        beliefs
            .graphs_of(&[orexis::ontology::PLAN], &Within::default())
            .unwrap()
            .is_empty(),
        "and handed down nothing"
    );
}
