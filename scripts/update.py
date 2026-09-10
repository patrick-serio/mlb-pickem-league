import pandas as pd
import json
import os
import statsapi
import requests

# =========================
# 1. LOAD BACKEND DATA (PUBLISHED GOOGLE SHEETS CSV)
# =========================
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWl4YCWrtUO4JyHGGscp0PGFE8ioPicKk3kb4CfZwusb1-IBcPSK8hAVRNSiL-__nbDRqCQLPpvPu8/pub?gid=631576972&single=true&output=csv"

PLAYER_MAP_FILE = "config/player_map.json"
OUTPUT_FILE = "data/backend_updated.csv"

df = pd.read_csv(CSV_URL)

print("Loaded data:")
print(df.head())

# =========================
# 2. LOAD PLAYER MAP (JSON)
# =========================
with open(PLAYER_MAP_FILE, "r") as f:
    raw_map = json.load(f)

PLAYER_MAP = {
    item["Shorthand"]: item
    for item in raw_map
}

# =========================
# 3. TEMP FIX: DEFAULT SCORING TYPE
# =========================
def get_player_type(player):
    # TEMP FIX since JSON doesn't include Type yet
    return player.get("Type", "hitter")

# =========================
# 4. SAFE STATS EXTRACTION
# =========================
def get_stats(player_id, group):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats"

        params = {
            "stats": "season",
            "group": group,
            "season": 2026
        }

        r = requests.get(url, params=params)
        data = r.json()

        stats_list = data.get("stats", [])

        if not stats_list:
            return {}

        splits = stats_list[0].get("splits", [])

        if not splits:
            return {}

        return splits[0].get("stat", {})

    except Exception as e:
        print(f"Stats error for ID {player_id}: {e}")
        return {}

# Active Player Check (Injury/Minors Status) + MLB team lookup:
def build_active_roster_set():
    teams = statsapi.get('teams', {'sportId': 1, 'activeStatus': 'Y'})['teams']

    active_ids = set()
    team_map = {}   # player_id -> MLB team abbreviation

    for team in teams:
        roster = statsapi.get('team_roster', {
            'teamId': team['id'],
            'rosterType': 'active'
        })['roster']

        team_label = team.get('abbreviation') or team.get('name', '')

        for entry in roster:
            player_id = entry['person']['id']
            active_ids.add(player_id)
            team_map[player_id] = team_label

    return active_ids, team_map

# This function checks if a player ID is in the active roster set and returns "N" for active, "Y" for injured/minors
def get_injury_status(player_id):
    if player_id in ACTIVE_ROSTER_IDS:
        return "N"
    else:
        return "Y"

# Fallback for players not on an active 26-man roster (IL, minors) — their
# current org is still available from the person endpoint.
def get_mlb_team(player_id):
    if player_id in PLAYER_TEAM_MAP:
        return PLAYER_TEAM_MAP[player_id]

    try:
        data = statsapi.get('people', {'personIds': player_id})
        person = data.get('people', [{}])[0]
        team = person.get('currentTeam', {})
        return team.get('abbreviation') or team.get('name', '')
    except Exception as e:
        print(f"MLB team lookup error for ID {player_id}: {e}")
        return ""

# =========================
# 5. SCORING RULES
# =========================
def calculate_hitter_points(stats):

    hits = stats.get("hits", 0)
    doubles = stats.get("doubles", 0)
    triples = stats.get("triples", 0)
    home_runs = stats.get("homeRuns", 0)

    singles = hits - doubles - triples - home_runs
    if singles < 0:
        singles = 0

    return (
        singles * 3 +
        doubles * 6 +
        triples * 8 +
        home_runs * 10 +
        stats.get("baseOnBalls", 0) * 3 +
        stats.get("runs", 0) * 2 +
        stats.get("rbi", 0) * 2 +
        stats.get("stolenBases", 0) * 4 +
        stats.get("hitByPitch", 0) * 3
    )

def innings_to_outs(ip):
    try:
        ip_str = str(ip)

        if "." in ip_str:
            whole, frac = ip_str.split(".")

            whole = int(whole)

            # Only allow valid baseball fractions
            if frac == "1":
                extra_outs = 1
            elif frac == "2":
                extra_outs = 2
            else:
                extra_outs = 0

            return whole * 3 + extra_outs

        else:
            return int(ip_str) * 3

    except:
        return 0

