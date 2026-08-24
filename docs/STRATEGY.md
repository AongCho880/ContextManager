# Universal AI Context Protocol

**Spec version: 2.0** · Vendor-neutral · Works with any AI assistant, at any point in a project.

> **Hand this file to any AI.** Chat or agent, Claude or ChatGPT or Gemini or Copilot or Cursor
> or whatever ships next month. Say:
>
> > *"Set up (or audit) this project's context system per the Universal AI Context Protocol v2 in
> > this document. Start at §9."*
>
> §9 is written as a procedure to execute, not background reading. Everything before it is the
> reasoning an AI needs to execute §9 correctly.

> **What changed from v1.** v1 assumed two kinds of AI tool; there are three, and the middle one
> is where data actually gets destroyed (§2, §6). v1 said "don't trust modification time" without
> offering a replacement; v2 has one (R7, §4.1). v1 restated the same rules across five sections —
> violating its own §5 — so v2 states each rule exactly once, numbered, and references it by ID
> everywhere else. v2 also adds what v1 had no answer for: concurrency claiming, file-size
> rotation, secrets, working language, a recovery playbook, and a one-file mode for projects too
> small to justify four.

---

## Table of contents

1. [The problem](#1-the-problem)
2. [Three access tiers](#2-three-access-tiers)
3. [Architecture](#3-architecture)
4. [The rules (canonical)](#4-the-rules-canonical)
5. [File specifications](#5-file-specifications)
6. [Case study: how this breaks](#6-case-study-how-this-breaks)
7. [Tool compatibility snapshot](#7-tool-compatibility-snapshot)
8. [Verification over trust](#8-verification-over-trust)
9. [Procedure: set up or audit (for an AI to execute)](#9-procedure-set-up-or-audit-for-an-ai-to-execute)
10. [Templates](#10-templates)
11. [Per-tier checklists](#11-per-tier-checklists)
12. [Recovery playbook](#12-recovery-playbook)
13. [Lite mode: one file](#13-lite-mode-one-file)
14. [Summary](#14-summary)

---

## 1. The problem

Long-running work — a thesis, a paper, a codebase, a business plan — hits the same four facts no
matter which AI is in front of you:

- **Sessions don't end, they stop.** A usage limit, a closed tab, a dropped connection, a crashed
  terminal. Interruption arrives mid-sentence and without warning.
- **Nothing crosses between products, or between accounts on one product.** A ChatGPT thread
  cannot see a Claude thread. A second Claude account cannot see the first one's history. Any
  vendor's "memory" feature is invisible to every other vendor — and usually to your own other
  account.
- **A new session doesn't know the project's history** unless that history is written somewhere it
  can read.
- **Tools touch projects differently.** Some edit disk live. Some work on a staged snapshot and
  push it back later. Some see only what you paste. Mixing them without a protocol is precisely
  how work disappears.

The fix: **state lives on disk, in the project folder, in plain text every tool can read.**
Whichever AI shows up next, its first act is to read a small set of files and its every checkpoint
is to update them. That's the whole idea. The rest of this document is the mechanics that make it
survive contact with real tools.

---

## 2. Three access tiers

v1 of this strategy split AI tools in two. That split hid the dangerous case. There are three, and
**an AI reading this must identify its own tier before doing anything else**, because the tier
determines which rules bind hardest.

### The self-test

Answer in order; the first *yes* is your tier.

| # | Question | If yes |
|---|---|---|
| 1 | Can I read a project file and write it back, with the change visible on the real filesystem immediately, no separate publish/commit/sync step? | **Tier 1 — Live disk** |
| 2 | Can I reach the files at all — through a connected folder, an upload/download cycle, a sandbox that syncs, a remote clone, a stage-then-commit bridge? | **Tier 2 — Bridged** |
| 3 | Otherwise: I only see what is pasted into this conversation. | **Tier 3 — Chat-only** |

### Tier 1 — Live disk

Reads and writes the real files, in place, now. *Examples: Claude Code CLI, Cursor, Copilot in an
IDE, Gemini CLI, Codex CLI, Aider, Windsurf, Zed.*

Lowest risk. Follows every rule in §4 directly. The one thing Tier 1 tools get wrong is assuming
their own built-in "resume session" feature is a substitute for `handoff.md` — it isn't; it is
local to one tool and one account (R1).

### Tier 2 — Bridged / staged

Sees a **copy**, edits the copy, pushes it back through a separate step: a desktop app's connected
folder, a cloud sandbox that stages and commits, an upload-edit-download cycle, an agent working
on a remote clone or branch. *Examples: a desktop chat client with a linked folder, cloud coding
sandboxes, browser agents that hand you a file back, agents that clone your repo and open a PR.*

**This is where data dies.** The gap between reading the copy and writing it back is the window in
which someone else's work gets overwritten — and the overwrite looks *newer* than what it
destroyed (§6). Tier 2 must apply R3, R4, R5, and R7 with real discipline, and specifically must
**re-read immediately before the write-back, not just before the edit.**

A subtlety: an agent working on its own **git clone or branch** is Tier 1 *inside its clone* and
Tier 2 *relative to the project*. Its merge is the write-back. Resolve it with git's merge, never
by copying whole files over the originals.

### Tier 3 — Chat-only

Sees only the conversation. *Examples: any plain web or mobile chat with no file tools.*

The human is the hands: paste context in at the start, paste updates back at the end (§11). Tier 3
is not a lesser tier — plenty of serious work happens in a plain chat window — but it is the tier
where people most often assume a memory that isn't there (R1).

---

## 3. Architecture

```
project-root/
├── AGENTS.md                    ← the constitution: rules + map + routing. Read first, always.
│                                  Cross-vendor convention; not owned by any AI company.
├── CLAUDE.md · GEMINI.md ·      ← OPTIONAL one-line pointer stubs, only for a tool that insists
│   .cursor/rules/*.mdc ·          on its own filename. Content is one sentence: "AGENTS.md is
│   .github/copilot-instructions.md authoritative." Never a second copy of anything (R2).
├── .claude/ · .cursor/ · …      ← per-tool settings (permissions, approved commands). Never
│                                  project rules, never project state.
└── context/                     ← the shared live memory
    ├── handoff.md               ← right now. First read, most-written file, every session.
    ├── session-log.md           ← what already happened, newest first.
    ├── verified-facts.md        ← every number, with provenance. Omit for projects with no facts.
    ├── .lock                    ← advisory single-writer claim (R5). Transient.
    ├── archive/                 ← rotated session-log history (R11).
    └── tools/                   ← scripts that check instead of trusting (§8).
```

**One job per file, no overlap:**

| File | Horizon | Answers |
|---|---|---|
| `AGENTS.md` | Permanent | "What are the rules, and where is everything?" |
| pointer stubs | — | "Where are the real rules?" (one line) |
| `context/handoff.md` | Now | "What is the state this second, and what is the exact next step?" |
| `context/session-log.md` | Past | "What happened before, and why?" |
| `context/verified-facts.md` | Facts | "Where did this number come from? Is it verified?" |
| `context/.lock` | Transient | "Is another session writing right now?" |
| tool settings | — | "What is this one tool allowed to do?" |

### Why `AGENTS.md`

It is an open, cross-vendor convention read natively by a growing set of agents — not any one
company's format. Tools that insist on their own filename get a one-line stub pointing at it, so
the *content* still has exactly one home even though several filenames exist on disk (R2).

The name is not load-bearing. `PROJECT.md`, `AI_CONTEXT.md`, anything — the protocol requires only
that **exactly one file holds the real content** and every other instruction file points to it.
Treat the list of tools that auto-load `AGENTS.md` as a snapshot to verify (§7), never as a
permanent fact; the pointer-stub pattern survives whatever the conventions do next.

---

## 4. The rules (canonical)

**Every rule in this protocol is stated here, once.** Everywhere else — checklists, procedures,
templates — refers to it by ID. If you find a rule restated in full anywhere else in this
document, that's a bug in the document (R2 applied to itself).

| ID | Rule | Why |
|---|---|---|
| **R1** | **Disk is the only shared memory.** Nothing outside the project folder counts as context — not conversation history, not a vendor's memory feature, not a "project" note living inside one product, not your own recollection from earlier in this session. | The next session may be a different tool, a different account, or a different company. It can see the folder. It can see nothing else. |
| **R2** | **One fact, one home.** Every rule, number, state, and decision lives in exactly one file. Everywhere else, reference it by path. | Two copies drift. One session updates one copy, never sees the other, and afterwards nobody — human or AI — can tell which is current. Every tool wanting its own instructions file makes this easy to break by accident. |
| **R3** | **Checkpoint mid-work, not at the end.** Update `handoff.md` after each unit of work, after each decision, and *before* anything slow. | One write costs seconds. The "end" of a session may never arrive from inside that session. |
| **R4** | **Re-read immediately before editing.** Never edit from a copy read earlier in the session, however recently. | Another tool or account may have written since. This is the single habit that would have prevented §6. |
| **R5** | **One writer at a time.** Claim `context/.lock` before your first write; release it when done. There is no real locking — this is advisory and depends on every participant honoring it. | Concurrent writes have no merge. Last write wins silently and the other work is simply gone. |
| **R6** | **The tree wins over the notes.** If `handoff.md` or `AGENTS.md` disagrees with the actual code, documents, or data, the artifacts are right and the note is stale until proven otherwise. | Notes are written by hand and go stale. Artifacts are the thing itself. |
| **R7** | **Trust the sequence number, not the timestamp.** Each context file carries `seq` in its front matter. Bump it on every write. If the `seq` on disk is higher than the one you read, **you have been overtaken — re-read and merge; do not overwrite.** | A file's modification time proves only that something wrote it, not that the content is current. A stale snapshot committed back by a bridge has the newest mtime on the folder and the oldest content in it (§6). |
| **R8** | **Never invent a number.** Every quantity traces to a source, or is marked `UNVERIFIED`. Do not estimate, interpolate, or carry a figure forward because an earlier draft had it or another AI stated it confidently. When a document and its source disagree, stop and report the conflict; do not pick one. | Models differ in how confidently they fill gaps. Provenance is what catches that regardless of which model did it. |
| **R9** | **Read only what the task needs.** `AGENTS.md`'s routing table exists so a session loads the relevant slice, not the tree. | Context is finite and paid for. A session that reads everything has less room left to think. |
| **R10** | **No secrets in context files.** No keys, tokens, passwords, personal data, or embargoed figures. Reference the secret by name and say where it lives. | These files get pasted into chat windows, uploaded to sandboxes, and synced to vendors — by design. Assume everything in them is readable by every tool you use. |
| **R11** | **Keep files bounded.** Respect the size budgets in §5.5; rotate `session-log.md` into `context/archive/` when it exceeds them. | An unbounded log silently becomes a file nobody loads, which makes it a file that does nothing. |
| **R12** | **Append and reconcile; never regenerate.** `handoff.md`'s active work and `session-log.md`'s history are never rewritten wholesale, including by a re-run of §9. | Regeneration is indistinguishable from deletion after the fact. |

### 4.1 The sequence number (R7), concretely

Every context file opens with YAML front matter containing `seq`, a plain integer.

- **Read:** note the `seq`.
- **Write:** set `seq` to *the value currently on disk* + 1 — which means re-reading first (R4).
- **Overtaken:** if the disk `seq` is higher than what you read, another writer landed in between.
  Merge their content into yours; do not clobber. Log it in `session-log.md`.

It is a Lamport clock in six characters. It costs nothing, needs no tooling, works identically in
every tier including a human retyping it out of a chat window, and it is immune to the mtime lie
that destroyed a day of work in §6.

---

## 5. File specifications

### 5.1 `AGENTS.md` — the constitution

Read first by every session, in every tier — automatically by tools that recognize the filename,
manually by whoever opens a chat. **Target 40–60 lines.** A bloated instructions file costs every
session time to parse and, in practice, gets followed *less* reliably than a short one.

Contents:

- **Identity** — one paragraph: what this is, who it's for, is it confidential, **and the working
  language** (which language the prose is written in, which language notes and code comments use —
  these are often different and it is a costly thing for a new AI to guess wrong).
- **Layout** — the folder map, one line per entry.
- **Routing table** — "if the task is X, read Y first" (R9).
- **Non-negotiables** — hard rules that bind every session on every tool. Distinguish these from
  house style: a non-negotiable is something whose violation invalidates the work.
- **Working method** — build/test commands as *exact invocations*, not tool names; patching and
  writing conventions; verification-script usage.
- **Open items** — what's outstanding project-wide.
- **Resolved — do not reopen** — settled questions, so a future session on some other product
  doesn't re-litigate them.

> Think of it as **what you'd tell a new collaborator on day one** — rules, traps, compressed
> history — written once, read by whichever AI shows up next.

### 5.2 `context/handoff.md` — live state

The actual synchronization mechanism, and the one file that matters identically in all three
tiers.

**Lifecycle.** Read at session start; continue from `next_action` without re-deriving the plan or
re-asking settled questions. Update at every checkpoint (R3). When a task finishes, move a
paragraph to `session-log.md` and reset active work to *Nothing in flight*.

**Structure.** Front matter (`seq`, `updated_utc`, `updated_by`, `status`, `next_action` — so a
tool can parse the state without reading prose), then:

- **Status at a glance** — a table, one row per module/chapter/component.
- **Needs a human, not an AI** — decisions no AI should make alone, whatever its vendor.
- **Active work** — current task, decisions already made (marked, so they're not re-asked), and a
  **Next action** line specific enough to act on cold.
- **Working notes that outlive one session** — traps that shouldn't need rediscovering every time
  a different AI picks this up.

### 5.3 `context/session-log.md` — compressed history

Finished work, newest first, a few lines per session. What changed, what was verified, what turned
out to be wrong. **Record which tool/account did the work** — once more than one AI is involved,
different failure modes are worth tracing. Decisions belong here; numbers in `verified-facts.md`;
rules in `AGENTS.md` (R2).

### 5.4 `context/verified-facts.md` — provenance for every number

One row per quantity: value, **provenance** (which script, run, log line, cell, or source
document), and **status** — `output` (from a run), `config` (from a setting), `source` (from a
cited document), or `UNVERIFIED`. Governed by R8. Omit the file entirely for projects with no
factual claims to track.

### 5.5 Size budgets (R11)

| File | Soft cap | When exceeded |
|---|---|---|
| `AGENTS.md` | ~60 lines / 4 KB | Move detail into `context/`; keep only rules, map, routing |
| `context/handoff.md` | ~120 lines / 8 KB | Finished items → `session-log.md`; stale notes → delete |
| `context/session-log.md` | ~400 lines / 30 KB | Oldest entries → `context/archive/session-log-<YYYY>.md`, leave a pointer line |
| `context/verified-facts.md` | ~200 rows | Split by domain: `verified-facts-<area>.md`, listed in `AGENTS.md` |

### 5.6 File-local leftovers

A loose end that concerns exactly one file stays in that file, as a comment block at its foot
(`ACTION ITEMS: …`). Project-wide items go in `AGENTS.md`. This is R2, not a separate rule.

### 5.7 Tool settings

Per-tool config lives in that tool's own location and holds no project rules and no project state.
If a settings file supports free-text instructions, that text is a pointer stub, never a second
copy (R2).

---

## 6. Case study: how this breaks

Worth keeping, because it explains why R4, R5 and R7 are phrased the way they are. It happened
with a Tier 2 bridge, and it applies to every Tier 2 tool, not one product.

> A session **staged** the root instructions file and the live handoff file into a scratch
> location, edited that copy across a whole working day, and **committed it back three times.**
> Each commit reverted everything another account had written in the meantime — including a
> checkpoint written while a build was running.
>
> The damage was invisible from inside the folder, because the file that destroyed the work had
> the **newest modification time.** It looked like the freshest copy. It was an old snapshot that
> had swallowed newer work.

What each rule takes from this:

- **R4** — the re-read has to happen immediately before the write-back, not merely before the
  edit. On a bridge, those are hours apart.
- **R7** — mtime is not freshness. A `seq` that went backwards is detectable; a timestamp that
  went forwards is not informative.
- **R5** — the whole day was one long unclaimed write window.
- **R6** — `session-log.md` and the primary artifacts survived, because they accumulate rather
  than being replaced wholesale by one commit action.

**Practical takeaway:** prefer direct-to-disk editing wherever it's available. Where only a bridge
is available, checkpoint more often, keep the stage-to-commit window short, and re-read before
every commit — not just before every edit.

---

## 7. Tool compatibility snapshot

**This table ages. The protocol doesn't.** Verify any row against that tool's current docs before
relying on it; §§2–6 are the durable part.

| Tool / product | Tier | File access | Commonly auto-loaded file |
|---|---|---|---|
| Claude Code (CLI) | 1 | Direct disk | `CLAUDE.md` → stub to `AGENTS.md` |
| Cursor | 1 | Direct disk | `AGENTS.md`, or `.cursor/rules/*.mdc` |
| GitHub Copilot (IDE) | 1 | Direct disk | `AGENTS.md`, or `.github/copilot-instructions.md` |
| Gemini CLI | 1 | Direct disk | `AGENTS.md` or `GEMINI.md` |
| Codex CLI | 1 | Direct disk | `AGENTS.md` |
| Aider · Windsurf · Zed | 1 | Direct disk | `AGENTS.md`, or that tool's own rules file |
| Claude desktop / Cowork with a connected folder | **2** | Stage + commit back — §6 applies | none fixed; point it at `AGENTS.md` explicitly |
| Cloud coding sandboxes (Jules, Devin, hosted agents) | **2** | Remote clone / PR | `AGENTS.md` |
| ChatGPT with file upload/download | **2** | Upload, edit, download | none fixed; paste-and-reference |
| Any browser/computer-use agent editing files | **2** | Whatever it can reach | none |
| Claude · ChatGPT · Gemini — plain chat | 3 | None | n/a — §11 Tier 3 |

Whatever filename a given tool insists on, make it a one-line stub to `AGENTS.md` (R2). And treat
any tool's built-in "resume last session" as a convenience local to that tool and that account —
never a substitute for `handoff.md` (R1).

---

## 8. Verification over trust

Notes are not enough. Keep small scripts in `context/tools/` that turn "looks right" into "checked"
— worth more with every additional AI in the loop, because different models make different
mistakes:

- **Preservation check** — programmatically confirms an edit didn't change numbers, citations, or
  cross-references that were supposed to stay put. Reading a diff by eye is insufficient, and more
  so when the diff came from a different AI than the one reviewing it.
- **Protocol check** — validates this system itself: front matter present and parseable, `seq`
  monotonic, size budgets respected, lock not stale, `UNVERIFIED` rows surfaced, internal links
  resolving. The starter kit ships one (`ctx_check.py`).
- **Structure/style measurement** — measures what "sounds fine" is guessing at (sentence-length
  distribution against a reference corpus, section balance), useful precisely because different
  AIs default to different and mutually inconsistent styles.
- **Build audit** — runs against real build output, catching integration and layout problems
  regardless of which tool made the change.

**General rule:** whenever a project has you repeatedly asserting "this edit preserved the
content" or "this number is right," write the script that checks it. Memory and eyeballing are
exactly the things that do not survive a change of AI.

---

## 9. Procedure: set up or audit (for an AI to execute)

Execute this. Don't summarize it back.

### 9.0 Identify your tier

Run the self-test in §2. **Tier 3 → skip to 9.8.** Tier 1 and 2 continue; Tier 2 additionally
notes that every write below is a stage-and-commit, subject to R4 and R7.

### 9.1 Detect what exists

1. A root instructions file under any name: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules`,
   `.github/copilot-instructions.md`, `README-AI.md`, `AI_CONTEXT.md`.
2. A state folder or its near-equivalents: `context/`, `shared/`, `.notes/`, `docs/status.md`,
   `NOTES.md`, `PROGRESS.md`, `TODO.md`, `HANDOFF.md`, `STATE.md`.
   **If an equivalent exists under another name, adopt it — rename or point to it. Do not create a
   parallel system** (R2 applied to setup itself).
3. Tool-specific settings files already in use.
4. Version control: `git log -1`, `git status`. If present, recent history is the cheapest signal
   for reconstructing state (9.3).

### 9.2 Classify the stage

- **Day one** — little substantive content → **9.4**
- **Mid-flight, no context files** — real content, no tracking → **9.5**
- **Context files exist** → **9.6**

Ambiguous? State the inferred classification in one line before proceeding, so a wrong guess is
cheap to correct.

### 9.3 Gather signal before writing anything

- Directory tree, depth 2–3 — this becomes the layout map.
- **If under version control:** last 10–20 commit messages plus the diff of the most recent few.
  Fastest route to "what was being worked on." Note distinct author identities — more than one
  means the multi-AI rules matter here.
- **If not under version control:** the 10 most recently modified files, and any file whose name
  suggests status or notes. Weaker signal — label conclusions as inferred.
- Any existing single source of truth for numbers (results file, config, experiment log,
  database). It gets *referenced* by `verified-facts.md`, not copied into it (R2).
- Any existing README, style guide, or contributing doc — fold durable rules into `AGENTS.md`
  rather than leaving two rule-files to drift.
- The **working language** of the prose and of the notes (§5.1).

### 9.4 Fresh bootstrap (day one)

1. Create the §10 skeletons: `AGENTS.md`, `context/handoff.md`, `context/session-log.md`, and
   `context/verified-facts.md` — omitting the last for projects with nothing factual to track.
   **If the project is small enough that four files is overhead, use §13 lite mode instead.**
2. Fill the layout map and routing table from 9.3, even if most cells are empty.
3. Leave active work as *Nothing in flight* unless a first task was described.
4. Report what was created; ask the human to confirm the inferred identity, confidentiality, and
   working language. One confirmation beats a silent guess.

### 9.5 Backfill (mid-flight, no context files)

1. Same skeletons as 9.4.
2. Write a best-effort "Status at a glance" and "Active work" from 9.3's signals. **Label every
   inference** — *"(inferred from git log — please correct)"* — so guesses are visible at a glance.
3. **Do not invent history.** Write one log entry: *"Context protocol introduced <date>, backfilled
   from a scan; work before this point was not tracked in this format."*
4. Numeric claims found without clear provenance enter `verified-facts.md` as `UNVERIFIED`. Never
   promote them to `output` on the strength of them appearing in a draft (R8).
5. Report what was inferred, and flag what needs human confirmation before being treated as settled.

### 9.6 Audit and reconcile (context files exist)

1. Read `AGENTS.md`, then `handoff.md`, then the newest few `session-log.md` entries.
2. Compare `handoff.md`'s claimed state against the actual tree — file existence, recent commits.
   Disagreement resolves to the tree (R6).
3. Scan for duplication across `AGENTS.md`, `handoff.md`, and `session-log.md` (R2). **Flag
   duplicates; don't silently pick a survivor** — you can't tell which copy is current, that being
   the entire problem with duplication.
4. Check `seq` continuity and lock staleness (§12).
5. Check size budgets (§5.5) and rotate if needed.
6. Check that pointer stubs still match the tools actually in use; note gaps rather than expanding
   any tool's permissions unasked.
7. Report: consistent / drifted / missing / needs-a-human — in the tone of a "Needs a human"
   entry, not a silent fix.

### 9.7 Idempotency (R12)

Re-running this procedure must never regenerate `handoff.md`'s active work or `session-log.md`'s
history. They are append-and-reconcile targets. Only `AGENTS.md`'s *structural* sections — layout
map, routing table — may be regenerated outright when the directory has genuinely changed, and
even then Non-negotiables, Open items, and Resolved must be merged forward, never dropped.

### 9.8 Tier 3 variant (chat-only)

You cannot scan. Instead:

1. Ask the human to paste `AGENTS.md` and `context/handoff.md` — or, if neither exists, to say
   whether the project is day-one, mid-flight, or already has notes under some other name.
2. If they don't exist: produce the §10 skeletons as text and give the exact paths to save them at.
3. If they do: work from the pasted content exactly as Tier 1 would, with one difference — at the
   end of the session, **produce the updated front matter (with `seq` bumped) and Active work
   block, and tell the human to save it back.** You cannot do this step; saying so explicitly is
   what stops the session from evaporating when the tab closes.

---

## 10. Templates

### `AGENTS.md`

```markdown
# <Project> — instructions for any AI assistant

<What this is, in two lines. Confidential: yes/no.>
**Working language:** <prose language> · notes and code comments in <language>.
**Context protocol:** v2 — see `context/handoff.md` before acting.

## Layout

<folder tree, one line each>

## Where to look

| If the task is | Read first |
|---|---|
| Anything at all | `context/handoff.md` — live state |
| Picking up after a break | `context/session-log.md`, newest entry |
| Quoting any number | `context/verified-facts.md` |
| <task type> | <path> |

**This folder is the entire shared context.** No conversation memory, no vendor memory feature,
and no other product's project notes carry over. If a future session needs it, it is in a file.

## Non-negotiables

- Never invent a fact or number — every claim traces to a source, or is marked UNVERIFIED.
- Never put secrets in these files.
- <project-specific hard rules>

## Multi-AI rule

More than one AI tool or account may work this folder. Update `context/handoff.md` *during* work,
not at the end. Re-read any file immediately before editing it. Claim `context/.lock` before
writing. Bump `seq` on every write; if disk `seq` is ahead of yours, merge — never overwrite.

## Working method

<exact build/test commands, patching conventions, writing style, verification scripts>

## Open items

- <outstanding>

### Resolved — do not reopen

- <settled, so it isn't re-litigated>
```

### Pointer stub — verbatim, for `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, or any filename a tool demands

```markdown
See `AGENTS.md` at the project root. That file is authoritative for every AI assistant working in
this project. Do not duplicate its content here. If this file and `AGENTS.md` ever disagree,
`AGENTS.md` is correct and this file is stale.
```

### `context/handoff.md`

```markdown
---
ctx_protocol: "2.0"
file: handoff
seq: 1
updated_utc: <YYYY-MM-DDTHH:MMZ>
updated_by: <tool> / <machine or account>
status: idle          # idle | in-flight | blocked
next_action: "<one line, actionable cold>"
---

# Handoff — live working state

**Read this before doing anything else. Update it as you work, not when you finish.**
**Bump `seq` on every write. If the `seq` on disk is higher than the one you read, someone wrote
in between — re-read and merge; do not overwrite.**
**Chat-only AI: ask the human to paste this in, and to save your updated version back.**

## Status at a glance

| Area | Status |
|---|---|
| <module / chapter / component> | <one line> |

## Needs a human, not an AI

- <decisions no AI should make alone>

## Active work

**Task.** <what's underway, with just enough context to resume cold>

**Decided already — do not re-ask.**
- <decision>

**Next action.** <the exact next step>

## Working notes that outlive one session

- <traps that shouldn't need rediscovering on every tool>
```

### `context/session-log.md`

```markdown
---
ctx_protocol: "2.0"
file: session-log
seq: 1
---

# Session log

Newest first. One entry per session, a few lines. Decisions here; numbers in `verified-facts.md`;
rules in `AGENTS.md`.

---

## <YYYY-MM-DD> — <one-line title> — <tool / account used>

<What changed. What was verified, and how. What turned out to be wrong.>
```

### `context/verified-facts.md`

```markdown
---
ctx_protocol: "2.0"
file: verified-facts
seq: 1
---

# Verified facts

Single source of truth for every number quoted anywhere in this project. Never invent a value; an
unsourced number is UNVERIFIED, not an estimate.

| Quantity | Value | Provenance | Status |
|---|---|---|---|
| <accuracy, top-1> | <0.87> | <run_042.log line 12> | output |
| <sample size> | <1,204> | <config/train.yaml> | config |
| <claimed baseline> | <0.81> | <not yet traced> | UNVERIFIED |
```

### `context/.lock` (R5)

```yaml
holder: <tool> / <machine or account>
task: <what is being written>
claimed_utc: <YYYY-MM-DDTHH:MMZ>
expires_utc: <claimed + 90 minutes>
```

Claim before your first write, refresh if you run long, delete when done. A lock past `expires_utc`
is stale: you may break it, but say so in `session-log.md`. Advisory only — it works because
participants honor it, not because anything enforces it.

### Quick-context block — paste into any Tier 3 chat

```markdown
You're picking up work on <project>. It follows the Universal AI Context Protocol v2: state lives
in files, not in your memory, because the next session may be a different AI entirely.

You have no file access, so I am your hands. Below is AGENTS.md and context/handoff.md.

Please: follow the Non-negotiables; continue from handoff.md's "Next action" without re-deriving
the plan or re-asking anything listed as decided; never invent a number.

At the end of this session, give me (a) the updated front-matter block with `seq` bumped by one,
(b) the updated Active work / Next action block, and (c) a one-paragraph session-log entry — so I
can save them back myself.

--- AGENTS.md ---
<paste>

--- context/handoff.md ---
<paste>
```

### Bootstrap prompt — paste into any AI, any tier, any project

```markdown
Set up (or audit) this project's context system per the Universal AI Context Protocol v2
[attach or paste this document]. Identify your access tier first (§2), then execute §9. If you
cannot read the folder yourself, ask me for what you need and give me files to save.
```

---

## 11. Per-tier checklists

Each item cites the rule it enforces; §4 has the reasoning.

### Tier 1 — live disk

**Start:** opened from the project root so auto-load finds the stub → `AGENTS.md` · read
`handoff.md`, noted `seq` and Next action · resolved any note-vs-tree conflict toward the tree (R6)
· claimed `.lock` (R5).

**During:** checkpointing `handoff.md` at every unit of work (R3) · re-reading each file
immediately before editing (R4) · bumping `seq`, merging rather than clobbering if overtaken (R7) ·
giving each new fact exactly one home (R2) · no secrets (R10).

**End (or when a limit hits):** summary written into `session-log.md` · active work reset or a
clear Next action left · `.lock` released · budgets checked, log rotated if needed (R11).

### Tier 2 — bridged / staged

Everything in Tier 1, plus:

- **Re-read immediately before the commit/write-back, not just before the edit** (R4) — on a bridge
  these are hours apart, and that gap is §6.
- Keep the stage→commit window as short as the work allows; commit in small pieces.
- Never commit a whole folder back when you changed one file.
- Compare `seq` at commit time. Disk ahead of you? Merge (R7).
- Working from a clone or branch? Merge with git, never by copying files over the originals.

### Tier 3 — chat-only (the human's checklist)

**Start:** pasted the quick-context block (§10) · confirmed with the AI what the Next action is
before letting it run.

**During:** treated output as a draft, exactly as a Tier 1 edit would be · didn't let this session
overlap with an agent working the same folder (R5).

**End:** asked for the updated front matter + Active work block + log entry · **saved them into the
real files** · bumped `seq` by one (R7).

---

## 12. Recovery playbook

| Symptom | What it means | Do this |
|---|---|---|
| Notes contradict the code/documents | Notes went stale, or a write was lost | Trust the tree (R6). Correct `handoff.md` from the artifacts. Log the correction. |
| Disk `seq` higher than the one you read | You were overtaken mid-session | Re-read, merge both changes, write with `disk seq + 1`. Note the collision in the log (R7). |
| Two entries claim the same `seq` | Two writers landed simultaneously | Both are suspect. Reconstruct from artifacts and `session-log.md` (they accumulate); renumber forward. |
| `.lock` exists, past `expires_utc` | Abandoned session, likely an interrupt | Break it, note it in the log, carry on (R5). |
| `.lock` exists, still valid | Someone is writing right now | Wait, or work read-only. Don't write. |
| `handoff.md` truncated or unparseable | Interrupted mid-write | Recover from version control if present; otherwise rebuild from `session-log.md` + the tree, and mark the gap. |
| A session died with no checkpoint | R3 wasn't followed | Reconstruct from artifacts, recent commits, and file mtimes *as weak hints only* (R7). Write what's certain; mark the rest inferred. |
| A bridge commit reverted others' work | §6, exactly | Recover from version control. If none: `session-log.md` and the primary artifacts are the survivors — rebuild the notes from them. Then shorten the stage→commit window. |
| Document and source disagree on a number | Someone carried a figure forward | Stop. Report the conflict; do not pick a side (R8). Mark the row `UNVERIFIED` until traced. |
| Nobody can tell which copy of a rule is current | R2 was broken | Keep the copy consistent with the artifacts; delete the other; replace it with a path reference. |
| Context files got huge and nobody reads them | R11 | Rotate per §5.5. A log nobody loads does nothing. |

**If version control exists, most of the above is a `git log -p` away.** Initializing git in a
project folder — even a thesis, even a folder of Word documents — is the single cheapest insurance
policy this protocol can recommend.

---

## 13. Lite mode: one file

Four files is right for a project with real scope. It is overhead for a two-week side project, and
overhead is how a protocol stops being followed. Below roughly 200 lines of total context, use one
file — `AI_CONTEXT.md` at the root:

```markdown
---
ctx_protocol: "2.0-lite"
seq: 1
updated_utc: <...>
updated_by: <tool / account>
next_action: "<one line>"
---

# <Project> — AI context

**Rules.** <identity, working language, non-negotiables, exact build/test commands. 10 lines max.>

**Now.** <status, decisions already made, and the exact Next action.>

**Log.** <newest first, one line per session: date — what changed — which AI.>
```

Same rules (§4), same tiers (§2), same checklists (§11) — one file instead of four. **Upgrade
when** the file passes ~200 lines, a second person or a second AI joins regularly, or numbers start
needing provenance. Upgrading is a split, not a rewrite: Rules → `AGENTS.md`, Now →
`context/handoff.md`, Log → `context/session-log.md`, keeping the `seq` you're on (R12).

---

## 14. Summary

No AI's memory carries across products, across accounts, or reliably across sessions, and any
session can stop mid-sentence without warning — so a long-running project has to keep its state
**on disk, in plain text, in a shape that assumes no particular vendor.** Four files do it: rules
and map (`AGENTS.md`, with one-line stubs for tools that demand their own filename), live state
updated mid-work rather than at the end (`context/handoff.md`), compressed history
(`context/session-log.md`), and provenance for every number (`context/verified-facts.md`) — each
with exactly one job, none duplicating another. One file does it for small projects (§13).

Before doing anything, an AI identifies its tier: **live disk**, **bridged** (sees a copy, writes
back later — the tier where work actually gets destroyed), or **chat-only** (a human is its hands).
Then it follows twelve rules stated once in §4, of which four carry most of the weight: *disk is
the only shared memory* (R1), *checkpoint mid-work* (R3), *re-read immediately before editing —
and, on a bridge, immediately before writing back* (R4), and *trust the sequence number, not the
timestamp* (R7), because a stale snapshot pushed back by a bridge carries the newest modification
time and the oldest content.

§9 is the executable part: hand this document to whatever AI is open, in a project at any stage,
and it can identify its own tier, scan or ask, and bootstrap or audit the system without anyone
narrating the project's history first.
