//! THE BENCH, in Rust: the Planner on the problems of `bench/`, held to their plans as `test_bench.py` holds the
//! Python one — three moves for two disks, seven for three, fifteen for four, thirty-one for five, eight steps for
//! the parcel — and timed as the median of five passes, a fresh store each, with the statements of one pass beside
//! it. No time is asserted: the Pi drifts about twofold between invocations.
//!
//! It asks the crate's public names alone, `Planner` and `ontology`, as any user of the package would. A debug
//! build is held to the plans and times nothing, since a debug figure measures the compiler's checks:
//!
//! ```text
//! cargo test --release -p orexis-planning --test bench -- --nocapture                         # print the figures
//! OREXIS_BENCH_RECORD=1 cargo test --release -p orexis-planning --test bench -- --nocapture --test-threads 1
//! ```
//!
//! The second appends one row per case to `bench/results.tsv`, the case named `rust:<case>` so the two agents'
//! series stand apart in one ledger (knowledge/runbooks/measure-the-search.md).

use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;

use orexis::bind::{Value, bind};
use orexis::snapshots;
use orexis::store::{Store, Within, iri, value};
use orexis_planning::Planner;
use orexis_planning::ontology::PLAN_GRAPH;

const RUNS: usize = 5;
const COLUMNS: &[&str] = &[
    "date",
    "commit",
    "machine",
    "case",
    "budget",
    "runs",
    "median_ms",
    "min_ms",
    "queries",
    "updates",
    "steps",
];

const PLAN_Q: &str = "
SELECT ?outcome ?costs (COUNT(?step) AS ?steps) WHERE {
  GRAPH $plan { $plan planning:outcome ?outcome . OPTIONAL { $plan planning:spent ?costs }
                OPTIONAL { ?step a execution:Step ; execution:partOf $plan } } }
GROUP BY ?outcome ?costs";

fn bench() -> PathBuf {
    snapshots::tree().join("planning/tests/bench")
}

/// What one pass found: its outcome, what its plan costs, and its steps.
struct Found {
    outcome: String,
    costs: f64,
    steps: usize,
}

/// One pass over the case from a fresh store: the milliseconds it took, the queries and updates it ran, and its plan.
fn pass(case: &Path, budget: usize) -> (f64, (usize, usize), Found) {
    let beliefs = snapshots::stand_in(case);
    let before = beliefs.ran();
    let started = Instant::now();
    let mut planner = Planner::new(&beliefs, snapshots::AGENT, Some(budget)).expect("a planner");
    planner.plan(snapshots::now()).expect("a pass");
    let took = started.elapsed().as_secs_f64() * 1000.0;
    let mut ran = beliefs.ran();
    ran = (ran.0 - before.0, ran.1 - before.1);
    let mut imagined = planner.imaginaria.values();
    let (Some(im), None) = (imagined.next(), imagined.next()) else {
        panic!("{}: one scope", case.display())
    };
    ran = (ran.0 + im.ran().0, ran.1 + im.ran().1);
    (took, ran, plan(im, case))
}

fn plan(im: &Store, case: &Path) -> Found {
    let graphs = im.graphs_of(&[PLAN_GRAPH], &Within::default()).expect("graphs by kind");
    let [graph] = graphs.as_slice() else {
        panic!("{}: one plan, found {graphs:?}", case.display())
    };
    let text = bind(PLAN_Q, &[("plan", Value::iri(graph))]).expect("a bound text");
    let rows = im.rows(&text, &[]).expect("the plan's row");
    let [row] = rows.as_slice() else {
        panic!("{}: one row", case.display())
    };
    Found {
        outcome: iri(row, "outcome").expect("an outcome"),
        costs: value(row, "costs").map_or(f64::NAN, |c| c.parse().expect("a number")),
        steps: value(row, "steps").expect("a count").parse().expect("a count"),
    }
}

fn median(mut times: Vec<f64>) -> f64 {
    times.sort_by(f64::total_cmp);
    times[times.len() / 2]
}

fn out_of(program: &str, args: &[&str]) -> Option<String> {
    let out = Command::new(program).args(args).current_dir(bench()).output().ok()?;
    out.status
        .success()
        .then(|| String::from_utf8_lossy(&out.stdout).trim().to_string())
}

/// The commit the numbers are about, `-dirty` where the tree is not that commit.
fn commit() -> String {
    let Some(short) = out_of("git", &["rev-parse", "--short", "HEAD"]) else {
        return "unknown".into();
    };
    let dirty = out_of("git", &["status", "--porcelain", "--untracked-files=no"]).is_some_and(|s| !s.is_empty());
    if dirty { format!("{short}-dirty") } else { short }
}

/// Append one row to the ledger, under the header the Python bench writes.
fn record(row: &[String]) {
    let ledger = bench().join("results.tsv");
    let header = std::fs::read_to_string(&ledger)
        .ok()
        .and_then(|t| t.lines().next().map(str::to_string));
    if let Some(header) = &header {
        assert_eq!(
            header.split('\t').collect::<Vec<_>>(),
            COLUMNS,
            "the ledger's header is the bench's"
        );
    }
    let mut out = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&ledger)
        .expect("the ledger");
    if header.is_none() {
        writeln!(out, "{}", COLUMNS.join("\t")).expect("a header");
    }
    writeln!(out, "{}", row.join("\t")).expect("a row");
}

fn solved(case: &str, moves: usize, budget: usize) {
    let path = bench().join(format!("{case}.trig"));
    //  THE STATEMENTS OF ONE PASS, and its plan, off a run of its own: the count does not drift.
    let (_, (queries, updates), found) = pass(&path, budget);
    assert!(found.outcome.ends_with("#Satisfied"), "{case}: {}", found.outcome);
    assert_eq!((found.steps, found.costs), (moves, moves as f64), "{case}");
    if cfg!(debug_assertions) {
        return;
    }
    let times: Vec<f64> = (0..RUNS).map(|_| pass(&path, budget).0).collect();
    let (mid, least) = (
        median(times.clone()),
        times.iter().copied().fold(f64::INFINITY, f64::min),
    );
    println!(
        "{case}: median {mid:.0} ms of {RUNS} (min {least:.0}), {queries} queries, {updates} updates, Satisfied in \
         {moves} steps"
    );
    if std::env::var_os("OREXIS_BENCH_RECORD").is_some() {
        let row = [
            out_of("date", &["+%F"]).unwrap_or_default(),
            commit(),
            out_of("uname", &["-n"]).unwrap_or_default(),
            format!("rust:{case}"),
            budget.to_string(),
            RUNS.to_string(),
            format!("{mid:.0}"),
            format!("{least:.0}"),
            queries.to_string(),
            updates.to_string(),
            found.steps.to_string(),
        ];
        record(&row);
    }
}

#[test]
fn two_disks_in_three_moves() {
    solved("two_disk_hanoi", 3, 32);
}

#[test]
fn three_disks_in_seven_moves() {
    solved("three_disk_hanoi", 7, 128);
}

#[test]
fn four_disks_in_fifteen_moves() {
    solved("four_disk_hanoi", 15, 1024);
}

#[test]
fn five_disks_in_thirty_one_moves() {
    solved("five_disk_hanoi", 31, 4096);
}

#[test]
fn the_parcel_round_the_corner_in_eight_steps() {
    solved("courier_corner", 8, 128);
}
