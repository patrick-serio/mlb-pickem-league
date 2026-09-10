"""
build_dashboard.py

Reads data/team_scores.csv + data/team_rosters_updated.csv (produced by
team_scores.py) and writes two self-contained static HTML pages:

  docs/index.html    - standings + collapsible team rosters
  docs/players.html  - every player's point total and the raw stat line
                        behind it, sortable by column

Both are what GitHub Pages serves — no server, no build step, no JS
framework beyond a tiny bit of vanilla JS for sorting/filtering. Re-running
this script (or the daily GitHub Action) overwrites them in place, so the
published pages always reflect the latest data.
"""

import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import html
import os

# =========================
# CONFIG
# =========================

LEAGUE_NAME = "Fantasy Baseball League"     # <-- change to your league's name
TEAM_SCORES_FILE = "data/team_scores.csv"
ROSTER_FILE = "data/team_rosters_updated.csv"
OUTPUT_DIR = "docs"
INDEX_FILE = os.path.join(OUTPUT_DIR, "index.html")
PLAYERS_FILE = os.path.join(OUTPUT_DIR, "players.html")
DISPLAY_TZ = "America/New_York"             # timestamp shown on the page

# Stat columns update.py / team_scores.py attach to each player.
HITTER_STATS = [
    ("Hits", "H"), ("Doubles", "2B"), ("Triples", "3B"), ("HR", "HR"),
    ("BB", "BB"), ("Runs", "R"), ("RBI", "RBI"), ("SB", "SB"), ("HBP", "HBP"),
]
PITCHER_STATS = [
    ("IP", "IP"), ("ER", "ER"), ("Wins", "W"), ("Saves", "SV"),
    ("K", "K"), ("QS", "QS"), ("Holds", "HLD"),
]

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


def player_display_name(row) -> str:
    name = row.get("Full Name")
    if pd.isna(name) or not str(name).strip():
        name = row.get("Player")
    return str(name)


def is_injured(row) -> bool:
    return str(row.get("Injured", "")).strip().upper() == "Y"


# =========================
# SHARED NAV
# =========================

def build_nav(active: str) -> str:
    def link(href, label, key):
        cls = "active" if key == active else ""
        return f'<a href="{href}" class="{cls}">{label}</a>'

    return f"""
    <nav class="top-nav">
      {link('index.html', 'Standings', 'standings')}
      {link('players.html', 'Players', 'players')}
    </nav>"""


