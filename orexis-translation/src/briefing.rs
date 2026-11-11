//! THE BRIEFING, as `agent/translation/briefing.py` writes it: what the model is handed before a person's words — who
//! the agent is, what the chat lets it read and what it lets a person state (knowledge/domain/translation/briefing.md).
//! SMALL, AND SCOPED BY THE CHAT: it names the vocabularies the chat may read and the kinds of graph its queries read,
//! and the model loads and asks for what the question needs. The self graph is in it where the chat reads it, with what
//! each role the agent plays is. ONE BLOCK, CACHED. READ ON THE MIND'S THREAD, and handed to the model's as text.

use std::collections::BTreeSet;

use oxigraph::io::{RdfFormat, RdfSerializer};
use oxigraph::model::Triple;

use orexis::Error;
use orexis::ontology::{SELF_GRAPH, local_of};
use orexis::store::{Store, Within, value};

const ROLES_Q: &str = "
SELECT DISTINCT ?label ?comment WHERE {
  ?me a orexis:Self ; orexis:plays ?role . ?role a ?class .
  ?class rdfs:label ?label . OPTIONAL { ?class rdfs:comment ?comment } } ORDER BY ?label";

/// Who the agent is, what the chat lets the model read and what it lets a person state: one block, a name in the self
/// graph written with `prefixes`, as the chat's queries write theirs.
pub fn briefing(
    store: &Store,
    me: &str,
    reads: &[String],
    listing: &str,
    stating: &str,
    prefixes: &[(String, String)],
) -> Result<String, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let kinds: Vec<&str> = reads.iter().map(String::as_str).collect();
    let readable: BTreeSet<String> = if reads.is_empty() {
        BTreeSet::new()
    } else {
        store.graphs_of(&kinds, &Within::default())?.into_iter().collect()
    };
    let mut who = format!("YOU SPEAK FOR {}.", local_of(me));
    if !reads.is_empty() && selves.iter().all(|g| readable.contains(g)) {
        who += &format!(" Its self graph:\n\n{}", turtle(store, &selves, prefixes)?);
        let mut graphs: Vec<&str> = selves.iter().map(String::as_str).collect();
        graphs.extend(readable.iter().map(String::as_str));
        let roles = store.rows(ROLES_Q, &graphs)?;
        if !roles.is_empty() {
            let lines: Vec<String> = roles
                .iter()
                .map(|r| {
                    let comment = value(r, "comment").unwrap_or_default();
                    format!(
                        " - {}: {}",
                        value(r, "label").unwrap_or_default(),
                        comment.split_whitespace().collect::<Vec<_>>().join(" ")
                    )
                })
                .collect();
            who += &format!("\n\nTHE ROLES IT PLAYS:\n{}", lines.join("\n"));
        }
    }
    if reads.is_empty() {
        who += "\n\nThis chat lets you read nothing of the agent's store.";
    } else {
        who += &format!(
            "\n\nWHAT THIS CHAT LETS YOU READ: every graph of {}. Load a vocabulary to learn its terms before you query \
             them, and name the kinds of graph a query reads.\n{listing}",
            reads.iter().map(|k| local_of(k)).collect::<Vec<_>>().join(", ")
        );
    }
    Ok(who
        + &if stating.is_empty() {
            "\n\nA person states nothing here: what they write is a question, or nothing to keep.".to_string()
        } else {
            format!("\n\nWHAT A PERSON MAY STATE HERE, with the state tool. {stating}")
        })
}

/// The triples of `graphs` in Turtle, with `prefixes`.
pub fn turtle(store: &Store, graphs: &[String], prefixes: &[(String, String)]) -> Result<String, Error> {
    let mut triples: Vec<Triple> = Vec::new();
    for g in graphs {
        triples.extend(store.triples(g)?);
    }
    turtle_of(&triples, prefixes)
}

/// `triples` in Turtle, with `prefixes`.
pub fn turtle_of(triples: &[Triple], prefixes: &[(String, String)]) -> Result<String, Error> {
    let failed = |e: &dyn std::fmt::Display| Error::Evaluation(e.to_string());
    let mut serializer = RdfSerializer::from_format(RdfFormat::Turtle);
    for (name, iri) in prefixes {
        serializer = serializer.with_prefix(name, iri).map_err(|e| failed(&e))?;
    }
    let mut writer = serializer.for_writer(Vec::new());
    for t in triples {
        writer.serialize_triple(t).map_err(|e| failed(&e))?;
    }
    let bytes = writer.finish().map_err(|e| failed(&e))?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}
