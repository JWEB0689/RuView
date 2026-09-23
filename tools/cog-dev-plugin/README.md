# @cognitum/cog-dev

> Claude Code plugin, skills, subagents, and MCP connector for the **Cognitum Seed** dev/test/deploy/ops loop.

Wires your Cognitum Seed edge hardware appliance directly into your **Claude Code** and **Antigravity** sessions.

---

## Quickstart

### 1. Auto-discover & Connect

Connect your Seed device via USB-C or connect to the same local WiFi network, then run:

```bash
# If published / installed:
npx -y @cognitum/cog-dev mcp connect --auto-discover

# Or running directly from this repo:
node bin/cli.js mcp connect --auto-discover
```

If you know the explicit link-local or IP address:

```bash
node bin/cli.js mcp connect --seed http://169.254.42.1
```

### 2. Local Link (While npm publish is pending)

To make `cog-dev` available globally on your workstation:

```bash
cd tools/cog-dev-plugin
npm link
cog-dev mcp connect --auto-discover
```

---

## What It Configures

When you run `mcp connect`, the tool:
1. **Auto-discovers** your Cognitum Seed appliance over USB link-local (`169.254.42.1`), mDNS, or LAN.
2. **Registers the MCP Server** in Claude Code (`~/.claude.json`) and Antigravity (`~/.gemini/config/mcp_config.json`).
3. **Installs Plugin Assets** into `~/.claude/`:
   - **Slash Commands**: `/cog`, `/cog-connect`, `/cog-dev`, `/cog-test`, `/cog-deploy`, `/cog-ops`
   - **Skills**: `cog-dev`, `cog-test`, `cog-deploy`, `cog-ops`
   - **Subagents**: `cog-developer`, `cog-operator`

---

## MCP Tools Provided

The connected MCP server exposes:

| Tool | Description |
|---|---|
| `seed_health` | Query appliance CPU, temperature, memory, and runtime state |
| `seed_telemetry` | Stream live Channel State Information (CSI) sensing vectors |
| `seed_witness_audit` | Audit the Ed25519-signed cryptographic witness chain |
| `cog_list` | List active WASM cogs loaded in the Seed runtime |
| `cog_deploy` | Stage and deploy a compiled WASM cog to the device |

---

## Slash Commands

- **/cog connect**: Probe and wire Seed MCP into your session.
- **/cog dev**: Author, scaffold, and compile WASM cogs.
- **/cog test**: Run unit, simulation, and on-device tests.
- **/cog deploy**: Sign and deploy cogs via OTA with witness receipts.
- **/cog ops**: Monitor hardware status, anomaly z-scores, and system logs.

---

## Skills

- **`cog-dev`**: Guide for authoring size-optimized WASM micro-agents adhering to the Seed host ABI (16MB memory limit).
- **`cog-test`**: Test execution framework across host unit tests, simulation against CSI bursts, and on-device test slots.
- **`cog-deploy`**: Safe rollout procedures, Ed25519 signing, and automated rollback upon anomaly threshold breaches.
- **`cog-ops`**: Hardware observability, CSI subcarrier monitoring, and cryptographic audit trails.

---

## Subagents

- **`cog-developer`** (`model: sonnet`): Focused on WASM micro-agent engineering, CSI DSP filters, and host ABI integration.
- **`cog-operator`** (`model: sonnet`): Focused on edge deployment, witness chain verification, and telemetry monitoring.
