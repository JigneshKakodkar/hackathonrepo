import json
from pathlib import Path
from typing import Optional

from app.models import (
    AuctionProperty, PropertyAppraisal, TaxInfo, OfficialRecords,
    CodeEnforcement, CourtRecords, AuctionTerms, PropertyDossier,
    PropertySummary, DataFreshness
)

DATA_DIR = Path(__file__).parent.parent / "data"
STATIC_UPDATED_DATE = "2026-05-28"


def _normalize_address(address: str) -> str:
    return " ".join(address.lower().strip().rstrip(".").split())


class DataService:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir

        # Load all 7 public files (skip scenario_key.json — internal only)
        properties_list = self._load_json("auction_properties.json")
        self._properties: dict[str, dict] = {p["parcel_id"]: p for p in properties_list}
        self._properties_by_address: dict[str, str] = {
            _normalize_address(p["address"]): p["parcel_id"] for p in properties_list
        }
        self._appraisal: dict[str, dict] = self._load_json("property_appraiser.json")
        self._taxes: dict[str, dict] = self._load_json("tax_collector.json")
        self._records: dict[str, dict] = self._load_json("official_records.json")
        raw_code: dict[str, dict] = self._load_json("code_enforcement.json")
        # code_enforcement is keyed by address — normalize defensively
        self._code: dict[str, dict] = {_normalize_address(k): v for k, v in raw_code.items()}
        self._court: dict[str, dict] = self._load_json("court_records.json")
        self._auction_terms: dict = self._load_json("auction_terms.json")

    def _load_json(self, filename: str):
        with open(self.data_dir / filename) as f:
            return json.load(f)

    def list_property_summaries(self) -> list[PropertySummary]:
        out = []
        for p in self._properties.values():
            out.append(PropertySummary(
                parcel_id=p["parcel_id"],
                address=p["address"],
                minimum_bid=p["minimum_bid"],
                current_bid=p.get("current_bid"),
                beds=p["beds"],
                baths=p["baths"],
                sqft=p["sqft"],
                property_type=p["property_type"],
                auction_date=p["auction_date"],
            ))
        return out

    def get_parcel_id_by_address(self, address: str) -> Optional[str]:
        return self._properties_by_address.get(_normalize_address(address))

    def get_dossier(self, parcel_id: str) -> Optional[PropertyDossier]:
        prop_dict = self._properties.get(parcel_id)
        if not prop_dict:
            return None

        addr_key = _normalize_address(prop_dict["address"])
        code_dict = self._code.get(addr_key)
        if not code_dict:
            code_dict = {
                "address": prop_dict["address"],
                "open_violations": [],
                "unsafe_structure": False,
                "open_fines_total": 0,
                "compliance_deadline": None,
            }

        return PropertyDossier(
            property=AuctionProperty(**prop_dict),
            appraisal=PropertyAppraisal(**self._appraisal[parcel_id]),
            tax_info=TaxInfo(**self._taxes[parcel_id]),
            official_records=OfficialRecords(**self._records[parcel_id]),
            code_enforcement=CodeEnforcement(**code_dict),
            court_records=CourtRecords(**self._court[parcel_id]),
            rental_data=None,
            auction_terms=AuctionTerms(**self._auction_terms),
            data_freshness=DataFreshness(
                static_sources_updated=STATIC_UPDATED_DATE,
                rentcast_fetched_at=None,
            ),
        )

    def get_auction_terms(self) -> AuctionTerms:
        return AuctionTerms(**self._auction_terms)


# Module-level singleton
data_service = DataService()
