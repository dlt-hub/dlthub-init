---
# review: reads CI on a pull request the loop opened, repairs it or lets it stand, then
# requests a human reviewer.
#
# `review.lock.yml` beside it is the same workflow as GitHub runs it. Edit both in
# dlt-hub/engineering-agent-loop: editing either here stops the workflow running.
inlined-imports: true

run-name: "review #${{ github.event.issue.number || inputs.pr_number }}"

# no event on a pull request starts this: such a run leaves a check run on the head per job,
# and this has seven. The two dispatchers pass the number instead
on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: The pull request to review
        required: true
        type: string
  issue_comment:
    types: [created]
  # both write before this stage has checked whether the commenter may ask for anything
  reaction: none
  status-comment: false
  # a pass is dispatched by a bot, and neither bot is a collaborator here
  roles: all

  needs: [event_filter]

  permissions:
    actions: write
    checks: read
    contents: read
    pull-requests: write

  # the compiler drops this job's condition once a later job reads one of its outputs, so
  # the first step repeats the filter
  steps:
    - name: Resolve the profile before the pass starts
      id: profile
      if: >-
        github.event_name != 'issue_comment'
        || (github.event.issue.pull_request != null
            && (startsWith(github.event.comment.body, '/retry')
                || startsWith(github.event.comment.body, '/agent review'))
            && contains(github.event.issue.labels.*.name, 'agent:authored'))
      uses: dlt-hub/engineering-agent-loop/.github/actions/profile@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        github-token: ${{ secrets.GITHUB_TOKEN }}
        unclaimed: skip

    # a failed step in a green job, so the run stops without being reported as broken
    - name: Skip a pull request no profile claims
      id: claimed
      if: steps.profile.outcome == 'success' && steps.profile.outputs.profile == ''
      continue-on-error: true
      run: |
        echo "::notice::no profile in this repository claims the files this pull request changes."
        echo "There is nothing to review, so activation is skipped and no job after it runs."
        exit 1

    - name: Ask whether this pull request is one this loop owns
      id: scope
      if: steps.profile.outcome == 'success' && steps.profile.outputs.profile != ''
      uses: dlt-hub/engineering-agent-loop/.github/actions/scope-gate@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        profile: ${{ steps.profile.outputs.profile }}
        github-token: ${{ secrets.GITHUB_TOKEN }}

    - name: Skip a pull request this loop does not own
      id: owned
      if: steps.scope.outcome == 'success' && steps.scope.outputs.stop == 'true'
      continue-on-error: true
      run: |
        echo "::notice::this pull request is not one this loop reviews."
        echo "Activation is skipped and no job after it runs. The reason is on the step above."
        exit 1

    # not on a comment: `/retry` resets the budget a flake would have spent
    - name: Re-run a failing check once before the pass reads it
      id: rerun
      if: >-
        github.event_name != 'issue_comment'
        && steps.profile.outcome == 'success'
        && steps.profile.outputs.profile != ''
        && steps.owned.outcome != 'failure'
      continue-on-error: true
      uses: dlt-hub/engineering-agent-loop/.github/actions/rerun-checks@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        profile: ${{ steps.profile.outputs.profile }}
        github-token: ${{ secrets.GITHUB_TOKEN }}

    # last, so a comment the gates above stopped stays silent. Write access is read from the
    # API. The comment's `author_association` reports a different value to each reader, and
    # calls an organisation member whose membership is private a collaborator.
    #
    # no `id:`: the compiler turns one into a job output, and activation must not be gated
    # on a failed reaction
    - name: Acknowledge the comment this pass was started by
      if: >-
        github.event_name == 'issue_comment'
        && steps.profile.outcome == 'success'
        && steps.profile.outputs.profile != ''
        && steps.owned.outcome != 'failure'
      continue-on-error: true
      env:
        GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        # this job has no checkout, so `gh` cannot resolve the repository without it
        GH_REPO: ${{ github.repository }}
        COMMENT: ${{ github.event.comment.id }}
        ACTOR: ${{ github.event.comment.user.login }}
      run: |
        set -euo pipefail
        PERMISSION=$(gh api "repos/$GH_REPO/collaborators/$ACTOR/permission" --jq .permission \
          || echo none)
        case "$PERMISSION" in
          admin|maintain|write) ;;
          *) echo "::notice::$ACTOR has $PERMISSION access here; this comment is not acknowledged."
             exit 0 ;;
        esac
        gh api --silent -X POST "repos/$GH_REPO/issues/comments/$COMMENT/reactions" \
          -f content=eyes

jobs:
  event_filter:
    runs-on: ubuntu-slim
    if: >-
      github.event_name != 'issue_comment'
      || (github.event.issue.pull_request != null
          && (startsWith(github.event.comment.body, '/retry')
              || startsWith(github.event.comment.body, '/agent review'))
          && contains(github.event.issue.labels.*.name, 'agent:authored'))
    steps:
      - run: echo "this event is one this loop answers"

