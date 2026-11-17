//! THE WALL'S CLOCK AT A PACE, which a deployed agent alone reads, so the binary keeps it.
//!
//! The pace is world seconds per real second, a deployment fact (`OREXIS_TIME_PACE`), and the one conversion is
//! at a sleep (`real_delay`). The epoch (`OREXIS_TIME_EPOCH`) fixes the timeline's origin, so a restarted agent's
//! `now` lands where the world's clock stands; a paced clock with no epoch starts at the process's own start.

use std::time::{Duration, SystemTime, UNIX_EPOCH};

use orexis::Error;
use orexis::clock::{Clock, instant, seconds};
use oxsdatatypes::DateTime;

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
}
