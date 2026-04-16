"""demo config - simulates an SEO experiment on fake blog posts."""
import os

EXPERIMENT_BATCH_SIZE = 3
EVALUATION_DAYS = 1          # 1 day for demo (real: 14)
DATA_LAG_DAYS = 0            # no lag for demo (real: 3)
MAX_CONCURRENT = 3
MIN_EFFECT_SIZE = 0.03

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")
ALERT_WEBHOOK = ""
