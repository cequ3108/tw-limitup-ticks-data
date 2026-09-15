from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

CREDENTIAL_ENV = (
    "FUBON_ID",
    "FUBON_PASSWORD",
    "FUBON_CERT_PATH",
    "FUBON_CERT_PASSWORD",
)


class ConfigError(RuntimeError):
    """Missing or invalid local configuration."""


@dataclass(frozen=True)
class FubonCredentials:
    national_id: str
    password: str
    cert_path: str
    cert_password: str

    @classmethod
    def from_env(cls, env_file: str | os.PathLike[str] | None = ".env") -> FubonCredentials:
        if env_file:
            path = Path(env_file)
            if path.is_file():
                load_dotenv(path, override=False)
            else:
                load_dotenv(override=False)
        else:
            load_dotenv(override=False)

        values = {key: (os.environ.get(key) or "").strip() for key in CREDENTIAL_ENV}
        missing = [key for key, value in values.items() if not value]
        if missing:
            raise ConfigError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Copy .env.example to .env or export FUBON_ID, FUBON_PASSWORD, "
                "FUBON_CERT_PATH, FUBON_CERT_PASSWORD. Never commit secrets."
            )

        cert = Path(values["FUBON_CERT_PATH"]).expanduser()
        if not cert.is_file():
            raise ConfigError(f"Certificate file not found: {cert}")

        return cls(
            national_id=values["FUBON_ID"],
            password=values["FUBON_PASSWORD"],
            cert_path=str(cert.resolve()),
            cert_password=values["FUBON_CERT_PASSWORD"],
        )

    def __repr__(self) -> str:  # pragma: no cover - avoid leaking secrets in logs
        return (
            f"FubonCredentials(national_id='***', password='***', "
            f"cert_path={self.cert_path!r}, cert_password='***')"
        )
