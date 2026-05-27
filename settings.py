"""Load secrets and session cookies from .env (see .env.example)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill in your values."
        )
    return value


USERID = int(_require("USERID"))
TERMCODE = _require("TERMCODE")
DISCORD_WEBHOOK = _require("DISCORD_WEBHOOK")

COOKIES = {
    "_ga_GZ44FZWHSB": _require("COOKIE_GA_GZ44FZWHSB"),
    "_ga": _require("COOKIE_GA"),
    ".AspNet.Cookies": _require("COOKIE_ASPNET"),
    "__RequestVerificationToken": _require("COOKIE_REQUEST_VERIFICATION"),
}
