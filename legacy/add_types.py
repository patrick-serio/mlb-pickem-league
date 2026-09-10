import json

with open("player_map_with_ids.json", "r") as f:
    players = json.load(f)

for p in players:
    print("\n---")
    print(p["Shorthand"], " / ", p["Full Name"])
    t = input("Type (hitter / pitcher / both): ").strip().lower()

    if t not in ["hitter", "pitcher", "both"]:
        t = "hitter"

    p["Type"] = t

with open("player_map.json", "w") as f:
    json.dump(players, f, indent=4)

print("\nDone ✅ updated player_map.json")