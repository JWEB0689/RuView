---
description: Test cogs locally via simulator or directly on attached Cognitum Seed hardware.
argument-hint: "[unit|sim|device] [cog-name]"
---

# /cog-test

Execute tests against your cogs before deployment.

## Test Tiers

1. **Unit Tests (`/cog-test unit`)**:
   Runs standard local test harnesses against host-independent cog logic.
2. **Simulation (`/cog-test sim`)**:
   Executes the compiled WASM binary inside a local mock runner simulating Seed CSI feeds and vector stores.
3. **On-Device (`/cog-test device`)**:
   Deploys to an ephemeral test slot on the attached Seed (`http://169.254.42.1`), feeds a test burst, and evaluates latency and memory consumption.
