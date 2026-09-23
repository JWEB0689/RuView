---
description: Deploy, stage, and verify cogs onto Cognitum Seed hardware over OTA.
argument-hint: "[stage|canary|promote|rollback] [cog-name]"
---

# /cog-deploy

Deploys compiled WASM cogs to one or more Cognitum Seed devices.

## Workflow

1. **Package & Sign**:
   Signs the WASM binary hash using your local developer Ed25519 identity key.
2. **OTA Upload**:
   Transfers the bundle to `POST http://169.254.42.1/api/v1/cogs/deploy`.
3. **Witness Chain Attestation**:
   Waits for the Seed's onboard witness chain to record the deployment block and return an attestation receipt.
4. **Health Confirmation**:
   Monitors the first 100 execution cycles for memory leaks or coherence faults. If error threshold exceeds 1%, automatically rolls back to the previous stable epoch.
