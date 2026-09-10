"""
Run this yourself, locally, any time you want the full pipeline including
the PDF (fantasy_summary.pdf in output/). Requires assets/fonts/*.ttf and
assets/Cover_Page_2026.png to be present.

For the automated daily refresh (dashboard only, no PDF), see run_automated.py
— that's what the GitHub Action runs.
"""

import subprocess
import sys


def run_script(script_name):
    print(f"\n====================")
    print(f"Running {script_name}...")
    print(f"====================\n")

    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print(f"\n❌ Error in {script_name}")
        exit(1)

# =========================
# RUN PIPELINE
# =========================

run_script("scripts/update.py")            # pulls MLB stats → data/backend_updated.csv
run_script("scripts/team_scores.py")       # builds data/team_rosters_updated.csv + data/team_scores.csv
run_script("scripts/report.py")            # generates output/fantasy_summary.pdf
run_script("scripts/build_dashboard.py")   # generates docs/index.html for GitHub Pages

print("\n🎉 ALL DONE — REPORT + DASHBOARD GENERATED")
