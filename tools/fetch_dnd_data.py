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

    # --- NEW: Fetch classes and fighting styles ---
    # 4. Get list of all classes
    classes_index = fetch_json(f"{API_ROOT}/api/2014/classes")
    classes = []
    for class_item in classes_index["results"]:
        class_detail = fetch_json(f"{API_ROOT}{class_item['url']}")
        classes.append(class_detail)

    # Save classes (optional, may not be needed elsewhere but useful for debugging)
    with open(CACHE_DIR / "classes.json", "w") as f:
        json.dump(classes, f, indent=2)
    print(f"Saved {len(classes)} classes to {CACHE_DIR / 'classes.json'}")

    # 5. For each class, fetch features and extract fighting styles
    class_fighting_styles = {}
    for class_detail in classes:
        class_index = class_detail["index"]
        fighting_styles = []
        # Fetch features for this class
        features_url = f"{API_ROOT}{class_detail['url']}/features"
        features_data = fetch_json(features_url)
        for feature_ref in features_data["results"]:
            feature_detail = fetch_json(f"{API_ROOT}{feature_ref['url']}")
            # Check if this feature is a fighting style feature
            # Look for "Fighting Style" in the name, or maybe the feature grants a choice of fighting styles
            if "Fighting Style" in feature_detail.get("name", ""):
                # Some features have a 'feature_options' field with a list of options
                if "feature_options" in feature_detail:
                    options = feature_detail["feature_options"]
                    # The options may be in a 'from' list
                    for opt in options.get("from", []):
                        if opt.get("item"):
                            style_name = opt["item"]["name"]
                            fighting_styles.append(style_name)
                else:
                    # Fallback: try to parse the description
                    desc = " ".join(feature_detail.get("desc", []))
                    # Example: "You adopt a particular style of fighting: Archery, Defense, Dueling, ..."
                    if ":" in desc:
                        parts = desc.split(":", 1)
                        if len(parts) > 1:
                            styles_part = parts[1]
                            # Clean up
                            styles_part = styles_part.replace(".", "").strip()
                            # Split by commas or 'or'
                            styles = [s.strip() for s in styles_part.split(",") if s.strip()]
                            if styles:
                                fighting_styles.extend(styles)
        if fighting_styles:
            class_fighting_styles[class_index] = fighting_styles
        else:
            # Even if no fighting styles found, store empty list to indicate we processed it
            class_fighting_styles[class_index] = []

    # Save fighting styles mapping
    with open(CACHE_DIR / "class_fighting_styles.json", "w") as f:
        json.dump(class_fighting_styles, f, indent=2)
    print(f"Saved fighting styles mapping for {len(class_fighting_styles)} classes to {CACHE_DIR / 'class_fighting_styles.json'}")

if __name__ == "__main__":
    main()