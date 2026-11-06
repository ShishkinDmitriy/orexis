//! THE CLOCK: one timeline, and it may run fast (the-agent-keeps-one-timeline-and-its-clock-may-run-fast), as
//! `agent/clock.py` keeps it — and HANDED IN, never read from a global, so a walk or a bench runs in the world's
//! time and a container in the wall's (the-agent-moves-to-rust-one-package-at-a-time).
//!
//! The pace is world seconds per real second, a deployment fact (`OREXIS_TIME_PACE`), and the one conversion is
//! at a sleep (`real_delay`). The epoch (`OREXIS_TIME_EPOCH`) fixes the timeline's origin, so a restarted agent's
//! `now` lands where the world's clock stands; a paced clock with no epoch starts at the process's own start.

use std::str::FromStr;
use std::sync::Mutex;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use oxsdatatypes::{DateTime, DayTimeDuration};

use crate::Error;

/// The agent's instant, wherever it is read from.
pub trait Clock: Send + Sync {
    fn now(&self) -> DateTime;

    /// How long to actually sleep for `seconds` of the agent's time.
    fn real_delay(&self, seconds: f64) -> Duration {
        Duration::from_secs_f64(seconds.max(0.0))
    }
}

/// The wall's clock at a pace, from an epoch: what a deployed agent reads.
pub struct Paced {
    pace: f64,
    epoch: DateTime,
    epoch_real: f64,
}

impl Paced {
    /// The wall's own time.
    pub fn wall() -> Self {
        Paced {
            pace: 1.0,
            epoch: DateTime::now(),
            epoch_real: real_seconds(),
        }
    }

    /// At `pace`, from `epoch` where one is stated and from now where none is.
    pub fn new(pace: f64, epoch: Option<DateTime>) -> Result<Self, Error> {
        if pace <= 0.0 || !pace.is_finite() {
            return Err(Error::Evaluation(format!("a clock's pace is positive, not {pace}")));
        }
        Ok(match epoch {
            Some(epoch) => {
                let real = seconds_since_unix(epoch)?;
                Paced {
                    pace,
                    epoch,
                    epoch_real: real,
                }
            }
            None => Paced {
                pace,
                epoch: DateTime::now(),
                epoch_real: real_seconds(),
            },
        })
    }

    /// As the environment says: `OREXIS_TIME_PACE` and `OREXIS_TIME_EPOCH`, an epoch with no zone read as UTC.
    pub fn from_env() -> Result<Self, Error> {
        let pace = match std::env::var("OREXIS_TIME_PACE") {
            Ok(text) if !text.is_empty() => text
                .parse()
                .map_err(|_| Error::Evaluation(format!("OREXIS_TIME_PACE is no number: {text}")))?,
            _ => 1.0,
        };
        let epoch = match std::env::var("OREXIS_TIME_EPOCH") {
            Ok(text) if !text.is_empty() => Some(instant(&text)?),
            _ => None,
        };
        Paced::new(pace, epoch)
    }
}

impl Clock for Paced {
    fn now(&self) -> DateTime {
        if self.pace == 1.0 {
            return DateTime::now();
        }
        let past = (real_seconds() - self.epoch_real) * self.pace;
        self.epoch
            .checked_add_day_time_duration(seconds(past))
            .unwrap_or(self.epoch)
    }

    fn real_delay(&self, seconds: f64) -> Duration {
        Duration::from_secs_f64(seconds.max(0.0) / self.pace)
    }
}

/// A clock a test moves by hand: the instant it is set to, until it is set again.
pub struct Manual(Mutex<DateTime>);

impl Manual {
    pub fn at(at: DateTime) -> Self {
        Manual(Mutex::new(at))
    }

    pub fn set(&self, at: DateTime) {
        *self.0.lock().expect("a clock nobody poisoned") = at;
    }

    pub fn advance(&self, by: f64) {
        let mut at = self.0.lock().expect("a clock nobody poisoned");
        *at = at.checked_add_day_time_duration(seconds(by)).unwrap_or(*at);
    }
}

impl Clock for Manual {
    fn now(&self) -> DateTime {
        *self.0.lock().expect("a clock nobody poisoned")
    }
}

/// An instant from its text, a zone of UTC where it states none.
pub fn instant(text: &str) -> Result<DateTime, Error> {
    let at = DateTime::from_str(text).map_err(|e| Error::Evaluation(format!("no instant: {text}: {e}")))?;
    match at.timezone_offset() {
        Some(_) => Ok(at),
        None => {
            DateTime::from_str(&format!("{text}Z")).map_err(|e| Error::Evaluation(format!("no instant: {text}: {e}")))
        }
    }
}

