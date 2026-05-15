# Imported professional subagents

Agents in this directory are vendored from upstream open-source collections under their original MIT licenses. Each file carries an HTML-comment attribution block immediately after its frontmatter. All `name:` fields have been prefixed with `imported-` to namespace them apart from the project-custom team in the parent `.claude/agents/` directory.

## Source

All 9 imports come from **[VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)** (MIT License, Copyright © 2025 VoltAgent). See `LICENSE-voltagent.txt` for the full text.

## Inventory

| Imported name | Upstream path | Specialty |
|---|---|---|
| `imported-security-auditor` | `04-quality-security/security-auditor.md` | OWASP-style vulnerability audit, compliance assessment |
| `imported-code-reviewer` | `04-quality-security/code-reviewer.md` | PR-style review (quality, security, best practices) |
| `imported-sql-pro` | `02-language-specialists/sql-pro.md` | Advanced SQL: query optimization, indexes, warehouse patterns |
| `imported-debugger` | `04-quality-security/debugger.md` | Systematic bug hunting from stack traces / error logs |
| `imported-incident-responder` | `03-infrastructure/incident-responder.md` | Active outage / breach response, evidence preservation |
| `imported-python-pro` | `02-language-specialists/python-pro.md` | Type-safe modern Python, async, type coverage |
| `imported-api-designer` | `01-core-development/api-designer.md` | REST/GraphQL design, OpenAPI, auth, versioning |
| `imported-test-automator` | `04-quality-security/test-automator.md` | Test framework architecture, CI/CD test integration |
| `imported-postgres-pro` | `05-data-ai/postgres-pro.md` | Postgres-specific: query tuning, HA, replication |

## When to use imported vs custom

The 13 **custom** agents in `.claude/agents/` (the mindex-coordinator-agent and its 12 specialists, including database-architect-agent) are calibrated to this codebase — they reference CLAUDE.md rules, the Mindex palette, the dual-path schema management, etc.

The 9 **imported** agents are deep generalists. Use them when:
- you need OWASP rigor that goes beyond `data-protector-agent`'s scope (`imported-security-auditor`)
- you want a PR-shaped review with no domain bias (`imported-code-reviewer` — complements `code-architect-agent`)
- you have a thorny Postgres query plan to optimise (`imported-postgres-pro`, `imported-sql-pro` — complement `database-architect-agent` and `performance-watchdog`)
- you're systematically chasing a bug from a stack trace (`imported-debugger`)
- you're in a live incident and need a checklist (`imported-incident-responder`)
- you're writing new pure-Python utilities outside `app.py` (`imported-python-pro`)
- you're designing a new `/api/*` surface and want REST-design rigor (`imported-api-designer` — pairs with `code-architect-agent`)
- you're building a new test suite from scratch (`imported-test-automator`)

The coordinator (`mindex-coordinator-agent`) can delegate to any of these by `subagent_type`.

## Updates

These files are pinned snapshots from the moment of import — they will NOT track upstream changes. Re-sync manually when a meaningful upstream improvement lands: `git clone --depth 1 https://github.com/VoltAgent/awesome-claude-code-subagents /tmp/voltagent` and diff.

## Why these, not the wshobson/agents repo?

The [wshobson/agents](https://github.com/wshobson/agents) collection is also MIT-licensed and high quality, but it ships agents as bundles inside top-level **plugins** (each plugin contains an `agents/` subdir plus orchestration). For a clean one-file-one-agent import shape we used VoltAgent's flat structure. If a specific wshobson agent is wanted later, copy it under the same `imported-` rename convention and add an attribution comment.
