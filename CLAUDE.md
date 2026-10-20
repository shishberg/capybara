# Working in this repo

Keep project facts in the READMEs and docs, not here. This file covers where to look and how to work.

## Orienting yourself

- Read `README.md` before answering design questions. Its build, parts and outputs tables say which code and docs are current, and `docs/design-status.md` lists the decisions.
- `seed/` is the part of Rosebear v3's generator that the paused board pipeline runs, not a design version. Its README says what still depends on it. Change it only to fix that pipeline.
- Earlier versions and their design notes are in the Rosebear repo (github.com/shishberg/rosebear). This repo was Rosebear's `v4/` until the split, so older docs and commit messages call it v4.
- Docs can disagree with each other or describe paused work. When they conflict, check the code or the generated output before trusting either doc.
- `output/` is generated and gitignored. Never edit it by hand. It is still useful to read: generated pinout and wiring files often answer hardware questions faster than the source does.
- Answer hardware questions (which controller, which pins are free, which parts) by searching the repo for part numbers, net names and GPIO numbers. Don't infer them from indirect evidence.
- `.claude/worktrees/` holds agent worktrees, not project source.

## Writing docs

- One fact, one place. Each decision or fact lives in a single doc; other docs link to it rather than restating it. Before adding a fact, search for where it already lives and update that instead.
- When something is dropped from the design, remove it from the docs rather than leaving notes about what it might become.

## Committing

- Always commit your work before finishing. Uncommitted or untracked work is easy to lose and hard for the next session to find.
- Run `git status` at the start and end of a task. Look for untracked directories as well as modified files, and ask about anything significant that isn't tracked.
- Keep commits to the task at hand. Leave unrelated changes you didn't make out of your commits, and mention them.
- Commit messages are a short description. Commits from before the split start with `v4:`; new ones don't need a prefix. Keep the `PROTOTYPE` marker for prototype work.
