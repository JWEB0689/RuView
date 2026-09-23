---
name: cog-ops
description: Monitoring, telemetry analysis, anomaly detection, and witness auditing for Cognitum Seed edge hardware. Use when diagnosing device state, viewing CSI streams, or checking audit logs.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Cog Operations Skill

Procedures for operating and maintaining Cognitum Seed edge hardware appliances.

## Key Operations

### 1. Hardware Status Check
Query the device health endpoint:
```bash
node tools/cog-dev-plugin/bin/cli.js ops status --seed http://169.254.42.1
```
Monitors:
- Core CPU and thermal throttling
- RAM usage (heap vs WASM linear memory allocations)
- CSI frame ingestion rate (target 100 Hz - 1000 Hz)

### 2. Telemetry Streaming & Anomaly Detection
Stream real-time inference vectors and check Z-score anomaly metrics:
```bash
node tools/cog-dev-plugin/bin/cli.js ops telemetry --seed http://169.254.42.1 --stream
```

### 3. Witness Chain Verification
Verify the cryptographic immutability of recorded events:
```bash
node tools/cog-dev-plugin/bin/cli.js ops witness --verify --seed http://169.254.42.1
```
Validates SHA-256 chain continuity and Ed25519 signatures across all epochs.
