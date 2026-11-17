# orexis-sensing

Turns a sensor's bytes into observations, and says when a sensor is silent or stuck. An observation is a percept:
no reader of the mind is handed one.

- **Loaded for:** `sensing:Observer`, which is beneath `belief:Deliberator`.
- **Words:** `ontology.ttl` (`sensing:`), speaking SOSA and SSN. **Dictionary:** `knowledge/domain/sensing/`.
- **Imports:** the kernel, and the transport family's contract (`orexis-transport/`), naming no member.
- **Its housekeeper:** `orexis-sensing-influxdb/` writes each reading to the series store.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| bytes a transport read for a sensor (`received`, a call, not an event) | the MQTT member, for a sensor on a topic | a percept written per reading, then `sensing:Perceived` said |
| the clock, at the frequency a sensor a member answers when asked states, and once at start | | the sensor asked, through the member that reaches it |
| an asked sensor's answer (an arrival) | the member asked | handed to `received`: a percept written per reading |
| a graph of kind `sensing:ObservationGraph` written | itself | `sensing:Perceived` said to belief |
| `sensing:ObservingTrigger`: `belief:Revised` | belief | `sensing:Observing` |
| the clock, as often as the observer's role says (`sensing:askedEveryS`), every 60 s of the agent's time where it says nothing | | the ask after silent sensors (`missed`) |

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `sensing:Observing` | each percept the revision concluded of is said as the observation it is, with how long after the percept before it it came | the observation, for the series and the journal |

No activity, on the timer: each sensor whose latest percept ended a limit of cadences ago is kept as a
`sensing:SilenceGraph` and said in the log; a sensor giving one number for its last `sensing:stuckAfter` readings
is said stuck by sensing's rule.

## What it says

`sensing:Perceived` (beneath `belief:RevisingTrigger`), each observation, how many sensors are silent, and each
sensor doubted or no longer doubted.