def get_quality_starts(player_id):
    try:
        data = statsapi.player_stat_data(
            player_id,
            group="pitching",
            type="seasonAdvanced"
        )

        stats_list = data.get("stats", [])

        if not stats_list:
            return 0

        # This structure is slightly different than before
        return stats_list[0].get("stats", {}).get("qualityStarts", 0)

    except Exception as e:
        print(f"QS error for ID {player_id}: {e}")
        return 0

def calculate_pitcher_points(stats, quality_starts):

    outs = innings_to_outs(stats.get("inningsPitched", 0))

    return (
        outs +
        stats.get("earnedRuns", 0) * -3 +
        stats.get("wins", 0) * 5 +
        stats.get("saves", 0) * 5 +
        stats.get("strikeOuts", 0) * 3 +
        quality_starts * 5 +   # ← now injected cleanly
        stats.get("holds", 0) * 2
    )

# =========================
# 6. MAIN LOOP
# =========================

print("Building active MLB roster set...")
ACTIVE_ROSTER_IDS, PLAYER_TEAM_MAP = build_active_roster_set()
print(f"Loaded {len(ACTIVE_ROSTER_IDS)} active players")

for i, row in df.iterrows():

    player_name = row["Player"]
    player = PLAYER_MAP.get(player_name)

    if not player:
        print(f"Missing: {player_name}")
        df.at[i, "Total Points"] = 0
        continue

    player_id = player["Player ID"]
    player_type = player.get("Type", "hitter")
    injured_status = get_injury_status(player_id)

    total_points = 0
    hitting_stats = {}
    pitching_stats = {}
    qs = 0

    print("\n---")
    print("Player:", player_name)
    print("Type:", player_type)

    # =========================
    # CASE 1: HITTER
    # =========================
    if player_type in ["hitter", "both"]:

        hitting_stats = get_stats(player_id, "hitting")

        print("Hitting:", hitting_stats)

        if hitting_stats:
            total_points += calculate_hitter_points(hitting_stats)

    # =========================
    # CASE 2: PITCHER
    # =========================
    if player_type in ["pitcher", "both"]:

        pitching_stats = get_stats(player_id, "pitching")
        qs = get_quality_starts(player_id)

        print("Pitching:", pitching_stats)
        print("QS:", qs)

        if pitching_stats:
            total_points += calculate_pitcher_points(pitching_stats, qs)

    df.at[i, "Total Points"] = total_points
    df.at[i, "Injured"] = injured_status
    df.at[i, "Type"] = player_type
    df.at[i, "Player ID"] = player_id
    df.at[i, "MLB Team"] = get_mlb_team(player_id)

    # =========================
    # SAVE THE RAW STAT LINE
    # (so the dashboard can show what's behind each player's points,
    # not just the final total)
    # =========================
    df.at[i, "Hits"] = hitting_stats.get("hits", 0)
    df.at[i, "Doubles"] = hitting_stats.get("doubles", 0)
    df.at[i, "Triples"] = hitting_stats.get("triples", 0)
    df.at[i, "HR"] = hitting_stats.get("homeRuns", 0)
    df.at[i, "BB"] = hitting_stats.get("baseOnBalls", 0)
    df.at[i, "Runs"] = hitting_stats.get("runs", 0)
    df.at[i, "RBI"] = hitting_stats.get("rbi", 0)
    df.at[i, "SB"] = hitting_stats.get("stolenBases", 0)
    df.at[i, "HBP"] = hitting_stats.get("hitByPitch", 0)

    df.at[i, "IP"] = pitching_stats.get("inningsPitched", 0)
    df.at[i, "ER"] = pitching_stats.get("earnedRuns", 0)
    df.at[i, "Wins"] = pitching_stats.get("wins", 0)
    df.at[i, "Saves"] = pitching_stats.get("saves", 0)
    df.at[i, "K"] = pitching_stats.get("strikeOuts", 0)
    df.at[i, "QS"] = qs
    df.at[i, "Holds"] = pitching_stats.get("holds", 0)

# =========================
# 7. SAVE OUTPUT
# =========================
os.makedirs("data", exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"\nDone ✅ {OUTPUT_FILE} created")
