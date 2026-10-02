"""Run while the backend is stopped: python seed.py --reset."""
import argparse
import json
import os
from pathlib import Path

from app.store import ROOT, Store

parser = argparse.ArgumentParser(description="Initialize or reset synthetic LifeSync state.")
parser.add_argument("--reset", action="store_true", help="Replace saved prototype cases with fresh fixtures.")
args = parser.parse_args()
path = Path(os.getenv("LIFESYNC_DB_PATH", str(ROOT / "backend" / "data" / "state.sqlite3")))
existed = path.exists()
store = Store(path)
if args.reset:
    with store.transaction() as state:
        state.clear()
        state.update(json.loads((ROOT / "fixtures" / "seed.json").read_text(encoding="utf-8")))
    print("Reset synthetic clients, cases, tasks, and history.")
else:
    print("Existing state preserved." if existed else "Initialized synthetic fixtures.")
