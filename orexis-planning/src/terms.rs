//! THE WORDS OF OTHER VOCABULARIES the crate's code names, each once: RDF's from oxigraph's own, SHACL's and Dublin
//! Core's here, and a term of a name.

use oxigraph::model::vocab::rdf;
use oxigraph::model::{NamedNode, Term};

pub(crate) const RDF_TYPE: &str = rdf::TYPE.as_str();
pub(crate) const RDF_FIRST: &str = rdf::FIRST.as_str();
pub(crate) const SH: &str = "http://www.w3.org/ns/shacl#";
pub(crate) const TEMPORAL: &str = "http://purl.org/dc/terms/temporal";

/// The term an IRI names.
pub(crate) fn node(iri: &str) -> Term {
    NamedNode::new_unchecked(iri).into()
}
