"""Source (SQL Server) and destination (BigQuery) connections, configured from environment / .env.

No secrets live in the repo: SQL Server uses Windows authentication, and BigQuery reads a
service-account key from the path in GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceSettings:
    server: str
    database: str
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_server_certificate: bool = True

    @classmethod
    def from_env(cls) -> SourceSettings:
        return cls(
            server=os.getenv("SQL_SERVER", "localhost"),
            database=os.getenv("SQL_DATABASE", "RxSource"),
            driver=os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
            trust_server_certificate=os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "yes").lower() in {"yes", "true", "1"},
        )

    def sqlalchemy_url(self) -> URL:
        """mssql+pyodbc URL with Windows authentication (no username/password)."""
        return URL.create(
            "mssql+pyodbc",
            host=self.server,
            database=self.database,
            query={
                "driver": self.driver,
                "trusted_connection": "yes",
                "Encrypt": "yes",
                "TrustServerCertificate": "yes" if self.trust_server_certificate else "no",
            },
        )


@dataclass(frozen=True)
class DestinationSettings:
    project_id: str
    location: str
    credentials_path: Path

    @classmethod
    def from_env(cls) -> DestinationSettings:
        project = os.getenv("GCP_PROJECT_ID")
        key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not project:
            raise SettingsError("GCP_PROJECT_ID is not set (see .env.example)")
        if not key:
            raise SettingsError("GOOGLE_APPLICATION_CREDENTIALS is not set (path to the service-account JSON key)")
        path = Path(key)
        if not path.is_file():
            raise SettingsError(f"service-account key not found: {path}")
        if REPO_ROOT in path.resolve().parents:
            raise SettingsError("the service-account key must live outside the repository")
        return cls(project_id=project, location=os.getenv("BIGQUERY_LOCATION", "EU"), credentials_path=path)

    def credentials(self) -> dict:
        info = json.loads(self.credentials_path.read_text(encoding="utf-8"))
        if info.get("type") != "service_account":
            raise SettingsError("GOOGLE_APPLICATION_CREDENTIALS must point to a service-account key")
        info["project_id"] = self.project_id  # load into the configured project
        return info
