#!/usr/bin/env python3
"""
Fetch D&D 5e race and subrace data from the 5e API and cache it locally.
Run once: python tools/fetch_dnd_data.py
"""
import requests
import json
import time
from pathlib import Path

endpoints = [
    "skills",
    "ability-scores",
    "traits",
    "proficiencies"
]

API_ROOT = "https://www.dnd5eapi.co"
CACHE_DIR = Path("data/dnd_cache")

def fetch_json(url):
    """Fetch JSON from a URL with a small delay to be polite."""
    print(f"Fetching {url}...")
    time.sleep(0.1)  # be kind to the API
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Get list of all races
    races_index = fetch_json(f"{API_ROOT}/api/2014/races")
    races = []
    for race_item in races_index["results"]:
        # race_item["url"] already starts with "/api/2014/races/..."
        race_detail = fetch_json(f"{API_ROOT}{race_item['url']}")
        races.append(race_detail)

    # Save races
    with open(CACHE_DIR / "races.json", "w") as f:
        json.dump(races, f, indent=2)
    print(f"Saved {len(races)} races to {CACHE_DIR / 'races.json'}")

    # 2. Get list of all subraces
    subraces_index = fetch_json(f"{API_ROOT}/api/2014/subraces")
    subraces = []
    for sub_item in subraces_index["results"]:
        sub_detail = fetch_json(f"{API_ROOT}{sub_item['url']}")
        subraces.append(sub_detail)

    with open(CACHE_DIR / "subraces.json", "w") as f:
        json.dump(subraces, f, indent=2)
    print(f"Saved {len(subraces)} subraces to {CACHE_DIR / 'subraces.json'}")

    # 3. Get endpoints "skills", "ability-scores", "traits", "proficiencies"
    for endpoint in endpoints:
        data = fetch_json(f"{API_ROOT}/api/2014/{endpoint}")
        # Save full details for each item (similar to races)
        items = []
        for item in data["results"]:
            detail = fetch_json(f"{API_ROOT}{item['url']}")
            items.append(detail)
        with open(CACHE_DIR / f"{endpoint}.json", "w") as f:
            json.dump(items, f, indent=2)
        print(f"Saved {len(items)} {endpoint} to {CACHE_DIR / f'{endpoint}.json'}")

if __name__ == "__main__":
    main()