---
name: cog-test
description: Testing and validating cogs locally and on attached Cognitum Seed hardware. Use when running unit tests, benchmarking inference latency, or verifying edge behavior.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Cog Testing Skill

Guide for validating cogs across unit, simulation, and on-device tiers.

## Verification Tiers

### 1. Host Unit Tests
Run standard tests on your algorithmic calculations:
```bash
cargo test
```

### 2. Simulation Benchmark
Run the WASM binary against recorded CSI bursts:
```bash
node tools/cog-dev-plugin/bin/cli.js test sim --dataset tests/fixtures/csi-walk.bin
```
Verify:
- Heap usage remains under 16 MB.
- Latency per frame is < 5 ms.

### 3. On-Device Validation
Deploy to ephemeral execution slot on the attached Seed (`http://169.254.42.1`):
```bash
node tools/cog-dev-plugin/bin/cli.js test device --target my-cog.wasm
```
Confirm the witness receipt is signed and no panic occurred.