# =========================
# STANDINGS PAGE FRAGMENTS
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
            injured = is_injured(r)
            css_class = "roster-row injured" if injured else "roster-row"
            tag = '<span class="injury-tag">INJ</span>' if injured else ""
            row_html.append(f"""
            <tr class="{css_class}">
              <td class="pos">{esc(r.get('Position', ''))}</td>
              <td class="player">{esc(player_display_name(r))} {tag}</td>
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
# PLAYERS PAGE FRAGMENTS
# =========================

def dedupe_by_player(df: pd.DataFrame) -> pd.DataFrame:
    """A player can be drafted by more than one fantasy team, which means
    they'd appear once per team in team_rosters_updated.csv. Their stats and
    points are identical in every occurrence, so keep just one row per
    real player (by Player ID, falling back to Full Name if that's missing)."""
    if df.empty:
        return df

    key = df["Player ID"] if "Player ID" in df.columns else pd.Series(dtype=object)
    key = key.where(key.notna() & (key != 0), df["Full Name"]) if not key.empty else df["Full Name"]

    return df.assign(_dedupe_key=key).drop_duplicates(subset="_dedupe_key", keep="first").drop(columns="_dedupe_key")


def build_player_stat_table(df: pd.DataFrame, stat_cols, table_id: str) -> str:
    """df must already be filtered to one player type (hitters or pitchers)
    and deduped to one row per real player."""
    df = df.sort_values("Total Score", ascending=False)

    header_cells = ["<th data-sort=\"text\">Player</th>", "<th data-sort=\"text\">MLB Team</th>",
                     "<th data-sort=\"num\">PTS</th>"]
    header_cells += [f'<th data-sort="num">{label}</th>' for _, label in stat_cols]

    rows = []
    for _, r in df.iterrows():
        injured = is_injured(r)
        css_class = "player-row injured" if injured else "player-row"
        tag = '<span class="injury-tag">INJ</span>' if injured else ""
        mlb_team = str(r.get("MLB Team", "") or "").strip() or "—"

        cells = [
            f'<td class="player-cell" data-filter="{esc(player_display_name(r))} {esc(mlb_team)}">{esc(player_display_name(r))} {tag}</td>',
            f'<td>{esc(mlb_team)}</td>',
            f'<td class="score">{int(r["Total Score"])}</td>',
        ]
        for col, _ in stat_cols:
            val = r.get(col, 0)
            if col == "IP":
                # innings pitched displays as e.g. 182.1, not a plain float
                try:
                    val_display = f"{float(val):.1f}"
                except (TypeError, ValueError):
                    val_display = "0.0"
            else:
                try:
                    val_display = int(float(val))
                except (TypeError, ValueError):
                    val_display = 0
            cells.append(f'<td class="stat">{val_display}</td>')

        rows.append(f'<tr class="{css_class}">{"".join(cells)}</tr>')

    return f"""
    <table class="player-table" id="{table_id}">
      <thead><tr>{''.join(header_cells)}</tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def build_players_tables(roster: pd.DataFrame) -> str:
    roster = dedupe_by_player(roster)
    ptype = roster.get("Type", pd.Series(dtype=str)).astype(str).str.lower()

    hitters = roster[ptype.isin(["hitter", "both"])]
    pitchers = roster[ptype.isin(["pitcher", "both"])]

    return f"""
    <section>
      <h2>Hitters</h2>
      {build_player_stat_table(hitters, HITTER_STATS, "hitters-table")}
    </section>

    <section>
      <h2>Pitchers</h2>
      {build_player_stat_table(pitchers, PITCHER_STATS, "pitchers-table")}
    </section>"""


# =========================
# SHARED CSS
# =========================

BASE_CSS = """
  :root {
    --navy: #303444;
    --navy-light: #454a60;
    --gold: #D5A451;
    --cream: #F6EFDF;
    --cream-row: #EDE2C4;
    --red: #D14B36;
    --text: #22242E;
    --white: #FFFFFF;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--cream);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    line-height: 1.5;
  }

  header {
    background: var(--navy);
    color: var(--white);
    padding: 2.5rem 1.5rem 1.25rem;
  }

  .header-inner {
    max-width: 960px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  h1 {
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    font-size: 2.1rem;
    margin: 0;
    letter-spacing: 0.01em;
  }

  .updated {
    color: var(--gold);
    font-size: 0.9rem;
    font-family: 'Inter', sans-serif;
  }

  .top-nav {
    max-width: 960px;
    margin: 0 auto;
    padding: 0.75rem 1.5rem 0;
    display: flex;
    gap: 1.5rem;
    border-top: 1px solid rgba(255,255,255,0.12);
  }

  .top-nav a {
    color: rgba(255,255,255,0.65);
    text-decoration: none;
    font-family: 'Oswald', sans-serif;
    font-weight: 500;
    font-size: 0.95rem;
    padding: 0.6rem 0.1rem 0.5rem;
    border-bottom: 2px solid transparent;
  }

  .top-nav a.active {
    color: var(--white);
    border-bottom-color: var(--gold);
  }

  .top-nav a:hover {
    color: var(--white);
  }

  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  main.narrow {
    max-width: 760px;
  }

  h2 {
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    font-size: 1.3rem;
    color: var(--navy);
    margin: 0 0 1rem;
    border-bottom: 3px solid var(--gold);
    padding-bottom: 0.4rem;
  }

  section + section {
    margin-top: 2.5rem;
  }

  footer {
    text-align: center;
    color: #8a8d99;
    font-size: 0.8rem;
    padding: 1.5rem;
  }

  /* ---- Standings page ---- */

  ul.standings {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    overflow: hidden;
  }

  .standing-row {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.7rem 1rem;
    background: var(--white);
  }

  .standing-row:nth-child(odd) {
    background: var(--cream-row);
  }

  .rank {
    font-family: 'Oswald', sans-serif;
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--gold);
    width: 1.6rem;
    text-align: right;
  }

  .team-name {
    flex: 1;
    font-weight: 600;
    color: var(--navy);
    text-decoration: none;
  }

  .team-name:hover {
    text-decoration: underline;
  }

  .pts {
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .pts-label {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 0.8rem;
    color: #6b6e7a;
  }

  .team-card {
    background: var(--white);
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    margin-bottom: 0.75rem;
    overflow: hidden;
  }

  .team-card summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1.1rem;
    cursor: pointer;
    background: var(--navy);
    color: var(--white);
    font-family: 'Oswald', sans-serif;
    list-style: none;
  }

  .team-card summary::-webkit-details-marker {
    display: none;
  }

  .summary-team {
    font-weight: 600;
    font-size: 1.05rem;
  }

  .summary-total {
    color: var(--gold);
    font-weight: 600;
  }

  .roster-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }

  .roster-table th {
    text-align: left;
    background: var(--cream-row);
    color: var(--navy);
    padding: 0.5rem 1rem;
    font-weight: 600;
  }

  .roster-table td {
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--cream-row);
  }

  .roster-row.injured td,
  .player-row.injured td {
    background: var(--red);
    color: var(--white);
  }

  .injury-tag {
    display: inline-block;
    margin-left: 0.4rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    background: rgba(255,255,255,0.25);
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
  }

  .score {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  /* ---- Players page ---- */

  .filter-bar {
    margin-bottom: 1rem;
  }

  .filter-bar input {
    width: 100%;
    max-width: 320px;
    padding: 0.55rem 0.8rem;
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    background: var(--white);
    color: var(--text);
  }

  .filter-bar input:focus {
    outline: 2px solid var(--gold);
    outline-offset: 1px;
  }

  .player-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    background: var(--white);
    border: 1px solid var(--cream-row);
    border-radius: 6px;
    overflow: hidden;
  }

  .player-table th {
    text-align: left;
    background: var(--navy);
    color: var(--white);
    padding: 0.55rem 0.7rem;
    font-weight: 600;
    font-family: 'Oswald', sans-serif;
    font-size: 0.8rem;
    letter-spacing: 0.01em;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }

  .player-table th:hover {
    background: var(--navy-light);
  }

  .player-table th.sorted-asc::after {
    content: " \\25B2";
    color: var(--gold);
  }

  .player-table th.sorted-desc::after {
    content: " \\25BC";
    color: var(--gold);
  }

  .player-table td {
    padding: 0.5rem 0.7rem;
    border-top: 1px solid var(--cream-row);
    white-space: nowrap;
  }

  .player-table tbody tr:nth-child(odd) {
    background: var(--cream-row);
  }

  .player-table th[data-sort="num"] {
    text-align: center;
  }

  .player-table td.stat,
  .player-table td.score {
    font-variant-numeric: tabular-nums;
    text-align: center;
  }

  @media (max-width: 480px) {
    h1 { font-size: 1.6rem; }
    .roster-table { font-size: 0.85rem; }
    .player-table { font-size: 0.78rem; }
  }
