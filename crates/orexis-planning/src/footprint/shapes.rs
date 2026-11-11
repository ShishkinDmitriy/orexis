//! WHAT A SHAPE READS AND WHAT IT NAMES, as `footprint.reads_of_shape` and `footprint.terms_of_shape` read them —
//! what places a want in a scope and what a world is hashed within. And what a SELECT reads, `reads_of_select`, off
//! the parsed algebra as every text here is.

use std::collections::BTreeSet;

use oxigraph::model::Term;
use spargebra::Query;

use orexis::store::Store;

use super::{parseable, reads_of};
use crate::ontology::ABOUT;
use crate::shapes::Shapes;
use crate::terms::{RDF_FIRST, SH};

fn sh(local: &str) -> String {
    format!("{SH}{local}")
}

/// The predicates a SELECT's, a CONSTRUCT's or an ASK's WHERE reads — `None`, anything, where it will not parse.
pub fn reads_of_select(store: &Store, text: &str) -> Option<BTreeSet<String>> {
    let pattern = match store.parse_query(&parseable(text)).ok()? {
        Query::Select { pattern, .. }
        | Query::Construct { pattern, .. }
        | Query::Ask { pattern, .. }
        | Query::Describe { pattern, .. } => pattern,
    };
    reads_of(&pattern)
}

fn iri(term: &Term) -> Option<String> {
    match term {
        Term::NamedNode(n) => Some(n.as_str().to_string()),
        _ => None,
    }
}

/// Every predicate a shape's paths and SPARQL constraints read, or `None` for anything.
pub fn reads_of_shape(store: &Store, shapes: &Shapes, shape: &Term) -> Option<BTreeSet<String>> {
    let mut out = BTreeSet::new();
    for prop in shapes.objects(shape, &sh("property")) {
        out.extend(path_iris(shapes, shapes.value(&prop, &sh("path")).as_ref())?);
        for (p, o) in shapes.predicate_objects(&prop) {
            if p.as_str() == sh("equals") {
                out.extend(iri(&o).or_else(|| Some(o.to_string())));
            }
            if p.as_str() == sh("qualifiedValueShape") {
                out.extend(reads_of_shape(store, shapes, &o)?);
            }
        }
    }
    for constraint in shapes.objects(shape, &sh("sparql")) {
        let text = shapes
            .value(&constraint, &sh("select"))
            .map(|t| lexical(&t))
            .unwrap_or_default();
        out.extend(reads_of_select(store, &text)?);
    }
    for text in shapes.objects(shape, &sh("select")) {
        out.extend(reads_of_select(store, &lexical(&text))?);
    }
    for negated in shapes.objects(shape, &sh("not")) {
        out.extend(reads_of_shape(store, shapes, &negated)?);
    }
    for p in ["targetSubjectsOf", "targetObjectsOf", "targetClass"] {
        out.extend(
            shapes
                .objects(shape, &sh(p))
                .iter()
                .map(|o| iri(o).unwrap_or_else(|| o.to_string())),
        );
    }
    Some(out)
}

fn lexical(term: &Term) -> String {
    match term {
        Term::Literal(l) => l.value().to_string(),
        other => other.to_string(),
    }
}

/// Every TERM a shape names as what it is about or holds a value to: `planning:about`, `sh:hasValue` and `sh:class`
/// on its blocks and inside their qualified value shapes, a class it targets, and an avoided state's own about.
pub fn terms_of_shape(shapes: &Shapes, shape: &Term) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for p in ["property", "sparql"] {
        for block in shapes.objects(shape, &sh(p)) {
            for q in [ABOUT.to_string(), sh("hasValue"), sh("class")] {
                out.extend(shapes.objects(&block, &q).iter().filter_map(iri));
            }
            for inner in shapes.objects(&block, &sh("qualifiedValueShape")) {
                out.extend(terms_of_shape(shapes, &inner));
            }
        }
    }
    for negated in shapes.objects(shape, &sh("not")) {
        out.extend(terms_of_shape(shapes, &negated));
    }
    out.extend(shapes.objects(shape, &sh("targetClass")).iter().filter_map(iri));
    out.extend(
        shapes
            .objects(shape, ABOUT)
            .iter()
            .filter_map(iri)
            .filter(|o| *o != sh("this")),
    );
    out
}

/// A SHACL path's IRIs — `None`, anything, where there is no path or one this does not read.
fn path_iris(shapes: &Shapes, node: Option<&Term>) -> Option<BTreeSet<String>> {
    let node = node?;
    if let Some(i) = iri(node) {
        return Some(BTreeSet::from([i]));
    }
    if shapes.has(node, RDF_FIRST) {
        let mut out = BTreeSet::new();
        for part in shapes.list(node) {
            out.extend(path_iris(shapes, Some(&part))?);
        }
        return Some(out);
    }
    for p in ["inversePath", "oneOrMorePath", "zeroOrMorePath", "zeroOrOnePath"] {
        if let Some(inner) = shapes.value(node, &sh(p)) {
            return path_iris(shapes, Some(&inner));
        }
    }
    if let Some(alternatives) = shapes.value(node, &sh("alternativePath")) {
        return path_iris(shapes, Some(&alternatives));
    }
    None
}
