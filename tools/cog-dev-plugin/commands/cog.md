---
description: Cognitum Seed developer toolkit — orchestrate the dev, test, deploy, and ops loop for edge cogs and MCP sensing.
argument-hint: "[dev|test|deploy|ops|connect]"
---

# /cog

Manage the full lifecycle of Cognitum Seed cogs (WASM edge micro-agents) and hardware integration.

## Usage

```bash
/cog <subcommand> [options]
```

### Subcommands

- **/cog connect** `[--seed <url>|--auto-discover]`: Wire this Seed's MCP tools into your active Claude / Claude Code session.
- **/cog dev** `[scaffold|build|lint]`: Create, edit, and compile WASM-based cogs for on-device execution.
- **/cog test** `[unit|sim|device]`: Run test suites locally or dispatch execution tests to the attached Seed.
- **/cog deploy** `[stage|canary|promote|rollback]`: Package, sign with Ed25519 identity, and deploy cogs to the Seed via OTA.
- **/cog ops** `[status|telemetry|witness|logs]`: Monitor appliance health, stream CSI telemetry vectors, and verify witness chains.

## Quickstart

If you just plugged in a Cognitum Seed via USB-C:

```bash
/cog connect --auto-discover
```
