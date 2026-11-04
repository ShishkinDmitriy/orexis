//! BINDING A RULE TEXT: a text a package ships takes its parameters as `$name` tokens, bound by text as
//! `agent/store.py`'s `bind` binds them (#500) — a WHOLE token matched, each value rendered as the term it is, and
//! a text still carrying a token nobody bound REFUSED, `$this` aside, SHACL's own. The engine's own substitution
//! reaches only a variable the query projects at its top level, in Oxigraph as in pyoxigraph, so a token is what
//! reaches every scope.
//!
//! The text it makes is parsed once by the store, which keeps what it parsed by the text, so a text bound to the
//! same values again is not parsed again.

use std::collections::BTreeSet;
use std::sync::LazyLock;

use oxigraph::model::{Literal, NamedNode, Term};
use regex::Regex;

use crate::Error;

static TOKEN: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$([A-Za-z_][A-Za-z0-9_]*)\b").expect("a valid pattern"));

/// The one token that may survive binding: SHACL's `$this`, pre-bound by the judge, which a derivation writes
/// into a shape's select.
const SHACLS_OWN: &str = "this";

/// One value a token is bound to.
#[derive(Clone, Debug)]
pub enum Value {
    /// An IRI, written `<…>`.
    Iri(String),
    /// A term, written in its N-Triples form.
    Term(Term),
    /// Text spliced in verbatim — a `VALUES` block, a `USING` list — the one way to put unrendered text in.
    Raw(String),
    Bool(bool),
    Int(i64),
    Float(f64),
}

impl Value {
    pub fn iri(iri: impl Into<String>) -> Self {
        Value::Iri(iri.into())
    }

    pub fn raw(text: impl Into<String>) -> Self {
        Value::Raw(text.into())
    }

    /// The SPARQL text of the term the value is.
    pub fn render(&self) -> String {
        match self {
            Value::Iri(iri) => format!("<{iri}>"),
            Value::Term(term) => term.to_string(),
            Value::Raw(text) => text.clone(),
            Value::Bool(b) => b.to_string(),
            Value::Int(n) => n.to_string(),
            Value::Float(x) => format!("{x:?}"),
        }
    }
}

impl From<NamedNode> for Value {
    fn from(node: NamedNode) -> Self {
        Value::Iri(node.into_string())
    }
}

impl From<Literal> for Value {
    fn from(literal: Literal) -> Self {
        Value::Term(literal.into())
    }
}

impl From<Term> for Value {
    fn from(term: Term) -> Self {
        Value::Term(term)
    }
}

/// The text with every `$name` replaced by the term its value is: tokens the text does not carry are ignored, and
/// a token the caller did not bind refuses the text, `$this` aside.
pub fn bind(text: &str, values: &[(&str, Value)]) -> Result<String, Error> {
    let out = TOKEN.replace_all(text, |caps: &regex::Captures<'_>| {
        values
            .iter()
            .find(|(name, _)| *name == &caps[1])
            .map_or_else(|| caps[0].to_string(), |(_, value)| value.render())
    });
    let left: BTreeSet<String> = TOKEN
        .captures_iter(&out)
        .map(|caps| caps[1].to_string())
        .filter(|name| name != SHACLS_OWN)
        .collect();
    if left.is_empty() {
        Ok(out.into_owned())
    } else {
        Err(Error::Unbound(left.into_iter().collect()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_whole_token_is_bound_and_a_longer_one_is_not_touched() {
        let out = bind(
            "$this $thisOther $x",
            &[("x", Value::iri("http://a.example/x")), ("thisOther", Value::Int(2))],
        )
        .unwrap();
        assert_eq!(out, "$this 2 <http://a.example/x>");
    }

    #[test]
    fn a_token_nobody_bound_refuses_the_text_with_its_name() {
        let refused = bind("SELECT * WHERE { GRAPH $state { ?s ?p $o } }", &[]).unwrap_err();
        assert_eq!(refused.to_string(), "unbound in a rule text: $o, $state");
    }

    #[test]
    fn a_raw_value_is_spliced_as_written_and_a_term_is_rendered() {
        let at = Literal::new_typed_literal("2026-01-01T12:00:00Z", oxigraph::model::vocab::xsd::DATE_TIME);
        let out = bind("$v $at", &[("v", Value::raw("VALUES ?k { <a> }")), ("at", at.into())]).unwrap();
        assert_eq!(
            out,
            "VALUES ?k { <a> } \"2026-01-01T12:00:00Z\"^^<http://www.w3.org/2001/XMLSchema#dateTime>"
        );
    }
}
