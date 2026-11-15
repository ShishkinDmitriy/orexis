//! WHAT A PACKAGE'S ONTOLOGY STATES WHERE NOTHING ELSE DOES. A figure a role may state - a budget, a patience, a
//! limit or an interval - has a default, and the default is a statement too: the shape of
//! the role in the package's ontology carries it as `sh:defaultValue` on the property. So a figure
//! lives in a document and in no code, and a package reads its default off its own ontology, the text it brings
//! compiled into the binary (`task::documents!`), which is there whether or not a store holds it. What reads the
//! role is the package's own query; this only says which of its rows' answers holds, or the default.

use std::collections::BTreeMap;

use oxigraph::io::{RdfFormat, RdfParser};
use oxigraph::model::{NamedOrBlankNode, Quad, Term};

use crate::Error;

const SH: &str = "http://www.w3.org/ns/shacl#";

/// Every default one ontology states, by the property it is the default of.
pub struct Defaults {
    whose: &'static str,
    stated: Result<BTreeMap<String, Vec<String>>, String>,
}

impl Defaults {
    /// The defaults `ontology` states, the Turtle of the package `whose` names: each `sh:defaultValue` of a
    /// property shape, under the shape's `sh:path`.
    pub fn of(whose: &'static str, ontology: &str) -> Self {
        Defaults {
            whose,
            stated: stated(ontology),
        }
    }

    /// The default of `property`, as it is written: refused where the ontology states none or several that
    /// differ, since a figure nothing states is a package shipped broken and two are never picked between.
    pub fn word(&self, property: &str) -> Result<String, Error> {
        let stated = self
            .stated
            .as_ref()
            .map_err(|e| Error::Document(format!("{}'s ontology: {e}", self.whose)))?;
        let mut said = stated.get(property).cloned().unwrap_or_default();
        said.sort();
        said.dedup();
        match said.as_slice() {
            [one] => Ok(one.clone()),
            _ => Err(Error::Document(format!(
                "{}'s ontology states {} defaults for {property}, and one is the default",
                self.whose,
                said.len()
            ))),
        }
    }

    /// WHAT THE ROWS SAY OF A FIGURE, OR ITS DEFAULT: `variable` as a package's own query of its role bound it, where
    /// it is said once and is a number, and the default of `property` otherwise. Two answers are never picked
    /// between: several, or one that is no number, is the default, said in the log.
    pub fn said(&self, rows: &[crate::store::Row], variable: &str, property: &str) -> Result<f64, Error> {
        let mut said: Vec<String> = rows
            .iter()
            .filter_map(|row| crate::store::value(row, variable))
            .collect();
        said.sort();
        said.dedup();
        if let [one] = said.as_slice()
            && let Ok(figure) = one.parse::<f64>()
        {
            return Ok(figure);
        }
        let default = self.figure(property)?;
        if !said.is_empty() {
            log::warn!(
                "{}'s role says {} for {}: the default, {default}, holds",
                self.whose,
                said.join(", "),
                crate::ontology::local_of(property)
            );
        }
        Ok(default)
    }

    /// The default of `property`, a number.
    pub fn figure(&self, property: &str) -> Result<f64, Error> {
        let word = self.word(property)?;
        word.parse().map_err(|_| {
            Error::Document(format!(
                "{}'s ontology states {word:?} as the default of {property}, which is no number",
                self.whose
            ))
        })
    }
}

fn stated(ontology: &str) -> Result<BTreeMap<String, Vec<String>>, String> {
    let quads: Vec<Quad> = RdfParser::from_format(RdfFormat::Turtle)
        .with_base_iri("file:///ontology.ttl")
        .map_err(|e| e.to_string())?
        .for_slice(ontology.as_bytes())
        .collect::<Result<_, _>>()
        .map_err(|e| e.to_string())?;
    let objects = |s: &NamedOrBlankNode, p: &str| -> Vec<Term> {
        quads
            .iter()
            .filter(|q| &q.subject == s && q.predicate.as_str() == p)
            .map(|q| q.object.clone())
            .collect()
    };
    let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for quad in quads.iter().filter(|q| q.predicate.as_str() == format!("{SH}path")) {
        let Term::NamedNode(path) = &quad.object else { continue };
        for default in objects(&quad.subject, &format!("{SH}defaultValue")) {
            if let Term::Literal(l) = default {
                out.entry(path.as_str().to_string())
                    .or_default()
                    .push(l.value().to_string());
            }
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_default_is_read_off_the_shape_that_states_it_and_refused_where_none_or_two_are_stated() {
        let defaults = Defaults::of(
            "a package",
            "@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix : <http://example.org/p#> . \
             [] a sh:NodeShape ; sh:targetClass :Role ; \
                sh:property [ sh:path :every ; sh:defaultValue 10 ] , [ sh:path :from ; sh:defaultValue \"WARNING\" ] , \
                            [ sh:path :twice ; sh:defaultValue 1 ] , [ sh:path :twice ; sh:defaultValue 2 ] .",
        );
        assert_eq!(defaults.figure("http://example.org/p#every").unwrap(), 10.0);
        assert_eq!(defaults.word("http://example.org/p#from").unwrap(), "WARNING");
        assert!(defaults.figure("http://example.org/p#from").is_err());
        assert!(defaults.word("http://example.org/p#twice").is_err());
        assert!(defaults.word("http://example.org/p#nothing").is_err());
        assert!(Defaults::of("a package", "not turtle").word("x").is_err());
    }
}
