import json

import pytest

from el.connections import REPO_ROOT, DestinationSettings, SettingsError, SourceSettings


def test_sqlalchemy_url_uses_windows_auth():
    url = SourceSettings(server="localhost", database="RxSource").sqlalchemy_url()
    assert url.drivername == "mssql+pyodbc"
    assert url.username is None and url.password is None
    assert url.query["trusted_connection"] == "yes"
    assert url.query["driver"] == "ODBC Driver 18 for SQL Server"
    assert url.query["TrustServerCertificate"] == "yes"


def test_named_instance_and_strict_certificates():
    url = SourceSettings(server=r"localhost\SQLEXPRESS", database="Rx", trust_server_certificate=False).sqlalchemy_url()
    assert url.host == r"localhost\SQLEXPRESS"
    assert url.query["TrustServerCertificate"] == "no"
    # The URL renders without leaking anything secret (there is nothing secret in it).
    assert "password" not in url.render_as_string(hide_password=False).lower()


@pytest.fixture
def key_file(tmp_path):
    path = tmp_path / "sa.json"
    path.write_text(json.dumps({"type": "service_account", "project_id": "other-project", "client_email": "x@y"}))
    return path


def test_destination_from_env(monkeypatch, key_file):
    monkeypatch.setenv("GCP_PROJECT_ID", "rx-test")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key_file))
    monkeypatch.delenv("BIGQUERY_LOCATION", raising=False)
    dest = DestinationSettings.from_env()
    assert dest.location == "EU"
    creds = dest.credentials()
    assert creds["project_id"] == "rx-test"  # loads into the configured project, not the key's


@pytest.mark.parametrize("missing", ["GCP_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS"])
def test_destination_requires_env(monkeypatch, key_file, missing):
    monkeypatch.setenv("GCP_PROJECT_ID", "rx-test")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key_file))
    monkeypatch.delenv(missing)
    with pytest.raises(SettingsError, match=missing):
        DestinationSettings.from_env()


def test_destination_rejects_missing_key(monkeypatch, tmp_path):
    monkeypatch.setenv("GCP_PROJECT_ID", "rx-test")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(tmp_path / "nope.json"))
    with pytest.raises(SettingsError, match="not found"):
        DestinationSettings.from_env()


def test_destination_rejects_key_inside_repo(monkeypatch):
    inside = REPO_ROOT / "README.md"  # any existing file under the repo
    monkeypatch.setenv("GCP_PROJECT_ID", "rx-test")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(inside))
    with pytest.raises(SettingsError, match="outside the repository"):
        DestinationSettings.from_env()


def test_credentials_must_be_service_account(tmp_path):
    path = tmp_path / "user.json"
    path.write_text(json.dumps({"type": "authorized_user"}))
    with pytest.raises(SettingsError, match="service-account"):
        DestinationSettings("p", "EU", path).credentials()
