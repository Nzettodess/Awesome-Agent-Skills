---
name: ax-extract-workflow
description: Reconstruct the workflow behind a past artifact - "what made X work" / "extract workflow from <date|sha>" / "how did we ship Y". Uses ax to find relevant sessions and narrate the ordered skill arcs that produced the result. Use when the user asks how a specific artifact, feature, PR, or result was produced.
role: framing
---

# ax:extract-workflow - reconstruct the recipe behind a shipped artifact

Given a deliverable such as a demo, PR, or feature, this skill answers:
what skills, in what order, produced it? It resolves an anchor, windows the
relevant ax sessions, and narrates the ordered skill arcs in plain text.

Assumes `ax` (`axctl`) from <https://github.com/Necmttn/ax> is on PATH and
the local SurrealDB is running. If `ax sessions here` fails with a connection
error, tell the user to run `scripts/db-start.sh` and stop.

## When to fire

Use only on explicit reconstruction triggers:

- "what made <X> work" / "how did we ship <Y>"
- "extract workflow from <date>" / "extract workflow from <sha>"
- "what was the workflow around <topic>"
- "reconstruct the recipe for <artifact>"
- "show me how I built <feature>"

Do not fire on generic "what did I do today" or "show recent activity".
That is `ax sessions here` territory, not this skill.

## Step 1 - resolve the anchor

Decide one of four modes based on what the user gave you:

| User said | Mode | Action |
| --- | --- | --- |
| commit sha, full or short | sha | use it directly |
| date, YYYY-MM-DD | date | use `ax sessions around <date>` |
| topic / feature / artifact name | topic | use `ax recall "<topic>" --sources=commit --json` to find candidate shas |
| "this repo, recently" | pwd | use `ax sessions here --days=14` |

For topic mode, pick the most relevant sha and continue in sha mode. If
results are ambiguous, ask the user to pick one before continuing.

## Step 2 - window the sessions

Pick the right command for the resolved anchor:

```bash
ax sessions near <sha> --json
ax sessions around <date> --days=3 --json
ax sessions here --days=14 --json
```

Pick the most relevant sessions from the JSON, defaulting to five. Bias toward
sessions with high turn counts and files related to the artifact.

## Step 3 - inspect each session

For each picked session:

```bash
ax sessions show <id> --json
ax sessions show <id> --by-role
```

Read the `top_skills`, `children`, and `agent_delegations` arrays. Use
`agent_delegations` for delegation context. If a child session looks central to
the artifact, drill in with `children[].session_id`:

```bash
ax sessions show <id> --expand=<child-session-id>
ax sessions show <id> --all
```

## Step 4 - narrate

Write everything inline. Do not create files.

### Ordered skill arc

Lead with the framing skill that opened the work, then execution skills, then
verification. For each skill, name it and write one line on what it produced.

Example:

```text
1. brainstorming -> defined the workflow extraction problem
2. writing-plans -> turned grilled questions into a plan
3. subagent-driven-development -> executed the plan with review gates
4. verification-before-completion -> checked the finished artifact
```

### Key decisions

Pull two to four turn excerpts where the user steered the work. Use recall for
targeted evidence:

```bash
ax recall "<keyword>" --json
```

Quote one line per decision and cite the session id.

### Reproducer brief

If the user asks for a reusable recipe, summarize the skills, the order, and
the key steering inputs in one paragraph.

## Output contract

Keep the answer in chat. Do not create files under `.ax/tasks/` or anywhere
else. Do not modify the repo. This is a read-only, reconstruction-focused
skill.
