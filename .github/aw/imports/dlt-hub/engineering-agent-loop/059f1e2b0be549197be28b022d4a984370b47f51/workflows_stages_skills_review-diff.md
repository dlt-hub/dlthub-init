# Skill: read the diff on one pull request

This is the pass that answers "does the change do what was asked for". It runs once per head, on a pull request whose checks are green and whose reviewer threads are all answered, and it is the only pass in this loop that reads the diff rather than a failing check or a reviewer's request.

Your brief says which pass you are. If it opens `# Review brief — reading the diff`, this skill is the one to follow and the repair skill beside it applies only to the patch you write. If it opens `# Review brief`, this skill is not your business: follow that one.

You produce two things: a patch repairing what you can, and a file naming what you could not. Both are described below, and the file is written whether or not there is a patch. Where your brief carries **The pull request body**, that section says what to do with it: correct it in one `update_pull_request`, whose rules are in `skills/review-repair.md`, or report what is wrong and make no call.

A brief saying **Report only. Make no edits and produce no patch.** means the second of those and no patch either. The repair budget on that pull request is spent and it is going to a person whatever you find, so every result is a finding and nothing below about writing a patch or rewriting the description applies.

## Read the brief first

`/tmp/gh-aw/agent/brief.md` holds everything the workflow gathered before you started:

- the pull request, its branch and its head commit;
- what it was asked to do — the spec sub-issue a person edited before approving the build, or the ticket itself where there is no spec;
- the whole diff against the base;
- the files it changed;
- the `allow` and `deny` globs from the profile, deny winning over allow;
- the pull request description and this repository's rules for one, where it states any;
- the dimensions you judge against, appended at the end by this repository's profile.

The branch is checked out, so you can read any file in it. Read the ones the diff touches and the ones it should have touched: a component's story, the e2e case that reaches a route, the file a user-facing string belongs in. **Every path you name in a finding is a path you read.** A finding that guesses at a file's contents is worse than no finding, because a reviewer has to go and check it.

## Judge against the dimensions, all of them, every pass

The dimensions are the profile's, and they are at the end of your brief. They belong to the repository the change lands in, not to this loop, so do not substitute your own and do not skip one because the diff looks small. Where a dimension names a rules file in this repository, read that file — it is in the checkout.

Report one line per dimension, including the ones that found nothing. A dimension you say nothing about reads as a dimension nobody applied.

## Repair what you can

One patch, inside the `allow` globs and nothing under a `deny` glob. The same gate that runs on dispatch runs on your patch: a denied path is a red run and no push.

- Repair the smallest thing that answers the finding. Do not reformat, rename or tidy anything the finding did not name.
- **Leave the branch green.** Every check on this head passes right now. You cannot run them — there is no package manager and no test runner in this stage's toolset, and that is deliberate — so reason the change out from what you can read. A patch that breaks a check turns the next pass into a repair pass, which is told the branch is wrong and the check is right, so the shortest fix available to it is to undo what you just did.
- If a repair needs a judgement that is not yours — a product decision, a change outside the allowed paths, a rewrite of the test the ticket asked for — do not make it. Report it as a finding.
- Do not add dependencies or configuration.
- A description short of the rules quoted in your brief is corrected in the same pass, in one `update_pull_request`, where that section asks for a correction. It is not a patch and buys no pass.

A finding you repaired is not a finding. Describe it under `## Repaired` and leave it out of `## Findings`.

## Write what you found

Write `/tmp/gh-aw/agent/review-findings.md`, beside the brief you read. It is the only account of this pass anybody sees: the workflow puts it in the state comment on the pull request and reads one thing out of it, which is whether a `[critical]` line is left.

The four sections, in this order and with these exact headings:

```markdown
## Verdict

One sentence: what this change does and whether it does what was asked for.

## Dimensions

- <dimension name> — what you checked and what you found, one line.

## Repaired

- <what the patch changes, and which finding it answers>

## Findings

- [critical] `path/to/file.ts:42` — what is wrong. Fix: what should happen instead.
- [warning] `path/to/other.tsx` — what is wrong. Fix: what should happen instead.
```

Write `- none` under `## Repaired` when there is no patch, and `- none` under `## Findings` when nothing is left. Both are results and both are worth reading.

### The three severities

- **`[critical]`** — the change is wrong, or it breaks a rule this repository states, and you did not repair it. It hands the pull request to a person: the workflow applies `agent:needs-human` and the verdict stops being a pass. Use it for a regression, a rule in the profile's dimensions the change breaks, acceptance criteria the change does not meet, a deleted or weakened test, and anything you were about to repair but could not.
- **`[warning]`** — worth a reviewer's attention and not a reason to stop. It changes no verdict. Use it where you repaired what you could and something is left over, or where you are not certain enough to call it critical.
- **`[nit]`** — a preference. It changes nothing and costs a reviewer a line to read.

Tag every line under `## Findings` with exactly one of them, first thing on the line. An untagged line is counted as nothing.

**A `[critical]` you already fixed must not be under `## Findings`.** Quoting it there as context hands the pull request to a person for a problem that no longer exists, which is the one failure this file exists to prevent.

## What is not yours

- **Do not decide the verdict.** You report; the workflow decides. It reads the tags, the patch and the budgets, and it writes the state comment, the risk label and the reviewer request from them.
- **No comment, no label, no review.** A second account of this pass would only be a chance for the two to disagree.
- Do not reopen the risk tier, the budgets, or whether this pull request should have been built. Those were settled before you started.
- **Refusing is finishing.** If you cannot read the diff at all, write the file saying so in one line and produce no patch. Keep `report_incomplete` for a pass that genuinely broke — a turn budget that ran out mid-review, a file the brief named that you could not read.

## Rules

- Every path you name is a path you read.
- No preamble, no sign-off. The file is the output.
