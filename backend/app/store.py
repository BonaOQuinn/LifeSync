"""Atomic, durable local prototype storage. No cloud credentials are required."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self.connect()
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            if not connection.execute("SELECT 1 FROM state WHERE id = 1").fetchone():
                fixture = json.loads((ROOT / "fixtures" / "seed.json").read_text(encoding="utf-8"))
                connection.execute("INSERT INTO state VALUES (1, ?)", (json.dumps(fixture),))
            connection.commit()
        finally:
            connection.close()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    @contextmanager
    def transaction(self):
        # BEGIN IMMEDIATE serializes competing writes across threads and workers.
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            state = json.loads(connection.execute("SELECT data FROM state WHERE id = 1").fetchone()[0])
            yield state
            connection.execute("UPDATE state SET data = ? WHERE id = 1", (json.dumps(state),))
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def snapshot(self):
        connection = self.connect()
        try:
            return json.loads(connection.execute("SELECT data FROM state WHERE id = 1").fetchone()[0])
        finally:
            connection.close()
