//! A FORK: one graph's facts under another name, less what each retraction takes, plus what is added — how a
//! possible world is made of its parent and a ground of the one before it. What the parent says of itself is no
//! fact of it, and is not copied: the fork's metadata is said by whoever names it. A world is a value, so the parent is
//! never touched. The imaginarium is planning's, so the fork is too; the kernel keeps the store's primitives
//! (`Store::quads`, `Store::add`, `Store::update`) it is made of.

use oxigraph::model::{NamedNode, Quad, Triple};

use orexis::Error;
use orexis::metadata::stated_quads;
use orexis::store::Store;

/// `parent`'s facts under `name`, less what each retraction takes, plus `added` — THE ORDER IS THE WHOLE OF IT:
/// copy, every delete, then the adds, since a construct reuses the very node its retraction names. A copy is a fork
/// that retracts and adds nothing.
///
/// A RETRACTION THAT WILL NOT RUN RETRACTS NOTHING, LOUDLY, and the fork exists either way: it is a package's bug
/// and must not take an agent down. Each runs on its own, parsed once by its text.
pub(crate) fn fork(
    store: &Store,
    parent: &str,
    name: &str,
    added: &[Triple],
    retracts: &[String],
) -> Result<(), Error> {
    let into = NamedNode::new(name).map_err(|e| Error::Evaluation(e.to_string()))?;
    let copied: Vec<Quad> = stated_quads(store.quads(parent)?)
        .into_iter()
        .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone()))
        .collect();
    store.add(copied)?;
    for text in retracts {
        if let Err(refused) = store.update(text) {
            log::error!("a retraction would not run, so it retracts nothing: {refused}");
        }
    }
    store.add(added.iter().map(|t| t.clone().in_graph(into.clone())))
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;

    use oxigraph::model::{Literal, NamedNode, Triple};

    use super::*;

    fn facts(store: &Store, graph: &str) -> BTreeSet<String> {
        store
            .triples(graph)
            .unwrap()
            .into_iter()
            .map(|t| t.to_string())
            .collect()
    }

    fn parent() -> Store {
        let store = Store::new().unwrap();
        store
            .update("INSERT DATA { GRAPH <urn:test:parent> { <urn:test:s> <urn:test:level> 5 ; <urn:test:temp> 20 } }")
            .unwrap();
        store
    }

    const LEVEL_10: &str = "<urn:test:s> <urn:test:level> \"10\"^^<http://www.w3.org/2001/XMLSchema#integer>";
    const LEVEL_5: &str = "<urn:test:s> <urn:test:level> \"5\"^^<http://www.w3.org/2001/XMLSchema#integer>";
    const TEMP_20: &str = "<urn:test:s> <urn:test:temp> \"20\"^^<http://www.w3.org/2001/XMLSchema#integer>";

    fn level_10() -> Triple {
        Triple::new(
            NamedNode::new("urn:test:s").unwrap(),
            NamedNode::new("urn:test:level").unwrap(),
            Literal::new_typed_literal("10", oxigraph::model::vocab::xsd::INTEGER),
        )
    }

    #[test]
    fn a_fork_copies_then_deletes_then_adds_and_leaves_its_parent_as_it_was() {
        let store = parent();
        let retract = "PREFIX t: <urn:test:>
                   DELETE { GRAPH <urn:test:child> { t:s t:level ?l } } \
                   WHERE { GRAPH <urn:test:child> { t:s t:level ?l } }";
        fork(
            &store,
            "urn:test:parent",
            "urn:test:child",
            &[level_10()],
            &[retract.to_string()],
        )
        .unwrap();
        assert_eq!(
            facts(&store, "urn:test:child"),
            [LEVEL_10.to_string(), TEMP_20.to_string()].into()
        );
        assert_eq!(
            facts(&store, "urn:test:parent"),
            [LEVEL_5.to_string(), TEMP_20.to_string()].into(),
            "the parent is untouched — a world is a value"
        );
    }

    #[test]
    fn two_retractions_spelling_one_label_two_ways_both_run() {
        let store = parent();
        let one = "PREFIX : <urn:test:>
               DELETE { GRAPH <urn:test:child> { :s :level ?l } } \
               WHERE { GRAPH <urn:test:child> { :s :level ?l } }";
        let two = "PREFIX : <urn:other:>
               DELETE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } } \
               WHERE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } }";
        fork(
            &store,
            "urn:test:parent",
            "urn:test:child",
            &[],
            &[one.to_string(), two.to_string()],
        )
        .unwrap();
        assert!(facts(&store, "urn:test:child").is_empty(), "both deletions applied");
    }

    #[test]
    fn a_retraction_that_will_not_run_retracts_nothing_and_the_fork_still_exists() {
        let store = parent();
        fork(
            &store,
            "urn:test:parent",
            "urn:test:child",
            &[level_10()],
            &["DELETE nonsense".to_string()],
        )
        .unwrap();
        let child = facts(&store, "urn:test:child");
        assert!(child.contains(LEVEL_5), "the old reading stands");
        assert!(child.contains(LEVEL_10), "and the adds went in");
    }

    #[test]
    fn a_copy_is_a_fork_that_retracts_and_adds_nothing() {
        let store = parent();
        fork(&store, "urn:test:parent", "urn:test:child", &[], &[]).unwrap();
        assert_eq!(facts(&store, "urn:test:child"), facts(&store, "urn:test:parent"));
    }
}
