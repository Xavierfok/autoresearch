#!/usr/bin/env python3
"""autoresearch demo: simulated SEO experiment engine.

runs the full autoresearch loop on fake blog posts with simulated metrics.
no external APIs needed - everything is local.

usage:
    python experiment.py              # full run
    python experiment.py --tick       # evaluate only
    python experiment.py --health     # check setup
    python experiment.py --simulate   # run 3 full cycles (for demo)
"""

# ---- experiment strategy (edited by Claude) ----

HYPOTHESIS = "add power words and numbers to titles for higher CTR"

STRATEGY = {
    "title": "add a number and a power word (proven, essential, ultimate) to the title",
    "meta": "start with an action verb, include the target keyword in first 50 chars",
    "intro": "open with a surprising statistic or bold claim",
    "headings": "make headings question-based to match search intent",
}

# ================================================================
# FIXED INFRASTRUCTURE BELOW - DO NOT EDIT
# ================================================================

import argparse
import json
import random
import sys
import os
import time
from datetime import datetime, timedelta, timezone

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


# --- real articles from dataresearchtools.com (simulated metrics) ---

FAKE_POSTS = [
    {"id": "8505", "name": "best web scraping tools in 2026: the mega comparison guide", "metric": 340},
    {"id": "8504", "name": "build a RAG chatbot with web scraping: the complete python tutorial", "metric": 180},
    {"id": "8495", "name": "how to benchmark proxy providers: a rigorous methodology", "metric": 220},
    {"id": "8492", "name": "build a news crawler in python: step-by-step tutorial", "metric": 160},
    {"id": "8488", "name": "proxy industry report 2026: market size, trends, and forecasts", "metric": 280},
    {"id": "6096", "name": "best Philippines proxy providers 2026: Filipino IP address guide", "metric": 95},
    {"id": "6090", "name": "best Thailand proxy providers 2026: Thai IP addresses for every use case", "metric": 110},
    {"id": "843", "name": "mobile proxies for SEO rank tracking and SERP monitoring", "metric": 420},
    {"id": "842", "name": "proxy authentication methods: IP whitelisting vs username/password", "metric": 150},
    {"id": "799", "name": "proxy automation: scripting multi-account workflows with mobile proxies", "metric": 190},
]


def select_targets() -> list[dict]:
    """return fake blog posts as targets."""
    active = get_active_target_ids()
    eligible = [
        {**p, "current_state": p["name"]}
        for p in FAKE_POSTS
        if p["id"] not in active
    ]
    eligible.sort(key=lambda x: x["metric"], reverse=True)
    return eligible[:EXPERIMENT_BATCH_SIZE]


def apply_strategy(target: dict, strategy: dict) -> str:
    """simulate applying strategy - realistic title rewrite."""
    title = target["name"]
    # strip existing year tags and prefixes
    clean = title.split(":")[0].strip() if ":" in title else title

    rewrites = {
        "add number + power word": lambda t: f"{random.randint(7,15)} proven strategies for {t.lower()}",
        "rewrite as question": lambda t: f"what's the best approach to {t.lower()}?",
        "prepend (2026)": lambda t: f"(2026 updated) {t}",
        "action verb opener": lambda t: f"master {t.lower()} today",
    }

    style = strategy.get("title", "add number + power word")
    rewrite_fn = rewrites.get(style, rewrites["add number + power word"])
    return rewrite_fn(clean)


def measure_targets(target_ids: list[str], start_date, end_date) -> dict:
    """simulate metrics with some random variance."""
    result = {}
    for tid in target_ids:
        post = next((p for p in FAKE_POSTS if p["id"] == tid), None)
        if post:
            base = post["metric"]
            # add random variance (-20% to +30%)
            noise = random.uniform(-0.2, 0.3)
            result[tid] = base * (1 + noise)
    return result


def measure_control(start_date, end_date) -> float:
    """simulate control group metric."""
    base = sum(p["metric"] for p in FAKE_POSTS) / len(FAKE_POSTS)
    # control has smaller variance
    noise = random.uniform(-0.05, 0.05)
    return base * (1 + noise)


