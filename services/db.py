import sqlite3, os
BASE = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(BASE, 'healthcare_pm.db')
SCHEMA = os.path.join(BASE, 'schema.sql')
SEED = os.path.join(BASE, 'seed_data.sql')

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with get_db() as c:
        c.executescript(open(SCHEMA).read())
        if c.execute("SELECT COUNT(*) FROM project_charter").fetchone()[0] == 0:
            c.executescript(open(SEED).read())

def q(sql, args=(), one=False):
    with get_db() as c:
        rows = c.execute(sql, args).fetchall()
        return (rows[0] if rows else None) if one else rows

def run(sql, args=()):
    with get_db() as c:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid

def qd(sql, args=(), one=False):
    """Return plain dicts (JSON-serialisable)."""
    rows = q(sql, args, one)
    if one:
        return dict(rows) if rows else None
    return [dict(r) for r in rows]
