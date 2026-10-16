"""Simulate a new batch of source activity (late lines, restatements, duplicates, price changes).

    python -m generator.simulate
    python -m generator.simulate --late-lines 5000 --price-changes 5

Run it between two `python -m el.run` calls to watch the incremental load pick up only
the changed rows, and between dbt runs to see the medicine price snapshot record history.
"""

from __future__ import annotations

import argparse

from .db import REPO_ROOT, SqlServerSettings, connect

BATCH_SQL = REPO_ROOT / "sql_server" / "simulate" / "new_batch.sql"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m generator.simulate", description=__doc__.splitlines()[0])
    p.add_argument("--late-lines", type=int, default=2000)
    p.add_argument("--restatements", type=int, default=500)
    p.add_argument("--duplicates", type=int, default=20)
    p.add_argument("--price-changes", type=int, default=3)
    args = p.parse_args(argv)

    with connect(SqlServerSettings(), autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute(BATCH_SQL.read_text(encoding="utf-8"),
                    args.late_lines, args.restatements, args.duplicates, args.price_changes)
        while cur.description is None and cur.nextset():
            pass
        for action, count in cur.fetchall():
            print(f"  {action:<28} {count:>6,}")


if __name__ == "__main__":
    main()
