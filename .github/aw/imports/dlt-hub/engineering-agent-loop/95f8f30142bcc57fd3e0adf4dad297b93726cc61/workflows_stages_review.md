---
# import-only, pinned by workflows/review.md; see workflows/stages/triage.md.

imports:
  - shared/guardrails.md
  # a frontmatter import, not a body `{{#import}}`: the remote resolver follows only the former.
  - skills/review-repair.md
  # the reviewing pass (#315). Its own file rather than a section of the one above, because
  # the two passes are told different things about the same pull request; each says which
  # brief it answers and the brief's own first line decides.
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
  # #397. Without this, a GitHub Pages link in a body is replaced by `(domain/redacted)`.
  # gh-aw's own default redaction allowlist carries `github.io`, and setting `network:`
  # anywhere replaces that default outright rather than adding to it, so the Storybook
  # preview link the profile skills ask for never reached a pull request. Unioned with
  # `network.allowed` for redaction only: the firewall's own allowlist is untouched.
  allowed-domains: [dlt-hub.github.io]
  # the dlt-hub org forbids the Actions identity from writing pull requests.
  github-app:
    client-id: ${{ vars.AGENT_LOOP_APP_CLIENT_ID }}
    private-key: ${{ secrets.AGENT_LOOP_APP_PRIVATE_KEY }}

  push-to-pull-request-branch:
    max: 1
    # never `target: '*'`; a workflow_dispatch has no pull request on the event, so it is named.
    target: "${{ github.event.issue.number || inputs.pr_number }}"
    # the pre-flight needs `administration: read`, which the App lacks; protection holds at push.
    check-branch-protection: false
    # #392, and the policy is left at its default because the key is inert here today: this
    # handler implements `deny` and `fallback-to-issue` and nothing for `request-review`, so a
    # patch touching a top-level dot folder is pushed rather than held. The exclusion is set so
    # a repair pass does not start being refused the e2e file `runtime-web` allows if that gap
    # ever closes. Trailing slash, as on dispatch.
    protected-files:
      exclude: [".integration_tests/"]

  # the body this loop wrote, corrected against the rules this repository states for one. The
  # brief carries them only on a pass that starts a model, so the commonest run (green, no
  # thread waiting, the diff already read) still stops before the model and costs nothing.
  update-pull-request:
    max: 1
    target: "${{ github.event.issue.number || inputs.pr_number }}"
    # the title is dispatch's and is not this pass's to move; `replace` because a body is
    # rewritten whole or not at all.
    title: false
    body: true
    operation: replace
    # the body already carries the footer dispatch wrote; a second one would be added on every
    # pass that touches it.
    footer: false
---

# review

A pull request this loop authored is in front of you. Read the brief: it says whether a check is failing, a reviewer is waiting, or nobody has yet read what the change does. Repair what it names, or read the diff and report what you find, or make no edits at all. Nothing else is yours to do.
