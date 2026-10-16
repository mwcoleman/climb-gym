"""Shared Garmin Connect login. Every other script imports get_client() from here.

Credentials come from the project's .env (GARMIN_EMAIL / GARMIN_PASSWORD). After the first
login the session is saved to GARMIN_TOKEN_DIR (default: <project>/garmin-tokens, gitignored),
and later runs reuse it without the password or an MFA code.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
TOKEN_DIR = Path(os.environ.get("GARMIN_TOKEN_DIR", ROOT / "garmin-tokens"))


def get_client():
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    g = Garmin(
        os.environ.get("GARMIN_EMAIL") or None,
        os.environ.get("GARMIN_PASSWORD") or None,
        prompt_mfa=lambda: input("Garmin MFA code: "),
    )
    g.login(str(TOKEN_DIR))
    return g
