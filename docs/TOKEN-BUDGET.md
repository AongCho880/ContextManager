# Making the context kit cheaper to run

An analysis of where the AI context kit spends tokens, and seven changes ranked by measured
saving. Nothing here is implemented — this is the case for each change so you can pick.

Token figures are estimated at 4 characters per token. That is close enough to compare options
against each other, and every number below is measured from real files rather than guessed, except
where marked *(projected)*.

---

## 1. Where the tokens actually go

**An empty kit, freshly installed, before anyone has written a word:**

| File | Bytes | Lines | ~Tokens |
|---|---:|---:|---:|
| `START-HERE.md` | 10,419 | 232 | **2,605** |
| `AGENTS.md` | 1,491 | 51 | 373 |
| `context/current-state.md` | 905 | 41 | 226 |
| `context/handoff.md` | 1,051 | 40 | 263 |
| `context/decisions.md` | 1,075 | 45 | 269 |
| `context/session-log.md` | 478 | 18 | 120 |
| **Session-start total** | | | **~3,856** |

Two-thirds of that is the instruction file. Every session pays 2,605 tokens to be told how the
system works, before it learns anything about the project.

**The same kit on a project a few months in** — a simulated long-running project, with a
session-log grown to a few hundred entries:

| File | ~Tokens |
|---|---:|
| `START-HERE.md` | 2,605 |
| `context/session-log.md` | **4,217** |
| `AGENTS.md` | 374 |
| `context/verified-facts.md` | 221 |
| `context/current-state.md` | 181 |
| `context/handoff.md` | 127 |
| `context/decisions.md` | 128 |
| **Session-start total** | **~7,853** |

**And the ceiling the checker currently permits.** The soft caps in `ctx_check.py` allow 72,000
bytes across the five files before it warns — roughly **18,000 tokens**, plus START-HERE, for a
worst-case session start of about **20,600 tokens** spent before any work begins.

### The diagnosis in one line

The kit optimizes for a session being *fully informed*, and charges the full price at startup,
every time. Most of what it loads is not needed for the task at hand.

Three separate problems hide in that sentence, and they have different fixes: the instruction file
is re-read every session, the history files grow without bound, and everything is loaded eagerly
whether or not the task touches it.

---

## 2. Seven changes, ranked by measured saving

### 2.1 Tiered reading — load two files, not five

**Saving: ~1,200 tokens on a young project, ~4,000+ on an old one, growing over time.**

Step 2 of `START-HERE.md` currently tells every AI to read five files. Two of them are almost
never needed in full:

- `session-log.md` — history. A session needs the last two entries, not two hundred.
- `decisions.md` — a session needs to know *whether* something is pending and *what titles* are
  settled. It needs the full text of a settled decision only when it is about to touch that area.

Change the protocol to:

| Tier | Files | When |
|---|---|---|
| **Always** | `handoff.md`, and the top of `current-state.md` | Every session |
| **Once** | `AGENTS.md` | First contact with the project |
| **Index only** | `decisions.md`, `session-log.md` — first ~12 lines | Every session |
| **On demand** | Full `decisions.md`, older log entries, `verified-facts.md` | When the task calls for it |

The mechanism that makes "index only" work: give `decisions.md` and `session-log.md` a compact
index at the top — pending count, and a one-line-per-item list of titles and dates. A `head -12`
then answers "is there anything here I need?" for about 40 tokens instead of 4,000.

Measured on the simulated long-running project: startup drops from **7,853 to 440 tokens**, before
counting the START-HERE saving below.

### 2.2 Put START-HERE.md on a diet

**Saving: ~1,900 tokens per session, on every project, forever.**

Where its 2,605 tokens go:

| Section | ~Tokens | Share |
|---|---:|---:|
| Step 1 — scan level | 372 | 14.3% |
| The rules worth remembering | 366 | 14.0% |
| Decisions that need the user | 320 | 12.3% |
| Step 3 — write the Current State | 260 | 10.0% |
| Step 0 — access tier | 236 | 9.1% |
| Step 2 — understand what is there | 224 | 8.6% |
| Step 6 — verify | 186 | 7.2% |
| Step 4 — one task | 180 | 6.9% |
| Step 7 — update files | 155 | 5.9% |
| Preamble | 126 | 4.8% |
| Step 5 — do the work | 110 | 4.2% |
| Step 8 — first-run note | 69 | 2.7% |

No single section is bloated. The file is long because every step carries its justification — the
*why* alongside the *what*. That prose earns its place the first time a person reads it and is
dead weight on every subsequent machine read.

Split it: a one-screen operating card of about 60 lines carrying the procedure, the decision-block
template, and the five rules; and the reasoning moved into `README.md`, which AIs never load.
Roughly **650 tokens instead of 2,605** *(projected — the compressed version has not been
written)*.

Keep the decision-block template verbatim in the card. It is 12 lines and it is the one piece
where exact shape matters more than brevity.

### 2.3 Hard caps, roughly six times tighter

**Saving: caps the worst case at ~3,000 tokens instead of ~18,000.**

Current caps versus what the tiered model needs:

| File | Now | Proposed | Why |
|---|---:|---:|---|
| `AGENTS.md` | 80 lines | 50 | Rules and commands, nothing else |
| `current-state.md` | 150 | 60 | A picture, not an inventory |
| `handoff.md` | 80 | 40 | One task |
| `decisions.md` | 300 | 120 + archive | Settled decisions rotate out |
| `session-log.md` | 400 | 80 + archive | The last ~10 sessions |

