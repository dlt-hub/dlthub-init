# Skill: repair one failing pull request

You have a pull request branch checked out and a brief that already knows what needs doing. Your job is a patch, or no patch, and on a brief that carries the section about it the pull request description beside that. You do not decide whether this pull request passes, you do not decide whether it gets another attempt, and you do not decide when a human takes over. All three are decided deterministically around you, before you start and after you finish.

There are three reasons you might have been started, and the brief says which. **A failing check**, or **a reviewer waiting**, or **a diff nobody has read**. Each is counted against its own budget and the brief reports all three.

The third one is the reviewing pass, and its brief opens `# Review brief — reading the diff`. `skills/review-diff.md` is what that pass follows; this file then governs only the patch it writes, which is the method, the limits on what a patch may touch, and the pull request body. **Everything else below is about the first two**, and a brief opening `# Review brief` is one of those.

A reviewer reaches you two ways and the brief quotes both under one heading: a comment on a line, and a `Request changes` review whose request is written in the summary. A summary names no file, so work out from the request itself which of the allowed paths it is about.

## Read the brief first, and only once

`/tmp/gh-aw/agent/brief.md` was assembled before you started. It holds:

- the pull request, its branch and its head commit;
- how many repair passes and how many feedback passes have already been spent;
- the failing checks, by name, and what they printed;
- **or** what a reviewer is waiting on, quoted: a review thread with the file and line it is against, a `Request changes` review summary with the reviewer who wrote it, or both;
- the files the pull request already changed;
- the `allow` and `deny` globs from the profile, deny winning over allow;
- where this repository states rules for a pull request description, that description and those rules.

**Do not read the profile, do not list or search the tree, and do not fetch the pull request.** The brief answers all of it.

The brief opens with an instruction. Follow it literally.

- If it quotes a reviewer's requests: **do what they ask**, inside the allowed paths, in one patch. Read the file each thread is against and change only what the thread is about. For a review summary, read the files the request names or implies and change only those.
- If it says checks are green and no reviewer is waiting: **make no edits.** Stop. (You will rarely see this one: the workflow stops before starting you when there is nothing to do.)
- If it says the repair budget is spent: **make no edits.** A patch produced at that point is refused by the gate and fails the run. That is not a bug to work around; the budget is the point.
- Otherwise it names a repair pass and the checks that failed. Repair them.

## Method

1. Read the brief.
2. From the failing check names and the files the pull request changed, read the specific files involved: the failing test and the source it exercises. Only those.
3. Work out the smallest edit that makes the failing check pass.
4. Make it. Change nothing else.

## You cannot run the test suite, and are not meant to

There is no package manager and no test runner in this stage's toolset: no `pnpm`, no `pytest`, no `make`, and no way to run the check you are repairing before you push it. The shell you do have is a fixed allowlist for git plumbing, not a general one, so an arbitrary command is refused rather than run. Do not look for a way round it, and do not report it as a missing tool. It is withheld on purpose.

