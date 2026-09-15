from __future__ import annotations

import json
from pathlib import Path

from tw_limitup_ticks.cli import main
from tw_limitup_ticks.config import ConfigError, FubonCredentials
from tw_limitup_ticks.timeutil import micros_to_taipei


def test_cli_select_dry_run(capsys):
    assert main(["select", "--dry-run"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["date"] == "2024-04-30"
    assert {item["symbol"] for item in payload["symbols"]} == {"2345", "2303", "6488"}


def test_cli_archive_and_script_style_flags(tmp_path: Path):
    out = tmp_path / "ticks"
    assert main(["--dry-run", "archive", "--out", str(out)]) == 0
    assert (out / "2024-04-30" / "manifest.json").is_file()
    assert (out / "2024-04-30" / "2345.parquet").is_file()


def test_cli_select_fetch_write_chain(tmp_path: Path, capsys):
    candidates = tmp_path / "candidates.json"
    trades_dir = tmp_path / "trades"
    out = tmp_path / "ticks"
    assert main(["select", "--dry-run", "--output", str(candidates), "--touched-only"]) == 0
    assert main(["fetch", "--dry-run", "--candidates", str(candidates), "--output-dir", str(trades_dir)]) == 0
    capsys.readouterr()
    assert main(
        [
            "write",
            "--dry-run",
            "--candidates",
            str(candidates),
            "--trades-dir",
            str(trades_dir),
            "--out",
            str(out),
        ]
    ) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["symbol_count"] == 2
    assert (out / "2024-04-30" / "6488.parquet").is_file()


def test_env_dry_run_skips_credentials(tmp_path: Path, monkeypatch):
    for key in ("FUBON_ID", "FUBON_PASSWORD", "FUBON_CERT_PATH", "FUBON_CERT_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TW_LIMITUP_DRY_RUN", "1")
    out = tmp_path / "ticks"
    assert main(["archive", "--out", str(out)]) == 0
    assert (out / "2024-04-30" / "manifest.json").is_file()


def test_live_archive_without_credentials_exits_cleanly(tmp_path: Path, monkeypatch, capsys):
    for key in ("FUBON_ID", "FUBON_PASSWORD", "FUBON_CERT_PATH", "FUBON_CERT_PASSWORD", "TW_LIMITUP_DRY_RUN"):
        monkeypatch.delenv(key, raising=False)
    assert main(["archive", "--out", str(tmp_path / "ticks")]) == 1
    err = capsys.readouterr().err
    assert "FUBON_ID" in err


def test_credentials_required_outside_dry_run(tmp_path: Path, monkeypatch):
    for key in ("FUBON_ID", "FUBON_PASSWORD", "FUBON_CERT_PATH", "FUBON_CERT_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    try:
        FubonCredentials.from_env(tmp_path / "missing.env")
        assert False, "expected ConfigError"
    except ConfigError as exc:
        assert "FUBON_ID" in str(exc)


def test_credentials_repr_hides_secrets(tmp_path: Path, monkeypatch):
    cert = tmp_path / "client.pfx"
    cert.write_bytes(b"not-a-real-cert")
    monkeypatch.setenv("FUBON_ID", "A123456789")
    monkeypatch.setenv("FUBON_PASSWORD", "super-secret")
    monkeypatch.setenv("FUBON_CERT_PATH", str(cert))
    monkeypatch.setenv("FUBON_CERT_PASSWORD", "cert-secret")
    creds = FubonCredentials.from_env(None)
    text = repr(creds)
    assert "super-secret" not in text
    assert "cert-secret" not in text
    assert "A123456789" not in text


def test_time_us_converts_to_taipei():
    # 2024-04-30 13:30:00+08:00
    assert micros_to_taipei(1714455000000000) == "2024-04-30T13:30:00+08:00"
