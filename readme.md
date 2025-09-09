# Route Optimizer

Script for planning daily client visits that balances urgency with travel efficiency.

## Problem

Was spending too much time driving between client locations without any systematic way to plan routes. Needed something to prioritize overdue clients while keeping travel distances reasonable.

## What it does

Takes a CSV of client locations and visit history, then generates an optimized daily route. Focuses on clients who haven't been visited recently and clusters nearby locations together. Uses Google Routes API to account for real traffic and road conditions.

## Setup

```bash
pip install pandas numpy scikit-learn matplotlib requests python-dotenv

# Add Google Maps API key to .env file
GOOGLE_MAPS_API_KEY=your_key_here

python start.py
```

## Input

Needs a CSV with client names, coordinates, and days since last visit. The script filters for clients over 20 days overdue and tries to build routes of about 10-13 stops.

## Output

Generates a route visualization and prints travel time estimates. Also reorders stops based on opening times if that data is available.

The algorithm tries different starting points and picks the route that best balances urgency against total distance. Usually results in 4-5 hours of driving time plus stops.