# a pass counts its own attempts, so two runs on one pull request must not overlap
concurrency:
  job-discriminator: ${{ github.run_id }}
  group: review-${{ github.event_name == 'issue_comment' && ((startsWith(github.event.comment.body, '/retry') || startsWith(github.event.comment.body, '/agent review')) && contains(github.event.issue.labels.*.name, 'agent:authored') && github.event.issue.number || format('inert-{0}', github.run_id)) || inputs.pr_number }}
  cancel-in-progress: false

if: >-
  (github.event_name != 'issue_comment'
    || (github.event.issue.pull_request != null
        && (startsWith(github.event.comment.body, '/retry')
            || startsWith(github.event.comment.body, '/agent review'))
        && contains(github.event.issue.labels.*.name, 'agent:authored')))
  && needs.pre_activation.outputs.claimed_result != 'failure'
  && needs.pre_activation.outputs.owned_result != 'failure'

imports:
  - dlt-hub/engineering-agent-loop/workflows/stages/review.md@059f1e2b0be549197be28b022d4a984370b47f51

permissions:
  actions: read
  checks: read
  contents: read
  issues: read
  pull-requests: read

timeout-minutes: 25

pre-agent-steps:
  - name: Gate a comment before the agent starts
    uses: dlt-hub/engineering-agent-loop/.github/actions/retry-gate@059f1e2b0be549197be28b022d4a984370b47f51
    with:
      pr: ${{ github.event.issue.number || inputs.pr_number }}
      github-token: ${{ secrets.GITHUB_TOKEN }}
      # comment text reaches a script as an argument, never as shell
      comment-body: ${{ github.event.comment.body }}
      comment-actor: ${{ github.event.comment.user.login }}

  - name: Check out the pull request branch
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      REVIEW_PR: ${{ github.event.issue.number || inputs.pr_number }}
    run: |
      BRANCH=$(gh pr view "$REVIEW_PR" --repo "$GITHUB_REPOSITORY" --json headRefName --jq .headRefName)
      git fetch origin "pull/$REVIEW_PR/head"
      git checkout -B "$BRANCH" FETCH_HEAD

  - name: Resolve the profile from the pull request
    id: profile
    uses: dlt-hub/engineering-agent-loop/.github/actions/profile@059f1e2b0be549197be28b022d4a984370b47f51
    with:
      pr: ${{ github.event.issue.number || inputs.pr_number }}
      github-token: ${{ secrets.GITHUB_TOKEN }}

  - name: Assemble the review brief
    id: brief
    uses: dlt-hub/engineering-agent-loop/.github/actions/review-brief@059f1e2b0be549197be28b022d4a984370b47f51
    with:
      pr: ${{ github.event.issue.number || inputs.pr_number }}
      profile: ${{ steps.profile.outputs.profile }}
      github-token: ${{ secrets.GITHUB_TOKEN }}
      # acted on by this run, so it comes off the event rather than the state comment
      comment-body: ${{ github.event.comment.body }}
      comment-actor: ${{ github.event.comment.user.login }}

  - name: Hand the check rollup to the verdict
    uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
    with:
      name: review-pr-view
      path: /tmp/agent-loop/pr-view.json
      retention-days: 1

  # no model is called. It exits non-zero because a skipped job would take the verdict, the
  # label and the reviewer request with it, so a red run here is expected
  - name: Stop before the model when there is nothing for it to do
    if: >-
      steps.brief.outputs.work != 'repair'
      && steps.brief.outputs.work != 'feedback'
      && steps.brief.outputs.work != 'review'
      && steps.brief.outputs.work != 'final-review'
    env:
      WORK: ${{ steps.brief.outputs.work }}
    run: |
      echo "::notice::brief says work=$WORK; stopping before inference."
      echo "The verdict, the risk label and the reviewer request still run. A failed job here is"
      echo "the correct outcome: it is how they are reached without paying for a model."
      exit 1

# an artifact rather than a safe output: declaring `add-comment` would put
# `permission-issues: write` back on the conclusion job's token
post-steps:
  - name: Hand what the reviewing pass found to the verdict
    if: always()
    uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
    with:
      name: review-findings
      path: /tmp/gh-aw/agent/review-findings.md
      if-no-files-found: ignore
      retention-days: 1

