"""Small environment-based configuration; no secrets read during module import."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    database_url: str | None = field(default=None, repr=False)
    model_pointer_path: Path = ROOT / "ml/models/current_model.json"
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(
            x.strip()
            for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if x.strip()
        )
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        port = int(os.getenv("API_PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("API_PORT must be in 1..65535")
        path = Path(os.getenv("MODEL_POINTER_PATH") or "ml/models/current_model.json")
        return cls(
            database_url=os.getenv("DATABASE_URL"),
            model_pointer_path=path if path.is_absolute() else ROOT / path,
            cors_origins=origins,
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=port,
        )
