# <PROJECT NAME>

<What this project is, in one or two lines.>

**Confidential:** <yes / no> · **Working language:** <prose language; notes and comments in ___>

---

## Any AI working here: read `START-HERE.md` first

It has the workflow. State lives in `context/`, not in conversations — nothing carries over
between sessions except those files.

## Where things are

```
<folder tree — one line per entry, only what an AI needs to navigate>
```

| If the task is | Read |
|---|---|
| Anything at all | `context/current-state.md`, then `context/handoff.md` |
| Checking what is already settled | `context/decisions.md` |
| Quoting any number | `context/verified-facts.md` |
| <project-specific task> | <path> |

## Commands

Write the real invocation, not the name of the tool.

```bash
# build:
# test:
# lint:
# run:
python3 context/tools/ctx_check.py     # checks the context files are consistent
```

## Rules for this project

- Never invent a fact or a number — trace it, or mark it UNVERIFIED.
- Never put keys, passwords, or personal data in `context/` — these files get pasted into chat
  windows and synced to vendors by design.
- <project-specific: coding style, writing conventions, what must never be changed>

## Conventions

- <how to patch code, how to name things, formatting, anything a new contributor would get wrong>
