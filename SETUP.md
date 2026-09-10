# Getting the daily refresh + dashboard live

## 1. Add the font/cover assets (optional, only for the PDF)
Drop `Nexa-Heavy.ttf` and `Lobster-Regular.ttf` into `assets/fonts/`, and
`Cover_Page_2026.png` into `assets/`. These are only needed if you plan to
run `run_all.py` locally to generate a PDF — the automated daily dashboard
doesn't use them.

## 2. Set your league name
Open `scripts/build_dashboard.py` and set `LEAGUE_NAME` at the top to your
actual league's name.

## 3. Create the GitHub repo
1. Go to https://github.com/new
2. Name it something like `fantasy-league` (Public is fine — the data here
   is just player stats and team names, and Public repos get GitHub Actions
   + Pages entirely free with no minute limits).
3. Don't add a README/gitignore — you'll push this folder as-is.

## 4. Push the project
From inside this folder on your own computer:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## 5. Turn on GitHub Pages
1. In the repo, go to **Settings → Pages**.
2. Under "Build and deployment", set **Source** to "Deploy from a branch".
3. Set **Branch** to `main` and the folder to `/docs`. Save.
4. GitHub gives you a URL like
   `https://<your-username>.github.io/<repo-name>/` — that's the link you
   share with the league. It updates automatically every time
   `docs/index.html` changes.

## 6. Let the daily workflow run
`.github/workflows/daily-refresh.yml` runs every day at 12:00 UTC (8am ET).
No extra setup needed — Actions is on by default for a new repo.
- Change the schedule by editing the `cron` line.
- Trigger a run manually any time: **Actions** tab → "Daily league refresh"
  → **Run workflow**.
- Check a run's logs in that same tab if a day's refresh doesn't show up.

## 7. Send the link
Once step 5's Pages URL is live and step 6 has run at least once
successfully, share that URL with the league (group chat, email, wherever).
Nothing else to send — it refreshes itself from here on.

## Notes
- No secrets or API keys are needed — both Google Sheets links are public
  "publish to web" CSVs, and the MLB Stats API is open.
- `legacy/` holds the pre-`player_map.json` scripts, kept only for
  reference — nothing in the active pipeline uses them.