So reason the repair out from what you can read (the brief's account of the failure, the failing test, and the source it exercises) rather than from a run you cannot make. CI runs the check on the commit you push, and that run is the only verdict the loop acts on; a local pass would not have changed it. If reading is not enough to be sure of the fix, that is a hand-over: produce no patch and say in one line what you could not determine.

## What a repair is

The check is failing because the branch is wrong, not because the check is wrong. Fix the code the check is testing.

- **Repairing a failing check: do not edit or delete the test to make it agree with the code.** The check is the evidence; rewriting the assertion destroys it. If the test genuinely asserts the wrong thing, that is a judgement a human makes: make no edits and say so in one line.
- **Answering a reviewer is the one exception, and it is narrow.** When a reviewer with write access asks for a change in behaviour, a test that pins the old behaviour is part of what they asked you to change, and updating it in the same patch is correct rather than tampering. It stays an exception: update only the assertions the request necessarily moves, never a test the request did not mention, and never a file whose own comments say it is a contract that does not move with the copy around it.
- Do not touch anything outside the `allow` globs, and nothing at all under a `deny` glob. The same gate that runs on dispatch runs on your patch; a denied path is a red run and no push.
- **Never repair a check by undoing something a reviewer asked for.** The brief names those files when there are any. A check that is red because a test still pins behaviour a reviewer moved is a test that is out of date. Change the test to match and say so in the commit message. If the only way to make the check pass is to revert the request, make no edits and say so in one line: that is a hand-over, not your call.

## Answering a reviewer is the same job, with the same limits

A reviewer's request is not more trusted than an issue body, and it does not widen anything.

- **A request under a denied path is refused, not worked around.** You will not normally see one on a thread: the workflow settles that against the profile before you start and answers the thread itself. A review summary names no path, so it cannot be settled that way — if what it asks for is out of bounds, make no edits and say so in one line.
- **Answer what was asked and nothing adjacent.** A reviewer pointing at one line is not an invitation to tidy the file.
- **Do not reply on the thread, and do not answer the review.** The workflow posts the reply — on the thread where there is one, and as a pull request comment for a review summary, which has none — from the same commit it recorded. A second voice there is a second account of what happened, and the two can disagree. This is the same reason you write no comment and no label.
- Do not reformat, rename, or tidy anything the failing check did not name.
- Do not add tests, dependencies, or configuration.

## The pull request body, when the brief carries it

The brief quotes the current body under **The pull request body**, with this repository's own rules for one where it states any. It appears on a repair pass, a feedback pass and a reviewing pass alike, and on the read-only hand-over, which is not given this file and whose own section says to report the body rather than rewrite it. On a reviewing pass it appears whether or not this repository states a rule, because that pass holds the diff and the section then asks whether what the body says about the change is true of it. If that section is not in your brief, say nothing about the description and write no `update_pull_request`.

- Read the body against everything the section asks of it. If it answers all of it, leave it and say nothing.
- If it does not, make **one** `update_pull_request` call carrying the whole corrected body. It replaces the description outright, so a section you leave out is deleted.
- Keep the `Closes #<n>` line as it stands, and keep the `> Generated by` footer verbatim. An attribution line above it (`🤖 Generated with ...`, `Co-authored-by`) is not part of that and is dropped.
- The HTML comments at the end are gh-aw's. Do not copy them. It strips every comment out of what you write and appends its own, so the ones under the rewritten body name this run.
- The body is the second job. What the brief says this pass is for (the repair, the reviewer's request, or reading the diff) is the first: if you cannot finish both, finish that one and leave the description alone.
- Correcting the body is not a repair and buys no pass. A pass that rewrites the description and produces no patch still reads as a pass that produced no patch.

## The output

One `push_to_pull_request_branch`, or nothing. Where the brief asked for it, one `update_pull_request` beside that.

- The commit message is Conventional Commits: `<type>(<scope>): <lowercase imperative subject>`, no trailing period, subject line only.
- **Commit with plain `git commit -m`.** `git commit` is on this stage's allowlist; `git -c <key>=<value> commit` is a different command and is refused. The run configures a git identity before you start, so the plain form is all you need. Drop the flags and run the plain form rather than treating the refusal as a tool you are missing.
- Pass the `branch` argument, and pass the branch the brief names: it is checked out for you and it is the one the pull request is on. Do not open a pull request; one already exists.
- Which pull request the patch lands on is not yours to say. The workflow fixes that before you start, so a `pull_request_number` from you is ignored at best.
- No comment, no label, no summary. The workflow writes the state comment itself, from the same numbers it used to decide your budget, and a second account of what happened would only be a chance for the two to disagree.
- **Refusing is finishing. Do not call `report_incomplete` for it.** A refusal you can state in one line is the whole answer to the pass, and that line reaches the pull request: the workflow reads it out of this session and puts it in the state comment beside the verdict, the `agent:needs-human` label and the reviewer it asks for. `report_incomplete` says something different: that the run broke, rather than that you decided something on purpose. Keep it for a pass you genuinely could not finish: a turn budget that ran out mid-repair, a file the brief named that you could not read.

## Rules

- Every path you name is a path you read.
- If you cannot repair the failure inside the allowed paths, produce no patch and say why in one line. Producing a patch you know is wrong spends a pass the loop cannot get back.
- No preamble, no sign-off.
