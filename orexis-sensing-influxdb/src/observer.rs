//! THE OBSERVER THE SELF PLAYS, as what archives its readings reads it: where the series store it names answers, and
//! how often.

use orexis::store::Store;
use orexis_sensing::ontology::OBSERVER;

/// THE OBSERVER THE SELF PLAYS, AS WHAT ARCHIVES ITS READINGS READS IT: a field for each thing `sensing:Observer`
/// may say of archiving. What sensing itself reads of the role, its sensors and its limits, is sensing's.
#[derive(Debug, Clone, PartialEq)]
pub struct Observer {
    /// Where the series store the role names answers (`sensing:archivedIn`), as the world's deployment states it:
    /// None where the role names none or the world says nothing of the one named.
    pub archived_in: Option<String>,
    /// How often readings are archived, in the agent's seconds (`sensing:archivedEveryS`), and the default
    /// sensing's ontology states where the role states none.
    pub archived_every_s: f64,
}

impl Observer {
    /// The observer the self plays, read off its self graph and the world's deployment graph by this package's own
    /// query. An agent plays one observer: two are refused, and where the self plays none nothing is said.
    pub fn new(store: &Store) -> Result<Self, orexis::Error> {
        /// THE OBSERVER THE SELF PLAYS, IN ONE QUERY: where the series store it names answers, and how often its
        /// readings are archived, the role's word or, where it says none, the default sensing's ontology states on the
        /// observer's shape (`sh:defaultValue`).
        const OBSERVER_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        PREFIX schema: <https://schema.org/>
        PREFIX sensing: <http://example.org/orexis/sensing#>
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT ?role ?kind ?archive (COALESCE(?everySaid, ?everyOwn) AS ?every) WHERE { \
        ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind . \
        OPTIONAL { ?role sensing:archivedEveryS ?everySaid FILTER(?everySaid > 0) } \
        OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path sensing:archivedEveryS ; sh:defaultValue ?everyOwn ] } \
        OPTIONAL { ?role sensing:archivedIn ?store . ?store schema:url ?archive } }";
        use orexis::ontology::{DEPLOYMENT, ONTOLOGY, SELF_GRAPH};
        use orexis::store::{Within, value};
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let mut rows = Vec::new();
        for row in store.rows(&OBSERVER_Q.replace("{ROLE}", OBSERVER), &known)? {
            let kind = value(&row, "kind").unwrap_or_default();
            if kind == OBSERVER || store.closed(&kind)?.iter().any(|class| class == OBSERVER) {
                rows.push(row);
            }
        }
        //  ONE IS PLAYED: what the role says is said to this package once for the agent, and two are never picked
        //  between, which onboarding refuses before a boot does.
        let played: std::collections::BTreeSet<String> = rows.iter().filter_map(|row| value(row, "role")).collect();
        if played.len() > 1 {
            return Err(orexis::Error::Document(format!(
                "the self plays {} observers, and an agent plays one",
                played.len()
            )));
        }
        if rows.is_empty() {
            return Err(orexis::Error::Document(format!(
                "the self plays no {}",
                orexis::ontology::local_of(OBSERVER)
            )));
        }
        let said = |what: &str| {
            rows.iter()
                .find_map(|row| value(row, what))
                .filter(|said| !said.is_empty())
        };
        //  A FIGURE NEITHER THE ROLE NOR THE SHAPE STATES is a package shipped broken.
        let figure = |what: &str| {
            said(what)
                .and_then(|figure| figure.parse::<f64>().ok())
                .ok_or_else(|| orexis::Error::Document(format!("sensing's ontology states no default for {what}")))
        };
        Ok(Observer {
            archived_in: said("archive"),
            archived_every_s: figure("every")?,
        })
    }
}
