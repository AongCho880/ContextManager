# ai-context-kit

**This folder is the payload.** Copy it into any project, at any stage, and hand it to any AI.

```bash
./install.sh /path/to/your/project
```

Then open any AI in that project and say: **"Read START-HERE.md and follow it."**

Nothing existing is ever overwritten. Manual install works too — copy `START-HERE.md`, `AGENTS.md`
and `context/` into the project by hand. That is all the script does.

```bash
python3 context/tools/ctx_check.py            # check the files stay consistent
python3 context/tools/ctx_check.py --budget   # what a session start costs, in tokens
```

Everything here is a template meant to be filled in per project — do not fill in the copies in
this repo.

**Full documentation, requirements, and measured token costs: [`../README.md`](../README.md).**