Make them errors rather than warnings past 1.5x, so the file gets trimmed rather than tolerated.
A cap nobody enforces is a suggestion, and the current file sizes show what happens to
suggestions.

### 2.4 A rolling summary, so archived history is never re-read

**Saving: keeps 2.1's index cheap permanently, instead of degrading as the archive grows.**

Rotation currently moves old entries to `context/archive/` and leaves a pointer. But a session that
needs older context has to go read the archive, which is the expensive thing rotation was supposed
to avoid.

Fix: on every rotation, update a five-line **"Everything before `<date>`"** summary at the top of
`session-log.md` — what was built, what was decided, what turned out to be wrong. Costs ~60 tokens
to carry, and means the archive is for forensics only. Compaction, not deletion.

### 2.5 A per-task file list

**Saving: the difference between reading a directory and reading four files. Highly variable,
often the largest single win on a big codebase.**

Add to `handoff.md`'s front matter:

```yaml
files: [report/pdf.py, report/charts.py, tests/test_report.py]
```

The next session loads exactly those and stops. Today it re-derives which files matter by scanning
— which is precisely the work the previous session already did and threw away.

This is the same idea as the routing table in `AGENTS.md`, but per-task instead of per-project, and
it is the cheapest of these changes to implement.

### 2.6 Make the scan gate cost-aware

**Saving: prevents the single most expensive mistake the kit can make.**

The Full-versus-Minimum choice is good, but it asks the user to price something only the AI can
measure. "Full scan" on a 40-file project is fine; on a 4,000-file monorepo it will not fit in the
context window at all, and the AI will discover that halfway through.

Change Step 1 so the AI **measures first, then offers**: count files and bytes at the chosen root,
and state the estimate in the question — *"Full scan is roughly 340 files, ~120k tokens"* — so the
answer is informed. Where a full scan cannot fit, say so and propose a subsystem-by-subsystem
sweep instead of starting one that will fail.

Worth adding a third option while you are in there: a **targeted scan** — the files the task names,
plus what they import. Between the two current extremes, and the right answer most of the time.

### 2.7 Read-efficiency rules, and a `--budget` flag

**Saving: modest individually, compounding across a session.**

Six lines in the card, costing ~80 tokens to carry:

- Search for a fact; do not load a file to find it.
- Read line ranges, not whole files, when you know roughly where you are going.
- Never re-read a file you just wrote.
- Never quote file contents back to the user — they can open the file.
- Edit in place; do not rewrite a file to change three lines.
- Run the narrowest test that proves the change, not the whole suite.

The last one is worth its own note: tool output counts against context just as file reads do, and
a full test suite's output is frequently larger than the file being tested.

Then make the budget visible. `ctx_check.py --budget` reports what a session start currently
costs:

```
startup read: ~2,840 tokens
  handoff.md           127
  current-state.md     181
  decisions.md (index)  40
  session-log.md (index) 40
  START-HERE.md        650
  AGENTS.md            374   (first session only)
```

A budget nobody can see is a budget nobody keeps. This is roughly 30 lines of Python and it turns
every other item on this list from a rule into a number.

---

## 3. Projected result

| | Now | After | Change |
|---|---:|---:|---|
| Empty kit, session start | 3,856 | ~900 | −77% |
| Simulated long-running project | 7,853 | ~1,100 | −86% |
| Worst case the caps permit | ~20,600 | ~3,000 | −85% |
| Growth as the project ages | Unbounded | Flat | — |

*(Projected. The "after" column assumes all seven changes; the tiered-reading and cap figures are
measured, the START-HERE figure is an estimate until the compressed version exists.)*

The flat-growth row matters more than the percentages. Today the kit gets more expensive every
week a project runs, which means it is most costly exactly when a project is most complex.

---

## 4. Four things that look like savings and are not

**Dropping `decisions.md`.** It is the cheapest file in the kit and it prevents an AI from
re-litigating a settled question — which costs a conversation, not a few hundred tokens. Keep it,
index it, archive the settled ones.

**Skipping verification to save tool output.** An unverified claim in `current-state.md` gets built
on. The rework is always more expensive than the test run, and it arrives later, when it is harder
to trace.

**Compressing the files into terse shorthand.** Notes stripped to keywords get misread, and a
misread state file sends a session down the wrong path. The saving is real and small; the failure
is rare and large. Compress by *removing* content that has aged out, not by abbreviating content
that still matters.

**Making the AI summarize the files back to you at session start.** It feels like a useful
confirmation. It costs output tokens to restate what is already on disk, and it is the single most
common way a session wastes its opening. Have it state the next action in one line and start
working.

---

## 5. If you only do three

1. **Put START-HERE.md on a diet** (2.2) — biggest per-session saving, affects every project, and
   nothing else depends on it.
2. **Tiered reading with indexes** (2.1) — biggest saving on any project older than a few weeks,
   and it is what stops cost growing with age.
3. **`--budget`** (2.7) — small, and it makes the other two measurable rather than hopeful.

Caps and rolling summaries (2.3, 2.4) follow naturally once tiered reading is in, because the
index is what makes a tight cap tolerable. The per-task file list (2.5) is fifteen minutes of work
and worth doing whenever you next touch `handoff.md`.
