"""orexis-calibrate — tell a world's agent what one of its sensors is reading now.

  orexis-calibrate terrace terrace moisture_sensor_terrace dry          # the probe is in dry air now
  orexis-calibrate terrace terrace moisture_sensor_terrace wet --raw 1105

**A calibration is the agent's belief** (`sensing:CalibrationGraph`, born from the world's
`beliefs/<agent>.ttl`), so recalibrating is telling the agent, not editing a document or flashing a
board: the point named takes the number the sensor's latest observation holds, or the one given,
and the next reading is concluded through it. The act is sensing's (`agent/sensing/calibrate.py`).

**It runs inside the agent's own image, against the agent's own volume, while the agent is
stopped**: one process holds a volume at a time, and the store must be opened by the engine that
wrote it, which the image pins and the host's environment need not. So this stops the agent's
service, runs the act with `podman compose run` — the service's own mounts and user — and starts it
again, whether or not the act succeeded, since an agent left stopped is worse than a calibration
refused. The agent resumes where it stood: every graph of its own is kept.
"""

from __future__ import annotations

import argparse
import logging
import subprocess

from .compose import STATE
from .worlds import world_dir, worlds

log = logging.getLogger("calibrate")


def steps(agent: str, sensor: str, reference: str, raw: float | None = None) -> list[list[str]]:
    """The three commands, run in the world's directory: stop the agent, tell it, start it."""
    service = f"agent-{agent}"
    told = ["python", "-m", "agent.sensing.calibrate", STATE, sensor, reference, *(["--raw", str(raw)] if raw is not None else [])]
    return [["podman", "compose", "stop", service],
            ["podman", "compose", "run", "--rm", "--no-deps", service, *told],
            ["podman", "compose", "start", service]]


def calibrate(world: str, agent: str, sensor: str, reference: str, raw: float | None = None, run=subprocess.run) -> None:
    """Tell `agent` of `world` that `sensor` reads `reference` now — its latest number, or `raw`."""
    here = world_dir(world)
    stop, tell, start = steps(agent, sensor, reference, raw)
    run(stop, cwd=here, check=True)
    try:
        run(tell, cwd=here, check=True)
    finally:
        run(start, cwd=here, check=True)
    log.info("%s of %s now believes %s reads %s", agent, world, sensor, reference if raw is None else f"{reference} at {raw}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(prog="orexis-calibrate", description="Tell a world's agent what one of its sensors reads now.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("agent", help="the agent's id")
    p.add_argument("sensor", help="the sensor's orexis:localId")
    p.add_argument("reference", help="the calibration point's label, e.g. dry or wet")
    p.add_argument("--raw", type=float, help="the number to take; the sensor's latest where absent")
    args = p.parse_args()
    calibrate(args.world, args.agent, args.sensor, args.reference, args.raw)


if __name__ == "__main__":
    main()
