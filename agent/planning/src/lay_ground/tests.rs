//! `lay_ground`, held to `agent/planning/tests/lay_ground/`'s cases as `test_lay_ground.py` holds the Python act,
//! and to its tests beside them. The cases laid with the predictor's foresight, `tests/foreseen/`, come with the
//! prediction package.

use std::collections::{BTreeMap, HashSet};
use std::path::PathBuf;

use oxigraph::model::vocab::xsd;
use oxigraph::model::{Literal, NamedNode};
use oxsdatatypes::DayTimeDuration;

use orexis::snapshots;

use super::*;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/lay_ground")
}

const T: &str = "http://example.org/test#";

#[test]
fn lay_ground_lays_the_grounds_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = snapshots::stand_in(&case);
        lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
        snapshots::held_to_diff(&case, &store, "lay_ground");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    assert!(snapshots::cases_in(&cases()).len() >= 3);
    assert!(snapshots::orphans_in(&cases()).is_empty());
}

fn within(locals: &[&str]) -> BTreeSet<String> {
    locals.iter().map(|l| format!("{T}{l}")).collect()
}

fn hash_of(store: &Store, ground: &str) -> String {
    let text =
        format!("SELECT ?h WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{ground}> orexis:hash ?h }} }}");
    orexis::store::value(&store.rows(&text, &[]).unwrap()[0], "h").unwrap()
}

#[test]
fn a_forecast_read_by_nothing_lays_no_ground_and_one_read_is_a_period_by_everything_it_holds() {
    let case = cases().join("two_stretches_in_one_scope_are_two_grounds.trig");
    let store = snapshots::stand_in(&case);
    let level = within(&["level"]);
    let grounds = lay_ground(
        &store,
        snapshots::now(),
        &Laying {
            within: Some(&level),
            ..Laying::default()
        },
    )
    .unwrap();
    assert_eq!(grounds.len(), 2, "the temperature is read by nothing");
    assert_ne!(
        hash_of(&store, &grounds[0]),
        hash_of(&store, &grounds[1]),
        "the level dropped, which is read"
    );
    let store = snapshots::stand_in(&case);
    let both = within(&["level", "temperature"]);
    let grounds = lay_ground(
        &store,
        snapshots::now(),
        &Laying {
            within: Some(&both),
            ..Laying::default()
        },
    )
    .unwrap();
    assert_eq!(grounds.len(), 3);
}

#[test]
fn a_belief_ahead_that_no_text_reads_lays_no_ground() {
    let case = cases().join("a_forecast_holding_later_crosses_whole.trig");
    let laid = lay_ground(&snapshots::stand_in(&case), snapshots::now(), &Laying::default()).unwrap();
    assert_eq!(laid.len(), 2, "read anything: a ground at three");
    let store = snapshots::stand_in(&case);
    let level = within(&["level"]);
    let laid = lay_ground(
        &store,
        snapshots::now(),
        &Laying {
            within: Some(&level),
            ..Laying::default()
        },
    )
    .unwrap();
    assert_eq!(laid.len(), 1, "the warmth is read by nothing");
    assert!(
        store
            .graphs_of(&[CHANGEABLE_GRAPH], &Within::default())
            .unwrap()
            .is_empty(),
        "and nothing of the forecast was cut"
    );
}

fn node(local: &str) -> NamedNode {
    NamedNode::new(format!("{T}{local}")).unwrap()
}

fn integer(n: &str) -> Term {
    Literal::new_typed_literal(n, xsd::INTEGER).into()
}

