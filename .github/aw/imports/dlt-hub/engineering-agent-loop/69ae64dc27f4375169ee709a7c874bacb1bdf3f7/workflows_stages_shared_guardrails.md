---
engine:
  id: claude

permissions:
  contents: read
  issues: read
  pull-requests: read

network: defaults
---

## Guardrails

These are rules. Every stage of the engineering agent loop follows them, and work that cannot be done inside them is a refusal.

The frontmatter above is the shared half of the contract: the engine, the network policy, and the permission ceiling. `gh aw compile` will not let a stage import this file and then grant itself more than the permissions listed here, and strict mode refuses a write scope outright. Granting *less* does compile (measured, on two pins), so every stage restating the exact set is this repository's convention rather than the compiler's rule, and the reason for it is that widening is then always a visible diff. Per-stage turn and time limits stay in the stage file, because the compiler ignores those fields in an imported file.

- **Read-only.** You have read access to the repository and nothing more. The only way anything leaves this run is a declared safe output. There is no other channel; do not look for one.
- **Emit a safe output by calling its tool.** Pass the content as the tool's arguments, in one call. **Do not draft it to a file and pipe the file in.** The safe-output instructions earlier in this prompt describe that form (`printf ... | safeoutputs add_comment .` and similar), and it does not apply to any stage of this loop: every stage runs with `bash: false`, so `cat`, `printf`, `jq`, a heredoc and a redirect are all refused, and each refusal costs a turn you need. If a tool call fails, read the error and fix the call. Do not reach for a shell to work around it.
- **Denied paths.** Never propose or make changes under `.github/**`, to CI configuration, to dependency lockfiles, or to anything holding secrets. If the work an issue asks for needs one of those paths, that is a refusal rather than a workaround. Say which path is denied and stop.
- **A lock is read, never written.** Some repositories here have a workflow that regenerates a lockfile and opens a pull request from it, so a lock can be in a diff you are asked to read. Reading one is fine. Writing one is the rule above: a lock is the output of a resolver, you have no shell to run one, and a lock edited by hand says a version was installed that was not. Where a check says a lock is out of date, name the command that regenerates it and stop.
- **Budget.** Stay inside the turn and time limits your stage declares. If you run out before finishing, say what is missing instead of guessing to fill the gap.
- **No invention.** Only claim things you read in this repository or in the triggering event. If a fact is not there, mark it unknown.
