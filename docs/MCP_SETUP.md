# MCP_SETUP.md

Optional Model Context Protocol (MCP) servers for the mindex-portal project. **None of these are auto-installed** — they require an operator decision and a credential setup step. The template at `.claude/mcp_servers.json` is wired with everything disabled by default.

## What is MCP?

The Model Context Protocol lets Claude Code talk to external tools — databases, GitHub, browser automation, vector stores — through a thin standard interface. Each MCP server runs as a subprocess that Claude Code spawns; it exposes "tools" and "resources" that the assistant can call alongside its built-in tools. See <https://code.claude.com/docs/en/mcp> for the official intro.

## High-value servers for this project

### `filesystem` — bounded directory access
- **Package**: `@modelcontextprotocol/server-filesystem` (official, npm)
- **What it enables**: secure, sandboxed file ops with an explicit allowlist of root paths. Built-in `Read`/`Write`/`Edit` already cover the repo root; this one is useful when you want Claude to operate against an *additional* directory (e.g. a sibling repo, the Render-mounted `/var/data/` snapshot, an exports dir) without granting permission-everywhere.
- **Status**: actively maintained.

### `git` — repository tools
- **Package**: `mcp-server-git` (official, pypi)
- **What it enables**: structured queries on `git log` / `git blame` / `git diff` without parsing CLI output. Useful for the `business-analyst-agent` (last-changed-when queries) and `code-architect-agent` (blame-driven duplication checks).
- **Status**: actively maintained.

### `fetch` — web content for LLMs
- **Package**: `@modelcontextprotocol/server-fetch` (official, npm)
- **What it enables**: pull and convert web pages to LLM-friendly text. Equivalent to the built-in WebFetch but with conversion built in. Useful when `imported-api-designer` references external API docs or when `business-analyst-agent` needs to check competitor product pricing.
- **Status**: actively maintained.

### `playwright` — browser automation
- **Package**: `@playwright/mcp` (Microsoft, npm)
- **What it enables**: a stateful browser session that the assistant can drive (click, fill, screenshot, evaluate JS). The project's e2e suite (`scripts/run_e2e.py` + `scripts/auto_test.py`) already does this through Python, but `@playwright/mcp` makes it possible to interactively explore a page from within a turn without a pre-written script.
- **Status**: actively maintained; one of the most-installed MCP servers in the Claude Code ecosystem.

### `postgres` — read-only DB access
- **Package**: ⚠ **NOT** the original `@modelcontextprotocol/server-postgres` (archived May 2025 due to an unpatched SQL-injection bug). Use one of:
  - **pgEdge Postgres MCP** — `@pgedge/postgres-mcp` — supports Postgres 14+, well-maintained
  - **Zed-patched fork** — `@zeddotdev/postgres-context-server` v0.1.4+ — SQL-injection fix on the original
- **What it enables**: SELECT/EXPLAIN access without shelling out to `scripts/db_query.py`. Pairs with `database-architect-agent` for fast iterative discovery on the production schema.
- **Status**: third-party, MIT-licensed. **Use a read-only role** in the connection string. Do not point this at the write-capable prod `DATABASE_URL` — create a dedicated read-only user.

### `github` — issues, PRs, releases
- **Package**: official Anthropic MCP **archived**; community fork `@modelcontextprotocol/server-github-community` or use the `gh` CLI directly via Bash. Most teams stick with `gh` because it's already on PATH and well-permissioned.
- **What it would enable**: file an issue, open a PR, comment on a review without shelling out. Marginal value when `gh` already works.

### `memory` — knowledge graph
- **Package**: `@modelcontextprotocol/server-memory` (official, npm)
- **What it enables**: persistent cross-conversation memory beyond the auto-memory in `C:\Users\polyt\.claude\projects\.../memory/`. Useful if you want a structured triple-store (subject/predicate/object) rather than the current free-form Markdown.
- **Status**: actively maintained. Overlaps with auto-memory; pick one or the other to avoid drift.

### `sequential-thinking` — multi-step reasoning aid
- **Package**: `@modelcontextprotocol/server-sequentialthinking` (official, npm)
- **What it enables**: a structured scratchpad the assistant can write thoughts to between turns. Marginal value when `Plan` mode and the TaskList already provide structure.

### `sentry` / `render` — third-party-as-of-2026
- Neither has an official MCP server. Sentry has a community one (`@getsentry/mcp-sentry` proof-of-concept) but adoption is light. Render has no MCP — for now, use the `scripts/get_logs.py` wrapper plus `render.yaml` for infra config.

## Setup instructions

### Prerequisites

- **Node.js 20+** — most MCP servers ship as npm packages and run via `npx`.
- **Python 3.12+** — for `mcp-server-git` (`uvx` from astral.sh).
- **Read-only Postgres role** — see `scripts/db_query.py` for how the application reads. For MCP, create a separate role:

  ```sql
  CREATE ROLE mindex_readonly LOGIN PASSWORD '<a-fresh-strong-secret>';
  GRANT CONNECT ON DATABASE mindex_db_pw2a TO mindex_readonly;
  GRANT USAGE ON SCHEMA public TO mindex_readonly;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO mindex_readonly;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mindex_readonly;
  ```

### Enable a server

1. Copy `.claude/mcp_servers.json` (the template) to `.mcp.json` at the repo root (the canonical location Claude Code reads from).
2. Uncomment the server block(s) you want.
3. Fill in the env-var placeholders. **Never commit a real credential**.
4. Restart Claude Code (or run `/mcp` to reload).
5. Run `/mcp` to inspect connected servers and the tools they expose.

### Recommended starter set

If you're enabling MCP for the first time, start with two:

- **`playwright`** — high impact, low risk, no credentials needed.
- **`postgres` (pgEdge or Zed fork)** — high impact for `database-architect-agent`'s discovery phase. Use the read-only role above.

Add others as the need surfaces.

## Use cases

| Use case | MCP that helps |
|---|---|
| Iterative schema exploration of prod | postgres (read-only role) |
| Capture a screenshot of the production /points/board mid-conversation | playwright |
| Cross-reference yesterday's git history while reviewing today's diff | git |
| Re-summarize a competitor's pricing page | fetch |
| Operate on the Render persistent disk at `/var/data` without permission-everywhere | filesystem (rooted at `/var/data`) |

## What NOT to enable

- **`postgres` with a write-capable URL** — turns SELECT-only safety guarantees into trust-the-LLM. Use a dedicated read-only role.
- **Multiple Postgres MCPs at once** — name conflicts and ambiguous routing. Pick one fork.
- **`memory` while auto-memory is on** — two competing persistence layers cause drift. Disable one.

## References

- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) — official docs
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — reference servers
- [pgEdge Postgres MCP](https://www.pgedge.com/blog/introducing-the-pgedge-postgres-mcp-server) — recommended Postgres MCP
