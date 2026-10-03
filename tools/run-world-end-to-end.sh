#!/usr/bin/env bash
# Run a world end to end from nothing, and say what did not happen (#47).
#
#   tools/run-world-end-to-end.sh <world> <agent> [timeout-seconds]
#
# Builds the images, brings up the series store, onboards the world with no secrets on disk, starts
# it on a fast clock, and waits for three things in order: every agent of the world connected over
# mTLS, a reading reaching <agent>, and an intention of <agent>'s resolving `done` after the
# simulator acted on a command. A world with nothing to simulate cannot pass, since nothing would
# answer the agent.
#
# What it holds the generators to as well: onboarding from nothing regenerates the committed
# compose file byte for byte, so a generator that drifted from the tree fails here rather than on
# the bench.
#
# The pace is a deployment fact, environment and never a belief (agent/clock.py): it is handed to
# every process of the world through a compose override, never written into the world. 1440 is a
# world day a real minute.
#
# Needs rootless podman and podman-compose — the generated files use `userns_mode: keep-id`, which
# is podman's — and `infra/secrets/admin.env`, which this refuses to invent.
set -euo pipefail

world=${1:?a world is required — there is no default world}
agent=${2:?an agent of the world is required, the one whose intention is waited for}
timeout=${3:-900}
pace=${OREXIS_TIME_PACE:-1440}

root=$(cd "$(dirname "$0")/.." && pwd)
dir="$root/world/$world"
override="$dir/compose.end-to-end.yaml"
cd "$root"

[ -d "$dir" ] || { echo "no world $world under world/" >&2; exit 2; }
[ -f infra/secrets/admin.env ] || {
  echo "infra/secrets/admin.env does not exist — copy infra/admin.env.example and fill it in" >&2; exit 2; }

say() { printf '\n== %s\n' "$*"; }
fail() {
  printf '\nFAILED: %s\n' "$*" >&2
  exit 1
}

logs_of() { podman logs "orexis-${world}_$1_1" 2>&1 || true; }

teardown() {
  status=$?
  if [ "$status" -ne 0 ]; then
    say "logs, since something did not happen"
    for c in $(podman ps -a --format '{{.Names}}' | grep "^orexis-${world}_" || true); do
      printf -- '--- %s\n' "$c"; podman logs --tail 60 "$c" 2>&1 || true
    done
  fi
  (cd "$dir" && podman-compose -f compose.yaml -f "$override" down -v >/dev/null 2>&1) || true
  rm -f "$override"
  exit "$status"
}
trap teardown EXIT

# wait_for <what did not happen> <seconds> <command...>: poll until the command succeeds.
wait_for() {
  local what=$1 seconds=$2; shift 2
  local until=$((SECONDS + seconds))
  until "$@" >/dev/null 2>&1; do
    [ "$SECONDS" -lt "$until" ] || fail "$what (waited ${seconds}s)"
    sleep 3
  done
}

say "images"
podman build -q -t orexis:local . >/dev/null
podman build -q -t orexis-mosquitto:local infra/mosquitto >/dev/null

say "the series store"
(cd infra && podman-compose up -d influxdb >/dev/null)
wait_for "the series store never answered its health check" 120 curl -sf http://localhost:8086/health

say "onboarding $world from nothing"
[ ! -e "$dir/secrets" ] || echo "note: $dir/secrets exists, so this is not onboarding from nothing"
orexis-onboard "$world"
git diff --exit-code -- "$dir/compose.yaml" \
  || fail "onboarding regenerated $world's compose file differently from the one committed"

say "starting $world at pace $pace"
epoch=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 - "$dir/compose.yaml" "$override" "$pace" "$epoch" <<'EOF'
import sys, yaml
source, target, pace, epoch = sys.argv[1:]
services = yaml.safe_load(open(source))["services"]
clocked = {name: {"environment": {"OREXIS_TIME_PACE": pace, "OREXIS_TIME_EPOCH": epoch}}
           for name, service in services.items() if service.get("image") == "orexis:local"}
yaml.safe_dump({"services": clocked}, open(target, "w"))
EOF
agents=$(python3 -c "import sys,yaml; print(' '.join(n for n in yaml.safe_load(open(sys.argv[1]))['services'] if n.startswith('agent-')))" "$dir/compose.yaml")
(cd "$dir" && podman-compose -f compose.yaml -f "$override" up -d >/dev/null)

say "every agent connected"
for service in $agents; do
  wait_for "$service never connected to its broker" 120 sh -c "podman logs orexis-${world}_${service}_1 2>&1 | grep -q 'with a certificate'"
  echo "  $service"
done

say "a reading reached $agent"
wait_for "no reading reached $agent: simulator -> broker -> agent did not happen" 180 \
  sh -c "podman logs orexis-${world}_agent-${agent}_1 2>&1 | grep -q 'received INFO'"

say "the world was acted on, and $agent saw it done"
wait_for "the simulator never acted on a command" "$timeout" \
  sh -c "podman logs orexis-${world}_simulation_1 2>&1 | grep -Eq 'poured|heats for'"
logs_of simulation | grep -E 'poured|heats for' | head -3
wait_for "$agent never resolved an intention done" 300 \
  sh -c "podman logs orexis-${world}_agent-${agent}_1 2>&1 | grep -Eq ': [^ ]+ — done$'"
logs_of "agent-$agent" | grep -E ' — done$' | head -3

say "$world ran end to end"
