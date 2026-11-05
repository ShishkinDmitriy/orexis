//! READING THE WANTS A STORE HOLDS — one function, its criteria arguments, as `agent/planning/find_wants.py` reads
//! them. A want IS its graph: whether it still holds and which family it is of are asked of the catalogue's row for
//! that graph, by the kinds the text names and the instant it stands at. It reads its own writes and writes
//! nothing; writing a want is the derivation's.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::isoformat;
use orexis::ontology::{DERIVED, RECORD};
use orexis::store::{Store, iri};

use crate::ontology::WANT;

/// HOW MANY A READ HANDS BACK unless the caller says otherwise: generous enough that no correct caller meets it,
/// small enough that meeting it is survivable.
pub const PAGE: usize = 100;

/// What a read narrows by, each said at the call site: one want by name, those derived from one desire, only the
/// family the derivation mints into, one holder's in a store holding a whole world — and the page.
#[derive(Clone, Debug)]
pub struct Finding<'a> {
    pub uri: Option<&'a str>,
    pub desire: Option<&'a str>,
    pub derived: bool,
    pub holder: Option<&'a str>,
    pub limit: usize,
    pub offset: usize,
}

impl Default for Finding<'_> {
    fn default() -> Self {
        Finding {
            uri: None,
            desire: None,
            derived: false,
            holder: None,
            limit: PAGE,
            offset: 0,
        }
    }
}

/// The wants `store` holds that stand at `at`, narrowed by `finding`, ordered by name. **A FULL PAGE IS SAID OUT
/// LOUD**: truncating in silence is the empty-result trap wearing a cap.
pub fn find_wants(store: &Store, at: DateTime, finding: &Finding<'_>) -> Result<Vec<String>, Error> {
    let mut patterns = "?w a planning:Want".to_string();
    if let Some(desire) = finding.desire {
        patterns.push_str(&format!(" ; prov:wasDerivedFrom <{desire}>"));
    }
    let r#where = match finding.uri {
        Some(uri) => format!("BIND(<{uri}> AS ?w) {patterns} ."),
        None => format!("{patterns} ."),
    };
    let now = isoformat(at);
    let came = if finding.derived {
        format!("    ?g orexis:arrivedBy <{DERIVED}> .\n")
    } else {
        String::new()
    };
    let mine = match finding.holder {
        Some(holder) => {
            format!("    OPTIONAL {{ ?g orexis:ownedBy ?owner }}\n    FILTER(!BOUND(?owner) || ?owner = <{holder}>)")
        }
        None => String::new(),
    };
    //  `?g a ?kind` IS THE JOIN, not only the filter: without it `?g` is bound solely inside the OPTIONAL, and binds
    //  to whichever graph has a period rather than to this want's.
    let text = format!(
        "
SELECT DISTINCT ?w WHERE {{
  GRAPH ?g {{ {where} }}
  GRAPH ?catalogue {{
    ?catalogue a orexis:CatalogueGraph .
    ?g a ?kind . VALUES ?kind {{ <{WANT}> <{RECORD}> }}
{came}{mine}
    OPTIONAL {{ ?g dcterms:temporal ?period . OPTIONAL {{ ?period orexis:start ?start }} OPTIONAL {{ ?period orexis:end ?end }} }} }}
  FILTER(!BOUND(?start) || ?start <= \"{now}\"^^xsd:dateTime)
  FILTER(!BOUND(?end) || ?end > \"{now}\"^^xsd:dateTime)
}} ORDER BY ?w LIMIT {} OFFSET {}",
        finding.limit, finding.offset,
        r#where = r#where,
    );
    let found: Vec<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "w")).collect();
    //  A PAGE OF ONE IS ALWAYS FULL, and one standing is the ordinary answer, not a leak.
    if finding.limit > 1 && found.len() == finding.limit {
        log::warn!(
            "wants: a full page of {} at offset {} — page or there is a leak",
            finding.limit,
            finding.offset
        );
    }
    Ok(found)
}

#[cfg(test)]
pub(crate) mod tests;
