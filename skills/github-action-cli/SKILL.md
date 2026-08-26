---
name: github-action-cli
description: Inspect and update GitHub Actions dependencies with github-actions-cli. Use when asked to find workflow files, list referenced actions, check action versions, apply action-version updates locally or remotely, or summarize GitHub organization repositories with this CLI. Do not use for running or debugging workflow executions; use GitHub CLI gh for those tasks.
---

# GitHub Actions CLI

Use the `github-actions-cli` executable. The skill name is singular for discovery, but the package and executable are plural.

## Establish the target and capability

1. Resolve whether the target is a local repository path or an explicit `owner/repo`. Default to the current directory only when that matches the user's scope.
2. Check availability with `command -v github-actions-cli`. If it is absent, prefer a one-off `uvx github-actions-cli ...` invocation when `uvx` is available. Downloading or installing the package remains subject to the host's approval rules.
3. Check the installed interface with `github-actions-cli --help` and the relevant subcommand's `--help`. Released versions differ; use the installed help when it conflicts with examples below.
4. Use the latest documented syntax unless the installed version says otherwise. The current package requires Python 3.10 or newer.

## Authentication

The CLI queries the GitHub API, so provide a token through the `GITHUB_TOKEN` environment variable. Do not print the token, embed it in a command, commit it, or put it in `--github-token` unless the execution environment supplies that argument without exposing it.

Read-only checks need access to the repositories being inspected. Updating a remote repository needs content/commit permissions as well. Treat missing or insufficient authentication as a blocker to report, not a reason to request or broaden token permissions automatically.

## Choose the narrowest operation

List workflow files:

```bash
github-actions-cli --repo . list-workflows
github-actions-cli --repo owner/repo list-workflows
```

List action references from one workflow:

```bash
github-actions-cli --repo . list-actions .github/workflows/ci.yml
```

Check for outdated action versions without changing files:

```bash
github-actions-cli --repo . update-actions
github-actions-cli --repo owner/repo update-actions
```

Add `--major-only` before the subcommand when the user wants only major-version changes:

```bash
github-actions-cli --repo . --major-only update-actions
```

Increase logging with `-v` or `-vv` only when diagnosing the CLI itself. Avoid verbose output when it could reveal repository metadata unnecessarily.

Analyze repositories across the authenticated user's organizations only when the user requests organization-wide inventory:

```bash
github-actions-cli analyze-orgs
github-actions-cli analyze-orgs --exclude ignored-org
```

This command emits CSV. Preserve the header and parse it as CSV rather than splitting on commas manually.

## Apply updates safely

Run a read-only `update-actions` check first and summarize the proposed version changes. Then:

- For a local target, use `github-actions-cli --repo . update-actions --update` only when the request authorizes editing workflow files. Inspect the resulting Git diff, ensure only intended workflow references changed, and run the repository's relevant validation.
- For an `owner/repo` target, `--update` writes and commits directly to the remote repository. Do not run it without explicit authorization for that repository and remote commit. Use `-commit-msg "..."` after the subcommand when a custom message is requested.
- Do not combine an organization-wide scan with automatic updates. Select and authorize each remote repository separately.
- Do not assume a version bump is compatible merely because the CLI found it. Review release notes or migration guidance for major upgrades when the task requires applying them.

Remote example, after authorization:

```bash
github-actions-cli --repo owner/repo update-actions --update -commit-msg "chore(ci): update actions"
```

## Report the result

State the repository and scope checked, workflows/actions found, available updates, whether files or a remote commit changed, and any authentication or compatibility caveat. For local edits, include the validated diff summary. Never reproduce secrets or credential-bearing command lines.

Authoritative package reference: https://pypi.org/project/github-actions-cli/
