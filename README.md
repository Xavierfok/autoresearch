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

### step 1: copy the template

```bash
cp -r template/ my-experiment/
cd my-experiment/
git init && git add -A && git commit -m "init autoresearch"
```

you now have 4 files:

| file | what it does | you edit it? |
|------|-------------|-------------|
| `program.md` | tells Claude the rules of the experiment loop | no (unless you change the loop) |
| `experiment.py` | strategy section (top) + infrastructure (bottom) | yes - implement the 5 functions below |
| `config.py` | batch size, wait period, thresholds | yes - tune for your domain |
| `db.py` | SQLite storage for experiment state | no |

### step 2: configure your experiment in config.py

```python
EXPERIMENT_BATCH_SIZE = 5    # how many targets per experiment
EVALUATION_DAYS = 14         # how long to wait before judging
DATA_LAG_DAYS = 3            # delay in your analytics pipeline (e.g. GSC = 3 days)
MAX_CONCURRENT = 6           # max experiments running at the same time
MIN_EFFECT_SIZE = 0.03       # minimum lift to count as a win (0.03 = 3%)
```

### step 3: implement 5 functions in experiment.py

open `experiment.py`. near the top you'll find 5 functions that raise `NotImplementedError`. these are the only things you need to fill in.

#### 1. `select_targets()` - what to experiment on

return a list of dicts. each dict must have `id`, `name`, `current_state`, and `metric`.

```python
# example: SEO blog posts
def select_targets() -> list[dict]:
    posts = fetch_from_wordpress_api()  # your code
    gsc = fetch_from_google_search_console()  # your code
    return [
        {
            "id": str(post["id"]),
            "name": post["title"],
            "current_state": post["title"],  # stored for revert
            "metric": gsc.get(post["url"], {}).get("impressions", 0),
        }
        for post in posts
    ]
```

```python
# example: email subject lines
def select_targets() -> list[dict]:
    campaigns = fetch_from_mailchimp()  # your code
    return [
        {
            "id": str(c["id"]),
            "name": c["subject_line"],
            "current_state": c["subject_line"],
            "metric": c["open_rate"],
        }
        for c in campaigns
    ]
```

#### 2. `apply_strategy(target, strategy)` - make the change

takes one target + the STRATEGY dict. apply the change and return the new state as a string.

```python
# example: SEO - rewrite title via WordPress REST API
def apply_strategy(target: dict, strategy: dict) -> str:
    new_title = call_claude_to_rewrite(target["name"], strategy)  # your code
    update_wordpress_post(target["id"], new_title)  # your code
    return new_title
```

```python
# example: pricing - update a product price
def apply_strategy(target: dict, strategy: dict) -> str:
    new_price = calculate_new_price(target, strategy)  # your code
    update_shopify_product(target["id"], new_price)  # your code
    return str(new_price)
```

#### 3. `measure_targets(target_ids, start_date, end_date)` - get metrics

return a dict of `{target_id: metric_value}` for the given date range.

```python
# example: SEO - pull impressions from Google Search Console
def measure_targets(target_ids, start_date, end_date) -> dict:
    gsc_data = query_gsc_for_period(start_date, end_date)  # your code
    return {tid: gsc_data.get(tid, {}).get("impressions", 0) for tid in target_ids}
```

```python
# example: email - pull open rates from your ESP
def measure_targets(target_ids, start_date, end_date) -> dict:
    return {tid: get_campaign_open_rate(tid) for tid in target_ids}  # your code
```

#### 4. `measure_control(start_date, end_date)` - baseline metric

return a single number: the metric for everything NOT in experiments, over the same period. this is the control group that prevents you from confusing seasonal trends with real improvement.

```python
# example: SEO - site-wide impressions minus experiment URLs
def measure_control(start_date, end_date) -> float:
    all_data = query_gsc_for_period(start_date, end_date)
    experiment_urls = get_all_experiment_urls()  # from db
    control = {url: d for url, d in all_data.items() if url not in experiment_urls}
    return sum(d["impressions"] for d in control.values())
```

```python
# example: email - average open rate of non-experiment campaigns
def measure_control(start_date, end_date) -> float:
    all_campaigns = get_campaigns_in_period(start_date, end_date)
    experiment_ids = get_active_target_ids()  # from db
    control = [c for c in all_campaigns if c["id"] not in experiment_ids]
    return sum(c["open_rate"] for c in control) / len(control)
```

#### 5. `revert_target(target_id, old_state)` - undo the change

restore a target to its original state. `old_state` is whatever string you returned from `apply_strategy`.

```python
# example: SEO - push old title back to WordPress
def revert_target(target_id: str, old_state: str):
    update_wordpress_post(target_id, old_state)
```

```python
# example: pricing - restore original price
def revert_target(target_id: str, old_state: str):
    update_shopify_product(target_id, float(old_state))
```

```python
# example: email - can't unsend, so no-op
def revert_target(target_id: str, old_state: str):
    pass  # emails can't be reverted
```

### step 4: test it

```bash
# verify your functions work
python experiment.py --health

# run one cycle manually
python experiment.py

# check results
python experiment.py --tick     # evaluate mature experiments
```

### step 5: run autonomously via cron

```bash
# add to crontab - runs every morning at 6am
0 6 * * * cd /path/to/my-experiment && claude --dangerously-skip-permissions -p "$(cat program.md)"
```

Claude Code wakes up, reads program.md, checks git history for past hypotheses, evaluates any mature experiments, and starts a new one with a fresh hypothesis. every hypothesis becomes a git commit, so Claude's knowledge compounds over time.

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
  template/           # copy this to start a new project
    program.md        # protocol file Claude reads each run
    experiment.py     # strategy (top) + infrastructure (bottom)
    config.py         # tunable parameters
    db.py             # SQLite storage (zero external deps)
  examples/
    seo-demo/         # runnable demo with real article titles, simulated metrics
  skill/
    SKILL.md          # Claude Code skill definition (/autoresearch)
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
