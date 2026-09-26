---
name: fast-flights
description: Use fast-flights to scrape Google Flights and get flight information. Activated when user asks about flight prices, flight search, flight data, or needs to query flight availability/prices from Google Flights.
---

# fast-flights

A fast, robust Google Flights scraper (API) for Python. It uses Base64-encoded Protobuf to query Google Flights and retrieve flight data.

**PyPI Package:** `fast-flights` v3.1.0 (requires Python >= 3.10)
**Repository:** https://github.com/AWeirdDev/flights
**Docs:** https://aweirddev.github.io/flights

## Installation

```bash
pip install fast-flights
```

## Actual API (v3.1.0 - Working)

The canonical API is `FlightQuery` + `create_query` + `get_flights`.
(`create_filter` is kept as an alias of `create_query`; `FlightData` /
`get_flights_from_filter` were the v3.0 names — `from fast_flights import FlightData`
fails on v3.1.0, do not use them.)

```python
from fast_flights import FlightQuery, Passengers, create_query, get_flights

# Create a query
query = create_query(
    flights=[
        FlightQuery(date="2026-06-09", from_airport="TNG", to_airport="BVA"),
    ],
    trip="one-way",           # or "round-trip", "multi-city"
    passengers=Passengers(adults=1),
    seat="economy",           # "economy", "premium-economy", "business", "first"
    currency="MAD",           # e.g. "USD", "EUR", "MAD"; "" lets Google decide
    language="en",            # "" lets Google decide
)

# Execute the query
result = get_flights(query)  # -> ResultList (a list of Flights)

# Access results (price is an int in the selected currency)
print(f"Number of itineraries: {len(result)}")
for itin in result:
    print(f"Price: {itin.price}")
    print(f"Airlines: {itin.airlines}")
    for leg in itin.flights:
        print(f"  {leg.from_airport.code} {leg.departure} -> "
              f"{leg.to_airport.code} {leg.arrival} "
              f"({leg.duration} min, {leg.plane_type})")
```

With proxy or an integration:

```python
result = get_flights(query, proxy="http://user:pass@host:port")
```

## Core Components

### FlightQuery

