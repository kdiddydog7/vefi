<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Developer guide

Technical reference for running VeFi from source and building on it. **If you
just want to shop for cars, the main [README](README.md) has everything you
need** — this file is only for people poking at the code.

## Setup

Same as the main README's *Install & run*: clone the repo, create a virtual
environment, `pip install -r requirements.txt`, then `streamlit run app.py`.

## Where things live

| Area | Where |
|------|-------|
| Static config (endpoints, paths, nationwide grid) | `vefi/config.py` |
| API keys / quota limit (per user) | `~/.vefi/config.json` via `vefi/settings_store.py` |
| MarketCheck call count | `~/.vefi/usage.json` via `vefi/usage.py` |
| Saved searches | `data/searches/<slug>/` via `vefi/data/library.py` |
| Per-VIN caches (decode, photos, listing extras) | `data/cache/` via `vefi/cache.py` |
| Bundled make/model/body-type list | `vefi/resources/makes_models.json` via `vefi/taxonomy.py` |

Everything under `data/` and `~/.vefi/` is per-user and gitignored — a user's
searches and keys never get committed.

## Project layout

```
app.py                 Streamlit entry point (thin)
vefi/
  config.py            endpoints, paths, defaults, nationwide grid
  settings_store.py    read/write API keys + quota limit
  usage.py             persistent MarketCheck call counter
  cache.py             on-disk caches for per-listing data
  search.py            high-level search orchestration
  pricing.py           price-vs-mileage deal model
  mapping.py           Folium map builder
  options_decode.py    VIN / listing option parsing
  api/
    marketcheck.py     MarketCheck client (meters + logs every call)
    geocoding.py       pgeocode + keyless Census fallback
    distance.py        haversine straight-line distance
  data/
    transform.py       MarketCheck JSON -> DataFrame
    library.py         saved-search catalog
  ui/                  Streamlit components (sidebar, search form, results, details, settings)
tests/                 pytest suite for the pure logic
```

## Tests

See [tests/README.md](tests/README.md). Run `pytest` from the project root; the
suite mocks all network calls and uses temp directories, so it never touches
real data or spends a MarketCheck API call.

## License

Contributions are accepted under the project's **GPL-3.0** license (see
[LICENSE](LICENSE)).
