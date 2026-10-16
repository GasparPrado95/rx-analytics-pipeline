"""SQL Server connection settings (from .env) and a small T-SQL script runner."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = REPO_ROOT / "sql_server" / "ddl"

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class SqlServerSettings:
    server: str = os.getenv("SQL_SERVER", "localhost")
    database: str = os.getenv("SQL_DATABASE", "RxSource")
    driver: str = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    trust_cert: bool = os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "yes").lower() in {"yes", "true", "1"}

    def connection_string(self, database: str | None = None) -> str:
        # Windows authentication (Trusted_Connection): no passwords anywhere.
        return (
            f"DRIVER={{{self.driver}}};SERVER={self.server};DATABASE={database or self.database};"
            f"Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate={'yes' if self.trust_cert else 'no'};"
        )


def connect(settings: SqlServerSettings, database: str | None = None, autocommit: bool = False) -> pyodbc.Connection:
    return pyodbc.connect(settings.connection_string(database), autocommit=autocommit)


_GO = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)


def run_script(conn: pyodbc.Connection, path: Path) -> None:
    """Execute a T-SQL script, splitting on GO batch separators like sqlcmd does."""
    cur = conn.cursor()
    for batch in _GO.split(path.read_text(encoding="utf-8")):
        if batch.strip():
            cur.execute(batch)
            while cur.nextset():
                pass


# Secondary indexes are built after the bulk load: loading into tables with only their
# clustered primary keys is much faster than maintaining every index row by row.
INDEX_SCRIPT = "02_create_indexes.sql"


def create_schema(settings: SqlServerSettings) -> None:
    """(Re)create RxSource from the DDL scripts, without secondary indexes. Drops the database if it exists."""
    with connect(settings, database="master", autocommit=True) as conn:
        for script in sorted(DDL_DIR.glob("*.sql")):
            if script.name != INDEX_SCRIPT:
                run_script(conn, script)


def create_indexes(settings: SqlServerSettings) -> None:
    with connect(settings, autocommit=True) as conn:
        run_script(conn, DDL_DIR / INDEX_SCRIPT)
