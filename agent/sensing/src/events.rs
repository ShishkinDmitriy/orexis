//! WHAT SENSING SAYS HAPPENED, as `agent/sensing/events.py` declares it.
//!
//! AN OBSERVATION IS HISTORY: one point per observation written, measured under the observed property's own local
//! name, with field `value`, tagged `feature` and `sensor` — the SOSA roles, each the local name of its IRI — and
//! stamped with the reading's own `sosa:resultTime`; a defective sensor's point tagged `defective`; and the raw count
//! beside the reading, field `raw`, where the observation has one (#894). `orexis-dashboards` asks the Python
//! module's names, so a panel cannot query a name or a tag sensing does not write. AND IT IS A METRIC: how long after
//! the percept before it it came, beside the cadence the world states, tagged by the sensor. So is how many sensors
//! are silent now, and which sensors the agent doubts.

use std::collections::BTreeMap;

use oxigraph::model::{NamedNode, Term};
use oxsdatatypes::DateTime;

use orexis::events::{Event, Field, Mark, Number, Point};
use orexis::ontology::local_of;

use crate::ontology::{INTO, OBSERVATION_GRAPH, PERCEIVED, REVISES};

pub const FIELD: &str = "value";
pub const RAW: &str = "raw";

/// The measurement an observation of `property` is written under: the property's local name.
pub fn measurement_of(property: &str) -> String {
    local_of(property)
}

/// The tag a sensor or a subject goes by in the series: the local name of its IRI.
pub fn tag_of(iri: &str) -> String {
    local_of(iri)
}

/// An observation of `observed_property` reading `value` at `at`.
#[derive(Clone, Debug, PartialEq)]
pub struct Observed {
    pub observed_property: String,
    pub value: f64,
    pub at: DateTime,
    pub sensor: Option<String>,
    pub sensor_id: Option<String>,
    pub feature_id: Option<String>,
    pub interval_s: Option<f64>,
    pub cadence_s: Option<f64>,
    pub raw: Option<f64>,
    pub defective: bool,
}

impl Event for Observed {
    fn metric(&self) -> Option<&'static str> {
        Some("received")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("sensor", Mark::Tag(self.sensor.clone())),
            ("interval_s", Mark::Value(self.interval_s)),
            ("cadence_s", Mark::Value(self.cadence_s)),
        ]
    }

    fn point(&self) -> Option<Point> {
        let mut tags = BTreeMap::new();
        if self.defective {
            tags.insert("defective".to_string(), "true".to_string());
        }
        if let Some(feature) = self.feature_id.as_ref().filter(|f| !f.is_empty()) {
            tags.insert("feature".to_string(), feature.clone());
        }
        if let Some(sensor) = self.sensor_id.as_ref().filter(|s| !s.is_empty()) {
            tags.insert("sensor".to_string(), sensor.clone());
        }
        let mut fields = BTreeMap::from([(FIELD.to_string(), Field::Float(self.value))]);
        if let Some(raw) = self.raw {
            fields.insert(RAW.to_string(), Field::Float(raw));
        }
        Some(Point {
            measurement: measurement_of(&self.observed_property),
            tags,
            fields,
            time: Some(self.at),
        })
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// How many sensors are silent now.
#[derive(Clone, Debug, PartialEq)]
pub struct Silence {
    pub silent: Option<i64>,
}

impl Event for Silence {
    fn metric(&self) -> Option<&'static str> {
        Some("silence")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![("silent", Mark::Level(self.silent.map(Number::Int)))]
    }
}

/// A sensor the agent doubts, as it stands at the ask: silent, stuck, each one or nought.
#[derive(Clone, Debug, PartialEq)]
pub struct Doubted {
    pub sensor: String,
    pub silent: i64,
    pub stuck: i64,
}

impl Event for Doubted {
    fn metric(&self) -> Option<&'static str> {
        Some("doubted")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("sensor", Mark::Tag(Some(self.sensor.clone()))),
            ("silent", Mark::Level(Some(Number::Int(self.silent)))),
            ("stuck", Mark::Level(Some(Number::Int(self.stuck)))),
        ]
    }
}

#[cfg(test)]
mod tests {
    //! Held to what `agent/sensing/tests/test_events.py` asks.

    use super::*;
    use orexis::clock::instant;
    use orexis::events::counted;

    const CLIMATE: &str = "http://example.org/orexis/climate#";

    fn observed(raw: Option<f64>) -> Observed {
        Observed {
            observed_property: format!("{CLIMATE}SoilMoisture"),
            value: 0.2,
            at: instant("2026-01-01T12:00:00+00:00").unwrap(),
            sensor: Some("moisture_sensor_terrace".into()),
            sensor_id: Some("moisture_sensor_terrace".into()),
            feature_id: Some("terrace_bed".into()),
            interval_s: None,
            cadence_s: None,
            raw,
            defective: false,
        }
    }

    #[test]
    fn an_observation_is_measured_under_its_propertys_name_and_tagged_for_the_sosa_roles() {
        let point = observed(None).point().unwrap();
        assert_eq!(point.measurement, "SoilMoisture");
        assert_eq!(point.fields, BTreeMap::from([("value".to_string(), Field::Float(0.2))]));
        assert_eq!(
            point.tags,
            BTreeMap::from([
                ("feature".to_string(), "terrace_bed".to_string()),
                ("sensor".to_string(), "moisture_sensor_terrace".to_string())
            ])
        );
        assert_eq!(point.time, Some(instant("2026-01-01T12:00:00+00:00").unwrap()));
    }

    #[test]
    fn the_raw_count_rides_beside_the_reading_and_is_no_metric() {
        let said = observed(Some(1930.0));
        assert_eq!(said.point().unwrap().fields[RAW], Field::Float(1930.0));
        let names: Vec<&str> = said.marks().iter().map(|(n, _)| *n).collect();
        assert_eq!(names, ["sensor", "interval_s", "cadence_s"]);
    }

    #[test]
    fn a_doubted_sensor_is_a_level_per_sensor_and_no_count() {
        let d = Doubted {
            sensor: "probe".into(),
            silent: 0,
            stuck: 0,
        };
        assert!(!counted(&d.marks()));
        assert_eq!(d.metric(), Some("doubted"));
    }

    #[test]
    fn a_subject_and_a_sensor_stating_no_id_are_not_tagged() {
        let mut said = observed(None);
        said.sensor_id = None;
        said.feature_id = None;
        assert!(said.point().unwrap().tags.is_empty());
    }
}

/// Percepts written that nothing was concluded of yet: said for belief to revise, beneath its revising trigger by
/// sensing's ontology and in belief's words, the revisions to be sensing's own kind.
#[derive(Clone, Debug, PartialEq)]
pub struct Perceived {
    pub graphs: Vec<String>,
}

impl Event for Perceived {
    fn kind(&self) -> Option<&'static str> {
        Some(PERCEIVED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        let mut about: Vec<(&'static str, Term)> = self
            .graphs
            .iter()
            .filter_map(|g| NamedNode::new(g.as_str()).ok())
            .map(|g| (REVISES, Term::NamedNode(g)))
            .collect();
        about.push((INTO, Term::NamedNode(NamedNode::new_unchecked(OBSERVATION_GRAPH))));
        about
    }
}
