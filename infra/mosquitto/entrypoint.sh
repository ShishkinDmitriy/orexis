#!/bin/sh
# PID 1 stays root so the container can be SIGNALLED; mosquitto still drops to `user mosquitto`.
#
# Both halves are needed and neither is optional:
#
#   - Rootless podman cannot deliver a signal to a container whose PID 1 is unprivileged
#     ("send signal to pidfd: Permission denied"), and the kernel shields a namespace's PID 1
#     from `kill` inside it. With mosquitto itself as PID 1 there is no way to SIGHUP it at
#     all, so reloading the ACL meant recreating the container — and `podman stop` could not
#     reach it either, which is why it wedged in `Stopping` and needed its conmon killed.
#     Note that setting no USER in the image is NOT enough on its own: mosquitto drops
#     privileges itself, so PID 1 ends up unprivileged either way. Measured, not assumed.
#   - Running the broker as root would be a real regression for a network-facing process. So
#     mosquitto drops privileges exactly as before, via `user mosquitto` in lan.conf.
#
# root shell as PID 1, unprivileged broker as its child: signals land, and nothing listens on
# the network as root. See knowledge/decisions/series-and-bus-isolation.md.
#
# No `set -e`: this script's whole job is to outlive signals, and `wait` returns 128+n every
# time one arrives.

/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf &
broker=$!

# HUP is the one that matters: `agora-mqtt` regenerates passwd and acl.conf, and mosquitto
# rereads both on this signal WITHOUT dropping a single connected client.
reload() {
    echo "entrypoint: SIGHUP -> reloading mosquitto ($broker)"
    kill -HUP "$broker" 2>/dev/null || echo "entrypoint: could not signal $broker"
}
shutdown() { kill -TERM "$broker" 2>/dev/null; }

trap reload HUP
trap shutdown TERM INT

# `wait` is interrupted by every trapped signal, so it has to be resumed rather than called
# once. A status below 128 means the broker itself exited, and then so do we.
while true; do
    wait "$broker"
    status=$?
    [ "$status" -lt 128 ] && break
    kill -0 "$broker" 2>/dev/null || break
done
exit "$status"