def revert_target(target_id: str, old_state: str):
    """simulate reverting a post."""
    print(f"    reverting {target_id} -> {old_state[:50]}")


# --- evaluation math ---

def compute_relative_lift(batch_pre, batch_post, control_pre, control_post) -> float:
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
    any_reverted = False

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
        pre_start = (started - timedelta(days=EVALUATION_DAYS)).date()
        pre_end = started.date()
        post_start = started.date()
        post_end = (started + timedelta(days=EVALUATION_DAYS)).date()

        targets = get_targets(exp_id)
        target_ids = [t["target_id"] for t in targets]

        print(f"\n[evaluate] experiment {exp_id}: {exp['hypothesis'][:60]}")

        batch_pre_data = measure_targets(target_ids, pre_start, pre_end)
        batch_post_data = measure_targets(target_ids, post_start, post_end)
        batch_pre = sum(batch_pre_data.values())
        batch_post = sum(batch_post_data.values())

        control_pre = measure_control(pre_start, pre_end)
        control_post = measure_control(post_start, post_end)

        lift = compute_relative_lift(batch_pre, batch_post, control_pre, control_post)
        verdict = verdict_from_lift(lift)

        print(f"  batch: {batch_pre:.0f} -> {batch_post:.0f}")
        print(f"  control: {control_pre:.0f} -> {control_post:.0f}")
        print(f"  relative lift: {lift:+.4f}  verdict: {verdict}")

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
        else:
            print(f"  -> KEPT")

    return any_reverted


def start_experiment() -> str | None:
    if not STRATEGY:
        print("[start] no strategy set")
        return None

    running = count_running()
    if running >= MAX_CONCURRENT:
        print(f"[start] {running} running (max {MAX_CONCURRENT})")
        return None

    targets = select_targets()
    if len(targets) < EXPERIMENT_BATCH_SIZE:
        print(f"[start] only {len(targets)} eligible (need {EXPERIMENT_BATCH_SIZE})")
        return None

    batch = targets[:EXPERIMENT_BATCH_SIZE]
    exp_id = create_experiment(HYPOTHESIS, STRATEGY, len(batch))
    print(f"\n[start] experiment {exp_id}: {HYPOTHESIS[:60]}")

    for i, target in enumerate(batch):
        print(f"  [{i+1}/{len(batch)}] {target['name'][:50]}...")
        new_state = apply_strategy(target, STRATEGY)
        insert_target(exp_id, target["id"], target["name"], target["current_state"], new_state, target.get("metric", 0))
        print(f"    -> {new_state[:60]}")

    now = datetime.now(timezone.utc).isoformat()
    update_experiment(exp_id, {"status": "running", "started_at": now, "batch_size": len(batch)})
    print(f"\n  {len(batch)} targets applied. status=running")
    return exp_id


def show_history():
    """print experiment history table."""
    exps = get_experiments()
    if not exps:
        print("\nno experiments yet.")
        return

    print(f"\n{'='*70}")
    print(f"{'id':<10} {'status':<18} {'lift':>8}  {'hypothesis':<30}")
    print(f"{'-'*10} {'-'*18} {'-'*8}  {'-'*30}")
    for e in exps:
        lift = e.get("relative_lift", 0) or 0
        lift_str = f"{lift:+.4f}" if lift else "   -   "
        status = e.get("status", "?")
        # color the status
        if status == "kept":
            status_display = f"\033[32m{status:<18}\033[0m"
        elif status == "reverted":
            status_display = f"\033[31m{status:<18}\033[0m"
        elif status == "running":
            status_display = f"\033[33m{status:<18}\033[0m"
        else:
            status_display = f"{status:<18}"
        print(f"{e['id']:<10} {status_display} {lift_str:>8}  {e['hypothesis'][:30]}")
    print(f"{'='*70}")


# --- presentation helpers ---

