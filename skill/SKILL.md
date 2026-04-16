---
name: autoresearch
description: Scaffold and run autonomous experiment loops. Claude asks simple questions, builds everything, runs the loop. Works for SEO, email, pricing, ads - anything measurable.
---

# /autoresearch

autonomous experimentation framework. Claude asks you a few questions, builds the project, and runs experiments on your behalf.

## commands

- `/autoresearch` or `/autoresearch init` - set up a new experiment (interactive)
- `/autoresearch run` - execute one experiment cycle
- `/autoresearch tick` - evaluate mature experiments only
- `/autoresearch history` - show results
- `/autoresearch demo` - run the built-in demo with simulated data

## init - interactive setup

when the user runs `/autoresearch` or `/autoresearch init`, walk them through setup by asking these questions one at a time. keep it conversational. do NOT dump all questions at once.

### question 1: what are you experimenting on?

ask: "what do you want to experiment on? describe it in plain english."

examples of what users might say:
- "blog post titles on my WordPress site"
- "email subject lines in Mailchimp"
- "product prices on my Shopify store"
- "landing page headlines"
- "ad copy on Google Ads"

from the answer, determine:
- **target type** (blog posts, emails, products, pages, ads)
- **what gets changed** (titles, subject lines, prices, headlines, copy)

### question 2: how do you measure success?

ask: "how do you measure whether a change worked? what metric and where does it come from?"

examples:
- "Google Search Console clicks and impressions"
- "open rate and CTR from Mailchimp"
- "conversion rate from Shopify analytics"
- "signup rate from Google Analytics"

from the answer, determine:
- **metric** (clicks, open rate, conversion rate, etc.)
- **data source** (GSC, Mailchimp, Shopify, GA4, etc.)

### question 3: how do you connect?

ask: "how do I connect to [their platform]? do you have API credentials, or should I use a REST API with auth?"

the user might say:
- "I have a WordPress app password" -> use WP REST API with Basic Auth
- "I have a GSC service account JSON" -> use google-auth + GSC API
- "I have a Mailchimp API key" -> use Mailchimp API
- "I have a Shopify admin token" -> use Shopify Admin API
- "just use mock data for now" -> generate simulated adapters like the demo

collect whatever credentials/endpoints they provide. store in a `.env` file (gitignored).

### question 4: tuning

ask: "a few quick settings. just hit enter for defaults:"

present each with a sensible default based on their domain:
- "how many [targets] per experiment?" (default: 5)
- "how many days to wait before judging?" (default: 14 for SEO, 7 for email, 3 for pricing)
- "minimum lift to keep a winner?" (default: 3%)

### then: build it

after all questions are answered:

1. copy template files (`program.md`, `experiment.py`, `config.py`, `db.py`) into the current directory
2. fill in `config.py` with the user's settings
3. implement all 5 adapter functions in `experiment.py` based on what they told you:
   - `select_targets()` - fetch targets from their platform
   - `apply_strategy(target, strategy)` - make changes via their API
   - `measure_targets(target_ids, start, end)` - pull metrics from their analytics
   - `measure_control(start, end)` - pull control group metrics
   - `revert_target(target_id, old_state)` - restore originals via their API
4. create `.env` with their credentials (gitignored)
5. add `.env` to `.gitignore`
6. run `python experiment.py --health` to verify connections
7. `git init && git add -A && git commit -m "init autoresearch"`

tell the user: "done. run `/autoresearch run` to start your first experiment, or set up cron for autonomous mode."

## run

when the user says `/autoresearch run`:

1. read `program.md` for the protocol
2. read `experiment.py` to see current strategy
3. read `git log` for past hypotheses
4. run `python experiment.py --tick` to evaluate mature experiments
5. if room for new experiments:
   a. analyze past results
   b. generate a new, distinct hypothesis
   c. edit ONLY the strategy section at the top of `experiment.py`
   d. `git add experiment.py && git commit -m "experiment: <hypothesis>"`
   e. run `python experiment.py`
   f. verify success

## how it works (for Claude, not the user)

### the editable boundary

`experiment.py` has two sections separated by a comment line:

```
TOP: HYPOTHESIS + STRATEGY dict  ->  Claude edits this
---------- DO NOT EDIT BELOW ----------
BOTTOM: evaluation, rollback, infra  ->  Claude never touches this
```

### git as memory

each hypothesis becomes a git commit. Claude reads `git log` before every run to understand what was tried and what worked. knowledge compounds.

### auto-revert

if relative lift < threshold, experiment posts get reverted to original content automatically.

## cron setup

when the user asks about autonomous mode, set up a cron/launchd job:
```
0 6 * * * cd /path/to/project && claude --dangerously-skip-permissions -p "$(cat program.md)"
```
