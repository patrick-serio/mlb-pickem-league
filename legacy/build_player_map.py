import pandas as pd
import statsapi
import json

# -----------------------------
# LOAD YOUR SHEET
# -----------------------------
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWl4YCWrtUO4JyHGGscp0PGFE8ioPicKk3kb4CfZwusb1-IBcPSK8hAVRNSiL-__nbDRqCQLPpvPu8/pub?gid=631576972&single=true&output=csv"
df = pd.read_csv(CSV_URL)

player_names = df["Player"].dropna().unique()

# -----------------------------
# BUILD MAP
# -----------------------------
PLAYER_MAP = {}

def resolve_name(name):
    try:
        results = statsapi.lookup_player(name)
        if not results:
            print(f"❌ No match: {name}")
            return None

        # take best match
        return results[0]["fullName"]

    except Exception as e:
        print(f"Error: {name} -> {e}")
        return None

for name in player_names:
    real_name = resolve_name(name)

    if real_name:
        PLAYER_MAP[name] = real_name
    else:
        PLAYER_MAP[name] = name  # fallback (so nothing breaks)

# -----------------------------
# SAVE OUTPUT
# -----------------------------
with open("player_map.json", "w") as f:
    json.dump(PLAYER_MAP, f, indent=4)

print("Done ✅ PLAYER_MAP created")