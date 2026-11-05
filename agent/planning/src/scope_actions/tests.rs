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
    assert!(snapshots::cases_in(&cases()).len() >= 5);
    assert!(snapshots::orphans_in(&cases()).is_empty());
}
