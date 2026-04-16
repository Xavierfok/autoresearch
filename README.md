# autoresearch

autonomous experimentation framework for Claude Code. let Claude run controlled experiments on your live systems, evaluate results against a control group, and automatically keep winners or revert losers.

## the pattern

```
hypothesis -> edit strategy -> apply -> wait -> measure -> evaluate -> keep/revert -> repeat
```

Claude Code reads a protocol file (`program.md`), edits a strategy section in `experiment.py`, applies changes to your targets, waits for data, evaluates with a control group, and decides to keep or revert. git history becomes Claude's long-term memory.

## quick start (demo)

```bash
git clone https://github.com/xavierfok/autoresearch
cd autoresearch/examples/seo-demo
python experiment.py --simulate
```

this runs 3 experiment cycles on simulated blog posts. no API keys, no external services.

## use it for your domain

```bash
# scaffold a new project
cp -r template/ my-experiment/
cd my-experiment/
```

edit `experiment.py` and implement the 5 adapter functions:

| function | what it does | SEO example |
|----------|-------------|-------------|
| `select_targets()` | pick what to experiment on | fetch WP posts + GSC data |
| `apply_strategy(target, strategy)` | make the change | rewrite title via WP REST API |
| `measure_targets(ids, start, end)` | get metrics | pull clicks from GSC |
| `measure_control(start, end)` | control group baseline | site-wide GSC minus experiment URLs |
| `revert_target(id, old_state)` | undo the change | push old title back to WP |

customize `config.py`:

```python
EXPERIMENT_BATCH_SIZE = 5    # targets per experiment
EVALUATION_DAYS = 14         # wait before evaluating
DATA_LAG_DAYS = 3            # analytics reporting delay
MAX_CONCURRENT = 6           # parallel experiments
MIN_EFFECT_SIZE = 0.03       # 3% threshold to keep
```

## run autonomously via cron

```bash
# add to crontab
0 6 * * * cd /path/to/project && claude --dangerously-skip-permissions -p "$(cat program.md)"
```

Claude Code wakes up, reads the protocol, checks experiment state, and either evaluates mature experiments or starts a new one with a fresh hypothesis.

## how it works

### the editable boundary

the most important design choice. `experiment.py` has two sections:

```python
# ---- experiment strategy (edited by Claude) ----
HYPOTHESIS = "add power words to titles"
STRATEGY = {"title": "add number + power word", ...}

# ================================================================
# FIXED INFRASTRUCTURE BELOW - DO NOT EDIT
# ================================================================
# ... evaluation math, rollback logic, safety checks ...
```

Claude edits above the line. never below. this is what makes autonomous operation safe.

### git as memory

each hypothesis becomes a git commit:
```
experiment: add power words and numbers to titles
experiment: question-based headings matching search intent
experiment: add year and freshness signals
```

Claude reads `git log` on every run to understand what was tried and what worked.

### control groups

every evaluation compares experiment targets against a control group (non-experiment targets over the same period). this prevents seasonal trends or site-wide changes from confounding results.

### auto-revert

if relative lift < -3%, the experiment is automatically reverted - old content is pushed back. this makes experimentation safe by default.

## project structure

```
autoresearch/
  template/           # generalized template files
    program.md        # protocol file Claude reads
    experiment.py     # strategy + infrastructure
    config.py         # tunable parameters
    db.py             # SQLite storage (zero deps)
  examples/
    seo-demo/         # runnable demo with simulated data
  skill/
    SKILL.md          # Claude Code skill definition
  slides/
    index.html        # reveal.js presentation
```

## works for

- **SEO**: blog post titles, meta descriptions, intros
- **email**: subject lines, preview text, send times
- **pricing**: price points, anchoring, framing
- **ads**: headlines, descriptions, creatives
- **landing pages**: hero copy, CTAs, social proof
- anything where you can apply a change, measure a metric, and revert if needed

## origin

born from a real production system at [dataresearchtools.com](https://dataresearchtools.com) that runs autonomous SEO experiments using Claude Code + WordPress + Google Search Console. this repo extracts the pattern into a reusable framework.

## license

MIT
