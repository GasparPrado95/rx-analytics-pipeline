"""Delete the BigQuery datasets a CI run created (e.g. ci_pr7_stg_rx, ci_pr7_marts_rx).

    python scripts/drop_ci_datasets.py --prefix ci_pr7

Safety: only prefixes starting with "ci_" are accepted, so this can never touch prod datasets.
"""

from __future__ import annotations

import argparse
import os
import sys

SAFE_PREFIX = "ci_"


def check_prefix(prefix: str) -> None:
    if not prefix.startswith(SAFE_PREFIX) or len(prefix) <= len(SAFE_PREFIX):
        raise ValueError(f"refusing to delete datasets for prefix {prefix!r}: must start with {SAFE_PREFIX!r}")


def select_datasets(dataset_ids: list[str], prefix: str) -> list[str]:
    check_prefix(prefix)
    return sorted(d for d in dataset_ids if d == prefix or d.startswith(prefix + "_"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--prefix", required=True, help="CI dataset prefix, e.g. ci_pr7")
    p.add_argument("--project", default=os.getenv("GCP_PROJECT_ID"))
    args = p.parse_args(argv)
    try:
        check_prefix(args.prefix)  # before connecting to anything
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    from google.cloud import bigquery  # imported late so the selection logic is testable offline

    client = bigquery.Client(project=args.project)
    targets = select_datasets([d.dataset_id for d in client.list_datasets()], args.prefix)
    for dataset_id in targets:
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        print(f"deleted {args.project}.{dataset_id}")
    if not targets:
        print(f"no datasets with prefix {args.prefix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
