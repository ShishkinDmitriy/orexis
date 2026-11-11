//! WHAT PARSING EVERY STATEMENT COSTS: each statement a pass ran parsed as pyoxigraph parses it, every time it is
//! run, against each distinct text parsed once, as the kernel's store parses.
//!
//! `cargo run --release --example parsing -- <statements.jsonl>`, a line `["query"|"update", text]` per statement
//! in the order the pass ran them.

use std::collections::HashSet;
use std::path::Path;
use std::time::Instant;

use orexis::namespaces::Namespaces;
use oxigraph::sparql::SparqlEvaluator;

fn main() {
    let path = std::env::args().nth(1).expect("a statements file");
    let statements: Vec<(bool, String)> = std::fs::read_to_string(path)
        .unwrap()
        .lines()
        .map(|line| {
            let (kind, text) = line.trim_start_matches('[').split_once(", ").unwrap();
            (kind == "\"query\"", unquote(text.trim_end_matches(']')))
        })
        .collect();
    let namespaces = Namespaces::of_tree(Path::new(orexis::boot::TREE)).unwrap();
    let evaluator = || {
        namespaces
            .iter()
            .fold(SparqlEvaluator::new(), |e, (l, i)| e.with_prefix(l, i).unwrap())
    };
    let parse = |query: bool, text: &str| {
        if query {
            drop(evaluator().parse_query(text).unwrap());
        } else {
            drop(evaluator().parse_update(text).unwrap());
        }
    };
    for round in 0..3 {
        let started = Instant::now();
        for (query, text) in &statements {
            parse(*query, text);
        }
        let every = started.elapsed();
        let started = Instant::now();
        let mut seen = HashSet::new();
        for (query, text) in &statements {
            if seen.insert(text.as_str()) {
                parse(*query, text);
            }
        }
        let once = started.elapsed();
        println!(
            "round {round}: {} statements parsed every time in {:.0} ms, {:.0} µs each; {} distinct texts parsed once in {:.0} ms",
            statements.len(),
            every.as_secs_f64() * 1000.0,
            every.as_secs_f64() * 1e6 / statements.len() as f64,
            seen.len(),
            once.as_secs_f64() * 1000.0
        );
    }
}

/// A JSON string's text, its escapes undone: enough for what Python's `json.dumps` writes.
fn unquote(quoted: &str) -> String {
    let inner = &quoted[1..quoted.len() - 1];
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match chars.next() {
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some('r') => out.push('\r'),
            Some('u') => {
                let hex: String = chars.by_ref().take(4).collect();
                out.push(char::from_u32(u32::from_str_radix(&hex, 16).unwrap()).unwrap_or('?'));
            }
            Some(other) => out.push(other),
            None => {}
        }
    }
    out
}
