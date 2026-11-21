//! THE SHAPES AS ONE GRAPH, read as `agent/store.py`'s `rdflib_view` crosses them into rdflib: every graph listed,
//! in the order listed, each in the order the engine hands its quads back, merged with a triple said twice kept
//! where it was first said — and each subject's triples grouped by predicate in the order a predicate is first
//! met, as rdflib's in-memory graph iterates them. The shape compiler numbers a shape's constraints in this
//! order, and a violation row carries the number, so the order is part of what a case holds.

use std::collections::{HashMap, HashSet};

use oxigraph::model::{NamedNode, NamedOrBlankNode, Term};

use crate::terms::RDF_FIRST;
use orexis::Error;
use orexis::store::Store;

const RDF_REST: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest";
const RDF_NIL: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil";

/// One subject's triples: each predicate, first met first, with its objects in the order met.
type Described = Vec<(NamedNode, Vec<Term>)>;

#[derive(Clone, Debug, Default)]
pub struct Shapes {
    subjects: HashMap<Term, Described>,
    /// Where set, only these subjects are described: a concise bounded description.
    within: Option<HashSet<Term>>,
}

impl Shapes {
    /// The graphs `graphs` hold, merged as rdflib merges them.
    pub fn of(store: &Store, graphs: &[String]) -> Result<Self, Error> {
        let mut subjects: HashMap<Term, Described> = HashMap::new();
        for graph in graphs {
            for quad in store.quads(graph)? {
                let subject: Term = match quad.subject {
                    NamedOrBlankNode::NamedNode(n) => n.into(),
                    NamedOrBlankNode::BlankNode(b) => b.into(),
                };
                let described = subjects.entry(subject).or_default();
                match described.iter_mut().find(|(p, _)| *p == quad.predicate) {
                    Some((_, objects)) => {
                        if !objects.contains(&quad.object) {
                            objects.push(quad.object);
                        }
                    }
                    None => described.push((quad.predicate, vec![quad.object])),
                }
            }
        }
        Ok(Shapes { subjects, within: None })
    }

    /// The concise bounded description of `root`: its triples and, recursively, those of every blank node they
    /// reach — what rdflib's `Graph.cbd` keeps.
    pub fn cbd(&self, root: &Term) -> Shapes {
        let mut within = HashSet::new();
        let mut pending = vec![root.clone()];
        while let Some(node) = pending.pop() {
            if !within.insert(node.clone()) {
                continue;
            }
            for (_, objects) in self.described(&node) {
                for o in objects {
                    if matches!(o, Term::BlankNode(_)) && !within.contains(o) {
                        pending.push(o.clone());
                    }
                }
            }
        }
        Shapes {
            subjects: self.subjects.clone(),
            within: Some(within),
        }
    }

    fn described(&self, subject: &Term) -> &[(NamedNode, Vec<Term>)] {
        if self.within.as_ref().is_some_and(|w| !w.contains(subject)) {
            return &[];
        }
        self.subjects.get(subject).map(Vec::as_slice).unwrap_or(&[])
    }

    /// The first object `subject` has under `predicate`.
    pub fn value(&self, subject: &Term, predicate: &str) -> Option<Term> {
        self.objects(subject, predicate).into_iter().next()
    }

    /// Every object `subject` has under `predicate`, in order.
    pub fn objects(&self, subject: &Term, predicate: &str) -> Vec<Term> {
        self.described(subject)
            .iter()
            .find(|(p, _)| p.as_str() == predicate)
            .map(|(_, o)| o.clone())
            .unwrap_or_default()
    }

    /// Every predicate and object of `subject`, one per triple, in order.
    pub fn predicate_objects(&self, subject: &Term) -> Vec<(NamedNode, Term)> {
        self.described(subject)
            .iter()
            .flat_map(|(p, objects)| objects.iter().map(move |o| (p.clone(), o.clone())))
            .collect()
    }

    /// Whether the triple is held.
    pub fn holds(&self, subject: &Term, predicate: &str, object: &Term) -> bool {
        self.objects(subject, predicate).contains(object)
    }

    /// Whether `subject` says anything under `predicate`.
    pub fn has(&self, subject: &Term, predicate: &str) -> bool {
        !self.objects(subject, predicate).is_empty()
    }

    /// Every triple described, subject by subject: within a concise bounded description, its triples alone.
    pub fn triples(&self) -> Vec<(Term, NamedNode, Term)> {
        let mut out = Vec::new();
        for subject in self.subjects.keys() {
            for (p, o) in self.predicate_objects(subject) {
                out.push((subject.clone(), p, o));
            }
        }
        out
    }

    /// An RDF list's members, from its head, as rdflib's `Collection` walks it.
    pub fn list(&self, head: &Term) -> Vec<Term> {
        let mut out = Vec::new();
        let mut node = head.clone();
        let mut seen = HashSet::new();
        while !matches!(&node, Term::NamedNode(n) if n.as_str() == RDF_NIL) && seen.insert(node.clone()) {
            match self.value(&node, RDF_FIRST) {
                Some(first) => out.push(first),
                None => break,
            }
            match self.value(&node, RDF_REST) {
                Some(rest) => node = rest,
                None => break,
            }
        }
        out
    }
}
