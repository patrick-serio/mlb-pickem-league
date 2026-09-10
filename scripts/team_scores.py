import pandas as pd
import json
import os

# =========================
# 1. CONFIG
# =========================

# Your team sheet published as CSV
TEAM_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT3JhNiWsIjqysuFgUr6V4udniZq9Z9a_P5ZDwjNij_ivydACmqXkbUo1H3S9RqTjsjkQGdUJSEB6-G/pub?gid=1506488927&single=true&output=csv"

# File created by update.py
BACKEND_FILE = "data/backend_updated.csv"
PLAYER_MAP_FILE = "config/player_map.json"

# Output files
ROSTER_OUTPUT = "data/team_rosters_updated.csv"
TEAM_OUTPUT = "data/team_scores.csv"

# Raw stat columns update.py attaches to each player, carried through to the
# roster file so the dashboard can show what's behind each point total.
STAT_COLUMNS = [
    "Hits", "Doubles", "Triples", "HR", "BB", "Runs", "RBI", "SB", "HBP",
    "IP", "ER", "Wins", "Saves", "K", "QS", "Holds",
]

# Non-numeric extras also attached by update.py.
EXTRA_COLUMNS = ["Type", "Player ID", "MLB Team"]

# =========================
# 2. LOAD DATA
# =========================

print("Loading data...")

team_df = pd.read_csv(TEAM_URL)
backend_df = pd.read_csv(BACKEND_FILE)

with open(PLAYER_MAP_FILE, "r") as f:
    player_map = pd.DataFrame(json.load(f))

backend_df = backend_df.merge(
    player_map[["Shorthand", "Full Name"]],
    left_on="Player",
    right_on="Shorthand",
    how="left"
)

backend_df.drop(columns=["Shorthand"], inplace=True)

# =========================
# 3. CLEAN TEAM SHEET
# =========================

# Forward-fill team names (since only first row has it)
team_df["Team"] = team_df["Team"].ffill()

# Optional: clean whitespace
team_df["Player"] = team_df["Player"].str.strip()
backend_df["Player"] = backend_df["Player"].str.strip()

# =========================
# 4. STANDARDIZE COLUMN NAMES
# =========================

# Ensure consistent naming
if "Total Points" in backend_df.columns:
    backend_df = backend_df.rename(columns={"Total Points": "Total Score"})

# =========================
# 5. MERGE (REPLACES XLOOKUP)
# =========================

print("Merging team roster with backend stats...")

backend_cols = ["Player", "Full Name", "Total Score", "Injured"] + [
    c for c in (EXTRA_COLUMNS + STAT_COLUMNS) if c in backend_df.columns
]

merged = team_df.merge(
    backend_df[backend_cols],
    on="Player",
    how="left"
)

# =========================
# FIX COLUMN NAMES
# =========================

# Rename backend columns first
merged.rename(columns={
    "Total Points": "Total Score_backend",
    "Injured": "Injured_backend"
}, inplace=True)

# If pandas created _x/_y columns, handle them
if "Total Score_y" in merged.columns:
    merged.rename(columns={"Total Score_y": "Total Score"}, inplace=True)
elif "Total Score_backend" in merged.columns:
    merged.rename(columns={"Total Score_backend": "Total Score"}, inplace=True)

if "Injured_y" in merged.columns:
    merged.rename(columns={"Injured_y": "Injured"}, inplace=True)
elif "Injured_backend" in merged.columns:
    merged.rename(columns={"Injured_backend": "Injured"}, inplace=True)

# Drop old columns from team sheet
cols_to_drop = [col for col in ["Total Score_x", "Injured?"] if col in merged.columns]
merged.drop(columns=cols_to_drop, inplace=True)

# =========================
# DEBUG CHECK
# =========================

print("\nFinal columns:")
print(merged.columns)

# =========================
# 6. HANDLE MISSING PLAYERS
# =========================

missing = merged[merged["Total Score"].isna()]["Player"].unique()

if len(missing) > 0:
    print("\n⚠️ Missing players (not found in backend):")
    for p in missing:
        print(" -", p)

# Fill missing values with 0
merged["Total Score"] = merged["Total Score"].fillna(0)

numeric_stat_cols = [c for c in STAT_COLUMNS if c in merged.columns]
merged[numeric_stat_cols] = merged[numeric_stat_cols].fillna(0)
if "Type" in merged.columns:
    merged["Type"] = merged["Type"].fillna("hitter")
if "MLB Team" in merged.columns:
    merged["MLB Team"] = merged["MLB Team"].fillna("")
if "Player ID" in merged.columns:
    merged["Player ID"] = merged["Player ID"].fillna(0)

# =========================
# 7. CALCULATE TEAM SCORES
# =========================

print("\nCalculating team totals...")

team_scores = (
    merged.groupby("Team")["Total Score"]
    .sum()
    .reset_index()
    .sort_values(by="Total Score", ascending=False)
)

# =========================
# 8. SAVE OUTPUTS
# =========================

os.makedirs("data", exist_ok=True)
merged.to_csv(ROSTER_OUTPUT, index=False)
team_scores.to_csv(TEAM_OUTPUT, index=False)

print("\nDone ✅")
print(f"Updated roster file → {ROSTER_OUTPUT}")
print(f"Team scores file → {TEAM_OUTPUT}")

# =========================
# 9. PRINT STANDINGS
# =========================

print("\n=== LEAGUE STANDINGS ===")

team_scores = team_scores.reset_index(drop=True)

for i, row in team_scores.iterrows():
    print(f"{i+1}. {row['Team']} - {int(row['Total Score'])} pts")
