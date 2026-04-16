# autoresearch

autonomous experimentation framework for Claude Code. Claude runs controlled experiments on your live systems, keeps winners, reverts losers. knowledge compounds over time.

```
hypothesis -> edit strategy -> apply -> wait -> measure -> evaluate -> keep/revert -> repeat
```

## quick start

### try the demo (no setup needed)

```bash
git clone https://github.com/xavierfok/autoresearch
cd autoresearch/examples/seo-demo
python experiment.py --simulate
```

runs 3 experiment cycles on real blog post titles with simulated metrics. takes 45 seconds.

### start your own experiment

if you have Claude Code installed, just run:

```
/autoresearch
```

Claude will ask you 4 simple questions:

1. **what are you experimenting on?** "blog post titles on my WordPress site"
2. **how do you measure success?** "clicks and impressions from Google Search Console"
3. **how do I connect?** "WordPress app password + GSC service account JSON"
4. **any tuning?** (hit enter for sensible defaults)

Claude builds everything from your answers. no code to write. then:

```
/autoresearch run     # run one experiment cycle
/autoresearch tick    # evaluate mature experiments
/autoresearch history # see results
```

### run autonomously

```bash
0 6 * * * cd /path/to/project && claude --dangerously-skip-permissions -p "$(cat program.md)"
```

Claude wakes up every morning, reads past experiments from git history, generates a new hypothesis, applies it, and waits. losers auto-revert. winners stay. the site gets better every cycle.

## how it works

### 3 files

| file | purpose |
|------|---------|
| `program.md` | the protocol - tells Claude the rules of the loop |
| `experiment.py` | strategy (top, Claude edits) + infrastructure (bottom, never touched) |
| `db.py` + `config.py` | SQLite state + tunable settings |

### the editable boundary

```python
# ---- experiment strategy (edited by Claude) ----
HYPOTHESIS = "add power words to titles"
STRATEGY = {"title": "add number + power word", ...}

# ================================================================
# FIXED INFRASTRUCTURE BELOW - DO NOT EDIT
# ================================================================
```

Claude edits above the line. never below. this is what makes autonomous operation safe.

### git as memory

every hypothesis becomes a git commit. Claude reads `git log` before each run - it knows what was tried, what worked, what failed. knowledge compounds. each cycle is smarter than the last.

### auto-revert

if a change hurts performance (relative lift < -3%), the experiment is automatically reverted to original content. experimentation is safe by default.

## works for

SEO, email subject lines, pricing, ad copy, landing pages - anything where you can change something, measure a metric, and revert if needed.

## origin

born from a production system at [dataresearchtools.com](https://dataresearchtools.com) running autonomous SEO experiments with Claude Code + WordPress + Google Search Console.

## license

MIT