Defines a single flight segment with per-leg filters:
- `date`: Travel date in `YYYY-MM-DD` format (or `datetime`)
- `from_airport`: Three-letter IATA airport code (e.g., "CMN", "CDG", "TNG")
- `to_airport`: Three-letter IATA airport code
- `max_stops`: Optional maximum stops (e.g., 0 for direct only)
- `airlines`: Optional list of airline/alliance codes (e.g., `["JL", "ONEWORLD"]`; the first leg's filter applies to the whole search).
  WARNING: server-side `airlines` filtering is unreliable — e.g. `airlines=["FR"]`
  raises `'NoneType' object is not subscriptable` when there is no match
  (observed LYS->MAD). Do NOT use it to find low-cost carriers; fetch all
  results and filter in Python instead (see "Filter by airline in Python").
- `earliest_departure_hour` / `latest_departure_hour`: 0–23, local airport time
- `earliest_arrival_hour` / `latest_arrival_hour`: 0–23, local airport time
- `max_duration_minutes`: e.g., 720
- `connecting_airports`: e.g., `["HND", "NRT"]`
- `min_layover_minutes` / `max_layover_minutes`
- `less_emissions_only`: bool

### Passengers

Configures passenger count:
- `adults`: Number of adult passengers
- `children`: Number of children
- `infants_in_seat`: Number of infants with a seat
- `infants_on_lap`: Number of infants on lap

### create_query()

Creates a flight query with:
- `flights`: List of `FlightQuery` objects
- `trip`: Trip type - `"one-way"`, `"round-trip"`, or `"multi-city"`
- `passengers`: `Passengers` object
- `seat`: Cabin class - `"economy"`, `"premium-economy"`, `"business"`, or `"first"`
- `language`: e.g., `"en"`, `"zh-TW"`; `""` lets Google decide
- `currency`: e.g., `"USD"`, `"EUR"`, `"MAD"`; `""` lets Google decide
- `max_stops`: Optional max stops applied to every leg
- `max_price`: Maximum price in the selected `currency`
- `carry_on_bags` / `checked_bags`: bag counts whose estimated fees are included
- `hide_separate_and_self_transfer`: hide separate-ticket/self-transfer itineraries
- `exclude_basic_economy`: exclude basic economy fares

### get_flights()

Executes the query: `get_flights(query, *, proxy=None, integration=None)`.
Returns a `ResultList` (a `list` of `Flights` with a `.metadata` attribute).

## Result Object Attributes

Each itinerary is a `Flights` dataclass:
- `price`: int, in the local/selected currency (e.g., MAD when searching Morocco routes)
- `airlines`: list of DISPLAY names (e.g., `['Ryanair']`, `['easyJet']`), NOT IATA codes
- `type`: cabin/result type string
- `flights`: list of `SingleFlight` legs
- `carbon`: `CarbonEmission` data

Each leg is a `SingleFlight` dataclass:
- `from_airport` / `to_airport`: `Airport(name, code)` — use `.code` for IATA
- `departure` / `arrival`: `SimpleDatetime(date=(y, m, d), time=(h, m))` — `departure.time` is an `(h, m)` tuple
- `duration`: int, minutes
- `plane_type`: aircraft type string

`ResultList.metadata` is a `JsMetadata` with `airlines` and `alliances` lists.

Data source is Google Flights only. Some carriers the user expects may never
appear (e.g., Volotea never returned even when expected) — that is a feed
limitation, not a query bug.

## Common Use Cases

### One-way flight

```python
from fast_flights import FlightQuery, Passengers, create_query, get_flights

query = create_query(
    flights=[
        FlightQuery(date="2026-06-15", from_airport="JFK", to_airport="LAX"),
    ],
    trip="one-way",
    passengers=Passengers(adults=1),
    seat="economy",
    currency="USD",
)

result = get_flights(query)
for itin in result:
    print(f"{itin.price} - {itin.airlines}")
```

### Round-trip flight

```python
query = create_query(
    flights=[
        FlightQuery(date="2026-06-06", from_airport="CMN", to_airport="CDG"),
        FlightQuery(date="2026-06-13", from_airport="CDG", to_airport="CMN"),
    ],
    trip="round-trip",
    passengers=Passengers(adults=1),
    seat="economy",
    currency="EUR",
)
```

### Filtered search (per-leg + whole-search filters)

```python
leg = FlightQuery(
    date="2026-06-09",
    from_airport="TNG",
    to_airport="BVA",
    max_stops=1,
    earliest_departure_hour=7,
    latest_departure_hour=18,
    max_duration_minutes=720,
)

query = create_query(
    flights=[leg],
    currency="MAD",
    max_price=1500,
    carry_on_bags=1,
    checked_bags=1,
    hide_separate_and_self_transfer=True,
    exclude_basic_economy=True,
)
result = get_flights(query)
```

### Filter by price (find cheapest)

```python
result = get_flights(query)
cheapest = min(result, key=lambda itin: itin.price)
print(f"Cheapest: {cheapest.price}")
```

### Always query twice: general + direct-only (low-cost carriers hidden)

A general search often hides direct low-cost options. Observed cases:
- RBA->LYS 2026-11-21 general: only Air France 1365+; with `max_stops=0`: easyJet 415 direct
- MAD->RBA 2026-11-30 general: Air France only; with `max_stops=0`: Ryanair 385 direct
- MRS->MAD general: Iberia only; with `max_stops=0`: Ryanair 263

So for every one-way search, run BOTH queries and merge:

```python
import time

def search_with_directs(date, frm, to, **kwargs):
    base = dict(trip="one-way", passengers=Passengers(adults=1),
                seat="economy", currency="MAD")
    base.update(kwargs)
    general = create_query(
        flights=[FlightQuery(date=date, from_airport=frm, to_airport=to)],
        **base,
    )
    direct = create_query(
        flights=[FlightQuery(date=date, from_airport=frm, to_airport=to,
                              max_stops=0)],
        **base,
    )
    out = list(get_flights(general))
    time.sleep(0.6)
    out += [f for f in get_flights(direct)
            if f.price not in {x.price for x in out}]
    time.sleep(0.6)
    return out
```

### Filter by airline in Python (do NOT use `airlines=[...]`)

Server-side `airlines=["FR"]` is broken (raises `NoneType ... not subscriptable`
on no match). Fetch everything, then filter on display names:

```python
result = get_flights(query)
lowcost = [r for r in result
           if any(a.lower() in ("ryanair", "easyjet") for a in r.airlines)]
# r.airlines looks like ['Ryanair'] or ['easyJet'] — match case-insensitively
```

### Search multiple airports

```python
morocco_airports = ["CMN", "RBA", "TNG", "RAK"]
paris_airports = ["CDG", "ORY", "BVA"]

all_results = []
for from_air in morocco_airports:
    for to_air in paris_airports:
        query = create_query(
            flights=[
                FlightQuery(date="2026-06-09", from_airport=from_air, to_airport=to_air),
            ],
            trip="one-way",
            passengers=Passengers(adults=1),
            seat="economy",
            currency="MAD",
        )
        result = get_flights(query)
        if result:
            best = min(result, key=lambda itin: itin.price)
            all_results.append(best)

# Sort by price
all_results.sort(key=lambda x: x.price)
```

## Integrations

### Bright Data (for production)

```python
from fast_flights import get_flights
from fast_flights.integrations import BrightData

result = get_flights(query, integration=BrightData(zone="..."))
```

### SearchApi (richer data, sponsored)

```python
from fast_flights.integrations import SearchApi, SearchApiResult

result: SearchApiResult = get_flights(query, integration=SearchApi())
# result.flights, result.cheaper_alternatives,
# result.price_insights, result.booking_options, ...
```

## Error Handling

```python
from fast_flights import FlightsNotFound

try:
    result = get_flights(query)
except FlightsNotFound:
    print("No flights found")
except Exception as e:
    print(f"Error: {e}")
```

Meanings observed in practice:
- `FlightsNotFound`, `list index out of range`, and `'NoneType' object is not
  subscriptable` all mean NO RESULTS for that date/pair (or no match for an
  `airlines` filter) — treat as empty, not a crash. Skip and continue.
- Rate limiting: sleep 0.6–1s between calls. ~100 sequential queries work fine
  with no proxy and no blocks.

## Gathering User Preferences

If the user doesn't provide enough details, ask clarifying questions to tailor the search. The AI agent using this skill has access to an interactive question-asking tool - use it when user gives vague requirements like "I want to fly to Paris" or omits key details.

### Questions to ask

Ask these questions when user requirements are incomplete:

1. **From airport** - Which city/airport are you flying from?
2. **To airport** - Which destination city?
3. **Travel date** - When do you want to travel?
4. **Trip type** - One-way or round-trip?
5. **Budget** - What's your maximum budget?
6. **Airline preference** - Any specific airline?
7. **Timing preference** - Morning, afternoon, evening, or no preference?
8. **Stops** - Direct only or allow layovers?
9. **Cabin class** - Economy, business, or first?
10. **Passengers** - Number of travelers?

### Example question flow

When user says "I want to fly to Paris", ask:

```
header: "From"
question: "Which city are you flying from?"
options: [
  {label: "Casablanca", description: "CMN - Mohammed V International"},
  {label: "Tangier", description: "TNG - Ibn Battouta Airport"},
  {label: "Marrakech", description: "RAK - Menara Airport"},
  {label: "Rabat", description: "RBA - Rabat-Sale Airport"},
  {label: "Other", description: "I'll specify the city or airport name/code"},
]
```

```
header: "When"
question: "When do you want to travel?"
options: [
  {label: "This month", description: "Within the next 30 days"},
  {label: "Next month", description: "1-2 months from now"},
  {label: "Flexible", description: "Within the next 3 months"},
  {label: "Specific date", description: "I have a fixed date"},
]
```

```
header: "Trip"
question: "Is this a one-way or round-trip flight?"
options: [
  {label: "One-way", description: "Flying to destination only"},
  {label: "Round-trip", description: "Return flight included"},
  {label: "Multi-city", description: "Multiple destinations"},
]
```

```
header: "Budget"
question: "What's your budget for the flight?"
options: [
  {label: "Budget", description: "Under MAD 500"},
  {label: "Moderate", description: "MAD 500 - 1500"},
  {label: "Flexible", description: "MAD 1500 - 3000"},
  {label: "Any", description: "Price is not a concern"},
]
```

```
header: "Timing"
question: "What time of day do you prefer to fly?"
options: [
  {label: "Morning", description: "6:00 - 12:00"},
  {label: "Afternoon", description: "12:00 - 18:00"},
  {label: "Evening", description: "18:00 - 24:00"},
  {label: "No preference", description: "Any time works"},
]
```

### Building query from answers

After gathering answers, build the search:

```python
# Map answers to library parameters
from_airport = answers["From"]   # e.g., "CMN"
to_airport = answers["To"]       # e.g., "CDG"
date = map_date(answers["When"])  # e.g., "2026-06-15"
budget = answers["Budget"]       # e.g., "Budget", "Moderate"
timing = answers["Timing"]     # e.g., "Morning"
max_stops = 0 if direct_only else 2
seat = "economy"             # or from answers
```

### Suggested common routes

For quick suggestions, use these common Morocco routes:

```python
morocco_to_paris = [
    ("CMN", "CDG"), ("CMN", "ORY"), ("CMN", "BVA"),
    ("TNG", "CDG"), ("TNG", "ORY"), ("TNG", "BVA"),
    ("RAK", "CDG"), ("RAK", "ORY"), ("RAK", "BVA"),
]

morocco_to_london = [
    ("CMN", "LHR"), ("CMN", "LGW"), ("CMN", "STN"),
    ("TNG", "LGW"), ("TNG", "STN"),
    ("RAK", "LGW"), ("RAK", "STN"),
]
```

### Building query from answers

After getting answers, build the search:

```python
# Map answers to library parameters
from_airport = answers[0]  # e.g., "CMN"
to_airport = answers[1]      # e.g., "CDG"
date = map_date(answers[2])  # Convert to YYYY-MM-DD
budget = map_budget(answers[3])
timing = answers[4]          # "morning", "afternoon", "evening", "any"
max_stops = map_stops(answers[5])
seat = answers[6]
```

### Suggested common routes

For quick suggestions, use these common Morocco routes:

```python
morocco_to_paris = [
    ("CMN", "CDG"), ("CMN", "ORY"), ("CMN", "BVA"),
    ("TNG", "CDG"), ("TNG", "ORY"), ("TNG", "BVA"),
    ("RAK", "CDG"), ("RAK", "ORY"), ("RAK", "BVA"),
]

morocco_to_london = [
    ("CMN", "LHR"), ("CMN", "LGW"), ("CMN", "STN"),
    ("TNG", "LGW"), ("TNG", "STN"),
    ("RAK", "LGW"), ("RAK", "STN"),
]
```

## Useful Airport Codes

### Morocco
- CMN - Casablanca (Mohammed V)
- RBA - Rabat
- TNG - Tangier
- RAK - Marrakech

### Paris
- CDG - Charles de Gaulle
- ORY - Orly
- BVA - Beauvais (budget flights)

### Others
- JFK - New York JFK
- LAX - Los Angeles
- LHR - London Heathrow
- NRT - Tokyo Narita

## Notes

- Uses Google Flights internal API via Protobuf
- May require Bright Data integration or a proxy for production (avoids blocking),
  but ~100 sequential queries with 0.6–1s sleeps need neither
- `price` is an int in the selected `currency`; pass `currency` explicitly for predictable results
- `r.airlines` are display names (`['Ryanair']`), not IATA codes — filter case-insensitively in Python
- General searches can hide direct low-costs — always also query `max_stops=0`
- Data source is Google Flights only; missing carriers (e.g., Volotea) are a feed limitation
- `duration` is in minutes; time filters use 0–23 local airport time
- Always ask clarifying questions if user requirements are vague
