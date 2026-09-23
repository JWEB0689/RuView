---
description: Author, scaffold, and compile WASM cogs for the Cognitum Seed edge runtime.
argument-hint: "[scaffold|build|lint] [cog-name]"
---

# /cog-dev

Develop edge cogs targeted for the Cognitum Seed WASM runtime.

## Subcommands

- **/cog-dev scaffold `<name>`**: Generate a starter template for a new sensing or analytical cog (Rust / AssemblyScript / C).
- **/cog-dev build `[name]`**: Compile the cog to `wasm32-unknown-unknown` with size-optimization and export verification.
- **/cog-dev lint `[name]`**: Verify imports and exports match the Cognitum Host ABI requirements (memory limits, coherence gates, witness hooks).

## Host ABI Requirements

Cogs run inside a sandboxed WASM environment on the Seed:
- Maximum linear memory: 16 MB.
- Exported entrypoints: `init()`, `process_frame(ptr, len) -> ptr`, `status()`.
- Allowed host imports: `witness_log(ptr, len)`, `vector_store(id, ptr, len)`, `get_time_ns()`.
