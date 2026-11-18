//! THE CHATS AN AGENT IS IN, as `agent/translation/chat.py` reads them off the common beliefs: each its channel, the
//! people in it by the names they go by, the agents in it by the names they answer to, the kinds of graph its model
//! may query and the words a person may state in it — and whether words name an agent. An agent answers to its local
//! id, its IRI's local name and the name it goes by, `schema:name`, as a word of its own.

use std::collections::BTreeMap;

use orexis::Error;
use orexis::ontology::{BELIEF, SELF_GRAPH, local_of};
use orexis::store::{Store, Within, iri, value};

/// One chat: its IRI, its channel, its people (IRI, name), its agents (IRI, the names it answers to), the kinds of
/// graph its model may query and the words a person may state in it.
#[derive(Clone, Debug, PartialEq)]
pub struct Chat {
    pub iri: String,
    pub channel: String,
    pub people: Vec<(String, String)>,
    pub agents: Vec<(String, Vec<String>)>,
    pub reads: Vec<String>,
    pub allows: Vec<String>,
    /// How the agent writes on it: the chat's own style, or its channel's kind's (`translation:writtenAs`).
    pub style: Style,
}

/// HOW THE AGENT WRITES ON A CHAT: what the model is told of writing there, where a style says, and how many messages
/// one answer may be, one where it says none.
#[derive(Clone, Debug, PartialEq)]
pub struct Style {
    pub guidance: Option<String>,
    pub messages_at_most: usize,
}

impl Default for Style {
    fn default() -> Self {
        Style {
            guidance: None,
            messages_at_most: 1,
        }
    }
}

impl Chat {
    /// Who wrote: the sender the channel told, where they are in the chat, or the chat's one person.
    pub fn person(&self, sender: Option<&str>) -> Option<(String, String)> {
        match sender {
            Some(s) => self.people.iter().find(|(p, _)| p == s).cloned(),
            None if self.people.len() == 1 => self.people.first().cloned(),
            None => None,
        }
    }
}

/// Every chat the self is in, read off the common beliefs beside its self graph.
pub fn chats_of(store: &Store) -> Result<Vec<Chat>, Error> {
    const CHATS_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX schema: <https://schema.org/>
    PREFIX speech: <http://example.org/orexis/speech#>
    SELECT ?chat ?channel ?who ?kind ?name ?id WHERE {
      ?me a orexis:Self . ?chat a speech:Chat ; speech:participant ?me , ?who ; speech:channel ?channel .
      ?who a ?kind . VALUES ?kind { schema:Person orexis:Agent }
      OPTIONAL { ?who schema:name ?name } OPTIONAL { ?who orexis:localId ?id } } ORDER BY ?chat ?who";
    const READS_Q: &str = "PREFIX speech: <http://example.org/orexis/speech#>
        SELECT ?chat ?kind WHERE { ?chat a speech:Chat ; speech:reads ?kind } ORDER BY ?chat ?kind";
    const ALLOWS_Q: &str = "PREFIX speech: <http://example.org/orexis/speech#>
        SELECT ?chat ?word WHERE { ?chat a speech:Chat ; speech:allows ?word } ORDER BY ?chat ?word";
    /// THE STYLE EACH CHAT IS WRITTEN IN: its own, or else its channel's kind's.
    const STYLE_Q: &str = "PREFIX speech: <http://example.org/orexis/speech#>
        PREFIX translation: <http://example.org/orexis/translation#>
        SELECT ?chat ?guidance ?most WHERE {
          ?chat a speech:Chat ; speech:channel ?channel .
          OPTIONAL { ?chat translation:writtenAs ?own }
          OPTIONAL { ?channel a ?kind . ?kind translation:writtenAs ?given }
          BIND(COALESCE(?own, ?given) AS ?style)
          ?style translation:guidance ?guidance . OPTIONAL { ?style translation:messagesAtMost ?most } }
        ORDER BY ?chat";
    let mut graphs = store.graphs_of(&[BELIEF], &Within::common())?;
    graphs.extend(store.graphs_of(&[SELF_GRAPH], &Within::default())?);
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    type Found = (String, BTreeMap<String, String>, BTreeMap<String, Vec<String>>);
    let mut found: BTreeMap<String, Found> = BTreeMap::new();
    for r in store.rows(CHATS_Q, &graphs)? {
        let (Some(chat), Some(channel), Some(who), Some(kind)) =
            (iri(&r, "chat"), iri(&r, "channel"), iri(&r, "who"), iri(&r, "kind"))
        else {
            continue;
        };
        let entry = found
            .entry(chat)
            .or_insert_with(|| (channel, BTreeMap::new(), BTreeMap::new()));
        if kind.ends_with("Person") {
            entry
                .1
                .insert(who.clone(), value(&r, "name").unwrap_or_else(|| local_of(&who)));
        } else {
            let mut names: Vec<String> = Vec::new();
            for n in [value(&r, "id"), Some(local_of(&who)), value(&r, "name")]
                .into_iter()
                .flatten()
            {
                if !n.is_empty() && !names.contains(&n) {
                    names.push(n);
                }
            }
            entry.2.insert(who, names);
        }
    }
    let mut reads: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for r in store.rows(READS_Q, &graphs)? {
        if let (Some(c), Some(k)) = (iri(&r, "chat"), iri(&r, "kind")) {
            reads.entry(c).or_default().push(k);
        }
    }
    let mut allows: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for r in store.rows(ALLOWS_Q, &graphs)? {
        if let (Some(c), Some(w)) = (iri(&r, "chat"), iri(&r, "word")) {
            allows.entry(c).or_default().push(w);
        }
    }
    let mut styles: BTreeMap<String, Style> = BTreeMap::new();
    for r in store.rows(STYLE_Q, &graphs)? {
        if let (Some(c), Some(guidance)) = (iri(&r, "chat"), value(&r, "guidance")) {
            styles.entry(c).or_insert(Style {
                guidance: Some(guidance),
                messages_at_most: value(&r, "most").and_then(|m| m.parse().ok()).unwrap_or(1).max(1),
            });
        }
    }
    Ok(found
        .into_iter()
        .map(|(iri, (channel, people, agents))| {
            let mut r = reads.get(&iri).cloned().unwrap_or_default();
            r.sort();
            let mut a = allows.get(&iri).cloned().unwrap_or_default();
            a.sort();
            Chat {
                channel,
                people: people.into_iter().collect(),
                agents: agents.into_iter().collect(),
                reads: r,
                allows: a,
                style: styles.get(&iri).cloned().unwrap_or_default(),
                iri,
            }
        })
        .collect())
}

fn word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_' || c == '-'
}

/// Whether `text` names an agent by one of `names`, as a word of its own, in any case.
pub fn named(text: &str, names: &[String]) -> bool {
    let text: Vec<char> = text.to_lowercase().chars().collect();
    names.iter().any(|name| {
        let name: Vec<char> = name.to_lowercase().chars().collect();
        if name.is_empty() || name.len() > text.len() {
            return false;
        }
        (0..=text.len() - name.len()).any(|i| {
            text[i..i + name.len()] == name[..]
                && (i == 0 || !word_char(text[i - 1]))
                && text.get(i + name.len()).is_none_or(|c| !word_char(*c))
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_agent_is_named_by_a_word_of_its_own() {
        let seeker = ["seeker".to_string()];
        assert!(named("seeker, how is it going?", &seeker) && named("ask the Seeker", &seeker));
        assert!(!named("the seekers are out", &seeker) && !named("house-seeker", &seeker));
    }
}
