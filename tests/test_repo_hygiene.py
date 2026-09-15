from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_covers_secrets_and_venv():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for token in (".env", "*.pfx", "venv/", ".venv/"):
        assert token in text


def test_gitattributes_tracks_parquet_with_lfs():
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "ticks/**/*.parquet" in text
    assert "filter=lfs" in text


def test_env_example_has_no_secrets():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FUBON_ID=" in text
    assert "FUBON_PASSWORD=" in text
    assert "FUBON_CERT_PATH=" in text
    assert "FUBON_CERT_PASSWORD=" in text
    for line in text.splitlines():
        if line.strip().startswith("FUBON_") and "=" in line:
            _, _, value = line.partition("=")
            assert value.strip() == ""
