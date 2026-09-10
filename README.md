# Fantasy League Automation

Pulls MLB stats, scores your league's rosters, and publishes a standings
dashboard — automatically, once a day, no manual steps.

## Folder structure

```
fantasy-league/
├── .github/workflows/daily-refresh.yml   Scheduled automation (runs daily)
├── assets/                               Fonts + cover image for the PDF report
│   └── fonts/
├── config/
│   └── player_map.json                   Shorthand → full name / MLB ID / hitter-pitcher map
├── data/                                 Pipeline outputs (auto-updated daily)
│   ├── backend_updated.csv
│   ├── team_scores.csv
│   └── team_rosters_updated.csv
├── docs/
│   └── index.html                        The published dashboard (GitHub Pages serves this)
├── output/
│   └── fantasy_summary.pdf               Generated only when you run run_all.py locally
├── scripts/
│   ├── update.py                         Pulls MLB stats → data/backend_updated.csv
│   ├── team_scores.py                    Merges rosters + stats → data/*.csv
│   ├── report.py                         Builds the PDF (manual use only)
│   └── build_dashboard.py                Builds docs/index.html
├── legacy/                               Superseded one-off scripts, kept for reference
├── run_all.py                            Full pipeline incl. PDF — run manually
├── run_automated.py                      Pipeline without PDF — what the daily Action runs
└── requirements.txt
```

## Two ways to run it

- **`python run_automated.py`** — stats → scores → dashboard. This is what
  runs automatically every day via GitHub Actions.
- **`python run_all.py`** — same, plus generates `output/fantasy_summary.pdf`.
  Run this yourself locally whenever you want a PDF; it needs the font files
  and cover image in `assets/` to be present.

See `SETUP.md` for how to get this live on GitHub.
