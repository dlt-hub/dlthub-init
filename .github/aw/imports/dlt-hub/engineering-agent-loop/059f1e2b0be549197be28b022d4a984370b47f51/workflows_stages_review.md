---
# import-only, pinned by workflows/review.md; see workflows/stages/triage.md.

imports:
  - shared/guardrails.md
  # a frontmatter import, not a body `{{#import}}`: the remote resolver follows only the former.
  - skills/review-repair.md
  # its own file rather than a section of the one above: the two passes are told different
  # things, and each brief's first line decides which it is
  - skills/review-diff.md

model: claude-sonnet-5

permissions:
  actions: read
  checks: read
  contents: read
  issues: read
  pull-requests: read

# `tools:` is additive. `bash: false` means no local tests; CI on the pushed commit is the verdict.
tools:
  edit:
  bash: false
  github: false

safe-outputs:
  # setting `network:` replaces gh-aw's default redaction allowlist outright, so without
  # this a GitHub Pages link in a body is rewritten to `(domain/redacted)`. Redaction only:
  # the firewall's own allowlist is untouched
  allowed-domains: [dlt-hub.github.io]
  # a pull request is written as the loop's App rather than as the Actions identity.
  github-app:
    client-id: ${{ vars.AGENT_LOOP_APP_CLIENT_ID }}
    private-key: ${{ secrets.AGENT_LOOP_APP_PRIVATE_KEY }}

  push-to-pull-request-branch:
    max: 1
    # never `target: '*'`; a workflow_dispatch has no pull request on the event, so it is named.
    target: "${{ github.event.issue.number || inputs.pr_number }}"
    # the pre-flight needs `administration: read`, which the App lacks; protection holds at push.
    check-branch-protection: false

  # the brief carries the repository's own rules for a body only on a pass that starts a
  # model, so the commonest run still stops before one and costs nothing
  update-pull-request:
    max: 1
    target: "${{ github.event.issue.number || inputs.pr_number }}"
    # the title is dispatch's; `replace` because a body is rewritten whole or not at all
    title: false
    body: true
    operation: replace
    # the body already carries the footer dispatch wrote
    footer: false
---

# review

A pull request this loop authored is in front of you. Read the brief: it says whether a check is failing, a reviewer is waiting, or nobody has yet read what the change does. Repair what it names, or read the diff and report what you find, or make no edits at all. Nothing else is yours to do.
