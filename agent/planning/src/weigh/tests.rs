//! `weigh`, held to `agent/planning/tests/weigh/`'s cases as `test_weigh.py` holds the Python act: whatever
//! `unweighed` lists weighed, and the diff the weighings. The estimate's two tests there lay a ground and derive
//! a want first, and come with `lay_ground` and `derive_wants`.

use std::path::PathBuf;

use orexis::snapshots;

use super::*;
use crate::unweighed::unweighed;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/weigh")
}

#[test]
fn weigh_writes_the_weighings_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = snapshots::stand_in(&case);
        let mut memo = Memo::default();
        let pairs = unweighed(&store, None, None, &mut memo).unwrap();
        assert!(!pairs.is_empty(), "{} has nothing left to weigh", case.display());
        for pair in pairs {
            weigh(
                &store,
                &iri(&pair, "for").unwrap(),
                &iri(&pair, "about").unwrap(),
                &mut memo,
            )
            .unwrap();
        }
        snapshots::held_to_diff(&case, &store, "weigh");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    snapshots::all_read(&cases(), 3);
}

#[test]
fn a_figure_is_read_as_sparql_reads_a_bare_number() {
    let datatype = |t: &str| match numeric(t).unwrap() {
        Term::Literal(l) => l.datatype().as_str().rsplit('#').next().unwrap().to_string(),
        other => panic!("{other}"),
    };
    assert_eq!(datatype("2"), "integer");
    assert_eq!(datatype("2.5"), "decimal");
    assert_eq!(datatype("2.0E0"), "double");
    assert!(numeric("two").is_err());
}
