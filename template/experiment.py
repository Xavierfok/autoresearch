#!/usr/bin/env python3
"""autoresearch experiment runner.

the strategy section at the top is edited by Claude each experiment.
the infrastructure section below is fixed. do not edit below the line.

usage:
    python experiment.py              # full run (evaluate + apply)
    python experiment.py --tick       # evaluate only, no new experiment
    python experiment.py --health     # verify setup
"""

# ---- experiment strategy (edited by Claude) ----

HYPOTHESIS = "baseline: no strategy applied yet"

STRATEGY = {
    # add your domain-specific strategy keys here.
    # examples for SEO: "title", "meta", "intro", "headings"
    # examples for email: "subject_line", "preview_text", "cta"
    # examples for pricing: "price_point", "anchor", "framing"
}

# ================================================================
# FIXED INFRASTRUCTURE BELOW - DO NOT EDIT
# ================================================================

import argparse
import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    EXPERIMENT_BATCH_SIZE, EVALUATION_DAYS, DATA_LAG_DAYS,
    MAX_CONCURRENT, MIN_EFFECT_SIZE,
)
from db import (
    create_experiment, update_experiment, get_experiments,
    get_mature_experiments, count_running, insert_target,
    get_targets, get_active_target_ids,
)


# --- YOU IMPLEMENT THESE (adapter functions) ---

def select_targets() -> list[dict]:
    """return a list of eligible targets for experimentation.

    each target dict must have at minimum:
        {"id": str, "name": str, "current_state": str, "metric": float}

    override this function for your domain:
    - SEO: fetch WordPress posts + GSC impressions
    - email: fetch upcoming campaigns
    - pricing: fetch product catalog
    """
    raise NotImplementedError("implement select_targets() for your domain")


def apply_strategy(target: dict, strategy: dict) -> str:
    """apply the strategy to a single target. returns new_state string.

    override this function:
    - SEO: rewrite title/meta/intro via WordPress API
    - email: update subject line via ESP API
    - pricing: update price via your commerce API
    """
    raise NotImplementedError("implement apply_strategy() for your domain")


def measure_targets(target_ids: list[str], start_date, end_date) -> dict:
    """measure performance for a set of targets over a date range.

    returns {target_id: metric_value}

    override this function:
    - SEO: pull clicks/impressions from GSC
    - email: pull open rate/CTR from ESP
    - pricing: pull conversion rate from analytics
    """
    raise NotImplementedError("implement measure_targets() for your domain")


def measure_control(start_date, end_date) -> float:
    """measure the control group (everything NOT in experiments).

    returns a single metric value for the control group.
    used to compute relative lift (experiment change - control change).
    """
    raise NotImplementedError("implement measure_control() for your domain")


def revert_target(target_id: str, old_state: str):
    """restore a target to its original state.

    override this function:
    - SEO: push old title/content back to WordPress
    - email: (usually can't revert sent emails - make this a no-op)
    - pricing: restore original price
    """
    raise NotImplementedError("implement revert_target() for your domain")


# --- evaluation math ---

def compute_relative_lift(batch_pre, batch_post, control_pre, control_post) -> float:
    """relative lift = batch change - control change."""
    batch_change = (batch_post - batch_pre) / max(batch_pre, 0.001)
    control_change = (control_post - control_pre) / max(control_pre, 0.001)
    return batch_change - control_change


def verdict_from_lift(lift: float) -> str:
    if lift > MIN_EFFECT_SIZE:
        return "kept"
    elif lift < -MIN_EFFECT_SIZE:
        return "reverted"
    return "kept_inconclusive"


# --- core loop ---

