"""Playwright-only backend with separate, resettable test data; binds loopback."""
import json

import uvicorn

from .main import create_app
from .store import ROOT

app = create_app(ROOT / "backend" / "data" / "e2e.sqlite3")
with app.state.store.transaction() as state:
    state.clear()
    state.update(json.loads((ROOT / "fixtures" / "seed.json").read_text(encoding="utf-8")))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
