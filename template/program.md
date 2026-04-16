# autoresearch

autonomous experiment engine. applies the autoresearch pattern to [YOUR DOMAIN]:
edit strategy, apply to targets, wait for data, evaluate, keep or revert.

**IMPORTANT: you are running non-interactively via cron. do NOT ask questions
or wait for user input. proceed autonomously. if something fails, log and continue.**

## what you CAN do

- edit the strategy section at the TOP of `experiment.py` (HYPOTHESIS and STRATEGY dict)
- run `python experiment.py` to apply a new experiment
- run `python experiment.py --tick` to evaluate mature experiments
- run `python experiment.py --health` to verify connections
- read the database to understand experiment state
- commit changes to experiment.py

## what you CANNOT do

- modify anything below the `# FIXED INFRASTRUCTURE` line in experiment.py
- modify config.py, db.py, or adapter files
- install new packages

## daily run protocol

```
EVERY RUN:

1. read state:
   - git log to see experiment history
   - query database for running/mature experiments
   - understand where you are in the research program

2. evaluate mature experiments:
   - run: python experiment.py --tick
   - read the output to understand what happened

3. if reverts happened this tick:
   - do NOT start a new experiment
   - exit cleanly

4. if no reverts and room for new experiments:
   - read full experiment history from git log and database
   - reason about what worked, what didn't, and why
   - generate a NEW hypothesis (must be distinct from all previous)
   - edit the strategy section at the top of experiment.py
   - git add experiment.py && git commit -m "experiment: <hypothesis>"
   - run: python experiment.py
   - verify it completed without errors

5. exit cleanly
```

## key rules

- you are resuming an ongoing research program, not starting fresh
- read git log and database state before doing anything
- each hypothesis must be distinct from all previous hypotheses
- if you run out of ideas, re-read past results, combine near-misses, try opposites
- never stop. if there are targets to experiment on, experiment
- log everything. future you needs to understand what past you was thinking
