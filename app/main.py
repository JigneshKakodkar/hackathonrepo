"""FastAPI application entrypoint for the Auction Data Service."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config  # noqa: F401  (ensures .env is loaded at startup)
from app.routes.properties import router as properties_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auction-data-service")

# Resolve the data/ directory relative to the project root (parent of app/).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EXPECTED_DATA_FILES = [
    "auction_properties.json",
    "property_appraiser.json",
    "tax_collector.json",
    "official_records.json",
    "code_enforcement.json",
    "court_records.json",
    "auction_terms.json",
    "scenario_key.json",
]

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
]

app = FastAPI(title="Auction Data Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties_router)


def _verify_data_files() -> None:
    """Verify the data/ folder exists and contains all expected files."""
    if not DATA_DIR.is_dir():
        logger.error("Data directory not found: %s", DATA_DIR)
        return

    missing = [
        name for name in EXPECTED_DATA_FILES if not (DATA_DIR / name).is_file()
    ]
    if missing:
        logger.error(
            "Missing %d expected data file(s) in %s: %s",
            len(missing),
            DATA_DIR,
            ", ".join(missing),
        )
    else:
        logger.info(
            "All %d expected data files found in %s",
            len(EXPECTED_DATA_FILES),
            DATA_DIR,
        )


@app.on_event("startup")
def on_startup() -> None:
    _verify_data_files()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "auction-data-service"}