def evaluate_mature() -> bool:
    """evaluate experiments that are old enough. returns True if any reverted."""
    any_reverted = False

    # complete incomplete reverts first
    for exp in get_experiments("reverting"):
        print(f"  completing revert for {exp['id']}...")
        for t in get_targets(exp["id"]):
            if t.get("old_state"):
                revert_target(t["target_id"], t["old_state"])
        update_experiment(exp["id"], {"status": "reverted"})
        any_reverted = True

    mature = get_mature_experiments(EVALUATION_DAYS, DATA_LAG_DAYS)
    if not mature:
        print("[evaluate] no mature experiments")
        return any_reverted

    for exp in mature:
        exp_id = exp["id"]
        started = datetime.fromisoformat(exp["started_at"])
        from datetime import timedelta
        pre_start = (started - timedelta(days=EVALUATION_DAYS)).date()
        pre_end = started.date()
        post_start = started.date()
        post_end = (started + timedelta(days=EVALUATION_DAYS)).date()

        targets = get_targets(exp_id)
        target_ids = [t["target_id"] for t in targets]

        print(f"\n[evaluate] experiment {exp_id}: {exp['hypothesis'][:60]}")

        # measure batch
        batch_pre_data = measure_targets(target_ids, pre_start, pre_end)
        batch_post_data = measure_targets(target_ids, post_start, post_end)
        batch_pre = sum(batch_pre_data.values())
        batch_post = sum(batch_post_data.values())

        # measure control
        control_pre = measure_control(pre_start, pre_end)
        control_post = measure_control(post_start, post_end)

        lift = compute_relative_lift(batch_pre, batch_post, control_pre, control_post)
        verdict = verdict_from_lift(lift)

        print(f"  batch: {batch_pre:.1f} -> {batch_post:.1f}")
        print(f"  control: {control_pre:.1f} -> {control_post:.1f}")
        print(f"  relative lift: {lift:.4f}, verdict: {verdict}")

        now = datetime.now(timezone.utc).isoformat()
        update_experiment(exp_id, {
            "status": "reverting" if verdict == "reverted" else verdict,
            "evaluated_at": now,
            "pre_metric": batch_pre,
            "post_metric": batch_post,
            "control_pre": control_pre,
            "control_post": control_post,
            "relative_lift": round(lift, 6),
            "verdict": verdict,
        })

        if verdict == "reverted":
            for t in targets:
                if t.get("old_state"):
                    revert_target(t["target_id"], t["old_state"])
            update_experiment(exp_id, {"status": "reverted"})
            any_reverted = True
            print(f"  REVERTED")
        else:
            print(f"  KEPT ({verdict})")

    return any_reverted


def start_experiment() -> str | None:
    """apply current strategy to a batch of targets. returns exp_id or None."""
    if not STRATEGY or HYPOTHESIS == "baseline: no strategy applied yet":
        print("[start] no strategy set. skipping.")
        return None

    running = count_running()
    if running >= MAX_CONCURRENT:
        print(f"[start] {running} running (max {MAX_CONCURRENT}). skipping.")
        return None

    targets = select_targets()
    active_ids = get_active_target_ids()
    eligible = [t for t in targets if t["id"] not in active_ids]

    if len(eligible) < EXPERIMENT_BATCH_SIZE:
        print(f"[start] only {len(eligible)} eligible (need {EXPERIMENT_BATCH_SIZE}). skipping.")
        return None

    batch = eligible[:EXPERIMENT_BATCH_SIZE]
    exp_id = create_experiment(HYPOTHESIS, STRATEGY, len(batch))
    print(f"\n[start] experiment {exp_id}: {HYPOTHESIS[:60]}")

    applied = []
    for i, target in enumerate(batch):
        print(f"  [{i+1}/{len(batch)}] {target['name'][:50]}...")
        try:
            new_state = apply_strategy(target, STRATEGY)
            insert_target(exp_id, target["id"], target["name"], target["current_state"], new_state, target.get("metric", 0))
            applied.append(target)
            print(f"    applied")
        except Exception as e:
            print(f"    failed: {e}")

    if not applied:
        update_experiment(exp_id, {"status": "failed"})
        return None

    now = datetime.now(timezone.utc).isoformat()
    update_experiment(exp_id, {"status": "running", "started_at": now, "batch_size": len(applied)})
    print(f"\n  {len(applied)} targets applied, status=running")
    return exp_id


# --- entry point ---

def main():
    parser = argparse.ArgumentParser(description="autoresearch experiment runner")
    parser.add_argument("--tick", action="store_true", help="evaluate only, no new experiment")
    parser.add_argument("--health", action="store_true", help="health check")
    args = parser.parse_args()

    if args.health:
        print("[health] checking setup...")
        try:
            from db import init_db
            init_db()
            print("  database: ok")
        except Exception as e:
            print(f"  database: FAIL ({e})")
        print("[health] done")
        return

    print("=" * 50)
    print(f"autoresearch - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    any_reverted = evaluate_mature()

    if args.tick:
        print("\n[tick mode] skipping new experiment")
    elif any_reverted:
        print("\n[start] reverts happened. skipping new experiment.")
    else:
        start_experiment()

    print(f"\n{'=' * 50}")
    print("done")


if __name__ == "__main__":
    main()
