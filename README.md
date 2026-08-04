<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# VeFi — Vehicle Finder

VeFi is a used-car search and analysis tool built on the [MarketCheck](https://www.marketcheck.com/)
API. Search dealer and for-sale-by-owner listings across the US, filter and map
them, spot good deals with a price-vs-mileage model, and keep a library of saved
searches — all from a Streamlit web UI.

> VeFi started as a personal project that helped its author save real money on a
> car purchase. It's now cleaned up and open-sourced so anyone can plug in their
> own API key and do the same.

## Features

- 🔎 **Dealer + FSBO search** by make, model, body type, year range, and radius —
  a single ZIP or a nationwide sweep.
- ✅ **Make / model / body-type dropdowns** sourced from MarketCheck's own
  taxonomy (bundled with the app), so a misspelling can't burn API calls on a
  search that returns nothing. Refresh the list from MarketCheck any time
  (Settings) to pick up new model years.
- 🗂️ **Search library** — save searches and switch between them in the UI. No more
  swapping files around by hand.
- 🔑 **API keys in the app** — enter your keys on the Settings page; nothing is
  hardcoded. Keys are stored locally in `~/.vefi/config.json`.
- 📊 **Call tracker** — a live meter shows how many MarketCheck calls you've used
  this month against your configured limit, so you never blow past the free tier
  unexpectedly.
- 🧮 **Deal detection** — a polynomial price-vs-mileage model flags cars priced
  above or below the pack.
- 🧩 **On-demand option decode** — used listings rarely disclose every factory
  option. Decode any VIN to pull its full option list (opt-in, since it costs an
  API call).
- 🗺️ **Interactive map, scatter chart, and sortable table**, plus bookmarking and
  a photo gallery per listing.
- 📍 **Distance** — fast, free straight-line distance from any ZIP, no API key.

## Requirements

- Python 3.9+
- A **free MarketCheck API key** — sign up at
  [marketcheck.com](https://www.marketcheck.com/).

## Install & run

```bash
git clone <your-fork-url> vefi
cd vefi
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. On first launch it will prompt you for your
MarketCheck key — paste it into **Settings**, save, and start searching.

## How it works

| Area | Where |
|------|-------|
| Static config (endpoints, paths, nationwide grid) | `vefi/config.py` |
| API keys / quota limit (per user) | `~/.vefi/config.json` via `vefi/settings_store.py` |
| MarketCheck call count | `~/.vefi/usage.json` via `vefi/usage.py` |
| Saved searches | `data/searches/<slug>/` via `vefi/data/library.py` |
| Per-VIN caches (decode, photos, listing extras) | `data/cache/` via `vefi/cache.py` |
| Bundled make/model/body-type list | `vefi/resources/makes_models.json` via `vefi/taxonomy.py` |

Everything under `data/` and `~/.vefi/` is local to you and is gitignored — your
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

## Running the tests

```bash
pip install pytest
pytest
```

The suite covers the pure logic (transform, usage counter, search library,
option decode, pricing) and runs against throwaway temp directories, so it never
touches your real data or makes network calls.

## A note on API quotas

MarketCheck's free tier is limited. VeFi caches aggressively (searches, VIN
decodes, photos, and listing details are all stored locally and reused) and shows
a running call count so you can stay under your limit. The monthly limit shown in
the meter is just for the display — set it to match your plan on the Settings
page.

## License

VeFi is licensed under the **GNU General Public License v3.0** — see
[`LICENSE`](LICENSE). You're free to use, modify, and share it, including
commercially; derivative works must also be released under the GPL.

MarketCheck and the U.S. Census geocoder are third-party services subject to
their own terms.
