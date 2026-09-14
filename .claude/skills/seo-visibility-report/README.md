# SEO Visibility & Opportunity Report Skill

Generates a client-ready PDF SEO report using live DataForSEO data. One command per
client per month. Report sections are conditional — only what you enable is included.

---

## Setup (once per machine)

### 1. Install Python dependency

```bash
pip install reportlab
```

### 2. Connect the DataForSEO MCP

The skill supports two DataForSEO MCP connectors and works with either or both:

| Connector | How it works | Preferred |
|-----------|-------------|----------|
| **V3** | Single `api_request` tool — direct HTTP calls to the DataForSEO REST API | ✅ Yes |
| **V1** | Individual named tools per endpoint (`backlinks_summary`, `serp_organic_live_advanced`, etc.) | Fallback |

If both connectors are connected, the skill automatically uses V3. If only one is available,
it uses whichever is present. If neither is connected, the skill will stop and ask you to
connect one before proceeding.

If you see a 401 error, re-authenticate the MCP connector.

### 3. Open a project folder in Claude Code

The skill reads and writes all files (configs, data JSON, PDF) relative to the current
Claude Code project folder. Open a dedicated folder before running:

```
your-agency/
  bloom-cosmetics.com_config.json       ← created once per client
  bloom-cosmetics.com_data_2026-05.json ← raw API data, kept for audit trail
  bloom-cosmetics.com_SEO_2026-05.pdf   ← final report
```

---

## Running the skill

Trigger it by typing in Claude Code:

```
Generate the SEO report for bloom-cosmetics.com
Run the monthly SEO report
Create the SEO report for May 2026
```

**First run for a client (no config file):** the skill walks you through setup —
report purpose, modules to include, tracked keywords, competitors, pages to audit,
location, and reporting dates. Answers are saved to `[domain]_config.json`.

**Every subsequent run:** config is loaded automatically, dates are suggested for the
new period, a summary of what will be fetched (with estimated API call count) is shown,
and you confirm before any calls are made.

**Updating config:** tell Claude "update the config for bloom-cosmetics.com" and it will
walk you through the relevant fields.

---

## Report Sections

All sections are optional and toggled during setup. Sections included depend on the
report purpose (existing client vs warm lead) and your selection.

| # | Section | Key Content |
|---|---------|-------------|
| Cover | — | Client name, domain, reporting period |
| 1 | Executive Summary | Visibility Index, estimated traffic, MoM KPIs, narrative |
| 2 | Keyword Rankings | Tracked keywords with positions, delta, SERP features, volume |
| 3 | Competitor Snapshot | Client vs selected competitors — traffic, avg position |
| 4 | Backlink Profile | Domain Rating (0-100), new/lost referring domains, 6-month trend |
| 5 | Technical Health | Lighthouse scores (mobile, lab), on-page issues per audited page |
| 6 | Local SEO | GBP KPIs, local pack rankings, pack competitors — per location |
| 7 | AI / LLM Visibility | Brand mentions across AI models |
| 8 | Next Actions | Up to 5 data-grounded recommendations with effort/impact/owner |

**Competitor Snapshot** only runs if competitors are defined in the client config.
**Local SEO** supports multiple locations — each gets its own block with GBP data
and local pack rankings.

---

## API Request Usage

A request estimate is shown before any calls are made. Typical breakdown:

| Section | Requests |
|---------|----------|
| Executive Summary | 2 (current + previous period overview) |
| Keyword Rankings | N keywords (SERP live) + 1 bulk volume + up to 10 historical |
| Competitor Snapshot | 1 per competitor (max 3) |
| Backlink Profile | 4 (summary + timeline + new domains + lost domains) |
| Technical Health | 2 per page (Lighthouse + on-page) |
| Local SEO | 1 GBP lookup + 1 per local keyword, per location |

For a typical setup (15 keywords, 3 competitors, 4 pages, 1 location): **~45-55 requests**.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: reportlab` | Run `pip install reportlab` |
| DataForSEO 401 | Re-connect / re-authenticate the DataForSEO MCP |
| Domain returns 0 keywords | Check domain spelling and location/language in config |
| Competitors not showing | Competitors must be set in config — not auto-discovered |
| PDF is blank or crashes | Check that `data_*.json` was written; re-run the skill |

---

## Files Written per Run

| File | Purpose |
|------|---------|
| `[domain]_config.json` | Client settings — keywords, competitors, pages, modules, dates |
| `[domain]_data_[YYYY-MM].json` | Raw DataForSEO data (keep for audit trail) |
| `[domain]_SEO_[YYYY-MM].pdf` | Final client-ready report |