#[test]
fn the_ground_where_a_step_in_flight_lands_holds_the_steps_change() {
    let store = snapshots::stand_in(&cases().join("two_stretches_in_one_scope_are_two_grounds.trig"));
    let tank = node("tank1");
    let landing = snapshots::now()
        .checked_add_day_time_duration(DayTimeDuration::new(900))
        .unwrap();
    let landed = [Landed {
        at: landing,
        retracts: vec![Triple::new(tank.clone(), node("temperature"), integer("20"))],
        adds: vec![
            Triple::new(tank.clone(), node("level"), integer("15")),
            Triple::new(tank.clone(), node("valve"), node("open")),
        ],
    }];
    let laying = Laying {
        landings: &[landing],
        landed: &landed,
        ..Laying::default()
    };
    let grounds = lay_ground(&store, snapshots::now(), &laying).unwrap();
    let facts = |ground: &str| -> BTreeSet<(String, String)> {
        store
            .triples(ground)
            .unwrap()
            .into_iter()
            .filter(|t| t.subject == tank.clone().into())
            .map(|t| {
                let p = t.predicate.as_str().rsplit('#').next().unwrap().to_string();
                let o = match &t.object {
                    Term::NamedNode(n) => n.as_str().to_string(),
                    Term::Literal(l) => l.value().to_string(),
                    other => other.to_string(),
                };
                (p, o)
            })
            .collect()
    };
    let pairs = |p: &[(&str, &str)]| -> BTreeSet<(String, String)> {
        p.iter().map(|(a, b)| (a.to_string(), b.to_string())).collect()
    };
    let open = format!("{T}open");
    assert_eq!(grounds.len(), 4);
    assert_eq!(
        facts(&grounds[0]),
        pairs(&[("level", "20"), ("temperature", "20")]),
        "the present holds what the world has shown"
    );
    assert_eq!(
        facts(&grounds[1]),
        pairs(&[("level", "15"), ("valve", &open)]),
        "where the step lands, its change"
    );
    assert_eq!(
        facts(&grounds[2]),
        pairs(&[("level", "5"), ("valve", &open)]),
        "inherited, and superseded again by key"
    );
    assert_eq!(
        facts(&grounds[3]),
        pairs(&[("level", "5"), ("valve", &open), ("temperature", "40")])
    );
}

const OPENING: &str = r#"
PREFIX : <http://example.org/test#>
PREFIX orexis: <http://example.org/orexis#>
PREFIX planning: <http://example.org/orexis/planning#>
PREFIX belief: <http://example.org/orexis/belief#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
INSERT DATA { GRAPH :actions {
  :open a orexis:Action ; orexis:takes :tank ;
    planning:effect [ a planning:Effect ; sh:rule [ a belief:Transition ; belief:update """PREFIX : <http://example.org/test#>
      DELETE { $tank :lid :closed } INSERT { ?tank :lid :open } WHERE { $tank :lid :closed . BIND($tank AS ?tank) }""" ] ] .
} }"#;

/// What every graph but the catalogue holds, by name.
fn held(store: &Store) -> BTreeMap<String, HashSet<Triple>> {
    let cat = store.catalogue().unwrap().unwrap();
    let mut out: BTreeMap<String, HashSet<Triple>> = BTreeMap::new();
    for graph in store.graph_names().unwrap() {
        if graph != cat {
            out.insert(graph.clone(), store.triples(&graph).unwrap().into_iter().collect());
        }
    }
    out
}

#[test]
fn an_action_added_makes_what_it_writes_changeable_and_nothing_else() {
    let store = snapshots::stand_in(&snapshots::tree().join("planning/tests/plans/a_low_tank_is_filled.trig"));
    let world = format!("{T}world");
    let lid = Triple::new(node("tank1"), node("lid"), node("closed"));
    store
        .add([lid.clone().in_graph(NamedNode::new(&world).unwrap())])
        .unwrap();
    let laid = lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
    let [ground] = laid.as_slice() else {
        panic!("one ground: {laid:?}")
    };
    let before = held(&store);
    assert!(
        before[&world].contains(&lid) && !before[ground].contains(&lid),
        "no writer writes a lid"
    );

    store.update(OPENING).unwrap();
    assert_eq!(
        lay_ground(&store, snapshots::now(), &Laying::default()).unwrap(),
        vec![ground.clone()]
    );
    let after = held(&store);

    let piece = format!("{world}.changeable");
    assert!(
        !before.contains_key(&piece) && after[&piece] == HashSet::from([lid.clone()]),
        "the lid is cut out"
    );
    let mut less = before[&world].clone();
    less.remove(&lid);
    assert_eq!(after[&world], less, "and out of the world");
    let mut more = before[ground].clone();
    more.insert(lid.clone());
    assert_eq!(after[ground], more, "and the present is laid with it");
    let actions = format!("{T}actions");
    assert!(after[&actions].is_superset(&before[&actions]) && after[&actions] != before[&actions]);
    let untouched: Vec<&String> = before
        .keys()
        .filter(|g| ![&world, ground, &actions].contains(g))
        .collect();
    assert!(!untouched.is_empty());
    let mut names: BTreeSet<&String> = after.keys().collect();
    names.remove(&piece);
    assert_eq!(names, before.keys().collect::<BTreeSet<_>>());
    for g in untouched {
        assert_eq!(after[g], before[g], "{g} changed");
    }
}
