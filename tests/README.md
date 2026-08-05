# Tests

VeFi's automated test suite (pytest). It's here for anyone who wants to fork,
modify, or contribute — **you don't need it just to run VeFi and shop for cars.**

## What it covers
The pure logic and a few end-to-end UI flows:

- **Data** — MarketCheck JSON → DataFrame transform (dealer + FSBO merged), the
  saved-search library, and the make/model/body taxonomy.
- **Analysis** — price-vs-mileage predicted pricing, the option/VIN decode, and
  the nationwide-search cost estimate.
- **Safety** — the persistent call counter and API-key redaction in error text.
- **UI flows** (via Streamlit's `AppTest`) — the make→model dropdown cascade,
  the filter "Clear" behavior, and the nationwide cost-confirmation gate.

Everything runs against **throwaway temp directories** and **mocks all network
calls**, so the tests never touch your real `~/.vefi` data or spend a single
MarketCheck API call.

## Running them
From the project root:

```bash
pip install pytest      # if you don't already have it
pytest
```

## How the isolation works
- `pytest.ini` scopes test discovery to this `tests/` folder.
- `conftest.py` points VeFi's config/data directories at temp locations *before*
  the package is imported, so nothing here reads or writes your real files.
