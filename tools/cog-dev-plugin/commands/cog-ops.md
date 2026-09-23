---
description: Operations, telemetry streaming, anomaly detection, and witness auditing for Cognitum Seed appliances.
argument-hint: "[status|telemetry|witness|logs]"
---

# /cog-ops

Day-2 operations and telemetry monitoring for Seed hardware.

## Actions

- **/cog-ops status**: Retrieve CPU, thermal, memory, and battery status from the attached Seed.
- **/cog-ops telemetry `[--duration 10s]`**: Stream realtime CSI feature vectors and spatial occupancy events.
- **/cog-ops witness `[--verify]`**: Audit the cryptographic hash chain of system state transitions.
- **/cog-ops logs `[--follow]`**: Tail device syslog and WASM module standard error output.
