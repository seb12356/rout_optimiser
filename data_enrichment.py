from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
import os


google_key = os.getenv('GOOGLE_MAPS_API_KEY')
def get_coordinates_from_postcode(postcode):
    # get lat and long from UK postcode using Postcode.io API
    postcode_clean = postcode.replace(" ", "")
    url = f"https://api.postcodes.io/postcodes/{postcode_clean}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()["result"]
            return data["latitude"], data["longitude"]
    except Exception as e:
        print(f"error for {postcode}: {e}")
    return None, None

def get_google_place_details(name, lat, lng):
    # use google places API to get business information
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 500,
        "keyword": name,
        "type": "restaurant",
        "key": google_key}
    response = requests.get(nearby_url, params=params).json()

    if not response.get("results"):
        return [None] * 9

    place = response["results"][0]
    address = place.get("vicinity", "")
    location = place["geometry"]["location"]
    place_id = place.get("place_id")

    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        "place_id": place_id,
        "fields": "url,website,name,geometry,formatted_address,"
                  "business_status,price_level,rating,user_ratings_total",
        "key": google_key}

    details_response = requests.get(details_url, params=details_params).json()
    details = details_response.get("result", {})
    print(details)
    return (
        details.get("formatted_address", address),
        location["lat"],
        location["lng"],
        details.get("url"),
        details.get("website"),
        details.get("business_status"),
        details.get("price_level"),
        details.get("rating"),
        details.get("user_ratings_total"))

def enrich_csv(input_csv, output_csv):
    #read takeaways, enrich with Google data, and save to csv
    df = pd.read_csv(input_csv, index_col=False)

    # Add new columns
    df["formatted_address"] = ""
    df["latitude"] = ""
    df["longitude"] = ""
    df["google_maps_url"] = ""
    df["website"] = ""
    df["business_status"] = ""
    df["price_level"] = ""
    df["rating"] = ""
    df["user_ratings_total"] = ""

    for i, row in df.iterrows():
        name = row.get("name")
        postcode = row.get("postcode")
        if pd.isna(name) or pd.isna(postcode):
            continue

        lat, lng = get_coordinates_from_postcode(postcode)
        if lat is None or lng is None:
            continue

        (addr, place_lat, place_lng, maps_url, website,
         status, price, rating, ratings_total) = get_google_place_details(name, lat, lng)

        df.at[i, "formatted_address"] = addr
        df.at[i, "latitude"] = place_lat
        df.at[i, "longitude"] = place_lng
        df.at[i, "google_maps_url"] = maps_url
        df.at[i, "website"] = website
        df.at[i, "business_status"] = status
        df.at[i, "price_level"] = price
        df.at[i, "rating"] = rating
        df.at[i, "user_ratings_total"] = ratings_total

        time.sleep(0.3)  # Respect API rate limits

    df.to_csv(output_csv, index=False)
    print(f"\noutput saved to {output_csv}")


enrich_csv("clients.csv", "client_with_url.csv")




def is_foodhub_site(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        time.sleep(4)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        if 'foodhub' in str(soup):
            return True
        return False

    except Exception as e:
        print(f"rrror checking {url}: {e}")
        return False



data = pd.read_csv('client_with_url.csv')

data['gpin_check'] =''
urls = data['website'].tolist()


for index, row in data.iterrows():
    if is_foodhub_site(row['website']):
        data.at[index, 'gpin_check'] = 'Foodhub'

    else:
        data.at[index, 'gpin_check'] = 'Other'

data.to_csv('clients_gpin.csv')