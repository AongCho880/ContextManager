#!/usr/bin/env python3
"""
ctx_check.py — consistency check for the AI context kit.

Carries the discipline nobody should have to memorize, so START-HERE.md can stay short.
Standard library only, no dependencies. Run from anywhere inside the project:

    python3 context/tools/ctx_check.py            # report
    python3 context/tools/ctx_check.py --quiet    # problems only
    python3 context/tools/ctx_check.py --budget   # what a session start costs, in tokens
    python3 context/tools/ctx_check.py --json     # for CI or a git hook

Exit codes:  0 = clean   1 = warnings   2 = errors

What it checks:
  · files grown past the point where a session start stays cheap
  · a missing index, without which a whole file gets read instead of its first 12 lines
  · decisions still pending — someone is blocked and may not know it
  · more than one task claimed as active, or a state that contradicts itself
  · a session that died mid-task without checkpointing
  · a stale copy written back over newer work (sequence number went backwards)
  · a write that skipped its sequence bump
  · files outgrowing what anyone will actually read
  · work marked done with no record of how it was verified
  · facts still UNVERIFIED
  · credentials that should never be in a file designed to be pasted around
  · the same fact drifting in two places
  · references to files that no longer exist
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = ".ctx_check_state.json"

# ---------------------------------------------------------------- configuration

# path -> (line cap, byte cap, required?)
# Sized so a session start stays cheap. Past 1.5x a cap it is an error, not a warning:
# an oversized file is one nobody loads, which makes it a file that does nothing.
FILES = {
    "AGENTS.md": (50, 4_000, True),
    "context/current-state.md": (60, 4_500, True),
    "context/handoff.md": (40, 3_000, True),
    "context/decisions.md": (120, 9_000, True),
    "context/session-log.md": (80, 6_000, True),
    "context/verified-facts.md": (250, 20_000, False),
}

# Files a session reads in full every time, vs. only the first N lines (the index).
ALWAYS_READ = ("context/handoff.md", "context/current-state.md")
INDEX_ONLY = {"context/decisions.md": 12, "context/session-log.md": 12}
FIRST_SESSION_ONLY = ("AGENTS.md",)
ENTRY_POINT_TOKENS = True  # count START-HERE.md in the budget; every session reads it

FRONT_MATTER_REQUIRED = {
    "context/current-state.md": ["seq", "updated_utc"],
    "context/handoff.md": ["seq", "updated_utc", "status", "next_action"],
    "context/decisions.md": ["seq"],
    "context/session-log.md": ["seq"],
    "context/verified-facts.md": ["seq"],
}

LOCK_PATH = "context/.lock"
ENTRY_POINT = "START-HERE.md"

# Credentials must never reach a file that gets pasted into chat windows by design.
SECRET_PATTERNS = [
    (r"\bsk-ant-[A-Za-z0-9_\-]{16,}", "Anthropic-style API key"),
    (r"\bsk-[A-Za-z0-9_\-]{16,}", "OpenAI-style API key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"\bghp_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"\bAIza[0-9A-Za-z_\-]{30,}", "Google API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"<>]{8,}",
     "credential assignment"),
]

DUP_MIN_CHARS = 60          # shorter lines are too generic to count as duplication
VERIFY_WORDS = ("verif", "tested", "test run", "checked", "confirmed", "built", "ran ")


# ---------------------------------------------------------------- helpers

class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, msg: str) -> None: self.errors.append(msg)
    def warn(self, msg: str) -> None: self.warnings.append(msg)
    def note(self, msg: str) -> None: self.notes.append(msg)

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else (1 if self.warnings else 0)


def find_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "context").is_dir() or (candidate / ENTRY_POINT).is_file():
            return candidate
    return start


def parse_front_matter(text: str) -> tuple[dict[str, str], bool]:
    """Flat `key: value` YAML front matter. Deliberately minimal — no dependencies."""
    if not text.startswith("---"):
        return {}, False
    end = text.find("\n---", 3)
    if end == -1:
        return {}, False
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip("\"'")
    return data, True


def parse_utc(value: str) -> datetime | None:
    value = value.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def body_hash(text: str) -> str:
    """Hash below the front matter, so bumping seq alone doesn't look like a content change."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def strip_comments(text: str) -> str:
    """Template guidance lives in HTML comments; it shouldn't trip content checks."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def section(text: str, heading: str) -> str:
    """Body of a `## heading` section. Stops at the next `##`, so nested `###` blocks stay in."""
    pattern = rf"^##\s*{re.escape(heading)}.*?$(.*?)(?=^##[^#]|\Z)"
    match = re.search(pattern, text, re.M | re.S | re.I)
    return strip_comments(match.group(1)) if match else ""


# ---------------------------------------------------------------- checks

def load(root: Path, rep: Report) -> dict[str, str]:
    contents: dict[str, str] = {}
    if not (root / ENTRY_POINT).is_file():
        rep.warn(f"missing {ENTRY_POINT} — the workflow every AI is supposed to read on arrival")
    for rel, (_l, _b, required) in FILES.items():
        path = root / rel
        if path.is_file():
            contents[rel] = path.read_text("utf-8", "replace")
        elif required:
            rep.error(f"missing required file: {rel}")
    return contents


def check_front_matter(contents: dict[str, str], rep: Report) -> dict[str, dict[str, str]]:
    metas: dict[str, dict[str, str]] = {}
    for rel, text in contents.items():
        required = FRONT_MATTER_REQUIRED.get(rel)
        if required is None:
            continue
        meta, found = parse_front_matter(text)
        if not found:
            rep.error(f"{rel}: no front matter — it needs at least `seq`")
            continue
        metas[rel] = meta
        for key in required:
            if key not in meta:
                rep.error(f"{rel}: front matter is missing `{key}`")
        seq = meta.get("seq")
        if seq is not None and not seq.lstrip("-").isdigit():
            rep.error(f"{rel}: seq is {seq!r}, which is not an integer")
    return metas


def check_seq(root: Path, contents: dict[str, str], metas: dict[str, dict[str, str]],
              rep: Report) -> None:
    """A stale copy written back over newer work is the failure this catches."""
    tools_dir = root / "context" / "tools"
    state_path = (tools_dir if tools_dir.is_dir() else root) / STATE_FILE
    previous: dict[str, dict[str, str]] = {}
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = {}

    current: dict[str, dict[str, str]] = {}
    for rel, text in contents.items():
        seq = metas.get(rel, {}).get("seq")
        if seq is None:
            continue
        current[rel] = {"seq": seq, "hash": body_hash(text)}
        was = previous.get(rel)
        if not was:
            continue
        if was["hash"] != current[rel]["hash"] and was["seq"] == seq:
            rep.warn(f"{rel}: the content changed but seq stayed at {seq} — bump it on every "
                     f"write, or a concurrent edit can be overwritten without anyone noticing")
        if was["seq"].lstrip("-").isdigit() and seq.lstrip("-").isdigit() \
                and int(seq) < int(was["seq"]):
            rep.error(f"{rel}: seq went backwards ({was['seq']} to {seq}) — an old copy was "
                      f"probably written back over newer work. Check git history before writing "
                      f"anything else.")

    try:
        state_path.write_text(json.dumps(current, indent=2), "utf-8")
    except OSError:
        rep.note("cannot write the checker's state file, so overwrite detection is off")


def check_decisions(contents: dict[str, str], rep: Report) -> None:
    """Something is blocked and the user may not know it."""
    text = contents.get("context/decisions.md")
    if not text:
        return
    pending = section(text, "Pending")
    titles = re.findall(r"^###\s*DECISION NEEDED\s*[—\-–]\s*(.+)$", pending, re.M)
    for title in titles:
        rep.warn(f"decision still pending: {title.strip()} — someone is blocked on an answer")
    if not titles and "DECISION NEEDED" in strip_comments(text.split("## Settled")[0]):
        rep.note("decisions.md has a pending block that doesn't match the expected heading shape")


def check_active_task(contents: dict[str, str], metas: dict[str, dict[str, str]],
                      rep: Report) -> None:
    """One task at a time, and a status that matches what the file actually says."""
    text = contents.get("context/handoff.md")
    if not text:
        return
    body = strip_comments(text)
    active = section(body, "Active task")
    tasks = re.findall(r"^\*\*Task\.\*\*", active, re.M)
    idle = "nothing in flight" in active.lower()
    status = metas.get("context/handoff.md", {}).get("status", "").lower()

    if len(tasks) > 1:
        rep.warn(f"handoff.md lists {len(tasks)} active tasks — work one at a time; the rest "
                 f"belong in current-state.md under what remains")
    if status == "in-flight" and idle:
        rep.warn("handoff.md says status: in-flight but the active task is 'Nothing in flight'")
    if status == "idle" and tasks and not idle:
        rep.warn("handoff.md has an active task but status: idle — set it to in-flight")
    if tasks and not re.search(r"^\*\*Next action\.\*\*\s*\S", active, re.M):
        rep.warn("handoff.md has an active task but no Next action — the next session will have "
                 "to re-derive the plan")


def check_done_verified(contents: dict[str, str], rep: Report) -> None:
    """Work called done with no record of how it was checked."""
    text = contents.get("context/current-state.md")
    if not text:
        return
    done = section(strip_comments(text), "Done")
    unverified = [
        line.strip().lstrip("-*• ").strip()
        for line in done.splitlines()
        if line.strip().startswith(("-", "*", "•"))
        and not line.strip().startswith("- <")
        and not any(word in line.lower() for word in VERIFY_WORDS)
    ]
    for item in unverified[:3]:
        rep.warn(f"current-state.md marks this done without saying how it was verified: "
                 f"{item[:70]}")
    if len(unverified) > 3:
        rep.warn(f"and {len(unverified) - 3} more done item(s) with no verification recorded")


def check_lock(root: Path, rep: Report) -> None:
    path = root / LOCK_PATH
    if not path.is_file():
        return
    meta: dict[str, str] = {}
    for line in path.read_text("utf-8", "replace").splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    holder = meta.get("holder", "someone")
    expires = parse_utc(meta.get("expires_utc", ""))
    now = datetime.now(timezone.utc)
    if expires is None:
        rep.warn(f"{LOCK_PATH}: held by {holder}, with no readable expiry — can't tell if it's stale")
    elif expires < now:
        mins = int((now - expires).total_seconds() // 60)
        rep.warn(f"{LOCK_PATH}: stale — {holder} claimed it and it expired {mins} min ago. Safe to "
                 f"delete; note it in session-log.md.")
    else:
        rep.note(f"{LOCK_PATH}: {holder} is writing until {meta.get('expires_utc')} — work "
                 f"read-only until it clears")


def check_budgets(contents: dict[str, str], rep: Report) -> None:
    for rel, text in contents.items():
        caps = FILES.get(rel)
        if not caps:
            continue
        max_lines, max_bytes, _ = caps
        lines, size = text.count("\n") + 1, len(text.encode("utf-8"))
        if lines <= max_lines and size <= max_bytes:
            continue
        action = ("move the oldest entries into context/archive/ and fold them into the "
                  "'Everything before' summary" if "session-log" in rel
                  else "archive the settled ones" if "decisions" in rel
                  else "trim it; this file is read at every session start")
        over = max(lines / max_lines, size / max_bytes)
        message = (f"{rel}: {lines} lines / {size:,} bytes, over the cap "
                   f"({max_lines} / {max_bytes:,}) — {action}")
        if over > 1.5:
            rep.error(message)
        else:
            rep.warn(message)


def check_indexes(contents: dict[str, str], rep: Report) -> None:
    """The index is what lets a session read 12 lines instead of the whole file."""
    for rel, depth in INDEX_ONLY.items():
        text = contents.get(rel)
        if text is None:
            continue
        head = "\n".join(text.splitlines()[:depth + 6])   # allow for front matter
        if "INDEX" not in head:
            rep.warn(f"{rel}: no index in the first {depth} lines — without it every session has "
                     f"to read the whole file instead of skimming the top")


def token_budget(root: Path, contents: dict[str, str]) -> tuple[list[tuple[str, int]], int]:
    """Estimate what one session start costs, at ~4 characters per token."""
    def tokens(text: str) -> int:
        return round(len(text) / 4)

    rows: list[tuple[str, int]] = []
    entry = root / ENTRY_POINT
    if entry.is_file():
        rows.append((ENTRY_POINT, tokens(entry.read_text("utf-8", "replace"))))
    for rel in ALWAYS_READ:
        if rel in contents:
            rows.append((rel, tokens(contents[rel])))
    for rel, depth in INDEX_ONLY.items():
        if rel in contents:
            head = "\n".join(contents[rel].splitlines()[:depth])
            rows.append((f"{rel} (index only)", tokens(head)))
    for rel in FIRST_SESSION_ONLY:
        if rel in contents:
            rows.append((f"{rel} (first session only)", tokens(contents[rel])))

    recurring = sum(n for name, n in rows if "first session" not in name)
    return rows, recurring


def check_facts(contents: dict[str, str], rep: Report) -> None:
    text = contents.get("context/verified-facts.md")
    if not text:
        return
    rows = [
        line for line in strip_comments(text).splitlines()
        if line.strip().startswith("|") and "UNVERIFIED" in line
        and "Status" not in line and "`UNVERIFIED`" not in line and "<" not in line
    ]
    if rows:
        rep.note(f"{len(rows)} number(s) still UNVERIFIED — trace them before quoting them anywhere")


def check_secrets(contents: dict[str, str], rep: Report) -> None:
    for rel, text in contents.items():
        for pattern, label in SECRET_PATTERNS:
            match = re.search(pattern, text)
            if match:
                line_no = text[:match.start()].count("\n") + 1
                rep.error(f"{rel}:{line_no}: possible {label} — remove it. These files get pasted "
                          f"into chat windows and synced to vendors by design.")
                break


def check_duplication(contents: dict[str, str], rep: Report) -> None:
    seen: dict[str, list[str]] = {}
    for rel, text in contents.items():
        for line in strip_comments(text).splitlines():
            stripped = line.strip().lstrip("-*#>• ").strip()
            if (len(stripped) < DUP_MIN_CHARS or stripped.startswith(("|", "<", "`"))):
                continue
            seen.setdefault(stripped, []).append(rel)
    dupes = {line: files for line, files in seen.items() if len(set(files)) > 1}
    for line, files in list(dupes.items())[:5]:
        rep.warn(f"the same line is in {' and '.join(sorted(set(files)))} — keep one, reference it "
                 f"from the other: {line[:60]}")
    if len(dupes) > 5:
        rep.warn(f"and {len(dupes) - 5} more line(s) duplicated across files")


def check_links(root: Path, contents: dict[str, str], rep: Report) -> None:
    pattern = re.compile(r"`([A-Za-z0-9_./\-]+\.(?:md|py|sh|ya?ml|json|txt|tex|ipynb|toml))`")
    for rel, text in contents.items():
        for target in sorted(set(pattern.findall(strip_comments(text)))):
            if target.startswith("<") or "*" in target:
                continue
            if not (root / target).exists() and not (root / "context" / target).exists():
                rep.note(f"{rel} points at `{target}`, which isn't there")


def check_placeholders(contents: dict[str, str], rep: Report) -> None:
    total = sum(len(re.findall(r"<[a-z][^>\n]{2,50}>", strip_comments(text)))
                for text in contents.values())
    if total:
        rep.note(f"{total} <placeholder>(s) still unfilled — the kit hasn't been set up for this "
                 f"project yet")


def check_freshness(metas: dict[str, dict[str, str]], rep: Report) -> None:
    meta = metas.get("context/handoff.md")
    if not meta:
        return
    updated = parse_utc(meta.get("updated_utc", ""))
    if updated is None:
        return
    if updated.year < 2000:
        rep.warn("handoff.md still has the placeholder date — set updated_utc on your first write")
        return
    days = (datetime.now(timezone.utc) - updated).days
    status = meta.get("status", "").lower()
    if status == "in-flight" and days > 2:
        rep.warn(f"handoff.md has been in-flight and untouched for {days} days — a session "
                 f"probably stopped without checkpointing. Check the work against the project "
                 f"before trusting what it says.")
    elif days > 30:
        rep.note(f"handoff.md was last updated {days} days ago — verify it against the project "
                 f"before relying on it")


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="AI context kit consistency check")
    parser.add_argument("--root", type=Path, default=None, help="project root (default: find it)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--quiet", action="store_true", help="errors and warnings only")
    parser.add_argument("--budget", action="store_true",
                        help="show what one session start costs in tokens, and stop")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else find_root(Path.cwd().resolve())
    rep = Report()

    contents = load(root, rep)

    if args.budget:
        rows, recurring = token_budget(root, contents)
        if args.json:
            print(json.dumps({"root": str(root), "recurring_tokens": recurring,
                              "items": [{"file": f, "tokens": n} for f, n in rows]}, indent=2))
            return 0
        print(f"Session-start cost — {root}")
        for name, count in rows:
            print(f"  {count:6,}  {name}")
        print(f"  {'-' * 6}")
        print(f"  {recurring:6,}  every session")
        first = sum(n for name, n in rows if "first session" in name)
        if first:
            print(f"  {recurring + first:6,}  first session on this project")
        print("\n  ~4 characters per token. Files not listed are read only when a task needs them.")
        return 0

    if contents:
        metas = check_front_matter(contents, rep)
        check_seq(root, contents, metas, rep)
        check_decisions(contents, rep)
        check_active_task(contents, metas, rep)
        check_done_verified(contents, rep)
        check_lock(root, rep)
        check_budgets(contents, rep)
        check_indexes(contents, rep)
        check_facts(contents, rep)
        check_secrets(contents, rep)
        check_duplication(contents, rep)
        check_links(root, contents, rep)
        check_placeholders(contents, rep)
        check_freshness(metas, rep)

    if args.json:
        print(json.dumps({"root": str(root), "errors": rep.errors, "warnings": rep.warnings,
                          "notes": rep.notes, "exit_code": rep.exit_code}, indent=2))
        return rep.exit_code

    print(f"Context check — {root}")
    for label, items in (("ERROR", rep.errors), ("WARN ", rep.warnings), ("note ", rep.notes)):
        if label.strip() == "note" and args.quiet:
            continue
        for item in items:
            print(f"  {label}  {item}")
    if rep.exit_code == 0:
        print("  OK     no problems" + (" — notes above are informational" if rep.notes else ""))
    return rep.exit_code


if __name__ == "__main__":
    sys.exit(main())
