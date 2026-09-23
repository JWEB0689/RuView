---
name: cog-dev
description: Authoring, building, and compiling WASM cogs for Cognitum Seed edge hardware. Use when developing on-device algorithms, writing CSI feature extractors, or preparing micro-agents.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Cog Development Skill

This skill guides you through developing micro-agents ("cogs") for the Cognitum Seed WASM edge execution environment.

## Architecture

A "cog" is a lightweight WebAssembly module executed on the Cognitum Seed appliance.
Cogs process high-frequency Channel State Information (CSI) packets, extract spatial features, update local vector embeddings, and trigger alerts without cloud roundtrips.

### Technical Constraints
- Target architecture: `wasm32-unknown-unknown`
- Memory limit: 16MB maximum linear memory
- No filesystem or raw network access inside WASM; all I/O is routed through host ABI imports.

## Standard Development Steps

1. **Scaffold a new cog**:
   ```bash
   node tools/cog-dev-plugin/bin/cli.js dev scaffold my-feature-cog
   ```
2. **Implement core handler**:
   Implement `process_frame(ptr, len)` to parse raw CSI subcarrier amplitudes/phases.
3. **Compile to optimized WASM**:
   ```bash
   cargo build --target wasm32-unknown-unknown --release
   ```
4. **Inspect exports**:
   Ensure `init`, `process_frame`, and `status` are exported.
