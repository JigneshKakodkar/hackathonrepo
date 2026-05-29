"""
RentCast API client.

Response shape verified live 2026-05-29 — keys are camelCase:
{
  "rent": 1400,
  "rentRangeLow": 1300,
  "rentRangeHigh": 1500,
  "latitude": 28.49,
  "longitude": -81.41,
  "subjectProperty": {...},
  "comparables": [
    {
      "formattedAddress": "...",
      "bedrooms": 2, "bathrooms": 1, "squareFootage": 867,
      "yearBuilt": 1976,
      "price": 1450,
      "status": "Inactive",
      "daysOnMarket": 88,
      "daysOld": 64,
      "distance": 0.2751,
      "correlation": 0.9807
    },
    ...
  ]
}

We normalize camelCase -> snake_case to match the dossier convention.
"""
import logging
import time
from datetime import datetime, timezone

import httpx

from app.config import RENTCAST_API_KEY, SKIP_RENTCAST
from app.models import RentalData, RentalComparable

logger = logging.getLogger(__name__)

RENTCAST_URL = "https://api.rentcast.io/v1/avm/rent/long-term"

PROPERTY_TYPE_MAP = {
    "Single Family": "Single Family",
    "Condo": "Condo",
    "Townhouse": "Townhouse",
    "Duplex": "Multi-Family",
}

# In-memory cache: (address_lower, beds, baths, sqft) -> (timestamp, RentalData)
_cache: dict[tuple, tuple[float, RentalData]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_mode_response() -> RentalData:
    return RentalData(
        rent_estimate=None,
        rent_range_low=None,
        rent_range_high=None,
        latitude=None,
        longitude=None,
        comparables=[],
        comparable_count=0,
        source="RentCast",
        fetched_at=_now_iso(),
        demo_mode=True,
    )


def _normalize_response(raw: dict) -> RentalData:
    raw_comps = raw.get("comparables") or []
    comps: list[RentalComparable] = []
    for c in raw_comps:
        try:
            comps.append(RentalComparable(
                address=c.get("formattedAddress", ""),
                rent=int(c["price"]),
                bedrooms=int(c["bedrooms"]),
                bathrooms=float(c["bathrooms"]),
                square_footage=int(c["squareFootage"]),
                year_built=c.get("yearBuilt"),
                distance_miles=round(float(c.get("distance", 0)), 4),
                days_old=int(c.get("daysOld", 0)),
                days_on_market=c.get("daysOnMarket"),
                status=c.get("status", "Unknown"),
                correlation=round(float(c.get("correlation", 0)), 4),
            ))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Skipping malformed comparable: {e}")

    return RentalData(
        rent_estimate=raw.get("rent"),
        rent_range_low=raw.get("rentRangeLow"),
        rent_range_high=raw.get("rentRangeHigh"),
        latitude=raw.get("latitude"),
        longitude=raw.get("longitude"),
        comparables=comps,
        comparable_count=len(comps),
        source="RentCast",
        fetched_at=_now_iso(),
        demo_mode=False,
    )


async def get_rent_estimate(
    address: str,
    property_type: str,
    beds: int,
    baths: float,
    sqft: int,
) -> RentalData:
    if SKIP_RENTCAST:
        logger.info("SKIP_RENTCAST=true; returning demo_mode rental data")
        return _demo_mode_response()
    if not RENTCAST_API_KEY:
        logger.info("RENTCAST_API_KEY not set; returning demo_mode rental data")
        return _demo_mode_response()

    cache_key = (address.lower().strip(), beds, baths, sqft)
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        logger.info(f"RentCast cache hit for {address}")
        return cached[1]

    rentcast_property_type = PROPERTY_TYPE_MAP.get(property_type, "Single Family")

    params = {
        "address": address,
        "propertyType": rentcast_property_type,
        "bedrooms": beds,
        "bathrooms": baths,
        "squareFootage": sqft,
    }
    headers = {"X-Api-Key": RENTCAST_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(RENTCAST_URL, params=params, headers=headers)
            response.raise_for_status()
            raw = response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"RentCast HTTP {e.response.status_code} for {address}: {e.response.text[:200]}")
        return _demo_mode_response()
    except (httpx.RequestError, ValueError) as e:
        logger.error(f"RentCast request failed for {address}: {e}")
        return _demo_mode_response()

    rental = _normalize_response(raw)
    _cache[cache_key] = (time.time(), rental)
    logger.info(f"RentCast fetched: {address} -> ${rental.rent_estimate}/mo ({rental.comparable_count} comps)")
    return rental
