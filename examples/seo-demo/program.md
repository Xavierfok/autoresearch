# autoresearch: SEO demo

this is a demo of the autoresearch pattern applied to SEO content optimization.
it uses fake blog posts and simulated metrics - no external APIs needed.

## quick start

```bash
cd examples/seo-demo
python experiment.py --simulate    # run 3 full cycles
python experiment.py --history     # see results
```

## what happens in the simulation

1. Claude "edits" the strategy section with a new hypothesis
2. the engine evaluates any mature experiments (keep or revert)
3. the engine applies the new strategy to a batch of blog posts
4. metrics are simulated with random variance
5. after the wait period, experiments are evaluated against a control group
6. winners are kept, losers are reverted

## the real version

the production SEO optimizer at dataresearchtools.com does the same thing but:
- fetches real posts from WordPress REST API
- measures real clicks/impressions from Google Search Console
- waits 17 days (14 + 3 day GSC lag) before evaluating
- reverts losers by pushing old content back to WordPress
- runs via cron every morning at 6am
- Claude Code reads program.md and autonomously decides the next hypothesis
