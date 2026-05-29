# auction-data-service

FastAPI service that prepares Florida auction property dossiers for consumption by an AI auction analysis agent.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the requirements:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and fill in your values:

   ```bash
   cp .env.example .env
   ```

4. Get a RentCast API key from https://app.rentcast.io/app/api and set
   `RENTCAST_API_KEY` in your `.env` file. To skip RentCast calls entirely,
   set `SKIP_RENTCAST=true`.

## Run

```bash
uvicorn app.main:app --reload
```

## Verify

- Health check: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs

## Data Layer

The service reads from the `data/` directory. See [DATA.md](data/DATA.md) for
details about the data layer and the individual JSON sources.
