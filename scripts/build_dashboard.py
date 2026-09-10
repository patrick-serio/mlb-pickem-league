"""
build_dashboard.py

Reads data/team_scores.csv + data/team_rosters_updated.csv (produced by
team_scores.py) and writes a single self-contained static HTML page to
docs/index.html.

That file is what GitHub Pages serves — no server, no build step, no JS
framework. Re-running this script (or the daily GitHub Action) overwrites it
in place, so the published page always reflects the latest data.
"""

import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import html
import os

# =========================
# CONFIG
# =========================

LEAGUE_NAME = "2026 Baseball Pick'em"     # <-- change to your league's name
TEAM_SCORES_FILE = "data/team_scores.csv"
ROSTER_FILE = "data/team_rosters_updated.csv"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
DISPLAY_TZ = "America/New_York"             # timestamp shown on the page

# =========================
# LOAD DATA
# =========================

def load_data():
    scores = pd.read_csv(TEAM_SCORES_FILE)
    scores["Total Score"] = pd.to_numeric(scores["Total Score"], errors="coerce").fillna(0)
    scores = scores.sort_values("Total Score", ascending=False).reset_index(drop=True)

    roster = pd.read_csv(ROSTER_FILE)
    roster["Total Score"] = pd.to_numeric(roster["Total Score"], errors="coerce").fillna(0)

    return scores, roster


def esc(value) -> str:
    return html.escape(str(value))


# =========================
# HTML FRAGMENTS
# =========================

def build_standings_rows(scores: pd.DataFrame) -> str:
    rows = []
    for i, row in scores.iterrows():
        rank = i + 1
        rows.append(f"""
        <li class="standing-row">
          <span class="rank">{rank}</span>
          <a class="team-name" href="#team-{esc(row['Team']).replace(' ', '-')}">{esc(row['Team'])}</a>
          <span class="pts">{int(row['Total Score'])}<span class="pts-label"> pts</span></span>
        </li>""")
    return "\n".join(rows)


def build_roster_sections(roster: pd.DataFrame) -> str:
    sections = []
    team_totals = roster.groupby("Team")["Total Score"].sum().sort_values(ascending=False)

    for team, total in team_totals.items():
        team_df = roster[roster["Team"] == team]
        row_html = []
        for _, r in team_df.iterrows():
            injured = str(r.get("Injured", "")).strip().upper() == "Y"
            css_class = "roster-row injured" if injured else "roster-row"
            player_name = r.get("Full Name")
            if pd.isna(player_name) or not str(player_name).strip():
                player_name = r.get("Player")
            tag = '<span class="injury-tag">INJ</span>' if injured else ""
            row_html.append(f"""
            <tr class="{css_class}">
              <td class="pos">{esc(r.get('Position', ''))}</td>
              <td class="player">{esc(player_name)} {tag}</td>
              <td class="score">{int(r['Total Score'])}</td>
            </tr>""")

        anchor = esc(team).replace(" ", "-")
        sections.append(f"""
      <details class="team-card" id="team-{anchor}">
        <summary>
          <span class="summary-team">{esc(team)}</span>
          <span class="summary-total">{int(total)} pts</span>
        </summary>
        <table class="roster-table">
          <thead>
            <tr><th>Pos</th><th>Player</th><th>Score</th></tr>
          </thead>
          <tbody>
            {''.join(row_html)}
          </tbody>
        </table>
      </details>""")

    return "\n".join(sections)


# =========================
# PAGE TEMPLATE
# =========================

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{league_name} — Standings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: #303444;
    --navy-light: #454a60;
    --gold: #D5A451;
    --cream: #F6EFDF;
    --cream-row: #EDE2C4;
    --red: #D14B36;
    --text: #22242E;
    --white: #FFFFFF;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: var(--cream);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    line-height: 1.5;
  }}

  header {{
    background: var(--navy);
    color: var(--white);
    padding: 2.5rem 1.5rem 2rem;
  }}

  .header-inner {{
    max-width: 760px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}

  h1 {{
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    font-size: 2.1rem;
    margin: 0;
    letter-spacing: 0.01em;
  }}

  .updated {{
    color: var(--gold);
    font-size: 0.9rem;
    font-family: 'Inter', sans-serif;
  }}

  main {{
    max-width: 760px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }}

  h2 {{
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    font-size: 1.3rem;
    color: var(--navy);
    margin: 0 0 1rem;
    border-bottom: 3px solid var(--gold);
    padding-bottom: 0.4rem;
  }}

  section + section {{
    margin-top: 2.5rem;
  }}

  ul.standings {{
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    overflow: hidden;
  }}

  .standing-row {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.7rem 1rem;
    background: var(--white);
  }}

  .standing-row:nth-child(odd) {{
    background: var(--cream-row);
  }}

  .rank {{
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--gold);
    width: 1.6rem;
    text-align: right;
  }}

  .team-name {{
    flex: 1;
    font-weight: 600;
    color: var(--navy);
    text-decoration: none;
  }}

  .team-name:hover {{
    text-decoration: underline;
  }}

  .pts {{
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }}

  .pts-label {{
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 0.8rem;
    color: #6b6e7a;
  }}

  .team-card {{
    background: var(--white);
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    margin-bottom: 0.75rem;
    overflow: hidden;
  }}

  .team-card summary {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1.1rem;
    cursor: pointer;
    background: var(--navy);
    color: var(--white);
    font-family: 'Oswald', sans-serif;
    list-style: none;
  }}

  .team-card summary::-webkit-details-marker {{
    display: none;
  }}

  .summary-team {{
    font-weight: 600;
    font-size: 1.05rem;
  }}

  .summary-total {{
    color: var(--gold);
    font-weight: 600;
  }}

  .roster-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }}

  .roster-table th {{
    text-align: left;
    background: var(--cream-row);
    color: var(--navy);
    padding: 0.5rem 1rem;
    font-weight: 600;
  }}

  .roster-table td {{
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--cream-row);
  }}

  .roster-row.injured td {{
    background: var(--red);
    color: var(--white);
  }}

  .injury-tag {{
    display: inline-block;
    margin-left: 0.4rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    background: rgba(255,255,255,0.25);
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
  }}

  .score {{
    font-variant-numeric: tabular-nums;
    text-align: right;
  }}

  footer {{
    text-align: center;
    color: #8a8d99;
    font-size: 0.8rem;
    padding: 1.5rem;
  }}

  @media (max-width: 480px) {{
    h1 {{ font-size: 1.6rem; }}
    .roster-table {{ font-size: 0.85rem; }}
  }}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <h1>{league_name}</h1>
    <span class="updated">Updated {updated}</span>
  </div>
</header>

<main>
  <section>
    <h2>Standings</h2>
    <ul class="standings">
      {standings_rows}
    </ul>
  </section>

  <section>
    <h2>Rosters</h2>
    {roster_sections}
  </section>
</main>

<footer>
  Refreshes automatically every day.
</footer>

</body>
</html>
"""


def build_page(scores: pd.DataFrame, roster: pd.DataFrame) -> str:
    now = datetime.now(timezone.utc).astimezone(ZoneInfo(DISPLAY_TZ))
    updated = now.strftime("%B %d, %Y at %-I:%M %p %Z")

    return PAGE_TEMPLATE.format(
        league_name=esc(LEAGUE_NAME),
        updated=esc(updated),
        standings_rows=build_standings_rows(scores),
        roster_sections=build_roster_sections(roster),
    )


def main():
    scores, roster = load_data()
    page_html = build_page(scores, roster)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page_html)

    print(f"Dashboard generated → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
