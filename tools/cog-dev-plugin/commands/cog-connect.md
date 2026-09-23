---
description: Wire the Cognitum Seed MCP server into your Claude / Claude Code session.
argument-hint: "[--seed <url>|--auto-discover]"
---

# /cog-connect

Connects an attached Cognitum Seed hardware device or local emulator to your active Claude Code session over MCP.

## Actions

1. Check for attached Seed appliance:
   - Probes USB link-local address: `http://169.254.42.1`
   - If `--auto-discover` is specified, checks USB gadget interface, mDNS (`_mcp._tcp`, `_cognitum._tcp`), and local subnet.
   - If `--seed <url>` is provided, targets the explicit host URL.
2. Verify connectivity by querying `/health` or `/mcp`.
3. Registers the MCP server in `~/.claude.json`:
   ```bash
   node tools/cog-dev-plugin/bin/cli.js mcp connect --auto-discover
   ```
4. Verifies tools exposed by the Seed:
   - `seed_health`: Appliance CPU, memory, uptime, temperature
   - `seed_telemetry`: CSI vectors and pose confidence
   - `seed_witness_audit`: Cryptographic witness receipts
   - `cog_deploy`: Load edge WASM modules
   - `cog_invoke`: Execute on-device functions
