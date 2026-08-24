# ContextManager

**Drop-in project state so any AI continues where the last one stopped** — Claude, ChatGPT,
Gemini, Copilot, Cursor, or whatever ships next month. One folder, no dependencies.

Every AI session ends the same way: abruptly, and with no memory. Products don't share context,
two accounts on one product don't either, and no vendor's memory feature is visible to any other
vendor. The project folder is the only thing every AI can see — so that is where the state lives.

---

## Quick start

```bash
git clone https://github.com/<you>/ContextManager.git
./ContextManager/ai-context-kit/install.sh /path/to/your/project
```

Then open any AI in your project and say:

> **Read START-HERE.md and follow it.**

It asks whether you want a **full**, **targeted**, or **minimum** scan — quoting the token cost of
each, measured from your actual project — waits for your answer, then works one task at a time,
verifying each one and updating the files before starting the next.

Nothing existing is ever overwritten. Manual install works too: copy `START-HERE.md`, `AGENTS.md`
and `context/` into the project yourself. That is all the script does.

For an AI with no file access, paste this instead:

> I'm working on `<project>`. You have no file access, so I'll paste the context in and save your
> updates back. Follow the workflow in the first file. At the end, give me the exact updated text
> for `current-state.md` and `handoff.md`, plus a one-line log entry.
>
> \--- START-HERE.md --- `<paste>`
> \--- context/current-state.md --- `<paste>`
> \--- context/handoff.md --- `<paste>`

---

## Repo layout

```
ContextManager/
├── README.md              you are here
├── LICENSE                MIT
├── AGENTS.md              governs this repo — not a template
├── docs/
│   ├── STRATEGY.md        the full reasoning, vendor by vendor
│   └── TOKEN-BUDGET.md    where the tokens go, and how they were cut
└── ai-context-kit/        the payload — copy THIS folder into a project
```

Everything under `ai-context-kit/` is a template meant to be filled in per project. Everything
above it describes the repo. The docs deliberately live *outside* the kit: they are 50KB of prose
about the idea, and copying them into every project you install into would defeat the point.

---

## What's in the kit

| File | Job |
|---|---|
| `START-HERE.md` | The workflow every AI follows. The one file that makes this work. |
| `AGENTS.md` | The project's rules, layout, and commands. Fill in once. |
| `context/current-state.md` | What exists, what's done, what's in progress, what remains. |
| `context/handoff.md` | The single task in flight, its next action, and the files it needs. |
| `context/decisions.md` | What's settled (don't reopen) and what's waiting on you. |
| `context/session-log.md` | What happened, newest first, indexed and rotating. |
| `context/verified-facts.md` | Every number, with its source. Delete if the project has none. |
| `context/tools/ctx_check.py` | Checks the files stay consistent. Standard library only. |
| `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` | One-line stubs, so tools that auto-load their own filename get pointed at `START-HERE.md`. |

---

## What it costs to run

Measured, at roughly 4 characters per token. Run `--budget` for your own project's real number.

### Reading: what a session loads before it starts working

```
$ python3 context/tools/ctx_check.py --budget

   1,286  START-HERE.md
     143  context/handoff.md
     181  context/current-state.md
      62  context/decisions.md (index only)
     124  context/session-log.md (index only)
     335  AGENTS.md (first session only)
   ------
   1,796  every session
   2,131  first session on this project
```

That figure stays roughly flat as the project ages, which is the point. Two mechanisms hold it
there: `decisions.md` and `session-log.md` are read as **indexes** — the first 12 lines, ~60 tokens
each — and everything else is read only when the task calls for it. Nothing loads the whole
history just to answer "what was I doing?"

| | Tokens |
|---|---:|
| Empty kit, fresh install | ~1,900 |
| Project a few months in | ~1,800 |
| Worst case the caps allow | ~3,300 |

The caps are what make the last row possible. When a file outgrows its cap the checker warns, and
past 1.5x it errors — because a context file too big to load is a file that does nothing.

### Writing: what checkpointing costs

The kit asks you to update `handoff.md` during work rather than at the end. That is not "after
every action" — it is after each unit of work, after a decision, and before anything slow. Call it
5–10 writes in a working session.

| | Tokens |
|---|---:|
| One `handoff.md` checkpoint (targeted edit + tool result) | ~100–150 |
| Eight checkpoints in a session | ~1,000 |
| With a re-read before each write | ~2,000 |
| **Losing an unsaved session and re-deriving it** | **10,000–50,000** |

Spending 2,000 to insure against 30,000 is worth it even if the loss only happens one session in
ten — and usage limits and closed tabs are not rare.

