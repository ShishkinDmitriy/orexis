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
pub(crate) mod tests {
    //! Reading the wants a store holds, held to what `test_find_wants.py` holds the Python read to. The rows are
    //! written as the derivation and a ledger write them, not through either writer, so a read is never tested against
    //! the writer that seeds it.

    use oxsdatatypes::DateTime;

    use orexis::clock::isoformat;
    use orexis::snapshots;

    use super::*;

    const DESIRE: &str = "urn:test:gardener.no_overdue_debts";
    const HOLDER: &str = "urn:test:gardener";

    pub(crate) fn at() -> DateTime {
        "2026-09-17T12:00:00+00:00".parse().unwrap()
    }

    pub(crate) fn store() -> Store {
        let store = Store::new(snapshots::namespaces()).expect("an empty store");
        store
        .update(
            "INSERT DATA {
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:ontology> a orexis:OntologyGraph }
  GRAPH <urn:test:ontology> { <urn:test:ObligationsGraph> rdfs:subClassOf orexis:RecordGraph } }",
        )
        .unwrap();
        store
    }

    pub(crate) fn graph_of(at: DateTime, until: Option<DateTime>) -> String {
        let stamp = |t: DateTime| isoformat(t).replace(':', "").replace('+', "p");
        format!(
            "urn:test:wants/{}--{}",
            stamp(at),
            until.map_or("open".to_string(), stamp)
        )
    }

    /// A want, written the way the derivation writes one: a graph of wants that arrived derived, its period the stretch.
    pub(crate) fn derived(store: &Store, uri: &str, from: DateTime, until: Option<DateTime>) {
        let graph = graph_of(from, until);
        let mut period = format!(" ; orexis:start \"{}\"^^xsd:dateTime", isoformat(from));
        if let Some(until) = until {
            period.push_str(&format!(" ; orexis:end \"{}\"^^xsd:dateTime", isoformat(until)));
        }
        store
            .update(&format!(
            "INSERT DATA {{
  GRAPH <{graph}> {{
    <{HOLDER}> planning:holds <{uri}> .
    <{uri}> a planning:Want ; prov:wasDerivedFrom <{DESIRE}> ; rdfs:label \"a want under test\" . }}
  GRAPH <urn:test:catalogue> {{
    <{graph}> a planning:WantGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived ; orexis:ownedBy <{HOLDER}> . }} }}"
        ))
            .unwrap();
        store
        .update(&format!(
            "INSERT {{ GRAPH <urn:test:catalogue> {{ <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH <urn:test:catalogue> {{ }}
         FILTER NOT EXISTS {{ GRAPH <urn:test:catalogue> {{ <{graph}> dcterms:temporal ?h }} }} }}"
        ))
        .unwrap();
    }

    /// A debt, written the way a ledger writes one: its own graph, a record of the case's own family.
    pub(crate) fn owed(store: &Store, uri: &str) {
        let graph = format!(
            "http://example.org/orexis/market#obligations/gardener/{}",
            uri.rsplit(':').next().unwrap()
        );
        store
            .update(&format!(
                "INSERT DATA {{
  GRAPH <{graph}> {{ <{uri}> a planning:Want ; prov:wasDerivedFrom <{DESIRE}> ; rdfs:label \"a debt under test\" . }}
  GRAPH <urn:test:catalogue> {{ <{graph}> a <urn:test:ObligationsGraph> , orexis:RecordGraph . }} }}"
            ))
            .unwrap();
    }

    fn find(store: &Store, finding: Finding<'_>) -> Vec<String> {
        find_wants(store, at(), &finding).unwrap()
    }

    #[test]
    fn a_saved_want_is_found_and_a_forgotten_one_is_not() {
        let store = store();
        assert!(find(&store, Finding::default()).is_empty(), "nothing has been derived");
        derived(&store, "urn:test:want", at(), None);
        assert_eq!(find(&store, Finding::default()), ["urn:test:want"]);
        store.forget_graph(&graph_of(at(), None), None).unwrap();
        assert!(
            find(&store, Finding::default()).is_empty(),
            "and its graph went with it"
        );
    }

    #[test]
    fn a_want_is_found_by_the_desire_it_was_derived_from() {
        let store = store();
        derived(&store, "urn:test:want", at(), None);
        let by = |desire: &'static str, derived: bool| Finding {
            desire: Some(desire),
            derived,
            ..Finding::default()
        };
        assert_eq!(find(&store, by(DESIRE, false)), ["urn:test:want"]);
        assert_eq!(find(&store, by(DESIRE, true)), ["urn:test:want"]);
        assert!(find(&store, by("urn:test:nobody", false)).is_empty());
        assert!(find(&store, by("urn:test:nobody", true)).is_empty());
        let named = |uri: &'static str| Finding {
            uri: Some(uri),
            ..Finding::default()
        };
        assert_eq!(find(&store, named("urn:test:want")), ["urn:test:want"]);
        assert!(find(&store, named("urn:test:missing")).is_empty());
    }

    #[test]
    fn a_want_whose_period_has_closed_is_not_handed_out() {
        let store = store();
        derived(
            &store,
            "urn:test:stale",
            "2020-01-01T00:00:00+00:00".parse().unwrap(),
            Some("2020-01-01T00:10:00+00:00".parse().unwrap()),
        );
        assert!(
            find(&store, Finding::default()).is_empty(),
            "its window closed years ago"
        );
        assert!(
            find(
                &store,
                Finding {
                    desire: Some(DESIRE),
                    derived: true,
                    ..Finding::default()
                }
            )
            .is_empty()
        );
    }

    #[test]
    fn a_debt_is_a_want_but_not_one_a_search_is_handed() {
        let store = store();
        derived(&store, "urn:test:derived", at(), None);
        owed(&store, "urn:test:owed");
        assert_eq!(find(&store, Finding::default()), ["urn:test:derived", "urn:test:owed"]);
        assert_eq!(
            find(
                &store,
                Finding {
                    desire: Some(DESIRE),
                    derived: true,
                    ..Finding::default()
                }
            ),
            ["urn:test:derived"],
            "a search is handed what a desire derived, and never a debt"
        );
        assert_eq!(
            find(
                &store,
                Finding {
                    desire: Some(DESIRE),
                    ..Finding::default()
                }
            ),
            ["urn:test:derived", "urn:test:owed"],
            "though both name it here"
        );
    }

    #[test]
    fn a_read_is_bounded_and_a_page_is_stable() {
        let store = store();
        for n in 0..5 {
            derived(&store, &format!("urn:test:want{n}"), at(), None);
        }
        let page = |limit, offset| Finding {
            limit,
            offset,
            ..Finding::default()
        };
        assert_eq!(find(&store, page(2, 0)).len(), 2, "capped");
        let (first, second) = (find(&store, page(3, 0)), find(&store, page(3, 3)));
        let all: Vec<String> = (0..5).map(|n| format!("urn:test:want{n}")).collect();
        assert_eq!(
            [first.clone(), second].concat(),
            all,
            "a page walks rather than resamples"
        );
        assert_eq!(find(&store, page(3, 0)), first, "and answers the same way twice");
    }

    #[test]
    fn a_holder_named_keeps_its_own_and_what_no_one_owns() {
        let store = store();
        derived(&store, "urn:test:mine", at(), None);
        owed(&store, "urn:test:anyones");
        let of = |holder: &'static str| Finding {
            holder: Some(holder),
            ..Finding::default()
        };
        assert_eq!(find(&store, of(HOLDER)), ["urn:test:anyones", "urn:test:mine"]);
        assert_eq!(find(&store, of("urn:test:someone_else")), ["urn:test:anyones"]);
    }
}
