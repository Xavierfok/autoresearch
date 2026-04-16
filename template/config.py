"""autoresearch configuration.

customize these values for your domain.
"""
import os

# experiment parameters
EXPERIMENT_BATCH_SIZE = 5       # targets per experiment
EVALUATION_DAYS = 14            # days to wait before evaluating
DATA_LAG_DAYS = 3               # days of data delay (e.g. analytics lag)
MAX_CONCURRENT = 6              # max running experiments at once
MIN_EFFECT_SIZE = 0.03          # minimum relative lift to keep (3%)

# database
DB_PATH = os.path.join(os.path.dirname(__file__), "autoresearch.db")

# alerts (optional - set env vars to enable)
ALERT_WEBHOOK = os.getenv("AUTORESEARCH_WEBHOOK", "")
