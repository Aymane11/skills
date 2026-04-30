---
name: fast-flights
description: Use fast-flights to scrape Google Flights and get flight information. Activated when user asks about flight prices, flight search, flight data, or needs to query flight availability/prices from Google Flights.
---

# fast-flights

A fast, robust Google Flights scraper (API) for Python. It uses Base64-encoded Protobuf to query Google Flights and retrieve flight data.

**PyPI Package:** `fast-flights` v3.0  
**Repository:** https://github.com/AWeirdDev/flights

## Installation

```bash
pip install fast-flights
```

## Actual API (v3.0 - Working)

The library's API changed in v3.0. Use these imports and functions:

```python
from fast_flights import FlightData, Passengers, create_filter, get_flights_from_filter

# Create a filter (replaces create_query from v2)
fl = create_filter(
    flight_data=[
        FlightData(date="2026-06-09", from_airport="TNG", to_airport="BVA"),
    ],
    trip="one-way",           # or "round-trip", "multi-city"
    passengers=Passengers(adults=1),
    seat="economy",         # "economy", "business", "first", "premium-economy"
)

# Execute the query
result = get_flights_from_filter(fl)

# Access results
print(f"Price: {result.current_price}")
print(f"Number of flights: {len(result.flights)}")
for f in result.flights:
    print(f"Price: {f.price}")
    print(f"Airline: {f.name}")
    print(f"Departure: {f.departure}")
    print(f"Arrival: {f.arrival}")
    print(f"Duration: {f.duration}")
    print(f"Stops: {f.stops}")
```

## Core Components

### FlightData

Defines a single flight segment with:
- `date`: Travel date in `YYYY-MM-DD` format
- `from_airport`: Three-letter IATA airport code (e.g., "CMN", "CDG", "TNG")
- `to_airport`: Three-letter IATA airport code
- `max_stops`: Optional maximum stops (e.g., 0 for direct only)

### Passengers

Configures passenger count:
- `adults`: Number of adult passengers (default: 1)
- `children`: Number of children
- `infants`: Number of infants

### create_filter()

Creates a flight filter with:
- `flight_data`: List of `FlightData` objects
- `trip`: Trip type - `"one-way"`, `"round-trip"`, or `"multi-city"`
- `passengers`: `Passengers` object
- `seat`: Cabin class - `"economy"`, `"business"`, `"first"`, or `"premium-economy"`
- `max_stops`: Optional max stops

### get_flights_from_filter()

Executes the query. Returns a `Result` object with:
- `current_price`: Typically price indicator ("typical", etc.)
- `flights`: List of `Flight` objects

## Flight Object Attributes

Each flight has:
- `price`: Price string (e.g., "MAD 845")
- `name`: Airline name
- `departure`: Departure time string (e.g., "5:45 on Tue, Jun 9" - returns 24h format by default)
- `arrival`: Arrival time string (e.g., "8:25 on Tue, Jun 9")
- `duration`: Duration (e.g., "2 hr 40 min")
- `stops`: Number of stops (0, 1, 2, "Unknown")
- `is_best`: Boolean if it's the best option

## Common Use Cases

### One-way flight

```python
from fast_flights import FlightData, Passengers, create_filter, get_flights_from_filter

fl = create_filter(
    flight_data=[
        FlightData(date="2026-06-15", from_airport="JFK", to_airport="LAX"),
    ],
    trip="one-way",
    passengers=Passengers(adults=1),
    seat="economy",
)

result = get_flights_from_filter(fl)
for f in result.flights:
    print(f"{f.price} - {f.name}")
```

### Round-trip flight

```python
fl = create_filter(
    flight_data=[
        FlightData(date="2026-06-06", from_airport="CMN", to_airport="CDG"),
        FlightData(date="2026-06-13", from_airport="CDG", to_airport="CMN"),
    ],
    trip="round-trip",
    passengers=Passengers(adults=1),
    seat="economy",
)
```

### Filter by price (find cheapest)

```python
result = get_flights_from_filter(fl)
cheapest = min(result.flights, key=lambda f: float(f.price.replace("MAD", "").replace(" ", "")))
print(f"Cheapest: {cheapest.price}")
```

### Search multiple airports

```python
morocco_airports = ["CMN", "RBA", "TNG", "RAK"]
paris_airports = ["CDG", "ORY", "BVA"]

all_results = []
for from_air in morocco_airports:
    for to_air in paris_airports:
        fl = create_filter(
            flight_data=[
                FlightData(date="2026-06-09", from_airport=from_air, to_airport=to_air),
            ],
            trip="one-way",
            passengers=Passengers(adults=1),
            seat="economy",
        )
        result = get_flights_from_filter(fl)
        if result.flights:
            best = min(result.flights, key=lambda f: float(f.price.replace("MAD", "").replace(" ", "")))
            all_results.append(best)

# Sort by price
all_results.sort(key=lambda x: float(x.price.replace("MAD", "").replace(" ", "")))
```

## Integrations

### Bright Data (for production)

```python
from fast_flights import get_flights_from_filter
from fast_flights.integrations import BrightData

result = get_flights_from_filter(fl, integration=BrightData())
```

## Error Handling

```python
try:
    result = get_flights_from_filter(fl)
except Exception as e:
    print(f"Error: {e}")
```

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
- May require Bright Data integration for production (avoids blocking)
- Results may include 0 price ("MAD 0") for some combinations - check individual flight details
- Flight times in departure/arrival format: "5:45 on Tue, Jun 9" (24h format)
- Duration format: "2 hr 40 min"
- Always ask clarifying questions if user requirements are vague