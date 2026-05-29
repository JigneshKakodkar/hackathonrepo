from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ==== Auction property (from auction_properties.json) ====

class AuctionProperty(BaseModel):
    parcel_id: str
    address: str
    latitude: float
    longitude: float
    beds: int
    baths: float
    sqft: int
    lot_sqft: Optional[int] = None
    year_built: int
    property_type: str
    auction_source: str
    auction_date: str
    minimum_bid: int
    current_bid: Optional[int] = None
    deposit_required: int
    closing_deadline_days: int
    as_is: bool
    financing_allowed: bool
    listing_url: str


# ==== Appraisal (from property_appraiser.json) ====

class PropertyAppraisal(BaseModel):
    parcel_id: str
    owner_name: str
    legal_description: str
    assessed_value: int
    land_value: int
    building_value: int
    market_estimate: int
    year_assessed: int
    homestead_exemption: bool
    last_sale_date: Optional[str] = None
    last_sale_price: Optional[int] = None


# ==== Tax info (from tax_collector.json) ====

class TaxCertificate(BaseModel):
    year: int
    certificate_number: str
    amount: int
    status: str


class PaymentHistoryEntry(BaseModel):
    year: int
    amount_billed: int
    status: str


class TaxInfo(BaseModel):
    parcel_id: str
    annual_tax: int
    unpaid_taxes: int
    delinquent: bool
    tax_certificates: List[TaxCertificate]
    payment_history: List[PaymentHistoryEntry]


# ==== Official records (from official_records.json) ====

class Mortgage(BaseModel):
    recording_date: str
    original_amount: int
    lender: str
    document_number: str
    status: str


class Judgment(BaseModel):
    date: str
    plaintiff: str
    defendant: str
    amount: int
    document_number: str


class MunicipalLien(BaseModel):
    date: str
    type: str
    amount: int
    releasing_authority: str
    document_number: str


class HOALien(BaseModel):
    date: str
    hoa_name: str
    amount: int
    status: str
    document_number: str


class ForfeitureRecord(BaseModel):
    case_number: str
    date_filed: str
    status: str
    agency: str


class OfficialRecords(BaseModel):
    parcel_id: str
    open_mortgages: List[Mortgage]
    judgments: List[Judgment]
    municipal_liens: List[MunicipalLien]
    hoa_liens: List[HOALien]
    federal_forfeiture: List[ForfeitureRecord]


# ==== Code enforcement (from code_enforcement.json) ====

class CodeViolation(BaseModel):
    case_number: str
    opened_date: str
    violation_type: str
    description: str
    fine_amount: int
    status: str


class CodeEnforcement(BaseModel):
    address: str
    open_violations: List[CodeViolation]
    unsafe_structure: bool
    open_fines_total: int
    compliance_deadline: Optional[str] = None


# ==== Court records (from court_records.json) ====

class CourtCase(BaseModel):
    case_number: str
    filed_date: str
    plaintiff: Optional[str] = None
    status: str
    type: Optional[str] = None


class ProbateCase(BaseModel):
    case_number: str
    filed_date: str
    status: str
    type: Optional[str] = None


class CourtRecords(BaseModel):
    parcel_id: str
    foreclosure_cases: List[CourtCase]
    eviction_cases: List[CourtCase]
    lawsuits: List[CourtCase]
    probate: List[ProbateCase]


# ==== Auction terms (from auction_terms.json) ====

class AuctionTerms(BaseModel):
    deposit_rules: str
    financing: str
    as_is_clause: str
    title_warning: str
    default_penalty: str
    closing: str
    inspection: str


# ==== Rental data (from RentCast, normalized) ====

class RentalComparable(BaseModel):
    address: str
    rent: int
    bedrooms: int
    bathrooms: float
    square_footage: int
    year_built: Optional[int] = None
    distance_miles: float
    days_old: int
    days_on_market: Optional[int] = None
    status: str
    correlation: float


class RentalData(BaseModel):
    rent_estimate: Optional[int] = None
    rent_range_low: Optional[int] = None
    rent_range_high: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    comparables: List[RentalComparable] = Field(default_factory=list)
    comparable_count: int = 0
    source: str = "RentCast"
    fetched_at: str
    demo_mode: bool = False


# ==== Master dossier (composed) ====

class DataFreshness(BaseModel):
    static_sources_updated: str
    rentcast_fetched_at: Optional[str] = None


class PropertyDossier(BaseModel):
    property: AuctionProperty
    appraisal: PropertyAppraisal
    tax_info: TaxInfo
    official_records: OfficialRecords
    code_enforcement: CodeEnforcement
    court_records: CourtRecords
    rental_data: Optional[RentalData] = None
    auction_terms: AuctionTerms
    data_freshness: DataFreshness


# ==== Summary view (for the index endpoint) ====

class PropertySummary(BaseModel):
    parcel_id: str
    address: str
    minimum_bid: int
    current_bid: Optional[int] = None
    beds: int
    baths: float
    sqft: int
    property_type: str
    auction_date: str
