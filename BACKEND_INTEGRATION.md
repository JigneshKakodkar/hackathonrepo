# Auction Data Service — Backend Integration Guide

This document is the integration guide for the **Auction Analysis Agent** backend. It describes the data layer that has been built and how to consume it from the agent.

**Scope of this service:** prepare property dossiers for Florida (Orange County) auction properties so an AI agent can analyze them. This service does NOT run the agent — it only provides the data the agent needs.

**Status:** Complete and verified. Ready for agent integration.

---

## Quick start

```bash
# Clone, set up environment
git clone <repo-url>
cd <project-directory>

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and paste your RentCast key (free tier at https://app.rentcast.io/app/api)

# Run
uvicorn app.main:app --reload
```

Then open:
- **http://localhost:8000/docs** — interactive API explorer
- **http://localhost:8000/api/health** — verify it's running

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────┐
│                    Auction Agent                         │
│              (your work — separate service)              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Auction Data Service                        │
│                (this service)                            │
│                                                          │
│  ┌──────────────────┐      ┌───────────────────────┐   │
│  │  Static Data     │      │  Live API Client      │   │
│  │  (data/*.json)   │      │  (RentCast)           │   │
│  │                  │      │                       │   │
│  │  - properties    │      │  - rent estimate      │   │
│  │  - appraisal     │      │  - rent range         │   │
│  │  - taxes         │      │  - 15 comparables     │   │
│  │  - records       │      │  - 1-hour cache       │   │
│  │  - code enf      │      └───────────────────────┘   │
│  │  - court         │                                  │
│  │  - terms         │                                  │
│  └────────┬─────────┘                                  │
│           │                                            │
│           ▼                                            │
│  ┌──────────────────────────────────────────┐         │
│  │  DataService → PropertyDossier (merged)  │         │
│  └──────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Key design points:**
- 7 static JSON files simulate Florida county/city/treasury data sources (no live integration with government systems)
- 1 live integration: RentCast for rental estimates and comparables
- All data is combined into a single `PropertyDossier` per property
- Address-based and parcel_id-based lookups both supported
- Graceful degradation: if RentCast fails or key is missing, dossier still returns with `rental_data.demo_mode: true`

---

## API endpoints

Base URL: `http://localhost:8000`

### `GET /api/health`

Health check. Returns:
```json
{"status": "ok", "service": "auction-data-service"}
```

### `GET /api/properties`

List of all 20 demo auction properties (summary view). Use this for the frontend property list.

**Response:** array of `PropertySummary`
```json
[
  {
    "parcel_id": "OC-2026-1001",
    "address": "4257 Holden Ave, Orlando, FL 32839",
    "minimum_bid": 61000,
    "current_bid": 66000,
    "beds": 2,
    "baths": 1,
    "sqft": 925,
    "property_type": "Condo",
    "auction_date": "2026-06-28"
  },
  ...
]
```

### `GET /api/properties/{parcel_id}`

**The main endpoint.** Returns the full dossier for one property, including a live RentCast call for rental data.

**Query params:**
- `skip_rental` (bool, default false) — if true, skips the RentCast call. Use this for fast static-only loads.

**Response:** `PropertyDossier` (see schema below)

**Latency:**
- With rental: ~800ms first call, ~5ms cached
- With `skip_rental=true`: ~5ms always

### `GET /api/properties/by-address/?address=...`

Address-based lookup. Useful when the agent receives an address from natural-language input (e.g., voice).

**Query params:**
- `address` (str, required) — full or partial property address; normalized internally
- `skip_rental` (bool, default false)

**Response:** `PropertyDossier`

**404 if no match.** Matching is case-insensitive and whitespace-tolerant.

### `GET /api/properties/{parcel_id}/rental`

Just the rental data block. Useful for parallel loading — call the main endpoint with `skip_rental=true` for instant static data, then call this in parallel to fill the Rental Yield widget when ready.

**Response:** `RentalData`

### `GET /api/auction-terms`

Standard Treasury/CWS auction terms. These apply to all properties from that source.

**Response:** `AuctionTerms` (single object)

---

## The PropertyDossier schema

The full response from `GET /api/properties/{parcel_id}`:

```json
{
  "property": {
    "parcel_id": "OC-2026-1001",
    "address": "4257 Holden Ave, Orlando, FL 32839",
    "latitude": 28.591845,
    "longitude": -81.296616,
    "beds": 2,
    "baths": 1.0,
    "sqft": 925,
    "lot_sqft": null,
    "year_built": 1978,
    "property_type": "Condo",
    "auction_source": "Treasury/CWS",
    "auction_date": "2026-06-28",
    "minimum_bid": 61000,
    "current_bid": 66000,
    "deposit_required": 13000,
    "closing_deadline_days": 45,
    "as_is": true,
    "financing_allowed": true,
    "listing_url": "https://cwsmarketing.com/auction/oc-2026-1001"
  },
  "appraisal": {
    "parcel_id": "OC-2026-1001",
    "owner_name": "Sunshine Holdings LLC",
    "legal_description": "LOT 12 BLK 3 PINE HILLS SUB",
    "assessed_value": 83550,
    "land_value": 22000,
    "building_value": 61550,
    "market_estimate": 74527,
    "year_assessed": 2025,
    "homestead_exemption": false,
    "last_sale_date": "2015-04-12",
    "last_sale_price": 45000
  },
  "tax_info": {
    "parcel_id": "OC-2026-1001",
    "annual_tax": 1145,
    "unpaid_taxes": 18813,
    "delinquent": true,
    "tax_certificates": [
      {"year": 2024, "certificate_number": "TC-2024-...", "amount": 5200, "status": "Outstanding"},
      ...
    ],
    "payment_history": [
      {"year": 2023, "amount_billed": 1145, "status": "Delinquent"},
      ...
    ]
  },
  "official_records": {
    "parcel_id": "OC-2026-1001",
    "open_mortgages": [
      {"recording_date": "...", "original_amount": 65000, "lender": "...", "document_number": "...", "status": "Active"}
    ],
    "judgments": [
      {"date": "...", "plaintiff": "...", "defendant": "...", "amount": 15000, "document_number": "..."}
    ],
    "municipal_liens": [],
    "hoa_liens": [],
    "federal_forfeiture": [
      {"case_number": "6:23-cv-...", "date_filed": "...", "status": "Final Order of Forfeiture entered", "agency": "U.S. Marshals Service"}
    ]
  },
  "code_enforcement": {
    "address": "4257 Holden Ave, Orlando, FL 32839",
    "open_violations": [
      {"case_number": "CE-2024-...", "opened_date": "...", "violation_type": "Overgrown lot", "description": "...", "fine_amount": 1500, "status": "Open"}
    ],
    "unsafe_structure": false,
    "open_fines_total": 4615,
    "compliance_deadline": "2026-06-30"
  },
  "court_records": {
    "parcel_id": "OC-2026-1001",
    "foreclosure_cases": [
      {"case_number": "2024-CA-...", "filed_date": "...", "plaintiff": "...", "status": "Active", "type": "Mortgage foreclosure"}
    ],
    "eviction_cases": [],
    "lawsuits": [
      {"case_number": "2024-CC-...", "filed_date": "...", "plaintiff": "...", "status": "Active", "type": "Civil collection"}
    ],
    "probate": []
  },
  "rental_data": {
    "rent_estimate": 1400,
    "rent_range_low": 1300,
    "rent_range_high": 1500,
    "latitude": 28.4944,
    "longitude": -81.4135,
    "comparables": [
      {
        "address": "2604 Lemon Tree Ln, Unit C, Orlando, FL 32839",
        "rent": 1450,
        "bedrooms": 2,
        "bathrooms": 1.0,
        "square_footage": 867,
        "year_built": 1976,
        "distance_miles": 0.2751,
        "days_old": 64,
        "days_on_market": 88,
        "status": "Inactive",
        "correlation": 0.9807
      },
      ...up to 15 comparables
    ],
    "comparable_count": 15,
    "source": "RentCast",
    "fetched_at": "2026-05-29T19:32:00Z",
    "demo_mode": false
  },
  "auction_terms": {
    "deposit_rules": "Deposit must be paid within 24 hours...",
    "financing": "No financing contingencies permitted...",
    "as_is_clause": "Property is sold AS-IS, WHERE-IS...",
    "title_warning": "Buyer is responsible for verifying clear title...",
    "default_penalty": "Failure to close results in forfeiture...",
    "closing": "Closing must occur within 30-60 days...",
    "inspection": "Inspection available by appointment only..."
  },
  "data_freshness": {
    "static_sources_updated": "2026-05-28",
    "rentcast_fetched_at": "2026-05-29T19:32:00Z"
  }
}
```

---

## How to map data to the agent's four widgets

The hackathon brief defines four agent widgets. Here's where to get the data for each:

### Widget 1: Buying Power

Determines the max safe bid given the user's financial profile.

**Read from dossier:**
- `property.minimum_bid` — starting price
- `property.current_bid` — current highest bid (or null)
- `property.deposit_required` — deposit needed up front
- `property.closing_deadline_days` — closing window
- `property.as_is` — no inspection contingency
- `property.financing_allowed` — usually false
- `appraisal.market_estimate` — what it's actually worth
- `auction_terms.deposit_rules` — payment timeline
- `auction_terms.default_penalty` — risk of bidding too high

**Inputs the agent gathers from the user:**
- Available cash, income, monthly expenses
- Credit profile and financing option
- Emergency reserve requirements
- Investment goal (flip / Airbnb / rental / resale)

### Widget 2: Hidden Costs

Identifies costs that survive the sale and become the buyer's problem.

**Read from dossier:**
- `tax_info.unpaid_taxes` — survives sale in most cases
- `tax_info.tax_certificates` — outstanding tax liens
- `official_records.open_mortgages` (filter `status == "Active"`) — may or may not be cleared
- `official_records.judgments` — attach to owner; check if also attach to property
- `official_records.municipal_liens` — code enforcement, utility, unsafe-structure liens
- `official_records.hoa_liens` — Condo/Townhouse only
- `official_records.federal_forfeiture` — confirms Treasury/CWS authority to sell
- `code_enforcement.open_violations` — may require remediation
- `code_enforcement.unsafe_structure` — could mean demolition order
- `code_enforcement.open_fines_total` — direct cost
- `court_records.foreclosure_cases` (filter `status == "Active"`) — title cloud
- `court_records.probate` — non-empty means estate administration delays

**Important agent logic:** distinguish costs that **survive** the sale (typically unpaid taxes, certain municipal liens, code violations, HOA assessments in Florida) from those **wiped out** by the sale (most subordinate liens for Treasury sales). The `auction_terms.title_warning` text explicitly warns about this.

### Widget 3: Rental Yield

Estimates whether the property makes sense as a rental investment.

**Read from dossier:**
- `rental_data.rent_estimate` — RentCast point estimate
- `rental_data.rent_range_low` / `rent_range_high` — sensitivity range
- `rental_data.comparables` — for showing detail to the user
- `appraisal.market_estimate` — current value (for cap rate against)
- `tax_info.annual_tax` — recurring cost
- `property.property_type` — affects HOA, insurance

**Inputs the agent gathers from the user:**
- Estimated repair cost
- Insurance estimate
- Property management %
- Vacancy assumption
- Investment goal (long-term rental vs Airbnb)

**Calculations the agent performs:**
- Monthly rent estimate (from `rental_data.rent_estimate`)
- Total monthly expenses
- Cash flow
- Cap rate = (annual NOI) / total project cost
- Cash-on-cash return
- Break-even rent
- Max bid for target return (back-calculate)

**`demo_mode: true` handling:** if RentCast returned no data, the agent should explain that rental analysis is unavailable and either skip the widget or ask the user for a manual rent estimate.

### Widget 4: Personalized Recommendation

The final Green/Yellow/Red light call.

**Reads:** all of the above. The recommendation is a synthesis, not a single field.

**Recommended classification heuristic** (the agent can refine):

| Tier | Criteria |
|---|---|
| 🟢 **Green light** | No active foreclosure, unpaid taxes < $1k, no active mortgages, no unsafe structure, total hidden costs estimable and < 10% of minimum bid, positive cash flow at conservative rent |
| 🟡 **Yellow light** | Some issues (small unpaid taxes, minor code violation, dismissed cases) but verifiable; max safe bid achievable with margin |
| 🔴 **Red light** | Active foreclosure, federal forfeiture, unsafe structure, multiple unreleased mortgages, total hidden costs > 25% of minimum bid, or insufficient cash for deposit + closing + reserves |

**Output format the brief requires:**
```
Recommendation: <Green/Yellow/Red>
Maximum Safe Bid: $X
Do Not Bid Above: $Y
Next Steps:
1. Verify taxes
2. Check official records
3. Check code violations
4. Confirm financing
5. Confirm title/closing responsibility
```

---

## Demo data: scenario distribution

The 20 demo properties are deliberately seeded across three scenarios:

| Tag | Count | Profile |
|---|---|---|
| 🟢 green | 6 | Clean records, no unpaid taxes, no liens, no violations |
| 🟡 yellow | 8 | One or two minor issues |
| 🔴 red | 6 | Serious problems — heavy taxes, active foreclosure, sometimes forfeiture |

**There's a hidden file `data/scenario_key.json`** that maps each `parcel_id` to its scenario tag. **This file is intentionally NOT exposed via the API** — the agent must classify properties based on the underlying data, not by reading the tag.

**Use the scenario key for validation:** during agent development, if the agent says "Green light" on a property tagged `red`, that's a bug.

---

## Important caveats

### 1. RentCast resolves some addresses to nearby municipalities

RentCast may resolve an Orlando address to `Edgewood, FL` (a small city surrounded by Orlando). This is correct — Edgewood is in Orange County. The `subjectProperty.formattedAddress` field in raw responses will reflect this, but for display we use the original address from `auction_properties.json`.

### 2. RentCast free tier limit

50 calls/month. The client has a 1-hour in-memory cache to reduce calls. For testing:
- Set `SKIP_RENTCAST=true` in `.env` to bypass RentCast entirely during development
- The `?skip_rental=true` query param works per-request

### 3. `demo_mode: true` is not an error

When `rental_data.demo_mode == true`, RentCast wasn't called (or failed). The dossier is still valid — the agent should just skip rental analysis or ask the user for a manual estimate.

### 4. Static data freshness

All non-RentCast data is static, dated 2026-05-28. In production these would be refreshed nightly. For the hackathon, treat them as frozen.

### 5. CORS allowed origins

Currently configured for:
- http://localhost:3000
- http://localhost:5173
- http://localhost:8080

If the agent or frontend runs on a different port, update the CORS list in `app/main.py`.

---

## Testing endpoints quickly

```bash
# Health check
curl http://localhost:8000/api/health

# List all properties
curl http://localhost:8000/api/properties

# Get a single property by parcel_id (full dossier with RentCast)
curl http://localhost:8000/api/properties/OC-2026-1001

# Get by address (URL-encoded)
curl "http://localhost:8000/api/properties/by-address/?address=4257%20Holden%20Ave,%20Orlando,%20FL%2032839"

# Fast static-only response
curl "http://localhost:8000/api/properties/OC-2026-1001?skip_rental=true"

# Rental data only (for parallel loading)
curl http://localhost:8000/api/properties/OC-2026-1001/rental

# Standard auction terms
curl http://localhost:8000/api/auction-terms
```

---

## Project structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, CORS, route registration, startup check
│   ├── config.py                # loads RENTCAST_API_KEY, SKIP_RENTCAST from .env
│   ├── models.py                # all Pydantic models (AuctionProperty, PropertyDossier, etc.)
│   ├── data_service.py          # loads JSON into memory, composes dossiers
│   ├── routes/
│   │   ├── __init__.py
│   │   └── properties.py        # all /api/properties* endpoints
│   └── sources/
│       ├── __init__.py
│       └── rentcast_client.py   # async httpx client, in-memory cache, response normalization
├── data/                        # 7 public + 1 internal JSON files (see DATA.md)
├── .env                         # local secrets (NOT committed)
├── .env.example                 # template
├── .gitignore
├── requirements.txt             # fastapi, uvicorn, pydantic, python-dotenv, httpx
├── README.md
├── DATA.md                      # detailed schema of the data layer
└── BACKEND_INTEGRATION.md       # this file
```

---

## Integration patterns

### Pattern 1: Agent receives address from voice input

```
User speaks: "Analyze 4257 Holden Ave in Orlando"
                    ↓
Voice → text: "4257 Holden Ave, Orlando, FL"
                    ↓
Agent calls: GET /api/properties/by-address/?address=4257%20Holden%20Ave,%20Orlando,%20FL
                    ↓
Receives full PropertyDossier
                    ↓
Agent analyzes each widget and synthesizes recommendation
```

### Pattern 2: Agent shows property list, user picks one

```
Frontend calls: GET /api/properties
                ↓ (renders list)
User clicks one
                ↓
Frontend calls: GET /api/properties/OC-2026-1001?skip_rental=true (fast)
                ↓ (renders dossier UI immediately)
Frontend calls: GET /api/properties/OC-2026-1001/rental (in parallel)
                ↓ (fills in Rental Yield widget when ready)
```

### Pattern 3: Agent has the parcel_id already

```
Agent calls: GET /api/properties/OC-2026-1001
             ↓
Receives full dossier (one call, ~800ms)
             ↓
Analyzes
```

---

## Error handling

| Scenario | Response |
|---|---|
| `parcel_id` not found | 404 with `{"detail": "Property X not found"}` |
| `address` not matched | 404 with `{"detail": "No property found matching address: X"}` |
| RentCast key missing | 200 with `rental_data.demo_mode: true` |
| RentCast network error | 200 with `rental_data.demo_mode: true` (failure is silent) |
| RentCast HTTP error (4xx/5xx) | 200 with `rental_data.demo_mode: true` (logged server-side) |
| RentCast quota exhausted (429) | 200 with `rental_data.demo_mode: true` |
| Invalid query params | 422 with FastAPI's validation error format |

The service is designed to **never fail the dossier request because of RentCast** — it always returns valid data, with `demo_mode: true` signaling that rental analysis isn't available.

---

## Future improvements (out of scope for hackathon)

If this becomes a real product:

1. **Replace static data with live integrations** — ATTOM Data API, Orange County Property Appraiser API, CWS RSS feed, PACER for federal forfeiture
2. **Add a real database** — Postgres with property records, change tracking
3. **Add authentication** — API key per agent client
4. **Add caching layer** — Redis for the RentCast cache (currently in-process)
5. **Expand geography** — currently Orlando/Orange County only
6. **Add webhooks** — push notifications when watched properties change

---

## Contacts

- **Data layer / this service:** Karthik
- **Agent layer / voice / dashboard:** Backend engineer (you)

For data layer questions or bug reports, see `DATA.md` for the full schema reference.