/// An instant as Python's `datetime.isoformat` spells it — `2026-01-01T12:00:00+00:00`, microseconds only where
/// there are some — the spelling every instant the Python kernel writes carries. A literal is compared as a
/// term, so `…Z` and `…+00:00` are two terms of one value, and a case written by the one kernel holds the other
/// only where both spell an instant alike.
pub fn isoformat(at: DateTime) -> String {
    let second: f64 = at.second().to_string().parse().unwrap_or(0.0);
    let whole = second.trunc();
    let micro = ((second - whole) * 1e6).round() as u32;
    let fraction = if micro > 0 {
        format!(".{micro:06}")
    } else {
        String::new()
    };
    let zone = match at.timezone_offset() {
        None => String::new(),
        Some(offset) => {
            let minutes: f64 = DayTimeDuration::from(offset)
                .as_seconds()
                .to_string()
                .parse::<f64>()
                .unwrap_or(0.0)
                / 60.0;
            let minutes = minutes as i64;
            let sign = if minutes < 0 { '-' } else { '+' };
            format!("{sign}{:02}:{:02}", minutes.abs() / 60, minutes.abs() % 60)
        }
    };
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}{fraction}{zone}",
        at.year(),
        at.month(),
        at.day(),
        at.hour(),
        at.minute(),
        whole as u32
    )
}

/// A stretch of seconds as Python's `timedelta(seconds=…)` makes it: rounded to the microsecond.
pub fn microseconds(seconds: f64) -> DayTimeDuration {
    let micros = (seconds * 1e6).round();
    let sign = if micros < 0.0 { "-" } else { "" };
    let micros = micros.abs() as u64;
    format!("{sign}PT{}.{:06}S", micros / 1_000_000, micros % 1_000_000)
        .parse()
        .unwrap_or_default()
}

/// A stretch of the timeline, in seconds, as the duration SPARQL adds to an instant.
pub fn seconds(seconds: f64) -> DayTimeDuration {
    DayTimeDuration::try_from(Duration::from_secs_f64(seconds.max(0.0))).unwrap_or_default()
}

/// A duration as the seconds it is.
pub fn seconds_of(duration: DayTimeDuration) -> f64 {
    duration.as_seconds().to_string().parse().unwrap_or(0.0)
}

fn real_seconds() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64())
}

fn seconds_since_unix(at: DateTime) -> Result<f64, Error> {
    let unix = instant("1970-01-01T00:00:00Z")?;
    let since = at
        .checked_sub(unix)
        .ok_or_else(|| Error::Evaluation(format!("an epoch out of range: {at}")))?;
    Ok(since.as_seconds().to_string().parse().unwrap_or(0.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_manual_clock_stands_where_it_is_set_and_moves_by_seconds() {
        let clock = Manual::at(instant("2026-01-01T12:00:00Z").unwrap());
        clock.advance(600.0);
        assert_eq!(clock.now(), instant("2026-01-01T12:10:00Z").unwrap());
    }

    #[test]
    fn a_fast_clock_runs_from_its_epoch_and_sleeps_by_its_pace() {
        let epoch = DateTime::now();
        let clock = Paced::new(3600.0, Some(epoch)).unwrap();
        assert!(clock.now() >= epoch);
        assert_eq!(clock.real_delay(3600.0), Duration::from_secs(1));
    }

    #[test]
    fn a_pace_that_is_not_positive_is_refused() {
        assert!(Paced::new(0.0, None).is_err());
    }

    #[test]
    fn an_instant_is_spelled_as_python_spells_it() {
        assert_eq!(
            isoformat(instant("2026-01-01T12:00:00Z").unwrap()),
            "2026-01-01T12:00:00+00:00"
        );
        assert_eq!(
            isoformat(instant("2026-01-01T12:00:00.5-05:30").unwrap()),
            "2026-01-01T12:00:00.500000-05:30"
        );
        let later = instant("2026-01-01T12:00:00Z")
            .unwrap()
            .checked_add_day_time_duration(microseconds(90.0000004));
        assert_eq!(isoformat(later.unwrap()), "2026-01-01T12:01:30+00:00");
    }

    #[test]
    fn an_epoch_with_no_zone_is_utc() {
        assert_eq!(
            instant("2026-01-01T12:00:00").unwrap(),
            instant("2026-01-01T12:00:00Z").unwrap()
        );
    }
}
