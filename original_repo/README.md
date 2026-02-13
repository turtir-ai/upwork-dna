# Upwork DNA Scraper

Upwork DNA Scraper is a Chrome extension that collects Jobs, Talent, and Project
Catalog data from Upwork search pages for keyword-based analysis. It runs inside
your browser session, so it uses your logged-in account and exports the data
locally as JSON or CSV.

## What it does
- Searches Upwork by keyword for Jobs, Talent, and Projects.
- Scrapes list results and then scrapes detail pages for each result.
- Exports per-target CSV files and a full JSON run snapshot.

## Targets and data
Jobs
- List fields: title, job type, budget, skills, posted time, client rating, location.
- Detail fields: description, experience level, duration, connects, questions, client
  stats, and more (stored as `detail_*` columns).

Talent
- List fields: name, title, hourly rate, location, skills.
- Detail fields: overview, hourly rate, job success, total earned, hours, languages,
  badges, and more.

Projects (Project Catalog)
- List fields: title, seller name, price, delivery time, rating, reviews.
- Detail fields: description, price, delivery, category, packages, skills, seller
  profile, and more.

## How it works
1. List phase: visits search pages and collects summary cards.
2. Detail phase: iterates each result and enriches it with `detail_*` fields.
   - Jobs/Talent: opens the detail view or page.
   - Projects: fetches each project detail page in the background to avoid losing
     the list scroll state.

For projects, each "Load More" click counts as one page. If `Max pages` is 0, it
keeps clicking until the button disappears, with a safety cap to prevent infinite
loops.

## Install
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click "Load unpacked" and select the `extension/` folder.

## Usage
1. Open Upwork, log in, and solve any challenge pages.
2. Open the extension popup.
3. Enter a keyword and select one or more targets.
4. Set `Max pages` (0 = all).
5. Click Start. Watch status updates for page and detail progress.
6. Use Export JSON or Export CSV to download results.
7. Use Clear to remove stored runs.

## Output files
- JSON: `upwork_scrape_<keyword>_<runId>.json` (full run state).
- CSV: one file per target: `upwork_<target>_<keyword>_<runId>.csv`.

CSV rows include base fields plus `detail_*` fields; `detail_status` and
`detail_error` show whether a detail scrape succeeded.

## Notes and limits
- The extension relies on your logged-in Upwork session and may pause if a
  challenge page appears.
- Upwork may change their UI; selectors can break and require updates.
- Use responsibly and respect Upwork's terms and rate limits.

## Privacy
All data is stored locally in Chrome storage and exported from your browser.
Nothing is sent to a server.
