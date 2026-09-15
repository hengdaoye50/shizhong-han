"""SQLite schema for 两汉侍中库（试点版）。

用法:
  python sources/init_db.py
  python sources/import_pilot.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS person (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  style_name TEXT,
  dynasty TEXT,                 -- 西漢|新|東漢|漢魏之際
  category TEXT,                -- 逗号分隔
  origin TEXT,
  birth TEXT,
  death TEXT,
  status TEXT DEFAULT '待审',   -- 已校
  notes TEXT
);

CREATE TABLE IF NOT EXISTS source (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book TEXT NOT NULL,
  juan TEXT,
  quote TEXT,
  path TEXT
);

CREATE TABLE IF NOT EXISTS shizhong_term (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id TEXT NOT NULL REFERENCES person(id),
  start_ym TEXT,
  end_ym TEXT,
  nature TEXT,                  -- 加官|正职|复合官等
  evidence TEXT,                -- 有明文|推断|阙疑
  source_id INTEGER REFERENCES source(id),
  UNIQUE(person_id, start_ym, end_ym, nature, source_id)
);

CREATE TABLE IF NOT EXISTS relation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_id TEXT,
  from_name TEXT NOT NULL,
  to_id TEXT,
  to_name TEXT NOT NULL,
  rel_type TEXT NOT NULL,
  note TEXT,
  status TEXT DEFAULT '草稿',
  source_id INTEGER REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS candidate (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book TEXT, juan TEXT, source_kind TEXT, source_file TEXT,
  match_type TEXT, hint_name TEXT, sentence TEXT,
  status TEXT, person TEXT, role_note TEXT, review_note TEXT,
  cand_row INTEGER, pilot TEXT
);

CREATE INDEX IF NOT EXISTS idx_person_name ON person(name);
CREATE INDEX IF NOT EXISTS idx_term_person ON shizhong_term(person_id);
CREATE INDEX IF NOT EXISTS idx_rel_from ON relation(from_name);
CREATE INDEX IF NOT EXISTS idx_rel_to ON relation(to_name);
CREATE INDEX IF NOT EXISTS idx_cand_status ON candidate(status);
"""


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.commit()
    con.close()
    print("schema ready ->", DB)


if __name__ == "__main__":
    main()
