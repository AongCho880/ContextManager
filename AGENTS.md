# ContextManager — instructions for any AI working on this repository

This repo ships a drop-in context kit for AI assistants. It is a **tool**, not a project that uses
the tool — so do not fill in the templates here.

## Layout

```
README.md            the repo's public face and full documentation
docs/                STRATEGY.md (the reasoning), TOKEN-BUDGET.md (the measurements)
ai-context-kit/      the payload — templates, install script, and the checker
```

## Rules for this repo

- **`ai-context-kit/` is templates.** The `<placeholders>` are deliberate. Never fill them in,
  never "helpfully" complete `context/handoff.md`, and never run `install.sh` against this repo.
- **`START-HERE.md` costs tokens on every session of every project that uses it.** Anything added
  there must earn its place; prefer `README.md` or `docs/` for reasoning.
- **The templates must fit under their own caps** in `ctx_check.py`. Check after editing them.
- Never invent a number. Token figures in `README.md` and `docs/` are measured — if you change a
  file's size, re-measure with `--budget` and update them.
- Documentation lives in one place. `README.md` is authoritative; `ai-context-kit/README.md` is a
  pointer and must stay short.

## Testing a change

```bash
tmp=$(mktemp -d)
./ai-context-kit/install.sh "$tmp"
python3 ai-context-kit/context/tools/ctx_check.py --root "$tmp"          # expect: placeholder warning only
python3 ai-context-kit/context/tools/ctx_check.py --root "$tmp" --budget # expect: ~1,900 every session
```

Verified on Python 3.10–3.13. Changes to `ctx_check.py` should be checked against a project that
is deliberately broken — two active tasks, a pending decision, a sequence number going backwards,
an oversized file, a missing index, a planted key — to confirm every detector still fires.

## Conventions

- Markdown wrapped at 100 characters.
- `ctx_check.py` stays standard-library only, and no syntax newer than Python 3.7.
- `install.sh` stays portable to bash 3.2 (macOS ships it) and never overwrites an existing file.
