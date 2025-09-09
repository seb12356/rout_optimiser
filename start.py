import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import haversine_distances
import matplotlib.pyplot as plt
import requests
import os


GOOGLE_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')


df = pd.read_csv("clients_with_visit_days.csv")
df = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

if "days_since_last_visit" not in df.columns:
    print('nope')
    df["days_since_last_visit"] = np.random.randint(0, 101, size=len(df))

df_overdue = df[df["days_since_last_visit"] > 20].copy().reset_index(drop=True)


# Generate Route Candidates

top_overdue = df_overdue.nlargest(30, "days_since_last_visit")

coords_rad = np.radians(df_overdue[["latitude", "longitude"]])
dist_matrix_miles = haversine_distances(coords_rad, coords_rad) * 3958.8

results = []

for idx in top_overdue.index:
    anchor_idx = idx
    distances = dist_matrix_miles[anchor_idx]
    nearby_idxs = distances.argsort()[1:10]
    candidate_idxs = [anchor_idx] + list(nearby_idxs)

    remaining = set(candidate_idxs)
    route = [anchor_idx]
    remaining.remove(anchor_idx)
    current = anchor_idx
    total_miles = 0

    while remaining:
        next_stop = min(remaining, key=lambda x: dist_matrix_miles[current, x])
        total_miles += dist_matrix_miles[current, next_stop]
        route.append(next_stop)
        remaining.remove(next_stop)
        current = next_stop

    avg_days = df_overdue.loc[route, "days_since_last_visit"].mean()
    results.append({"route": route,
        "total_distance_miles": total_miles,
        "avg_days_since_visit": avg_days})


# Select Best Route

results_sorted = sorted(results, key=lambda x: (-x["avg_days_since_visit"], x["total_distance_miles"]))
best_route = results_sorted[0]
route_df = df_overdue.loc[best_route["route"]].reset_index(drop=True)


# Send to Google API for Driving Optimization

start_address = "46 Albert Avenue, Hull, HU3 6QG, UK"
end_address = start_address

addresses = route_df["formatted_address"].tolist()
waypoints = [{"address": addr} for addr in addresses]

body = {
    "origin": {"address": start_address},
    "destination": {"address": end_address},
    "intermediates": waypoints,
    "travelMode": "DRIVE",
    "optimizeWaypointOrder": True,
    "routingPreference": "TRAFFIC_AWARE",
    "languageCode": "en-GB",
    "units": "IMPERIAL"}

headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": GOOGLE_API_KEY,
    "X-Goog-FieldMask": "*"}

url = "https://routes.googleapis.com/directions/v2:computeRoutes"
response = requests.post(url, json=body, headers=headers)
data = response.json()

if "routes" not in data:
    raise Exception(f"Google Routes API error: {data}")

route = data["routes"][0]
legs = route["legs"]
ordered_indices = route.get("optimizedIntermediateWaypointIndex", [])


# Reorder route_df
route_df = route_df.iloc[ordered_indices].reset_index(drop=True)

# Extract opening hour
def parse_hour(time_str):
    try:
        hour = int(time_str.split(":")[0])
        return hour if hour < 10 else hour - 24  # 10 or later means earlier (AM), so shift down
    except:
        return 99  # if blank or invalid, push to end

# Compare first and last opening time
top_open = parse_hour(route_df.loc[0, "open"])
bottom_open = parse_hour(route_df.loc[len(route_df) - 1, "open"])

# If bottom opens earlier than top, flip the route
if bottom_open < top_open:
    route_df = route_df.iloc[::-1].reset_index(drop=True)



# 5.Add Start/End

start_row = pd.Series({
    "name": "Home",
    "postcode": "",
    "open": "",
    "days_since_last_visit": "",
    "gpin_check": "",
    "VIP": "",
    "business_status": "",
    "user_ratings_total": "",
    "system_type": "",
    "status": "",
    "latitude":"" , # TODO Add lat & long to run
    "longitude":"" })

route_df = pd.concat([pd.DataFrame([start_row]), route_df, pd.DataFrame([start_row])], ignore_index=True)


# 6. Plot Driving Route

plt.plot(route_df["longitude"], route_df["latitude"], '-o', label='Google Optimized Driving Route')
for i, row in route_df.iterrows():
    plt.text(row["longitude"], row["latitude"], str(i + 1), fontsize=9, ha='center')

plt.title("Final Driving-Optimized Visit Route")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("final_google_optimized_route.png", dpi=300)
plt.show()


# 7. Show Final Reordered DataFrame and Totals


# Safely compute total distance and duration
total_distance_meters = sum(leg.get("distanceMeters", 0) for leg in legs)
total_duration_seconds = sum(int(leg.get("duration", "0s").replace("s", "")) for leg in legs)

total_distance_miles = total_distance_meters / 1609.34
total_duration_minutes = (total_duration_seconds / 60)
total_duration_minutes_route = (total_duration_seconds / 60) + 40* (len(route_df)-2)
print(len(route_df))
hours, minutes = divmod(total_duration_minutes_route, 60)
duration_str = f"{int(hours)} hr {int(minutes)} min"
print(f"⏱️ Estimated Time: {duration_str}")

print(f"\n Total Distance: {total_distance_miles:.2f} miles")
print(f"Estimated Time: {total_duration_minutes:.1f} minutes")

print("\nFinal Route (Driving-Optimized):")
print(route_df[["name", "postcode", "open", 'google_maps_url',"days_since_last_visit",'rating', "gpin_check","VIP", "business_status", "user_ratings_total", "system_type", "status"]])
