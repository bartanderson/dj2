import json

with open('config/fsms/buy.json', 'r') as f:
    data = json.load(f)

print("Keys:", data.keys())
print("Events type:", type(data.get('events')))
if 'events' in data:
    for event, val in data['events'].items():
        print(f"Event '{event}': type={type(val)}")
        if isinstance(val, dict):
            print("  Keys:", val.keys())
        elif isinstance(val, list):
            print("  First element type:", type(val[0]) if val else "empty")