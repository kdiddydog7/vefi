<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<p align="center">
  <img src="VeFi_125_tp.png" width="140" alt="VeFi logo">
</p>

<h1 align="center">VeFi — Vehicle Finder</h1>

<p align="center">
  Raw, unfiltered used-car data from MarketCheck — search, map, and find the real deals.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/UI-Streamlit-ff4b4b.svg" alt="Built with Streamlit">
</p>

VeFi is an open-source free used-car search and analysis tool built to use the [MarketCheck](https://www.marketcheck.com/)
API. 

VeFi fills some very specific gaps in the car shopping experience for people that 
are shopping for special cars.  

When you shop on any of the major car listing sites, after some time you begin
to realize that the experience is really designed to benefit the
dealerships paying for listings, not the consumers shopping. If you've ever
copy-pasted listing details out of cartrader, carguru, truecar, etc., so you
could paste it all into a spreadsheet and actually compare apples to apples, 
you may find VeFi very useful when car shopping.

## Here's information VeFi gives you that the car listing sites don't
When you search for cars in VeFi, what you get back is everything you need to
compare cars based on all the data that matters for your search --summarized, 
organized, and easily digested.

### The Price/Mile Graph
Cars with less miles are worth more.  But how much more?  VeFi plots every car
on a Price/Miles graph and shows you the trendline that instantly shows whether
a given listing is above or below that trendline. carguru.com will tell you if a listing
is a "good deal" but how do they determine that?  If you tell a dealership CarGuru
says their listing is not a good deal, do you think they care and that will matters
in negotiations?  If you show them 4 other similar cars with similar miles
in the area that are less money, THAT is information they know you might walk
based on.  

The trendline is simplistic; it doesn't factor in features, colors, etc. --just
price and miles. But its simplicity is powerful: The trendline recalculates with 
every filter you apply.  If you are only shopping for Volvo V60s with the Ultra 
package, in 3 colors, you can filter to those and see the trendline.  

<table>
  <tr>
    <td width="50%">
      <img src="assets/predicted_price.jpg" alt="Predictive price trendline"><br>
      <em>Price/Miles graphing and pricing trendline</em>
    </td>
  </tr>
</table>  

The trendline predicted price is also displayed in each listing's header. 
If a car is under the predicted price, it will show a small green pill metric with a down
arrow and the percentage under the predicted price. 

### The Geo Map
Eventually you are going venture out in the physical world of dealership lots, 
and VeFi puts every car you search for on a super-responsive, easily panable and
zoomable map. 

<table>
  <tr>
    <td width="50%">
      <img src="assets/geo_map.jpg" alt="View cars by location"><br>
      <em>Easily view cars by physical location</em>
    </td>
  </tr>
</table>  

And make sure to input your Zip Code in the filter criteria, even if you don't
want to restrict to a distance.  By entering your Zip, a straight-line distance is
calculated so you can prioritize closer cars. 

### The Results table
It's the most basic thing really. Put all the car details in a compact table to sort
through.  Again, the listing sites don't really want you sorting all the cars this 
efficiently. Those sites want you browsing page after page of horrible pictures 
with minimal data beyond miles and price.  

<table>
  <tr>
    <td width="50%">
      <img src="assets/results_table.jpg" alt="Image of table view"><br>
      <em>Information-dense table view for quick identification of good cars</em>
    </td>
  </tr>
</table>  

### The Bookmarks
When you do find cars that make the initial cut, bookmark them to the bookmarks tab. 
Both the main results table and bookmarks table let you export to .csv and
import to your spreadsheet of choice. 


### Some other useful things VeFi helps with
- Every listing has the dealer's URL linked, so you can always jump right to the 
  dealership's webpage.  Phone number is there too, if you need to call them.
- Actual option codes are available for most cars, decoded from the VIN. If you're
  looking for the Mark Levinson or Bowers and Wilkins audio options, or a specific
  suspension package, you can't really rely on dealer listings.
- VeFi also gives you a few "insider" pieces of information that listings often
  don't mention:  Days on market and amount reduced since originally listed. 
  Useful to know if the car you want is one the dealership considers "lot rot"
  (aged unit) that they can't wait to get rid of. 
- Immediate visibility of "single owner" and "clean carfax" cars.  Neither of these
  attributes guarantee a good car, but can help you identify what to look into. 
  

### One thing VeFi specifically DOESN'T give you
- No sponsored results cluttering your sorted list.  VeFi is just the raw data,
  presented cleanly.


## "Sounds pretty useful. What's the catch?"
There is a catch. VeFi uses the Marketcheck API. The lowest paid tier for that 
API is $300/month, plus sub-penny usage fees per API call.  That pricing is 
completely unrealistic for single-purchase consumer car shopping.

But Marketcheck DOES have a free tier:  500 API calls per month.  That's enough
for effective use, if you are careful. 

VeFi is designed to help you be careful.

### Close tracking of API calls
When you input your Marketcheck API key, you will also see your call quota of 500 set. 
Every call VeFi makes to MarketCheck is tracked so you can see your remaining capacity.

#### Nationwide searches
Nationwide searches deserve more detailed explanation.  Marketcheck doesn't offer 
the ability to do  a nationwide search in one call for the free tier, so VeFi uses
a geographically distributed set of Lat/Long coordinates with a 100 mile radius 
spacing to cover the US.  There are 68 unique points that are queried, so any nationwide
search will consume at least 68 of your 500 calls. 

68 calls is just where a nationwide search starts. If a single query has more than 50 matching 
car listings, then results are paginated and require extra calls. A search in a dense 
L.A. area / might generate 250 results, which is 5 calls for that one ZIP code. 

Finally, an extra 6 calls are made up front to sample 6 representative regions.  VeFi
estimates the total number of calls required to search nationwide based on that sample.
You can either accept or cancel the search to refine your criteria more narrowly. 

<table>
  <tr>
    <td width="50%">
      <img src="assets/nationwide_warning.jpg" alt="nationwide search warning"><br>
      <em>Strict API quota tracking</em>
    </td>
  </tr>
</table>  

The bottom line is that if you are searching for the best deal on a 2000-2010 Camry
nationwide, then VeFi isn't the tool for you. You will get 100s of listings in every
ZIP code and exhaust your entire monthly quota before covering even 1/2
the country.  If you are searching for an Alfa Giulia, you can search nationwide and 
will likely use the minimum number of calls possible for a nationwide search.  

#### Pictures don't consume API calls. 
The pictures you can browse are direct links to the dealership-hosted listing, so
you don't use API calls to browse pictures. 

#### Listing details and option packages
Every listing has the option to pull back 2 additional sets of information.  The first
is the dealer listing details that include the 'narrative' written by the dealership
and the features they list.  

The second is actually decoding the VIN to determine what options were ordered on
the car.  

For every listing you view, you will have the option to pull back this information if
you want, consuming extra API calls. Once you pull it back once, it is cached on your
machine. 

### Saved Searches
When you spend precious API calls on a search, VeFi lets you save those
results.  Once saved you can reload them again to analyze further without spending more
API calls.  Of course you will only get new listings by doing new searches.  

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
