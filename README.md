# secrets-shield-core

The secret, payment-card, email and home-path redaction core shared by ai-maestro-janitor and reports-sanitizer-plugin.

- `core/`: the redaction passes (token rules under `core/rules/`, payment cards, email, home paths), the pipeline that runs them in a fixed order, and the known-value matcher. Linear-time rules. `core/register.ts` is the janitor's mod wiring (hooks and the slash command); it imports types from `claude-code`, which do not resolve in this repo.
- `scan/`: the file scanner and in-place redactor built on the core (vault, restore, JSONL handling, write guard).
- `KNOWN-MISSES.md`: the secrets the shield knowingly does not hide, each pinned by `core/tests/known-misses.test.ts`.

It is TypeScript, run by [bun](https://bun.sh). There is no build step.

## Tests

```bash
bun test
```

The core tests import `claude-code/testing`, a module only the claude binary provides. `tsconfig.json` maps it to `test-support/claude-code-testing.ts`, which re-exports `describe`, `expect`, `mock` and `test` from `bun:test`. That covers every pure test. 15 tests (in `core/tests/shield.test.ts` and `core/tests/json-text.test.ts`) use the mod host (`$`, `on`, `mock.store`) and fail under bun; they run only through `claude plugin test`. `core/tests/load/` holds timing probes that need their own harness; bun test does not pick them up.

## Using it

Consumers vendor the files or install the package at a pinned tag (for example `v0.1.0`); never track a branch. `scan/scan.ts` reads its version from `.claude-plugin/plugin.json` of the repo root, which this repo does not have, so the caller sets `SHIELD_SCAN_VERSION`.

## Licence

MIT, see `LICENSE`. Derived from secret-shield 1.0.0 of awesome-claude-mods; see `NOTICE` for the upstream source, the changes and the rules taken from other projects.