safe-outputs:
  # each would otherwise file an issue in this tracker
  report-failure-as-issue: false
  missing-tool:
    create-issue: false
  report-incomplete:
    create-issue: false
  report-failed-jobs: false

  threat-detection:
    # nothing to scan when the only output is an incomplete result or a `noop`
    enabled: ${{ (needs.agent.outputs.output_types != '' && needs.agent.outputs.output_types != 'report_incomplete' && needs.agent.outputs.output_types != 'noop') || needs.agent.outputs.has_patch == 'true' }}

    engine:
      model: claude-sonnet-5

    # without this the scanner logs every run it warns on to an issue in this tracker
    report-as-issue: false

    # warns rather than blocks: blocking would take the verdict with it

  steps:
    # the run's own proxy is denied by design; the notice otherwise asks for it to be allowed
    - name: Drop the api-proxy's own denials from the firewall notice
      uses: dlt-hub/engineering-agent-loop/.github/actions/firewall-notice@059f1e2b0be549197be28b022d4a984370b47f51

    # a missing rollup reads as a hand-over, so this may fail without failing the job
    - name: Take the check rollup from the agent job
      continue-on-error: true
      uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
      with:
        name: review-pr-view
        path: /tmp/agent-loop

    - name: Take the agent's transcript from the agent job
      continue-on-error: true
      uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
      with:
        name: agent
        path: /tmp/agent-transcript

    - name: Take what the reviewing pass found from the agent job
      continue-on-error: true
      uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
      with:
        name: review-findings
        path: /tmp/agent-findings

    # the loop's App, which the model never holds a token for. It cannot write contents
    - name: Generate an App token for the verdict
      id: verdict-app-token
      uses: actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510 # v3.3.0
      with:
        client-id: ${{ vars.AGENT_LOOP_APP_CLIENT_ID }}
        private-key: ${{ secrets.AGENT_LOOP_APP_PRIVATE_KEY }}
        repositories: ${{ github.event.repository.name }}
        permission-actions: write
        permission-issues: write
        permission-pull-requests: write
        permission-contents: read

    - name: Resolve the profile from the pull request
      id: profile
      uses: dlt-hub/engineering-agent-loop/.github/actions/profile@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        github-token: ${{ steps.verdict-app-token.outputs.token }}

    - name: Gate the repair patch against the target profile
      if: contains(needs.agent.outputs.output_types, 'push_to_pull_request_branch')
      uses: dlt-hub/engineering-agent-loop/.github/actions/path-gate@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        profile: ${{ steps.profile.outputs.profile }}

    - name: Apply the verdict
      uses: dlt-hub/engineering-agent-loop/.github/actions/verdict@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        bot: ${{ steps.verdict-app-token.outputs.app-slug }}[bot]
        github-token: ${{ steps.verdict-app-token.outputs.token }}
        profile: ${{ steps.profile.outputs.profile }}
        ref: ${{ github.event.repository.default_branch }}
        comment-body: ${{ github.event.comment.body }}
        comment-actor: ${{ github.event.comment.user.login }}
        # anything but `true` means the scan dropped the patch
        detection-success: ${{ needs.detection.outputs.detection_success }}
        detection-reason: ${{ needs.detection.outputs.detection_reason }}
        findings: /tmp/agent-findings/review-findings.md
        # it writes no footer a later pass could read this off
        agent-aic: ${{ needs.agent.outputs.aic }}
        detection-aic: ${{ needs.detection.outputs.aic }}
        model: ${{ env.GH_AW_ENGINE_MODEL }}

    # a `/retry` makes no edits, so it must not move the label or the reviewer
    - name: Apply the risk tier
      if: >-
        github.event_name != 'issue_comment'
        || startsWith(github.event.comment.body, '/agent review')
      uses: dlt-hub/engineering-agent-loop/.github/actions/apply-risk@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        profile: ${{ steps.profile.outputs.profile }}
        github-token: ${{ steps.verdict-app-token.outputs.token }}

    - name: Nominate a reviewer
      if: >-
        github.event_name != 'issue_comment'
        || startsWith(github.event.comment.body, '/agent review')
      uses: dlt-hub/engineering-agent-loop/.github/actions/nominate-reviewer@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        pr: ${{ github.event.issue.number || inputs.pr_number }}
        bot: ${{ steps.verdict-app-token.outputs.app-slug }}[bot]
        profile: ${{ steps.profile.outputs.profile }}
        github-token: ${{ steps.verdict-app-token.outputs.token }}

    # narrower than the other two stages': a green agent job producing nothing but an
    # incomplete result is this workflow's free pass
    - name: Say on the pull request that this run did not finish
      if: needs.agent.result == 'failure'
      uses: dlt-hub/engineering-agent-loop/.github/actions/failure-notice@059f1e2b0be549197be28b022d4a984370b47f51
      with:
        number: ${{ github.event.issue.number || inputs.pr_number }}
        stage: review
        agent-result: ${{ needs.agent.result }}
        require-signal: 'true'
        github-token: ${{ steps.verdict-app-token.outputs.token }}
        engine-timeout: ${{ needs.agent.outputs.agentic_engine_timeout }}
        inference-access-error: ${{ needs.agent.outputs.inference_access_error }}
        model-not-supported-error: ${{ needs.agent.outputs.model_not_supported_error }}
        mcp-policy-error: ${{ needs.agent.outputs.mcp_policy_error }}
        ai-credits-rate-limit-error: ${{ needs.agent.outputs.ai_credits_rate_limit_error }}
        invocation-cap-exceeded: ${{ needs.agent.outputs.invocation_cap_exceeded }}
        http-400-response-error: ${{ needs.agent.outputs.http_400_response_error }}
        max-cache-misses-exceeded: ${{ needs.agent.outputs.max_cache_misses_exceeded }}
        shell-expansion-guard-rejected: ${{ needs.agent.outputs.shell_expansion_guard_rejected }}
---

# review
