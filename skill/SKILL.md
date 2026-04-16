---
name: autoresearch
description: Scaffold and run autonomous experiment loops. Claude edits strategy, applies to targets, waits, evaluates with a control group, keeps winners, reverts losers. Works for SEO, email, pricing, ads - anything measurable.
---

# /autoresearch

autonomous experimentation framework for Claude Code. the pattern:
**hypothesis -> edit strategy -> apply -> wait -> measure -> evaluate -> keep or revert**

## commands

- `/autoresearch init` - scaffold a new autoresearch project in the current directory
- `/autoresearch run` - execute one cycle of the experiment loop
- `/autoresearch tick` - evaluate mature experiments only (no new experiment)
- `/autoresearch history` - show experiment results
- `/autoresearch demo` - run the built-in SEO demo with simulated data

## init

when the user runs `/autoresearch init`, create these files in the current directory:

1. **program.md** - copy from the template. this is the protocol file you read on every autonomous run.
2. **experiment.py** - copy from the template. has two sections:
   - TOP: strategy section (HYPOTHESIS + STRATEGY dict) - this is what you edit each cycle
   - BOTTOM: fixed infrastructure - NEVER edit this
3. **config.py** - copy from the template. user customizes batch size, eval period, etc.
4. **db.py** - copy from the template. SQLite storage, zero external deps.

then ask the user: "what are you experimenting on?" and help them implement the 5 adapter functions in experiment.py:
- `select_targets()` - what to experiment on
- `apply_strategy(target, strategy)` - how to make changes
- `measure_targets(target_ids, start, end)` - how to get metrics
- `measure_control(start, end)` - control group measurement
- `revert_target(target_id, old_state)` - how to undo changes

## run

when executing a cycle (either via `/autoresearch run` or autonomously via cron):

1. read program.md for the full protocol
2. read experiment.py to see current strategy and past hypotheses (via git log)
3. run `python experiment.py --tick` to evaluate mature experiments
4. if no reverts happened and there's room for new experiments:
   a. analyze past results - what worked, what didn't
   b. generate a new, distinct hypothesis
   c. edit ONLY the strategy section at the top of experiment.py
   d. `git add experiment.py && git commit -m "experiment: <hypothesis>"`
   e. run `python experiment.py`
   f. verify success

## the boundary

the most important architectural concept is the **editable boundary**:

```python
# ---- experiment strategy (edited by Claude) ----
HYPOTHESIS = "..."
STRATEGY = {...}

# ================================================================
# FIXED INFRASTRUCTURE BELOW - DO NOT EDIT
# ================================================================
```

Claude edits above the line. never below. this is what makes autonomous operation safe.

## key principles

- **git is memory**: each hypothesis becomes a commit. Claude reads `git log` to learn from history.
- **control groups**: always measure a control (non-experiment targets) to avoid confounding.
- **auto-revert**: losers get reverted automatically. this makes experimentation safe.
- **distinct hypotheses**: never repeat a hypothesis. if stuck, combine near-misses or try opposites.

## cron setup

to run autonomously, add to crontab:
```
0 6 * * * cd /path/to/project && claude --dangerously-skip-permissions -p "$(cat program.md)"
```

this makes Claude Code your autonomous research agent.
