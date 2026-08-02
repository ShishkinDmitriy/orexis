# Deploy (Raspberry Pi, unattended)

Runs Agora as user services that start on boot and restart on failure. Rootless Podman is
user-level, so these are **user** units.

Services:
- `agora-infra` — brings up the InfluxDB / Fuseki / Grafana containers (podman compose).
- `agora-sim` — the plant edge: virtual plants sense, assert their own `:sensed` data, and
  get watered (there is no gateway — each plant authors its own reading). For real hardware,
  replace with devices that write `:sensed` directly.
- `agora-loop` — fires a round when a plant crosses `:LOW` (event-driven).

Mosquitto runs as a **system** service (`sudo systemctl enable --now mosquitto`), separate
from these.

## Install

```bash
# let user services run without an active login session
loginctl enable-linger "$USER"

mkdir -p ~/.config/systemd/user
cp deploy/systemd/agora-*.service ~/.config/systemd/user/
systemctl --user daemon-reload

# one-time: seed the world (ontology + structure) once infra is up
systemctl --user start agora-infra
.venv/bin/agora-seed

# enable + start (order handled by the units); set executor.actuate: true for the sim
systemctl --user enable --now agora-sim.service
systemctl --user enable --now agora-loop.service
```

Adjust the paths in the unit files if the repo or venv isn't at
`/home/dimonina/projects/not-yet` / `.venv`.

## Watch it

```bash
journalctl --user -u agora-sim -f          # plants sensing + getting watered
journalctl --user -u agora-loop -f         # rounds firing on LOW
```

Grafana dashboard: `http://<pi-ip>:3000/d/agora-moisture`.
Belief base: `agora-validate` (SHACL over `:sensed` + `:structure`) or the SPARQL curl in the
top-level README.

## Sensor-only phase (now)

`backend/config/plants.yaml` has `executor.actuate: false` — rounds run and log the
allocation decision but publish **no** valve commands. Watch `agora-loop` decide against
real moisture. When a pump/valve is wired and calibrated, set `actuate: true` and restart
`agora-loop`.
