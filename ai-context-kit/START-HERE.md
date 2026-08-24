# START HERE

You are an AI picking up this project. State lives in `context/`, not in conversations — you may
be the tenth AI here, on a different product. Work through these steps in order.

## 1. Read only this much

1. `context/handoff.md` — the task in flight, the next action, the files it needs. Always.
2. `context/current-state.md` — where the project stands. Always.
3. The first 12 lines of `context/decisions.md` and `context/session-log.md` — indexes. Always.
4. `AGENTS.md` — rules and commands. First session on this project only.
5. Everything else — only when the task actually needs it.

Where the notes and the project disagree, **the project is right**. Fix the notes, never the
reverse.

## 2. Ask for a scan level. Measure first, then ask, then wait

Count the files and bytes before asking, so the user is choosing with real numbers:

> This project is `<N>` files, roughly `<T>` tokens. Which scan?
> **Full** (~`<T>`) — everything. Nothing missed, and expensive.
> **Targeted** (~`<t>`) — the files the task names plus what they import. Usually the right one.
> **Minimum** (~`<t>`) — `context/`, the README, the tree, the last 10 commits.

If a full scan will not fit in your context window, say so and propose a subsystem sweep instead
of starting one that fails halfway. No answer, or nobody there? Use **targeted** and say so.

## 3. Update `context/current-state.md`

What exists · what is done and **how it was verified** · what is in progress · what remains.
Mark anything you concluded rather than were told with *(inferred)*. Do not invent history for
work that predates this kit. It is a picture of now, not a diary — history goes in the log.

## 4. Pick exactly one task

State it in a sentence and say what "done" looks like. **One.** Not two related ones, not a task
plus cleanup you noticed — anything else goes in `current-state.md` under what remains. If the
choice is unobvious, large, or hard to reverse, use the decision block below.

## 5. Work, checkpointing as you go

Write the task and the first next action into `handoff.md` **before** you start. Update it after
each unit of work, after each decision, and before anything slow — not at the end. A session can
stop without warning; a checkpoint costs ~150 tokens and saves the session.

Checkpoint after a unit of work, not after every tool call.

## 6. Verify before calling it done

Run it. Run the narrowest test that proves the change. Re-read the changed section against its
source. Paste real output, not a description of it. Then `python3 context/tools/ctx_check.py`.

Could not verify something? Say so and mark it unverified. **"It should work" is not
verification** — the next session will build on whatever you claim here.

## 7. Update and stop

`current-state.md` (task done, how verified, what remains) · `handoff.md` (next action, or
*Nothing in flight*) · `decisions.md` if anything was decided · one line in `session-log.md` ·
any new number in `verified-facts.md`. Report to the user, then return to step 4.

---

## Decisions that need the user

Anything hard to reverse, costly, destructive, direction-changing, or with no clearly better
option. Put this block in `context/decisions.md` under **Pending** *and* in your reply:

```markdown
### DECISION NEEDED — <short title>

**The choice.** <what has to be decided, in one line>

**Why it matters.** <what it affects, what breaks if it goes wrong, what it blocks>

**My recommendation.** <the option> — <why>

**Alternatives.**
- <option B> — <what you gain, what you give up>

**Blocked until you answer.** <what you will not do meanwhile>
```

Then **wait.** Do not proceed on your own recommendation, and do not do "the safe part" first. If
the user is away, work on something independent and say what is blocked. When they answer, move
the block to **Settled** with the date and one line of reasoning, so nobody reopens it.

## The rules

1. **The files are the only memory.** No chat history or vendor memory reaches the next session.
2. **Re-read before editing — when another session could have written since.** Solo, nothing else
   running: re-reading your own recent write is waste. Another AI or account on this folder, or a
   staged copy you push back later: always re-read, and for a staged copy before the push too.
3. **Checkpoint during work, not at the end.**
4. **One task at a time**, verified before it is called done.
5. **Never invent a number or a fact.** Trace it, or mark it `UNVERIFIED`.

## Spending context well

- Search for a fact; do not load a file to find it.
- Read line ranges when you know roughly where you are going.
- Never re-read a file you just wrote (see rule 2).
- Never quote file contents back to the user — they can open the file.
- Edit in place; do not rewrite a file to change three lines.
- Tool output costs the same as file reads. A full test suite often costs more than the file.
- A fact that would fit two files goes in one, referenced from the other. Two copies drift.

*New install, files still full of `<placeholders>`? Fill in `AGENTS.md` first — ask, don't guess.
Why the kit is shaped this way: `README.md`.*
