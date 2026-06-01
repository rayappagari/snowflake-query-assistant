---
name: pr-review
description: Reviews pull requests for code quality. Use when reviewing PRs or checking code changes.
---

Review the current branch diff for code quality issues. Focus on:
- Correctness bugs and logic errors
- Security vulnerabilities (injection, auth issues, exposed secrets)
- Readability and naming clarity
- Unnecessary complexity or missed simplifications
- Missing edge case handling

Use `git diff main...HEAD` to get the full diff. For each finding, include the file, line number, severity (critical / warning / suggestion), and a one-line explanation. Group findings by severity. End with a short overall verdict: approve, approve with suggestions, or request changes.
