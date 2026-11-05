//! REFINING A STEP: the want that keeps a step one level down, as `agent/planning/refine.py` mints it. THE GOAL IS
//! THE WORLD THE STEP LANDS IN, NOT ITS DIFF: every fact of a predicate a bridge concludes that the present holds,
//! less what the step retracts, plus what it adds — each regressed through the bridges, all to hold at once.

use std::collections::{BTreeSet, HashSet};
use std::sync::LazyLock;

use oxigraph::model::Triple;
use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::clock::isoformat;
use orexis::ontology::{BELIEF, GRAPH_PREFIX, RECORDED};
use orexis::store::{Store, Within};

use crate::admit::local_of;
use crate::bridge::{binding, expand, heads, literal, predicted, repr};
use crate::ontology::WANT;

static VARIABLE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\?(\w+)\b").expect("a valid pattern"));

/// Mint the want that keeps `step` below in the agent `me`'s own want graph; the want. None where no rule the store
/// holds concludes any fact the step adds.
pub fn refine(store: &Store, me: &str, step: &str, now: DateTime) -> Result<Option<String>, Error> {
    let bridges = heads(store)?;
    let concluded: BTreeSet<String> = bridges.iter().filter_map(|b| expand(&b.head.1, &b.names)).collect();
    let (adds, retracts) = predicted(store, step)?;
    if !adds.iter().any(|f| concluded.contains(f.predicate.as_str())) {
        return Ok(None);
    }
    let beliefs = store.graphs_of(&[BELIEF], &Within::default())?;
    let sources: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let mut graphs = beliefs.clone();
    graphs.extend(store.revisions_of(&sources, BELIEF)?);
    let mut present: HashSet<Triple> = HashSet::new();
    for g in &graphs {
        for t in store.triples(g)? {
            if concluded.contains(t.predicate.as_str()) {
                present.insert(t);
            }
        }
    }
    for t in &retracts {
        present.remove(t);
    }
    present.extend(
        adds.iter()
            .filter(|f| concluded.contains(f.predicate.as_str()))
            .cloned(),
    );
    let mut target: Vec<Triple> = present.into_iter().collect();
    target.sort_by_cached_key(repr);
    let (mut prefixes, mut conjuncts) = (BTreeSet::new(), Vec::new());
    for fact in &target {
        let mut branches = Vec::new();
        for bridge in &bridges {
            let Some(bound) = binding(&bridge.head, fact, &bridge.names) else {
                continue;
            };
            let branch = VARIABLE.replace_all(&bridge.r#where, |caps: &regex::Captures<'_>| {
                bound.get(&caps[1]).cloned().unwrap_or_else(|| caps[0].to_string())
            });
            branches.push(branch.into_owned());
            prefixes.extend(bridge.declared.iter().cloned());
        }
        if !branches.is_empty() {
            conjuncts.push(
                branches
                    .iter()
                    .map(|b| format!("{{ {b} }}"))
                    .collect::<Vec<_>>()
                    .join(" UNION "),
            );
        }
    }
    if conjuncts.is_empty() {
        return Ok(None);
    }
    let goal = conjuncts
        .iter()
        .map(|c| format!("{{ FILTER NOT EXISTS {{ {c} }} }}"))
        .collect::<Vec<_>>()
        .join(" UNION ");
    let head = if prefixes.is_empty() {
        String::new()
    } else {
        format!("{}\n", prefixes.into_iter().collect::<Vec<_>>().join("\n"))
    };
    let select = format!("{head}SELECT $this WHERE {{ {goal} }}");
    let want = format!("{step}.below");
    let graph = format!("{GRAPH_PREFIX}want/refined/{}", local_of(step));
    let shape = format!("{want}.met");
    let name = local_of(step);
    store.update(&format!(
        "INSERT DATA {{ GRAPH <{graph}> {{
  <{me}> planning:holds <{want}> .
  <{step}> execution:keptBy <{want}> .
  <{want}> a planning:Want ; planning:metWhen <{shape}> ;
      rdfs:label \"what {name} comes to, one level down\" ;
      prov:generatedAtTime \"{}\"^^xsd:dateTime .
  <{shape}> a sh:NodeShape ; sh:targetNode <{me}> ;
      sh:sparql [ a sh:SPARQLConstraint ; sh:message \"{name} is not kept below yet\" ;
                  sh:select {} ] . }} }}",
        isoformat(now),
        literal(&select)
    ))?;
    store.classify(&graph, WANT, RECORDED, Some(me), None, None)?;
    log::info!(
        "refining {name} into {} — {} fact(s) of the world it lands in, held below",
        local_of(&want),
        conjuncts.len()
    );
    Ok(Some(want))
}

#[cfg(test)]
pub(crate) mod tests;
