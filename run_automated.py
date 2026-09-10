"""
Entry point used by the daily GitHub Action.

Runs the data pipeline and rebuilds the dashboard, but skips report.py
(the PDF step), since that requires local font files and a cover image
that aren't tracked in this repo. Run run_all.py yourself, locally, any
time you want an updated PDF.
"""

import subprocess
import sys


def run_script(script_name):
    print(f"\n====================")
    print(f"Running {script_name}...")
    print(f"====================\n")

    result = subprocess.run([sys.executable, script_name], text=True)

    if result.returncode != 0:
        print(f"\n❌ Error in {script_name}")
        sys.exit(1)


run_script("scripts/update.py")            # pulls MLB stats → data/backend_updated.csv
run_script("scripts/team_scores.py")       # builds data/team_rosters_updated.csv + data/team_scores.csv
run_script("scripts/build_dashboard.py")   # generates docs/index.html for GitHub Pages

print("\n🎉 ALL DONE — DASHBOARD REFRESHED")
