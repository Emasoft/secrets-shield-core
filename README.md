# secrets-shield-core

The secret, payment-card, email and home-path redaction core shared by ai-maestro-janitor and reports-sanitizer-plugin.

- `core/`: the redaction passes (token rules under `core/rules/`, payment cards, email, home paths), the pipeline that runs them in a fixed order, and the known-value matcher. The engine only: the janitor's Claude Code mod registration stays in ai-maestro-janitor.
- `scan/`: the file scanner and in-place redactor built on the core (vault, restore, JSONL handling, write guard).
- `KNOWN-MISSES.md`: the secrets the shield knowingly does not hide, each pinned by `core/tests/known-misses.test.ts`.

It is TypeScript, run by [bun](https://bun.sh). There is no build step.

## Tests

```bash
bun test
```

The tests import `claude-code/testing`, a module only the claude binary provides. `tsconfig.json` maps it to `test-support/claude-code-testing.ts`, which re-exports `describe`, `expect` and `mock` from `bun:test` and wraps `test` so the host's `{ timeoutMs }` option becomes bun's `{ timeout }`. `core/tests/load/` holds timing probes that need their own harness; bun test does not pick them up. `bunx tsc --noEmit -p .` reports 51 type errors in `core/tests/patterns.test.ts` (a `string[]` where the test helper wants a 3-tuple); they are in the extracted source and are left as they are.

The janitor's host-bound tests (`shield.test.ts`, `json-text.test.ts`) are not part of this repo; they are expected to run under the Claude host; not verified here.

## Using it

Consumers vendor the files or install the package at a pinned tag (for example `v0.1.0`); never track a branch. `scan/scan.ts` reads its version from `.claude-plugin/plugin.json` of the repo root, which this repo does not have, so the caller sets `SHIELD_SCAN_VERSION`.

## Vendoring into a consumer

```bash
tools/vendor_into.py --into <consumer-root> --dir <subpath> --ref <tag|sha>
```

All three options are required. The script copies the files of that tag or commit of this repo into `<consumer-root>/<subpath>` and writes `<subpath>/UPSTREAM.json`: the source, the tag (only when the ref is a tag), the full commit sha and the sha256 of every file. Consumers ship only a read-only check of that pin; the writer stays here because CPV rule RC-164 forbids a plugin script that writes fetched code into its own tree.

- Everything under `tools/` is skipped, so the writer is never vendored and is not in the pin. Any other entry that is not a regular file (mode 100644) stops the run before anything is written.
- Deletion follows the previous `UPSTREAM.json` only: a file it lists that the new ref lacks is deleted, then its parent folders if they are now empty. With no previous pin nothing is deleted, and files that no pin lists (the consumer's own) are never touched.
- The run refuses when `--into` is not a git work tree, when `--dir` is absolute or is not strictly inside `--into`, and when `git status --porcelain` shows anything under the target, because git could not restore uncommitted changes there.

## Licence

MIT, see `LICENSE`. Derived from secret-shield 1.0.0 of awesome-claude-mods; see `NOTICE` for the upstream source, the changes and the rules taken from other projects.
