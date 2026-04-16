"""SQLite storage for autoresearch experiments.

zero-config, no external dependencies. the database file is created
automatically on first run.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma journal_mode=wal")
    return conn


def init_db():
    """create tables if they don't exist."""
    conn = _connect()
    conn.executescript("""
        create table if not exists experiments (
            id text primary key,
            hypothesis text not null,
            strategy text not null,
            status text not null default 'created',
            batch_size integer not null,
            started_at text,
            evaluated_at text,
            pre_metric real default 0,
            post_metric real default 0,
            control_pre real default 0,
            control_post real default 0,
            relative_lift real default 0,
            verdict text,
            created_at text default (datetime('now'))
        );

        create table if not exists experiment_targets (
            id text primary key,
            experiment_id text references experiments(id),
            target_id text not null,
            target_name text,
            old_state text,
            new_state text,
            pre_metric real default 0,
            post_metric real default 0,
            created_at text default (datetime('now'))
        );

        create index if not exists idx_exp_status on experiments(status);
        create index if not exists idx_et_exp on experiment_targets(experiment_id);
    """)
    conn.commit()
    conn.close()


def create_experiment(hypothesis: str, strategy: dict, batch_size: int) -> str:
    """create a new experiment. returns id."""
    conn = _connect()
    exp_id = str(uuid.uuid4())[:8]
    conn.execute(
        "insert into experiments (id, hypothesis, strategy, batch_size) values (?, ?, ?, ?)",
        (exp_id, hypothesis, json.dumps(strategy), batch_size),
    )
    conn.commit()
    conn.close()
    return exp_id


def update_experiment(exp_id: str, updates: dict):
    """update experiment fields."""
    conn = _connect()
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"update experiments set {sets} where id = ?", [*updates.values(), exp_id])
    conn.commit()
    conn.close()


def get_experiments(status: str = None) -> list[dict]:
    """get experiments, optionally filtered by status."""
    conn = _connect()
    if status:
        rows = conn.execute("select * from experiments where status = ? order by created_at", (status,)).fetchall()
    else:
        rows = conn.execute("select * from experiments order by created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mature_experiments(eval_days: int, lag_days: int) -> list[dict]:
    """get running experiments old enough to evaluate."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=eval_days + lag_days)).isoformat()
    conn = _connect()
    rows = conn.execute(
        "select * from experiments where status = 'running' and started_at <= ?", (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_running() -> int:
    return len(get_experiments("running"))


def insert_target(exp_id: str, target_id: str, target_name: str, old_state: str, new_state: str, pre_metric: float = 0):
    """record a target in an experiment."""
    conn = _connect()
    conn.execute(
        "insert into experiment_targets (id, experiment_id, target_id, target_name, old_state, new_state, pre_metric) values (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4())[:8], exp_id, target_id, target_name, old_state, new_state, pre_metric),
    )
    conn.commit()
    conn.close()


def get_targets(exp_id: str) -> list[dict]:
    """get all targets for an experiment."""
    conn = _connect()
    rows = conn.execute("select * from experiment_targets where experiment_id = ?", (exp_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_target_ids() -> set:
    """get target_ids currently in running experiments."""
    running = get_experiments("running")
    ids = set()
    for exp in running:
        for t in get_targets(exp["id"]):
            ids.add(t["target_id"])
    return ids


# auto-init on import
init_db()
