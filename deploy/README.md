# Deploy (Raspberry Pi, unattended)

Runs Agora as user services that start on boot and restart on failure. Rootless Podman is
user-level, so these are **user** units.

Services:
- `agora-infra` — brings up the InfluxDB / Fuseki / Grafana containers (podman compose).
- `agora-agent@<id>` — **one unit per agent**, and the instance name is the agent id. That is
  the only thing the process is told; it reads the world to learn what it is wired to, its own
  beliefs for what it wants, and runs exactly the modules its capabilities name. A crashed
  fern cannot take tomato with it, and no process holds two agents' private beliefs.
- `agora-sim` — the physical edge: virtual plants dry continuously, sense only when their
  agent asks, and get watered. Drop it once real ESP32s speak the same topics.

Mosquitto runs as a **system** service (`sudo systemctl enable --now mosquitto`), separate
from these.

## Install

```bash
# let user services run without an active login session
loginctl enable-linger "$USER"

mkdir -p ~/.config/systemd/user
cp deploy/systemd/agora-*.service ~/.config/systemd/user/
systemctl --user daemon-reload

# one-time: seed the belief base (T-Box + world + each agent's beliefs) once infra is up
systemctl --user start agora-infra
.venv/bin/agora-seed

# one unit per agent — the id after @ is the agent's id, and nothing else is configured
systemctl --user enable --now agora-agent@supplier.service
systemctl --user enable --now agora-agent@fern.service
systemctl --user enable --now agora-agent@tomato.service
systemctl --user enable --now agora-agent@succulent.service

# the physical edge (drop this when real hardware is on the same topics)
systemctl --user enable --now agora-sim.service
```

Which agents exist is itself in the world: `agora-validate` will tell you, or query
`?a a ag:Agent ; ag:localId ?id` — there is no list to keep in sync here.

Adjust the paths in the unit files if the repo or venv isn't at
`/home/dimonina/projects/agora` / `.venv`.

## Watch it

```bash
journalctl --user -u agora-agent@supplier -f   # rounds opening, clearing, valves
journalctl --user -u agora-agent@fern -f       # its cadence, its bids, what it won
journalctl --user -u agora-sim -f              # plants sensing + getting watered
```

Grafana dashboard: `http://<pi-ip>:3000/d/agora-moisture`.
Belief base: `agora-validate` (every shapes module over `:world` + `:beliefs/*` + `:sensed`) or the SPARQL curl in the
top-level README.

## Sensor-only phase (now)

`.env` has `AGORA_ACTUATE=false` — rounds run and log the allocation decision but publish
**no** valve commands. Watch the supplier decide against real moisture. When a pump/valve is
wired and calibrated, set `AGORA_ACTUATE=true` and restart `agora-agent@supplier`. (Valve
*calibration* is not here — it lives on the valve in `genesis/world.ttl`, because it is a fact
about the hardware.)
