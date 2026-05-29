"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()


def _parse_bool(value: str) -> bool:
    """Parse a string into a boolean.

    Treats "true", "True" and "1" (case-insensitive) as True; everything
    else is False.
    """
    if value is None:
        return False
    return value.strip().lower() in {"true", "1"}


# RentCast API key used to enrich property data. Empty string by default.
RENTCAST_API_KEY: str = os.getenv("RENTCAST_API_KEY", "")

# When True, skip any calls to the RentCast API. False by default.
SKIP_RENTCAST: bool = _parse_bool(os.getenv("SKIP_RENTCAST", "false"))