G = "\033[32m"   # green
R = "\033[31m"   # red
Y = "\033[33m"   # yellow
D = "\033[90m"   # dim
B = "\033[1m"    # bold
U = "\033[4m"    # underline
X = "\033[0m"    # reset


def typewrite(text, delay=0.03):
    """print text character by character."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def slow_print(text, pause=0.0):
    """print with optional pause after."""
    print(text)
    if pause:
        time.sleep(pause)


def thinking(message, duration=1.5):
    """show a thinking spinner."""
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  {D}{frames[i % 4]} {message}{X}  ")
        sys.stdout.flush()
        time.sleep(0.15)
        i += 1
    sys.stdout.write(f"\r  {G}+ {message}{X}  \n")


def banner(text, width=70):
    print(f"\n{G}{'=' * width}{X}")
    print(f"{G}{B}  {text}{X}")
    print(f"{G}{'=' * width}{X}")


def sub_banner(text):
    print(f"\n  {D}--- {text} ---{X}")


def show_boundary(hypothesis, strategy):
    """show the editable boundary being modified."""
    print(f"\n  {D}experiment.py:{X}")
    print(f"  {D}+--------------------------------------------+{X}")
    print(f"  {D}|{X} {G}# strategy section (edited by Claude){X}       {D}|{X}")
    print(f"  {D}|{X}                                            {D}|{X}")
    print(f"  {D}|{X} {G}HYPOTHESIS{X} = {Y}\"{hypothesis[:35]}\"{X}")
    for k, v in strategy.items():
        print(f"  {D}|{X} {G}STRATEGY[\"{k}\"]{X} = {Y}\"{v[:28]}\"{X}")
    print(f"  {D}|{X}                                            {D}|{X}")
    print(f"  {D}|{X} {R}{B}# ======= DO NOT EDIT BELOW ======={X}        {D}|{X}")
    print(f"  {D}|{X} {D}def evaluate_mature(): ...{X}                {D}|{X}")
    print(f"  {D}|{X} {D}def start_experiment(): ...{X}               {D}|{X}")
    print(f"  {D}|{X} {D}def revert_experiment(): ...{X}              {D}|{X}")
    print(f"  {D}+--------------------------------------------+{X}")


def verdict_reveal(lift, verdict):
    """dramatic verdict reveal."""
    time.sleep(0.8)
    sys.stdout.write(f"\n  relative lift: ")
    time.sleep(0.5)

    if lift > 0:
        sys.stdout.write(f"{G}{B}{lift:+.1%}{X}")
    else:
        sys.stdout.write(f"{R}{B}{lift:+.1%}{X}")
    time.sleep(0.5)

    sys.stdout.write(f"  ...  ")
    time.sleep(1.0)

    if verdict == "kept":
        print(f"{G}{B}KEPT{X}")
    elif verdict == "reverted":
        print(f"{R}{B}REVERTED{X}")
    else:
        print(f"{Y}{B}INCONCLUSIVE (kept){X}")
    print()


# --- simulation mode ---

DEMO_CYCLES = [
    {
        "hypothesis": "add power words and numbers to titles",
        "strategy": {"title": "add number + power word", "meta": "action verb opener"},
        # rigged: batch improves 12%, control flat -> kept
        "batch_pre": 480, "batch_post": 538,
        "control_pre": 121, "control_post": 123,
    },
    {
        "hypothesis": "question-based titles matching search intent",
        "strategy": {"title": "rewrite as question", "meta": "direct answer"},
        # rigged: batch drops 8%, control up 2% -> reverted
        "batch_pre": 510, "batch_post": 469,
        "control_pre": 118, "control_post": 120,
    },
    {
        "hypothesis": "year tags and freshness signals (2026 updated)",
        "strategy": {"title": "prepend (2026)", "meta": "latest + updated"},
        # rigged: batch improves 7%, control flat -> kept
        "batch_pre": 465, "batch_post": 498,
        "control_pre": 122, "control_post": 121,
    },
]


def simulate_evaluate(exp_id, cycle_data) -> str:
    """evaluate with predetermined metrics for a repeatable demo."""
    batch_pre = cycle_data["batch_pre"]
    batch_post = cycle_data["batch_post"]
    control_pre = cycle_data["control_pre"]
    control_post = cycle_data["control_post"]

    lift = compute_relative_lift(batch_pre, batch_post, control_pre, control_post)
    verdict = verdict_from_lift(lift)

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

    return verdict, lift, batch_pre, batch_post, control_pre, control_post


def simulate():
    """run 3 experiment cycles as a live presentation demo."""

    print(f"\n{D}{'.' * 70}{X}")
    time.sleep(0.3)
    banner("AUTORESEARCH DEMO")
    slow_print(f"\n  {D}simulating 3 autonomous experiment cycles{X}")
    slow_print(f"  {D}in production this runs daily via cron at 6am{X}\n", 1.5)

    exp_ids = []

    for i, cycle in enumerate(DEMO_CYCLES):
        # --- cycle header ---
        print(f"\n{G}{'*' * 70}{X}")
        print(f"{G}{B}  CYCLE {i+1}/3{X}")
        print(f"{G}{'*' * 70}{X}")
        time.sleep(1.0)

        # --- step 1: Claude reads state ---
        sub_banner("step 1: read state")
        thinking("reading git log for past hypotheses", 1.2)
        thinking("querying database for running experiments", 0.8)
        if exp_ids:
            slow_print(f"  {D}found {len(exp_ids)} past experiment(s){X}", 0.5)
        else:
            slow_print(f"  {D}no prior experiments - starting fresh{X}", 0.5)

        # --- step 2: evaluate mature experiments ---
        if exp_ids:
            sub_banner("step 2: evaluate mature experiments")
            prev_id = exp_ids[-1]
            prev_cycle = DEMO_CYCLES[i - 1]

            thinking("pulling metrics for experiment batch (17 days of data)", 1.5)
            thinking("pulling control group baseline", 0.8)

            verdict, lift, bp, bpo, cp, cpo = simulate_evaluate(prev_id, prev_cycle)

            slow_print(f"\n  experiment {Y}{prev_id}{X}: {prev_cycle['hypothesis']}")
            slow_print(f"  batch:   {D}{bp} -> {bpo} impressions{X}")
            slow_print(f"  control: {D}{cp} -> {cpo} impressions{X}")

            verdict_reveal(lift, verdict)

            if verdict == "reverted":
                slow_print(f"  {R}reverting posts to original copy...{X}", 0.3)
                targets = get_targets(prev_id)
                for t in targets:
                    slow_print(f"    {R}>{X} {D}restoring:{X} {t['target_name'][:45]}", 0.3)
                    if t.get("old_state"):
                        revert_target(t["target_id"], t["old_state"])
                update_experiment(prev_id, {"status": "reverted"})
                slow_print(f"\n  {D}original copy restored. no damage done.{X}", 1.0)
            else:
                slow_print(f"  {G}winners stay live. the site just got better.{X}", 1.0)
        else:
            sub_banner("step 2: evaluate")
            slow_print(f"  {D}no mature experiments to evaluate yet{X}", 0.5)

        # --- step 3: Claude generates hypothesis ---
        sub_banner("step 3: generate new hypothesis")
        if exp_ids:
            thinking("analyzing what worked and what didn't", 1.5)
        thinking("generating new hypothesis (must be distinct from all previous)", 1.2)

        global HYPOTHESIS, STRATEGY
        HYPOTHESIS = cycle["hypothesis"]
        STRATEGY = cycle["strategy"]

        time.sleep(0.3)
        typewrite(f"  {G}hypothesis:{X} {B}{HYPOTHESIS}{X}", 0.025)
        time.sleep(0.5)

        # --- step 4: edit strategy ---
        sub_banner("step 4: edit experiment.py")
        thinking("editing strategy section", 0.8)
        show_boundary(HYPOTHESIS, STRATEGY)
        time.sleep(0.8)

        slow_print(f"\n  {D}$ git add experiment.py{X}", 0.3)
        slow_print(f"  {D}$ git commit -m \"experiment: {HYPOTHESIS[:40]}...\"{X}", 0.8)

        # --- step 5: apply ---
        sub_banner("step 5: apply to targets")
        targets = select_targets()
        batch = targets[:EXPERIMENT_BATCH_SIZE]
        exp_id = create_experiment(HYPOTHESIS, STRATEGY, len(batch))

        for j, target in enumerate(batch):
            time.sleep(0.4)
            new_state = apply_strategy(target, STRATEGY)
            insert_target(exp_id, target["id"], target["name"], target["current_state"], new_state, target.get("metric", 0))
            slow_print(f"  [{j+1}/{len(batch)}] {target['name'][:40]}")
            slow_print(f"       {D}->{X} {Y}{new_state[:55]}{X}")

        now = datetime.now(timezone.utc).isoformat()
        # backdate so next cycle can evaluate it
        old_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        update_experiment(exp_id, {"status": "running", "started_at": old_date, "batch_size": len(batch)})
        exp_ids.append(exp_id)

        slow_print(f"\n  {G}{len(batch)} posts updated on live site. now we wait.{X}", 0.5)
        slow_print(f"  {D}(in production: 17 days. for this demo: instant){X}", 1.5)

    # --- final evaluation ---
    print(f"\n{G}{'*' * 70}{X}")
    print(f"{G}{B}  FINAL EVALUATION{X}")
    print(f"{G}{'*' * 70}{X}")
    time.sleep(1.0)

    last_id = exp_ids[-1]
    last_cycle = DEMO_CYCLES[-1]

    thinking("pulling final metrics", 1.2)
    verdict, lift, bp, bpo, cp, cpo = simulate_evaluate(last_id, last_cycle)

    slow_print(f"\n  experiment {Y}{last_id}{X}: {last_cycle['hypothesis']}")
    slow_print(f"  batch:   {D}{bp} -> {bpo} impressions{X}")
    slow_print(f"  control: {D}{cp} -> {cpo} impressions{X}")

    verdict_reveal(lift, verdict)

    if verdict == "reverted":
        targets = get_targets(last_id)
        for t in targets:
            if t.get("old_state"):
                revert_target(t["target_id"], t["old_state"])
        update_experiment(last_id, {"status": "reverted"})

    # --- scoreboard ---
    banner("EXPERIMENT SCOREBOARD")
    show_history()

    # --- closing ---
    print(f"\n  {B}this runs every morning at 6am. no human in the loop.{X}")
    print(f"  {D}Claude reads program.md, checks git history, picks a new hypothesis,{X}")
    print(f"  {D}edits the strategy, applies it, and waits. losers get auto-reverted.{X}")
    print(f"  {D}the site compounds improvements over time.{X}")
    print(f"\n  {G}{B}github.com/xavierfok/autoresearch{X}")
    print(f"  {D}clone it. implement 5 functions. let Claude experiment for you.{X}\n")


# --- entry point ---

def main():
    parser = argparse.ArgumentParser(description="autoresearch demo")
    parser.add_argument("--tick", action="store_true", help="evaluate only")
    parser.add_argument("--health", action="store_true", help="health check")
    parser.add_argument("--simulate", action="store_true", help="run 3 demo cycles")
    parser.add_argument("--history", action="store_true", help="show experiment history")
    args = parser.parse_args()

    if args.health:
        print("[health] database: ok")
        print("[health] fake posts: ok")
        return

    if args.simulate:
        # clean slate for demo
        db_path = os.path.join(os.path.dirname(__file__), "demo.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        from db import init_db
        init_db()
        simulate()
        return

    if args.history:
        show_history()
        return

    print("=" * 50)
    print(f"autoresearch demo - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    any_reverted = evaluate_mature()
    if args.tick:
        print("\n[tick mode] done")
    elif any_reverted:
        print("\n[start] reverts happened. skipping.")
    else:
        start_experiment()

    show_history()


if __name__ == "__main__":
    main()
