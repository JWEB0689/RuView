---
name: cog-deploy
description: Packaging, signing, and deploying WASM cogs to Cognitum Seed hardware. Use when rolling out new versions, canary testing, or managing edge rollbacks.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Cog Deployment Skill

Procedures for safe OTA distribution of cogs onto Cognitum Seed hardware appliances.

## Steps

1. **Build & Package**:
   Generate the release `.wasm` and compute the SHA-256 digest:
   ```bash
   shasum -a 256 dist/my-cog.wasm
   ```
2. **Sign with Ed25519 Key**:
   Sign the manifest using the developer key configured in `~/.cognitum/keys.json`.
3. **Upload to Seed Endpoint**:
   ```bash
   node tools/cog-dev-plugin/bin/cli.js deploy --seed http://169.254.42.1 --bundle dist/my-cog.wasm
   ```
4. **Verify Witness Receipts**:
   Ensure the seed device creates an epoch transition record on its local witness chain.
5. **Rollback Plan**:
   In case of anomaly detection spikes or unhandled traps:
   ```bash
   node tools/cog-dev-plugin/bin/cli.js deploy rollback --seed http://169.254.42.1
   ```