Two things make it cheap. **Write frequency is inversely proportional to file size, by design:**

| File | Written | Cap |
|---|---|---:|
| `handoff.md` | Many times per session | 40 lines |
| `current-state.md` | Once per task | 60 lines |
| `decisions.md` | Only when something is decided | 120 lines |
| `session-log.md` | Once per session, appended | 80 lines |
| `verified-facts.md` | When a number appears | 250 lines |

The file that gets hammered is deliberately the smallest. And **edits must be targeted** — changing
three lines costs three lines, not a whole-file rewrite. If your tool rewrites files by default,
checkpointing costs several times more than the table above.

One caveat worth knowing: edits accumulate in the conversation and get re-sent on every subsequent
turn, so the true cost grows faster than checkpoints × 150. Prompt caching absorbs most of that,
not all of it.

Full analysis in [`docs/TOKEN-BUDGET.md`](docs/TOKEN-BUDGET.md).

---

## Requirements

**This installs nothing.** No `pip install`, no `npm install`, no downloads, no network access, no
background process, no configuration outside the project folder you point it at. It copies a
handful of Markdown files and one Python script. Deleting the files removes it completely.

| Needed for | What | Minimum |
|---|---|---|
| The kit itself | Nothing — it is Markdown | — |
| `context/tools/ctx_check.py` | Python, standard library only | **3.8** |
| `install.sh` | bash — or copy the files by hand instead | 3.2 |
| The pre-commit hook, and recovering from mistakes | git — optional but recommended | any |

**The Python script is optional.** The workflow works without it; the checker exists so nobody has
to remember the details it enforces.

The checker imports only `argparse`, `hashlib`, `json`, `re`, `sys`, `datetime`, and `pathlib` —
all built in. Nothing to install, nothing that breaks when a dependency updates.

**Versions.** Verified on Python 3.10, 3.11, 3.12, and 3.13 — identical output on all four. It uses
no syntax or library feature newer than 3.7, so 3.8 and 3.9 should work as well, though that is
inferred from the code rather than tested. Check yours with `python3 -V`.

**Platform notes.** Linux and macOS work as shipped, including macOS's built-in bash 3.2. On
Windows, `install.sh` needs Git Bash or WSL — without either, copy the files by hand and run the
checker as `py -3 context\tools\ctx_check.py`. With no Python at all, skip the checker; nothing
else depends on it.

---

## Check

```bash
python3 context/tools/ctx_check.py            # report
python3 context/tools/ctx_check.py --quiet    # problems only
python3 context/tools/ctx_check.py --budget   # what a session start costs, in tokens
python3 context/tools/ctx_check.py --json     # for CI or a hook
```

Exit `0` clean · `1` warnings · `2` errors.

It carries the discipline nobody should have to memorize: decisions left pending, more than one
task claimed as active, a session that died mid-task without checkpointing, a stale copy written
back over newer work, files outgrowing the point where they get read, a missing index, leaked keys,
the same fact drifting in two places, and references to files that no longer exist.

Worth wiring in:

```bash
echo 'python3 context/tools/ctx_check.py --quiet' >> .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## Why it's shaped this way

Read the files before acting, write them during the work rather than after, keep one task in flight
so the record stays honest, verify before claiming, and give every fact exactly one home so two
copies can't drift apart.

A few of the rules are worth their reasoning, which `START-HERE.md` no longer carries so that it
stays cheap to load:

**Why one task at a time.** Not tidiness. A session that did one thing can describe what it did; a
session that did four things and got interrupted leaves a record nobody can trust.

**Why the project wins over the notes.** Code, documents and data are the thing itself. The notes
are someone's description of it, and descriptions go stale. When they disagree, correct the notes —
never the project.

**Why the AI must ask before scanning.** A full scan of a large repository can exceed the context
window entirely, and the AI discovers this halfway through. It measures and quotes a number before
offering, so the choice is informed rather than a guess.

**Why re-reading is conditional.** The re-read rule protects against another session having written
in between. Working alone, re-reading a file you wrote four minutes ago is paying for insurance
against something that cannot happen. Working alongside another AI, another account, or through a
staged copy you push back later, it is what prevents silent data loss.

**Why decisions get their own file.** Re-litigating a settled question costs a conversation, not a
few hundred tokens — and a new AI with no memory of the discussion will happily reopen it.

The full reasoning, including the compatibility matrix and the recovery playbook, is in
[`docs/STRATEGY.md`](docs/STRATEGY.md).

---

## License

MIT — see [`LICENSE`](LICENSE).