"""

# Vanilla JS: click-to-sort table headers + live name/team filter.
# No frameworks, no storage — everything lives in the DOM for the session.
PLAYERS_JS = """
function sortPlayerTable(table, colIndex, type) {
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const th = table.tHead.rows[0].cells[colIndex];
  const currentlyAsc = th.classList.contains('sorted-asc');
  const asc = !currentlyAsc;

  rows.sort((a, b) => {
    let x = a.cells[colIndex].innerText.trim();
    let y = b.cells[colIndex].innerText.trim();
    if (type === 'num') {
      x = parseFloat(x) || 0;
      y = parseFloat(y) || 0;
      return asc ? x - y : y - x;
    }
    return asc ? x.localeCompare(y) : y.localeCompare(x);
  });

  rows.forEach(r => tbody.appendChild(r));

  Array.from(table.tHead.rows[0].cells).forEach(c => {
    c.classList.remove('sorted-asc', 'sorted-desc');
  });
  th.classList.add(asc ? 'sorted-asc' : 'sorted-desc');
}

document.querySelectorAll('.player-table').forEach(table => {
  Array.from(table.tHead.rows[0].cells).forEach((th, i) => {
    th.addEventListener('click', () => sortPlayerTable(table, i, th.dataset.sort));
  });
});

const filterInput = document.getElementById('player-filter');
if (filterInput) {
  filterInput.addEventListener('input', () => {
    const q = filterInput.value.trim().toLowerCase();
    document.querySelectorAll('.player-table tbody tr').forEach(row => {
      const cell = row.querySelector('.player-cell');
      const haystack = (cell ? cell.dataset.filter : row.innerText).toLowerCase();
      row.style.display = haystack.includes(q) ? '' : 'none';
    });
  });
}
"""

# =========================
# PAGE TEMPLATES
# =========================

HEAD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{league_name} — {page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{base_css}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <h1>{league_name}</h1>
    <span class="updated">Updated {updated}</span>
  </div>
  {nav}
</header>
"""

INDEX_MAIN = """
<main class="narrow">
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

PLAYERS_MAIN = """
<main>
  <div class="filter-bar">
    <input id="player-filter" type="text" placeholder="Search player or team...">
  </div>

  {players_tables}
</main>

<footer>
  Refreshes automatically every day. Click a column header to sort.
</footer>

<script>
{players_js}
</script>

</body>
</html>
"""


def render_head(page_title: str, active_nav: str, updated: str) -> str:
    return HEAD_TEMPLATE.format(
        league_name=esc(LEAGUE_NAME),
        page_title=page_title,
        base_css=BASE_CSS,
        updated=esc(updated),
        nav=build_nav(active_nav),
    )


def build_index_page(scores: pd.DataFrame, roster: pd.DataFrame, updated: str) -> str:
    head = render_head("Standings", "standings", updated)
    body = INDEX_MAIN.format(
        standings_rows=build_standings_rows(scores),
        roster_sections=build_roster_sections(roster),
    )
    return head + body


def build_players_page(roster: pd.DataFrame, updated: str) -> str:
    head = render_head("Players", "players", updated)
    body = PLAYERS_MAIN.format(
        players_tables=build_players_tables(roster),
        players_js=PLAYERS_JS,
    )
    return head + body


def main():
    scores, roster = load_data()
    now = datetime.now(timezone.utc).astimezone(ZoneInfo(DISPLAY_TZ))
    updated = now.strftime("%B %d, %Y at %-I:%M %p %Z")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(build_index_page(scores, roster, updated))

    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        f.write(build_players_page(roster, updated))

    print(f"Dashboard generated → {INDEX_FILE}")
    print(f"Players page generated → {PLAYERS_FILE}")


if __name__ == "__main__":
    main()
