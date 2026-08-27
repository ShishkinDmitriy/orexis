"""orexis-ask — the sovereign puts one SPARQL question to one running agent.

  orexis-ask simulation fern 'SELECT ?p ?v WHERE { ?s ?p ?v } LIMIT 5'

`agent-centric-epistemics` says observe VIA the sovereign, and this is the via: the question
goes over the world's own bus on the sovereign principal's credential (minted by `orexis-mqtt`,
held in world/<world>/secrets/, never mounted into any container), the broker's ACL admits it
to exactly the per-agent question topics, and the AGENT answers about itself from its live
store. Nothing here opens a volume or reaches around an isolation boundary — the belief base
stays the agent's, and what this tool receives is voluntary disclosure on an authorised
channel. Read-only by construction on the far side: the responder runs `store.query`, which
structurally cannot execute an update; an UPDATE comes back as the engine's own error.

In onboarding and not in the agent image, like everything the sovereign wields.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading

import paho.mqtt.client as mqtt

from agent import ratified
from orexis_capability_reporting import sovereign
from agent.genesis import world_dir, worlds
from onboarding.mqtt import _PORTS_Q, device_credential_file

log = logging.getLogger("ask")


def _credentials(world: str) -> tuple[str, str]:
    path = device_credential_file(world, sovereign.SOVEREIGN)
    if not path.exists():
        raise SystemExit(f"no sovereign credential for {world!r} — run `orexis-mqtt {world}`")
    values = dict(line.split("=", 1) for line in path.read_text().splitlines()
                  if "=" in line)
    return values["MQTT_USERNAME"].strip(), values["MQTT_PASSWORD"].strip()


def ask(world: str, agent_id: str, modality: str, sparql: str,
        timeout_s: float = 10.0) -> dict:
    """One question, one answer, as a dict — the CLI prints it, a test asserts on it."""
    port = int(ratified.rows(ratified.dataset(world), _PORTS_Q)[0]["port"])
    user, password = _credentials(world)

    answer: dict = {}
    answered = threading.Event()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(user, password)

    def on_connect(c, *_):
        c.subscribe(sovereign.result_topic(agent_id))
        c.publish(sovereign.query_topic(agent_id),
                  json.dumps({"modality": modality, "sparql": sparql}))

    def on_message(c, _userdata, message):
        nonlocal answer
        answer = json.loads(message.payload.decode("utf-8"))
        answered.set()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", port)
    client.loop_start()
    try:
        if not answered.wait(timeout_s):
            raise SystemExit(f"{agent_id} did not answer within {timeout_s}s — is its "
                             f"container running, and was the ACL regenerated since the "
                             f"sovereign channel landed?")
    finally:
        client.loop_stop()
        client.disconnect()
    return answer


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-ask",
        description="Put one SPARQL question to one running agent, over its world's bus.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("agent", help="the agent's id, e.g. fern")
    p.add_argument("modality", help="which of the mind's stores to ask — beliefs or desires, "
                                    "more as they land. Required: there is no default "
                                    "modality, as there is no default world")
    p.add_argument("sparql", help="a SELECT — updates are refused by the engine itself")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    answer = ask(args.world, args.agent, args.modality, args.sparql, args.timeout)
    if "error" in answer:
        print(f"refused: {answer['error']}", file=sys.stderr)
        raise SystemExit(1)
    rows = answer.get("rows", [])
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    if answer.get("truncated"):
        print(f"(truncated: {answer['truncated']} rows matched)", file=sys.stderr)


if __name__ == "__main__":
    main()
