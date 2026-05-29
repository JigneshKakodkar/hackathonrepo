from fastapi import APIRouter, HTTPException, Query
from app.data_service import data_service
from app.models import PropertySummary, PropertyDossier, AuctionTerms, RentalData
from app.sources.rentcast_client import get_rent_estimate

router = APIRouter(prefix="/api", tags=["properties"])


@router.get("/properties", response_model=list[PropertySummary])
def list_properties():
    """Index view: summary of all 20 demo auction properties."""
    return data_service.list_property_summaries()


@router.get("/properties/{parcel_id}", response_model=PropertyDossier)
async def get_property(
    parcel_id: str,
    skip_rental: bool = Query(False, description="If true, skip the RentCast call for faster response"),
):
    """Full dossier including rental data (unless skip_rental=true)."""
    dossier = data_service.get_dossier(parcel_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Property {parcel_id} not found")

    if not skip_rental:
        rental = await get_rent_estimate(
            address=dossier.property.address,
            property_type=dossier.property.property_type,
            beds=dossier.property.beds,
            baths=dossier.property.baths,
            sqft=dossier.property.sqft,
        )
        dossier.rental_data = rental
        dossier.data_freshness.rentcast_fetched_at = rental.fetched_at

    return dossier


@router.get("/properties/by-address/", response_model=PropertyDossier)
async def get_property_by_address(
    address: str = Query(..., description="Full or partial property address"),
    skip_rental: bool = Query(False),
):
    """Look up a property by address. Useful for the voice agent's natural-language input."""
    parcel_id = data_service.get_parcel_id_by_address(address)
    if not parcel_id:
        raise HTTPException(status_code=404, detail=f"No property found matching address: {address}")
    dossier = data_service.get_dossier(parcel_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Property {parcel_id} not found")

    if not skip_rental:
        rental = await get_rent_estimate(
            address=dossier.property.address,
            property_type=dossier.property.property_type,
            beds=dossier.property.beds,
            baths=dossier.property.baths,
            sqft=dossier.property.sqft,
        )
        dossier.rental_data = rental
        dossier.data_freshness.rentcast_fetched_at = rental.fetched_at

    return dossier


@router.get("/properties/{parcel_id}/rental", response_model=RentalData)
async def get_rental_only(parcel_id: str):
    """Returns just the rental_data block. Useful for parallel loading in the frontend."""
    dossier = data_service.get_dossier(parcel_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Property {parcel_id} not found")
    return await get_rent_estimate(
        address=dossier.property.address,
        property_type=dossier.property.property_type,
        beds=dossier.property.beds,
        baths=dossier.property.baths,
        sqft=dossier.property.sqft,
    )


@router.get("/auction-terms", response_model=AuctionTerms)
def get_auction_terms():
    """Standard Treasury/CWS auction terms applied to all properties."""
    return data_service.get_auction_terms()
