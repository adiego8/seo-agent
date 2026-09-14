---
name: seo-visibility-report
description: >
  Generates an on-demand SEO Visibility & Opportunity report for agency clients.
  Use this skill whenever a user wants to create, generate, produce, or build an SEO report,
  visibility report, opportunity report, SEO assessment, SEO audit report, or SEO PDF.
  Also triggers on: "run the report for [client]", "generate report for [domain]",
  "create the SEO report", "build an SEO visibility report", "make a client SEO report",
  "SEO opportunity assessment for [domain]", "warm lead report for [domain]".
  Collects or loads config, pulls live data from DataForSEO MCP, and produces a neutral
  (unbranded) PDF with conditional sections based on the report's purpose and selected modules.
---

# SEO Visibility & Opportunity Report Skill

## What This Skill Does

Turns manual SEO reporting into a single-run workflow that produces a professional,
client-ready PDF. Works for both existing-client monthly/quarterly reviews and warm-lead
conversion reports.

**Output file:** `[client-domain]_SEO_[YYYY-MM].pdf` saved to the project folder.

---

## Interaction Rules (apply to every question in this skill)

- Ask questions ONE AT A TIME. Do not combine questions. Wait for reply before next.
- For ALL questions with a fixed set of options: use the `AskUserQuestion` tool to render
  an interactive select or multiselect UI. Do NOT output a numbered text list for these.
- Optional text fields: ask in plain text, note "(optional -- press Enter or type '-' to skip)".
  Store null if skipped.
- For open-ended lists (keywords, competitors, pages): ask in plain text. Never pre-fill.
- For yes/no: use AskUserQuestion single-select with "Yes" / "No" options.

---

## DataForSEO Connector Detection

This skill supports two DataForSEO MCP connectors. At the start of every run, detect
which is available and set `DFS_MODE` accordingly. Never mix modes within one run.

**Detection rule:**
- If both connectors are present → use **V3** (preferred).
- If only V3 present → use V3.
- If only V1 present → use V1.
- If neither present → stop and tell the user to connect the DataForSEO MCP.

**V1** — individual named tools per endpoint (e.g. `backlinks_summary`, `serp_organic_live_advanced`).
Check availability by attempting to list tools; V1 tools have distinct snake_case names matching endpoint names.

**V3** — single generic tool `api_request(method, path, data)`.
Check availability by verifying `api_request` tool is present.

All API calls throughout Steps 5–9 list both the V1 tool name and the V3 path inline
in the format `V1: tool_name / V3: POST /v3/path`. Use whichever matches `DFS_MODE`.
Appendix C has the full mapping table for reference.

---

## Step 1 -- Configurator

Run Q1-Q6 on EVERY new config setup (or when the user asks to reconfigure).
If a client config already exists and has all six answers, skip to Step 2 and show
a one-line summary: "Using saved config: [purpose] / [reader] / [modules]."

Ask each question one at a time using AskUserQuestion tool (interactive UI).
Save all answers to the client config under a `report_settings` block.

---

**Q1 -- Report purpose:**

Use AskUserQuestion, single-select, header "Report purpose":
- Question: "What is this report for?"
- Option 1: label "Existing-client report"
- Option 2: label "Warm-lead conversion"

Save as `report_settings.purpose`: "existing_client" or "warm_lead".

---

**Q2 -- Who will read it?**

Use AskUserQuestion, single-select, header "Primary reader":
- Question: "Who is the primary reader of this report?"
- Option 1: label "Business owner / exec"
- Option 2: label "Marketing manager / in-house team"

Save as `report_settings.reader`: "exec" or "manager".

---

**Q3 -- Client footprint:**

Use AskUserQuestion, single-select, header "Geographic footprint":
- Question: "What is the client's geographic footprint?"
- Option 1: label "Local",
            description "Targets customers in a specific city or region"
- Option 2: label "National / international",
            description "Country-level or global reach"
- Option 3: label "Both",
            description "Local presence AND national/international reach"

Save as `report_settings.footprint`: "local", "national", or "both".
If local or both: the Local SEO module is automatically included in defaults.
Collect city/region location(s) in Step 2 if footprint is local or both.

---

**Q4 -- Keyword source:**

Use AskUserQuestion, single-select, header "Keyword source":
- Question: "How should we define the keyword set for this report?"
- Option 1: label "Client-provided list",
            description "You supply the keywords -- recommended for existing clients"
- Option 2: label "Auto-discover from domain",
            description "We find what the domain already ranks for via DataForSEO"
- Option 3: label "Hybrid",
            description "Start with auto-discovered, then you add or remove terms"

Save as `report_settings.keyword_source`: "client_provided", "auto_discover", or "hybrid".
Default: "client_provided" for existing clients; "hybrid" for warm leads.

---

**Q5 -- Which modules to include?**

Pre-select defaults based on Q1 answer before showing:
  existing_client: keyword_rankings, backlinks, tech_health, next_actions
  warm_lead:       keyword_rankings, competitor_snapshot, backlinks, tech_health, next_actions

Module defaults by purpose:
  existing_client: keyword_rankings, backlinks, tech_health, next_actions
  warm_lead:       keyword_rankings, competitor_snapshot, backlinks, tech_health, next_actions
  + local_seo automatically added to recommended set if Q3 footprint = local or both

Before showing the question, determine which modules are in the recommended set based on
Q1 and Q3 answers. Then build each option's description dynamically:
- If the module IS in the recommended set: prepend "[Recommended] " to the description.
- If the module is NOT in the recommended set: no tag, description only.

Use AskUserQuestion, multiSelect: true, header "Report modules":
- Question: "Which modules should this report include?"
- Option 1: label "Keyword Rankings",
            description "[Recommended] or "" + "Position distribution, intent groups, opportunity keywords"
- Option 2: label "Local / GBP",
            description "[Recommended] or "" + "GBP snapshot + local pack rankings"
- Option 3: label "Competitor Snapshot",
            description "[Recommended] or "" + "Light overview of top competitor visibility"
- Option 4: label "Backlinks",
            description "[Recommended] or "" + "DR, referring domains, new/lost domain tables, 6-month trend"

Follow up with a second AskUserQuestion, multiSelect: true, header "More modules":
- Question: "Any additional modules?"
- Option 1: label "Technical Health",
            description "[Recommended] or "" + "Lighthouse scores, Core Web Vitals, on-page issues"
- Option 2: label "AI / LLM Visibility",
            description "[Recommended] or "" + "GEO readiness -- mentions in ChatGPT, Gemini, Perplexity"
- Option 3: label "Next Actions",
            description "[Recommended] or "" + "5 data-grounded recommendations with effort/impact"
- Option 4: label "None -- that's all",
            description "Skip, I've selected everything I need"

Merge both selections. Save final list as `report_settings.enabled_modules` (array).
Module keys: keyword_rankings, local_seo, competitor_snapshot, backlinks,
             tech_health, ai_llm_visibility, next_actions.

---

**Q6 -- Reporting period:**

Use AskUserQuestion, single-select, header "Reporting period":
- Question: "What period should this report cover?"
- Option 1: label "Last full month",
            description "Auto-calculates: [prev calendar month] vs [month before]"
- Option 2: label "Last quarter",
            description "Auto-calculates: [prev calendar quarter] vs [quarter before]"
- Option 3: label "Current snapshot",
            description "No comparison period -- single point in time (last 30 days)"
- Option 4: label "Custom dates",
            description "I'll enter the exact date ranges manually"

If 1: auto-calculate previous full calendar month and the one before. Show result:
  "Periods set: [Month YYYY] vs [Prev Month YYYY]. Confirm?"
  Use AskUserQuestion single-select "Yes, looks good" / "Change dates".
If 2: auto-calculate previous full calendar quarter and the one before. Same confirmation.
If 3: use today minus 30 days as date_from, today as date_to; set date_prev_from/to = null.
If 4: ask in plain text: "Enter current period: YYYY-MM-DD to YYYY-MM-DD"
      then: "Enter previous period for comparison: YYYY-MM-DD to YYYY-MM-DD (or '-' to skip)"

Save as `report_settings.period_mode`: "month", "quarter", "snapshot", or "custom".
Save four date fields + period labels to client config (see Appendix A).

---

## Step 2 -- Client Setup

Check for `[client-domain]_config.json` in the current project folder.
If not known yet: ask "Which client domain should I run the report for?"

**If config found:** load it, show a one-line summary, proceed to Step 3.

**If not found:** ask the following ONE AT A TIME:

1. Plain text: "Client name (e.g. 'Bloom Cosmetics'):"
2. Plain text: "Client domain -- root domain only, no www or https (e.g. 'bloom-cosmetics.com'):"

**Location setup:**
3. Plain text: "Location (e.g. 'United Kingdom', 'New York', 'Ukraine'):"
   Call `serp_locations` with the input. Take top 3 results and present via AskUserQuestion,
   single-select, header "Select location":
   - Question: "Which location matches your client?"
   - Option 1: label "[name 1]", description "[country 1] -- code [code 1]"
   - Option 2: label "[name 2]", description "[country 2] -- code [code 2]"
   - Option 3: label "[name 3]", description "[country 3] -- code [code 3]"
   - Option 4: label "None of these", description "I'll type a different location"
   If "None of these": ask plain text again and repeat.
   Save `location_code` and `location_name`.

   If Q3 = local or both:
   Plain text: "How many locations does this client have? (enter a number)"
   Then repeat the following for each location (i = 1 to N):
     Plain text: "Location [i] -- city or region (e.g. 'London', 'Manchester'):"
     Call `serp_locations` with the input. Present top 3 via AskUserQuestion,
     single-select, header "Select location [i]":
     - Question: "Which location matches location [i]?"
     - Option 1: label "[name 1]", description "[country 1] -- code [code 1]"
     - Option 2: label "[name 2]", description "[country 2] -- code [code 2]"
     - Option 3: label "[name 3]", description "[country 3] -- code [code 3]"
     - Option 4: label "None of these", description "I'll type a different location"
     If "None of these": ask plain text again and repeat location picker.
     Append {city_location_code, city_location_name} to `locations` array.
   Save `locations` as array of {city_location_code, city_location_name}.

4. Plain text: "Language (e.g. 'English', 'Ukrainian', 'German'):"
   Match against language_name in the DataForSEO locations list.
   Confirm via AskUserQuestion, single-select, header "Confirm language":
   - Question: "Language matched: [name] (code: [code]). Is this correct?"
   - Option 1: label "Yes, that's correct"
   - Option 2: label "No, let me retype"
   Save `language_code` and `language_name`.

**Keyword setup (driven by Q4):**

If keyword_source = "client_provided" or "hybrid":
5. "Paste your target keywords, one per line or comma-separated (recommended: up to 100 for
   optimal report quality and API cost; more is fine but will increase processing time):"
   After receiving: run keyword validation (see below).

If keyword_source = "auto_discover" or "hybrid":
   Call `dataforseo_labs_google_ranked_keywords` for the domain (limit 500).
   For "auto_discover": present the top 20 by volume for confirmation, note total found.
   For "hybrid": merge discovered list with client-provided list, deduplicate.

**Keyword validation (C2):**
After the keyword list is finalised, scan for likely junk terms:
- Flagging criteria: single characters, URLs, numbers only, competitor brand names
  not relevant to the client, very broad 1-word head terms (volume > 500k), duplicates.
- If any flagged terms found, present via AskUserQuestion, single-select, header "Keyword cleanup":
  - Question: "I flagged [N] keyword(s) as potentially off-topic or low-quality: [list].
    What should I do?"
  - Option 1: label "Remove all flagged terms",
              description "Drop the [N] flagged keywords from the list"
  - Option 2: label "Keep all flagged terms",
              description "Include them as-is, I know what I'm doing"
  - Option 3: label "I'll decide for each one",
              description "Review each flagged keyword one by one"
  If Option 3: for each flagged keyword, use AskUserQuestion single-select:
    "Keep '[keyword]'?" -- "Keep it" / "Remove it"
  Wait for all replies before saving the keyword list.

6. "Competitor domains -- root domains, comma-separated (recommended: up to 5; more is fine
   but each adds 1 extra API call)
   (optional -- press Enter or type '-' to skip):"

7. **Pages to audit for Technical Health:**

   Before showing the question, silently discover pages from the site:
   - Try fetching `https://[client_domain]/sitemap.xml` (check robots.txt first for sitemap path).
     If found: parse <loc> URLs, normalise to relative paths, sort by depth (shallowest first).
     Take top 4 (homepage always first).
   - If sitemap not found or empty: probe common paths with HEAD requests, keep HTTP 200 only:
     /, /about, /contact, /services, /shop, /blog, /pricing, /faq, /team
     Take top 4 that respond with 200.
   Store as `suggested_pages` (temporary, not saved to config yet).

   Use AskUserQuestion, single-select, header "Pages to audit":
   - Question: "How should we select pages for the Technical Health audit?"
   - Option 1: label "Use suggested pages",
               description "Found on site: [suggested_pages joined with ', ']"
   - Option 2: label "Enter manually",
               description "I'll type the paths I want audited"
   - Option 3: label "Scan full sitemap",
               description "Audit all pages from sitemap.xml -- may be 50-500+ calls, slow and costly"
   - Option 4: label "Homepage only",
               description "Quick audit of just /"

   **If Option 1 (suggested):**
   Ask plain text: "Any additional paths to add? (comma-separated, or '-' to skip)"
   Save `suggested_pages` + any additions as `top_pages_for_tech_audit`.

   **If Option 2 (manual):**
   Plain text: "Enter page paths, comma-separated (e.g. '/,/shop,/about', max 20):"
   Save as `top_pages_for_tech_audit`.

   **If Option 3 (scan full sitemap):**
   First show a warning via AskUserQuestion, single-select, header "Confirm sitemap scan":
   - Question: "Sitemap scan will audit every page individually -- this can mean hundreds of
     API calls and take several minutes. Continue?"
   - Option 1: label "Yes -- scan sitemap",  description "Proceed, I understand the cost"
   - Option 2: label "No -- enter manually", description "I'll type the paths instead"

   If confirmed:
   - Fetch `https://[client_domain]/sitemap.xml` (or path from robots.txt if different).
   - Parse all <loc> URLs, normalise to relative paths. No page limit.
   - If config already exists and has `sitemap_pages_audited`:
     - Compute NEW = all sitemap paths NOT in `sitemap_pages_audited`.
     - If NEW is empty:
       "No new pages found since last scan ([N] pages previously audited). Using existing list."
       Set `top_pages_for_tech_audit` = `sitemap_pages_audited`.
     - If NEW is not empty:
       Ask via AskUserQuestion, single-select, header "New pages found":
       - Question: "Found [N_new] new pages since last scan ([N_prev] already audited).
         What should we audit?"
       - Option 1: label "New pages only ([N_new])",
                   description "Audit only pages added since last scan"
       - Option 2: label "Full site ([N_total] pages)",
                   description "Re-audit everything including previously scanned pages"
       - Option 3: label "Enter manually",
                   description "I'll decide which paths to audit"
       Set `top_pages_for_tech_audit` accordingly.
       Append NEW to `sitemap_pages_audited` and save to config.
   - If config is new (no `sitemap_pages_audited`):
     - Parse full sitemap, get all paths.
     - Ask via AskUserQuestion, single-select, header "Sitemap scanned":
       - Question: "Found [N] pages in sitemap. Audit all of them?
         (~[N] API calls, may take [N/10] min)"
       - Option 1: label "Yes -- audit all [N] pages",
                   description "Full coverage, higher cost"
       - Option 2: label "No -- enter manually",
                   description "I'll choose which pages to include"
     - If Yes: set `top_pages_for_tech_audit` = all paths.
       Save full list as `sitemap_pages_audited` in config.
     - If No: fall through to manual entry.

   **If Option 4 (homepage only):**
   Set `top_pages_for_tech_audit` = ["/"].

8. "Report output folder -- leave blank for current project folder
   (optional -- reply '-' to skip):"

Save as `[client-domain]_config.json` using schema in Appendix A.

---

## Step 3 -- Validate

| Check | Rule |
|-------|------|
| Domain format | No https://, no trailing slash, no spaces. |
| Dates | date_from < date_to; prev ends before current starts (unless snapshot mode). |
| Keywords | At least 1. Over 100: show "You've entered [N] keywords -- this will increase API usage and processing time. Continue?" via AskUserQuestion Yes/No. |
| Competitors | Over 5: show "You've entered [N] competitors -- each adds ~1 API call. Continue?" via AskUserQuestion Yes/No. |
| reportlab | Run `python -c "import reportlab"`. Fail: run `pip install reportlab` once. |

Stop and describe exactly what needs fixing if any check fails.

---

## Step 4 -- Confirm Before Running

Display the full config and expected API request count. Wait for explicit confirmation.

```
------------------------------------------------------
REPORT CONFIGURATION
------------------------------------------------------
Domain:    [client_domain]
Client:    [client_name]
Purpose:   [purpose]          Reader: [reader]
Footprint: [footprint]        Period: [period_mode]
Period:    [period_current] ([date_from] - [date_to])
Compare:   [period_prev] ([date_prev_from] - [date_prev_to])

Keywords:  [N] terms          Source: [keyword_source]
Competitors: [list or none]
Pages to audit: [list or none]

Modules:   [enabled_modules list]

EXPECTED API REQUESTS
  Executive Summary:   2
  Keyword Rankings:    [N+2] (ranked keywords + volumes + SERP live)
  Local SEO:           [2 if enabled, else -]
  Competitor Snapshot: [M+1 if enabled, else -]
  Backlinks:           4
  Technical Health:    [2xP if enabled, else -]
  AI/LLM Visibility:  [2 if enabled, else -]
  ---------------------
  Total:               ~[sum] requests

OUTPUT
  PDF:  [output_path]
  Data: [client_domain]_data_[YYYY-MM].json
------------------------------------------------------
```

After displaying the config summary, use AskUserQuestion, single-select, header "Confirm":
- Question: "Ready to start fetching data?"
- Option 1: label "Yes -- start now",     description "Proceed with the above configuration"
- Option 2: label "No -- edit config",    description "Go back and change something"

Do not make any API calls until the user selects Option 1.
If Option 2: ask plain text "What would you like to change?", update config, re-display summary.

---

## Step 5 -- Fetch Data

Work through enabled modules in order. After each module: print a short status line.
If a call returns empty or errors: set that section's data to null and continue.
Never abort the whole run for one missing section.

For each section: extract ONLY the fields listed below.

### Framing Presets

Apply framing based on `report_settings.purpose`:

existing_client:
  cover_title: "SEO Performance Review"
  s1_header:   "Executive Summary"
  s2_header:   "Keyword Rankings"
  s6_header:   "What We're Doing Next"
  s6_framing:  "Progress on agreed targets + next sprint"

warm_lead:
  cover_title: "SEO Opportunity Assessment"
  s1_header:   "Visibility Overview"
  s2_header:   "Ranking Opportunities"
  s6_header:   "Gaps We'd Close"
  s6_framing:  "Where visibility is lost and what fixing it is worth"

Store the active framing preset in the config as `framing` so build_report.py can use it.

---

### 5.1 -- Executive TL;DR + Summary

Always included (not toggleable).

**Call 1 -- Current period:**
V1: `dataforseo_labs_google_domain_rank_overview` / V3: `POST /v3/dataforseo_labs/google/domain_rank_overview/live`
```json
{ "target": "[client_domain]", "location_code": [loc], "language_code": "[lang]" }
```
Extract into `s1.current_period`:
etv, keywords_count (V1) / count (V3 — map to keywords_count), pos_1, pos_2_3, pos_4_10, pos_11_20, pos_21_30, pos_31_100
Compute: `pos_31_100` = sum of pos_31_40 through pos_91_100.
Compute: `vi` using formula:
  VI = (pos_1*1.0 + pos_2_3*0.85 + pos_4_10*0.5 + pos_11_20*0.2 + pos_21_30*0.05)
       / max(keywords_count, 1) * 100

**Call 2 -- Previous period (skip if period_mode = snapshot):**
V1: `dataforseo_labs_google_historical_rank_overview` / V3: `POST /v3/dataforseo_labs/google/historical_rank_overview/live` — with date_prev_from / date_prev_to.
Same fields into `s1.previous_period`.

Write `s1.narrative`: 3-5 sentences. Be specific -- mention keyword gains, risks, what
drove traffic changes. Tone from framing preset (progress vs gaps).
Write `s1.insight`: one-line takeaway.
Write `s1.tldr`: top 3 actions (brief bullet points for the TL;DR page).

---

### 5.2 -- Keyword Rankings (module: keyword_rankings)

**Call 3 -- Ranked keywords:**
V1: `dataforseo_labs_google_ranked_keywords` / V3: `POST /v3/dataforseo_labs/google/ranked_keywords/live`
```json
{ "target": "[client_domain]", "location_code": [loc], "language_code": "[lang]", "limit": 500 }
```

**Call 4 -- Search volumes (bulk):**
V1: `kw_data_google_ads_search_volume` / V3: `POST /v3/keywords_data/google_ads/search_volume/live` — with tracked_keywords list.

**Call 5 -- Previous period positions (top 10 by volume):**
V1: `dataforseo_labs_google_historical_serps` / V3: `POST /v3/dataforseo_labs/google/historical_serps/live` — for the top 10 tracked terms.

Build `s2.keywords` -- one entry per tracked keyword:
  keyword, volume, pos_current, pos_previous, url, serp_features, status, intent_group

**Status rules:** WIN (improved >=3 pos AND current <=20) / RISK (dropped >=3) /
WATCH (dropped 1-2) / STABLE (changed 0-2 improvement) / NEW (no prev) / LOST (no current).

**Intent grouping (C3):**
Group each keyword into one of: informational, commercial, local, branded, navigational.
Heuristics:
- local: contains city/region name, "near me", "in [place]"
- informational: starts with how/what/why/guide/tips/best way
- commercial: contains buy/price/cost/cheap/best/review/vs/compare
- branded: contains client_domain root or client_name
- navigational: everything else
Store as `intent_group` field. Build `s2.keyword_groups` dict keyed by intent_group.

**Opportunity block (C4):**
Build `s2.opportunities`: keywords where pos_current is null or > 20.
For each: estimate monthly traffic at position 5 = volume * 0.065.
Store as `s2.opportunities` list with fields: keyword, volume, pos_current, potential_traffic.
Write `s2.insight`.

---

### 5.3 -- Local SEO (module: local_seo, conditional on Q3 = local/both)

Run the following for EACH location in `locations` array:

**Call 6 -- GBP presence (per location):**
V1: `business_data_business_listings_search` / V3: `POST /v3/business_data/google/my_business_info/live`
```json
{ "keyword": "[client_name]", "location_code": [city_location_code] }
```
Extract: business name, rating, review_count, address, is_claimed.

**Call 7 -- Local pack rankings + competitors (per location):**
V1: `serp_organic_live_advanced` / V3: `POST /v3/serp/google/organic/live/advanced` — for 3-5 city-modified keywords from the tracked list
(e.g. "[keyword] [city]" or keywords already containing city name).
```json
{ "keyword": "[kw]", "location_code": [city_location_code], "language_code": "[lang]", "depth": 20 }
```
For each SERP response:
- Find all items where `type == "local_pack"`.
- For the client domain: record `pack_position` (1/2/3 or null if not present) and `organic_position`.
- For each OTHER business in the local pack (up to 3 per keyword): extract
  `title` (business name), `domain`, `rating`, `rating_count`, `pack_position`.
- Deduplicate competitors across keywords -- keep the one with the most keyword appearances.

Build per-location object:
```json
{
  "location_name": "[city_location_name]",
  "city_location_code": [city_location_code],
  "gbp": { "name": "...", "rating": 4.7, "review_count": 312, "address": "...", "is_claimed": true },
  "local_pack_rankings": [{ "keyword": "...", "pack_position": 2, "organic_position": 4 }],
  "local_pack_competitors": [
    { "name": "...", "domain": "...", "avg_pack_position": 1.0,
      "avg_rating": 4.5, "total_reviews": 890, "keywords_in_pack": 3 }
  ]
}
```

Build `s_local.locations`: array of per-location objects (one per city).
Write `s_local.insight` -- summarise across all locations (e.g. strongest/weakest city).

---

### 5.4 -- Competitor Snapshot (module: competitor_snapshot, LIGHT only)

**Check config first:**
- If `config.competitors` is empty or absent → skip this section entirely. Set `s3_competitor_snapshot` to null and omit from the report.
- If `config.competitors` is a non-empty list → use those domains.
  For each: call `dataforseo_labs_google_domain_rank_overview` to get etv, avg_position, intersections.

**Call 8:**
V1: `dataforseo_labs_google_domain_rank_overview` / V3: `POST /v3/dataforseo_labs/google/domain_rank_overview/live` — one call per competitor domain.

Build `s3.client`: {etv, avg_position} -- taken from s1.current_period (etv) and
the domain_rank_overview result (avg_position). This is the client's own row shown at
the top of the comparison table.
Build `s3.competitors`: list of {domain, etv, intersections, avg_position}.
Note: this is a light snapshot. Do NOT compute full SOV/VI machinery.
Write `s3.insight`.

Note to include in report: "For a full competitive breakdown, see the Competitor Analysis report."

---

### 5.5 -- Backlink Profile (module: backlinks)

**Call 9:** V1: `backlinks_summary` / V3: `POST /v3/backlinks/summary/live`
Extract:
- V1: `rank`, `total_backlinks`, `referring_domains`, `dofollow`, `nofollow`
- V3: `rank`, `backlinks` (≠ `total_backlinks`), `referring_domains`, `referring_domains_nofollow` (no `dofollow`/`nofollow` fields)
IMPORTANT: The `rank` field is on a 0-1000 scale. Convert to Domain Rating (0-100) with:
  `dr = round(sin(rank / 636.62) * 100, 1)`
Display this converted value as "Domain Rating (DR)". Never show the raw rank value.

**Call 10:** V1: `backlinks_timeseries_new_lost_summary` / V3: `POST /v3/backlinks/timeseries_new_lost_summary/live`
```json
{ "target": "[domain]", "date_from": "[6 months before date_from]", "date_to": "[date_to]", "group_by": "month" }
```

From the timeseries response, derive `s4.previous` by taking the entry whose date falls
in the month **before** `date_from`. This gives consistent MoM comparison from API data
alone — no dependency on a previous run's data file.

Fields to extract for `s4.previous`: `new_referring_domains`, `lost_referring_domains`,
`new_backlinks`, `lost_backlinks`. Use cumulative totals from `backlinks_summary`
minus/plus the most recent month's delta to approximate `referring_domains` and
`total_backlinks` for the previous period.

If the timeseries has no entry for the previous month (e.g. first ever run with no
history), set `s4.previous` to null — delta columns will simply be omitted from the PDF.

**Call 11:** V1: `backlinks_referring_domains` / V3: `POST /v3/backlinks/referring_domains/live` — filtered by first_seen >= date_from (new domains).

**Call 12:** V1: `backlinks_referring_domains` / V3: `POST /v3/backlinks/referring_domains/live` — with is_lost = true and lost_date >= date_from.

Build `s4.current`, `s4.previous`, `s4.timeline`, `s4.new_domains`, `s4.lost_domains`.
Write `s4.insight`.

---

### 5.6 -- Technical Health (module: tech_health)

For each URL in `top_pages_for_tech_audit` (max 6), default to homepage if list is empty:

**Call 13-A:** V1: `on_page_lighthouse` / V3: `POST /v3/on_page/lighthouse/live/json`
```json
{ "url": "https://[domain][path]", "for_mobile": true }
```
Run mobile Lighthouse. Label output as "Lab diagnostic (Lighthouse)" -- not real CWV.
Extract: performance, seo_score, accessibility, lcp, cls.
- V1: scores are 0–100 directly; LCP/CLS come as formatted strings (`displayValue`)
- V3: scores are 0–1 — multiply by 100; LCP/CLS are raw numbers (`numericValue` in ms for time, ratio for CLS) — format manually: LCP = `round(ms/1000, 1)` s; CLS = round to 3dp
Status: performance >=90 = green, >=50 = amber, <50 = red.

**Call 13-B:** V1: `on_page_instant_pages` / V3: `POST /v3/on_page/instant_pages`
Detect: missing H1, missing meta description, images without alt, internal 301 redirects,
duplicate meta tags, missing schema.

Build `s5.pages` and `s5.issues` (sorted CRITICAL -> HIGH -> MEDIUM -> LOW).
If reader = "exec": include only CRITICAL and HIGH issues in the main body;
                    MEDIUM and LOW go to appendix or are omitted.
If reader = "manager": include all severity levels.
Write `s5.insight`.

---

### 5.7 -- AI / LLM Visibility (module: ai_llm_visibility, optional)

**Call 14:** V1: `ai_opt_llm_ment_agg_metrics` / V3: `POST /v3/ai_optimization/llm_mentions/target_metrics/live`
```json
{ "target": [{"domain": "[client_domain]"}], "platform": "google" }
```
Extract: total_mentions, avg_position, citations_count, models_count.

**Call 15:** V1: `ai_opt_llm_ment_search` / V3: `POST /v3/ai_optimization/llm_mentions/search_mentions/live` — Google AI Overviews
```json
{ "target": [{"domain": "[client_domain]"}], "platform": "google", "limit": 10 }
```
Extract: query, mention_type. Save as `s_ai.google_mentions`.

**Call 16:** V1: `ai_opt_llm_ment_search` / V3: `POST /v3/ai_optimization/llm_mentions/search_mentions/live` — ChatGPT
```json
{ "target": [{"domain": "[client_domain]"}], "platform": "chat_gpt", "limit": 10 }
```
Extract: query, mention_type. Save as `s_ai.chatgpt_mentions`.

Build `s_ai.metrics`: total_mentions, citations_count, avg_position, models_count.

Also check SERP AI Overview presence: for each tracked keyword where `serp_features`
includes "ai_overview", flag it.
Build `s_ai.ai_overview_keywords`: list of keywords where AI Overview appears.

Write `s_ai.insight`. Frame as "GEO (Generative Engine Optimization) readiness."

---

### 5.8 -- Next Actions

Write 5 prioritised recommendations grounded in the data from enabled modules.

For existing_client framing:
- Frame as "what we did + what's next"
- Reference specific results from this report
- Include effort already invested where relevant

For warm_lead framing:
- Frame as "gaps we'd close"
- Quantify opportunity: "fixing X could recover ~Y visits/mo"
- Be specific about what the agency would do

Each action: title, why, actions (steps), effort, impact, owner.
Store as `s6.actions`.

---

## Step 6 -- Assemble Data JSON

Save to `[client-domain]_data_[YYYY-MM].json`.
Config block = fully merged config (all fields in one object).
Schema: see Appendix B.

---

## Step 7 -- Generate PDF

```bash
python "[skill_dir]/scripts/build_report.py" "[project_folder]/[client-domain]_data_[YYYY-MM].json"
```

On success: `Report saved: [path]`.

Common errors:
- `ModuleNotFoundError: reportlab` -> `pip install reportlab`
- `UnicodeEncodeError` -> save JSON with `encoding="utf-8"`

---

## Step 8 -- Deliver

```
Report complete.

PDF:  [output_path]
Data: [data_json_path]

Summary:
  - Estimated traffic: [etv] (modeled)
  - Visibility Index: [vi] / 100
  - [N] of [total] tracked keywords on page 1
  - Top win: "[keyword]" moved [old] -> [new]
  - [N] new referring domains, [M] lost
  - [X] technical issues ([Y] critical)
  - 5 next actions included
```

---

## Step 9 -- Go Deeper

Immediately after Step 8 delivery, present follow-up offers via AskUserQuestion
(multi-select), header "Go deeper?", question "Want to dig deeper? Pick any — I'll run
a focused follow-up."

### Selection logic

1. **Check triggers** — evaluate each offer's fire condition against the data just collected.
2. **Rank by signal strength** — strongest finding first (large traffic drop > small gap > general offer).
3. **Enforce variety** — max 2 offers from the same theme; spread across: keywords / competitors+links / AI / technical+local / content.
4. **Floor 3 / cap 5** — if fewer than 3 trigger, fill from always-available offers (D9, D10, D3).
5. Always append "No thanks — report is enough" as the final option.

### Offer bank

Fill `{placeholders}` with real numbers/terms from the current report before displaying.

| ID | Label | Templated offer | Fire condition | Action |
|----|-------|-----------------|----------------|--------|
| D1 | Opportunity map | "You rank for {ranked}/{total_tracked} targets. Want the full gap map — every term you're missing (e.g. {top_opportunity_kw}, {top_opportunity_vol}/mo), with difficulty + the page to build?" | Opportunity keywords exist in s2 | Run inline: `keyword_ideas` + `keyword_suggestions` + `bulk_keyword_difficulty` → ranked opportunity table |
| D2 | Ranking-drop diagnosis | "{drop_count} keywords slipped (e.g. {top_drop_kw} {old_pos}→{new_pos}). Want a drop diagnosis — which URLs fell, who overtook you, what changed in the SERP?" | RISK keywords > 0 or ETV/VI declined | Run inline: `historical_serps` + `serp_organic_live_advanced` + `ranked_keywords` → per-URL drop table |
| D3 | Full competitor breakdown | "You're tracked vs {competitor_count} rivals. Want the head-to-head — keyword gaps, who owns which terms, where you can take share?" | Competitor module ran or competitors in config | → Run `competitor-backlink-gap` skill |
| D4 | Backlink & link-gap audit | "{ref_domains} referring domains, DR {dr}. Want a link deep dive — new/lost detail, spam review, and competitor links you don't have?" | Backlinks module returned data | → Run `competitor-backlink-gap` skill |
| D5 | Answer-engine monitoring | "This report covers Google AI Overview + ChatGPT. Want live monitoring across ChatGPT, Gemini, Claude & Perplexity — who's mentioned for your key questions?" | AI/LLM module ran or AI Overview keywords found | → Run `ai-visibility-report` skill |
| D6 | AI citation analysis | "You're cited {citation_count}× in AI answers. Want the exact pages that get cited, the questions that trigger them, and where competitors get cited instead?" | AI mentions data present (citations_count > 0) | → Run `ai-visibility-report` skill |
| D7 | Full technical crawl | "We audited {pages_audited} pages, {issue_count} issues ({critical_count} critical). Want a full-site crawl with a prioritized, dev-ready fix list?" | Tech module found issues or fewer than 5 pages audited | → Run `seo-portfolio-audit` skill |
| D8 | Local visibility deep dive | "Want a local deep dive — map-pack rankings across all locations, your GBP vs local rivals, and review gaps?" | Footprint = local or both | Run inline: `business_data_business_listings_search` + `serp_organic_live_advanced` (local pack) per city |
| D9 | Content plan | "Want a content plan for next quarter — your targets grouped into topic clusters, sized by opportunity and intent?" | Always available (esp. many informational/opportunity keywords) | → Run `content-plan-builder` skill |
| D10 | Demand & seasonality | "Want a trend view — are your core terms ({top_3_kws}) growing or declining, and when do they peak?" | Always available (esp. if traffic shifted) | Run inline: `kw_data_google_trends_explore` + `dataforseo_labs_google_historical_keyword_data` → trend chart |
| D11 | Flagship-page deep dive | "Want a deep dive on {top_page} — every keyword it ranks for, its SERP rivals, and an optimization brief?" | A key page identified (top-traffic page or worst-scoring tech page) | Run inline: `dataforseo_labs_google_ranked_keywords` (page filter) + `dataforseo_labs_google_relevant_pages` + `on_page_instant_pages` |
| D11b | Keyword cannibalization check | "Want to check if your pages are competing against each other for the same keywords?" | keyword_rankings module ran, 50+ ranked keywords | → Run `keyword-cannibalization-detector` skill |

### When the user selects an offer

- **Inline offers (D1, D2, D8, D10, D11):** run the listed endpoints immediately in this session, present a focused analysis in chat (no new PDF needed unless significant).
- **Skill offers (D3, D4, D5, D6, D7, D9, D11b):** tell the user "Type `run [skill-name]` to launch the {Skill Name} skill" and confirm the config is already available (domain, keywords, competitors carry over).
- If multiple offers selected: execute them in order, one at a time.

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Domain returns 0 ranked keywords | Stop. Ask user to verify domain and location. |
| A module has no data | Render placeholder only if module is enabled; else skip. |
| Lighthouse times out | Skip that URL; note in issues table. |
| DataForSEO 401 | Stop. "Please connect/re-authenticate the DataForSEO MCP." |
| User says no at Step 4 | Ask what to change, update config, re-display summary. |
| GBP not found | Note "No GBP listing found" in local section; do not abort. |

---

## Appendix A -- Client Config Schema (`[client-domain]_config.json`)

```json
{
  "client_name":              "Bloom Cosmetics",
  "client_domain":            "bloom-cosmetics.com",
  "location_code":            2826,
  "location_name":            "United Kingdom",
  "language_code":            "en",
  "language_name":            "English",
  "locations": [
    { "city_location_code": 1006886, "city_location_name": "London, England" },
    { "city_location_code": 1006886, "city_location_name": "Manchester, England" }
  ],
  "tracked_keywords":         ["organic moisturiser", "vegan foundation UK"],
  "competitors":              ["glowlab.co.uk", "naturalbeauty.com"],
  "top_pages_for_tech_audit": ["/", "/organic-moisturiser"],
  "sitemap_pages_audited":    ["/", "/organic-moisturiser", "/about", "/shop"],
  "output_folder":            null,

  "date_from":                "2026-05-01",
  "date_to":                  "2026-05-31",
  "date_prev_from":           "2026-04-01",
  "date_prev_to":             "2026-04-30",
  "period_current":           "May 2026",
  "period_prev":              "April 2026",

  "report_settings": {
    "purpose":         "existing_client",
    "reader":          "exec",
    "footprint":       "national",
    "keyword_source":  "client_provided",
    "period_mode":     "month",
    "enabled_modules": [
      "keyword_rankings", "backlinks", "tech_health", "next_actions"
    ]
  },

  "framing": {
    "cover_title": "SEO Performance Review",
    "s1_header":   "Executive Summary",
    "s2_header":   "Keyword Rankings",
    "s6_header":   "What We're Doing Next",
    "s6_framing":  "Progress on agreed targets + next sprint"
  }
}
```

---

## Appendix B -- Full Data JSON Schema

```json
{
  "config": {
    "client_name": "...", "client_domain": "...",
    "location_code": 2826, "location_name": "...",
    "language_code": "en", "language_name": "...",
    "city_location_code": null, "city_location_name": null,
    "tracked_keywords": ["..."], "competitors": ["..."],
    "top_pages_for_tech_audit": ["/"],
    "period_current": "May 2026", "period_prev": "April 2026",
    "date_from": "2026-05-01", "date_to": "2026-05-31",
    "date_prev_from": "2026-04-01", "date_prev_to": "2026-04-30",
    "output_path": "bloom-cosmetics.com_SEO_2026-05.pdf",
    "report_settings": {
      "purpose": "existing_client", "reader": "exec",
      "footprint": "national", "keyword_source": "client_provided",
      "period_mode": "month",
      "enabled_modules": ["keyword_rankings", "backlinks", "tech_health", "next_actions"]
    },
    "framing": {
      "cover_title": "SEO Performance Review",
      "s1_header": "Executive Summary",
      "s2_header": "Keyword Rankings",
      "s6_header": "What We're Doing Next",
      "s6_framing": "Progress on agreed targets + next sprint"
    }
  },
  "sections": {
    "s1_executive_summary": {
      "current_period":  { "etv": 28400, "keywords_count": 87, "vi": 42.3,
                           "pos_1": 2, "pos_2_3": 9, "pos_4_10": 20,
                           "pos_11_20": 18, "pos_21_30": 12, "pos_31_100": 26 },
      "previous_period": { "etv": 25350, "keywords_count": 81, "vi": 38.7,
                           "pos_1": 1, "pos_2_3": 7, "pos_4_10": 17,
                           "pos_11_20": 16, "pos_21_30": 14, "pos_31_100": 26 },
      "narrative": "May was a strong month for bloom-cosmetics.com ...",
      "insight":   "Traffic up 12% -- strongest month in Q2.",
      "tldr":      ["Visibility Index up 3.6 pts MoM", "2 new page-1 keywords", "DR held at 51"]
    },
    "s2_keyword_rankings": {
      "keywords": [
        { "keyword": "organic moisturiser", "volume": 12100, "intent_group": "commercial",
          "pos_current": 6, "pos_previous": 9, "url": "/organic-moisturiser",
          "serp_features": ["people_also_ask"], "status": "WIN" }
      ],
      "keyword_groups": {
        "commercial":     [{ "keyword": "...", "volume": 0, "pos_current": 0 }],
        "informational":  [],
        "local":          [],
        "branded":        [],
        "navigational":   []
      },
      "opportunities": [
        { "keyword": "best vegan foundation", "volume": 8100, "pos_current": null,
          "potential_traffic": 527 }
      ],
      "insight": "..."
    },
    "s_local": {
      "locations": [
        {
          "location_name": "London, England",
          "city_location_code": 1006886,
          "gbp": { "name": "Bloom Cosmetics London", "rating": 4.7, "review_count": 312,
                   "address": "12 King St, London", "is_claimed": true },
          "local_pack_rankings": [
            { "keyword": "organic moisturiser London", "pack_position": 2, "organic_position": 4 }
          ],
          "local_pack_competitors": [
            { "name": "The Body Shop", "domain": "thebodyshop.com",
              "avg_pack_position": 1.0, "avg_rating": 4.5, "total_reviews": 890,
              "keywords_in_pack": 3 }
          ]
        }
      ],
      "insight": "..."
    },
    "s3_competitor_snapshot": {
      "client": { "etv": 28400, "avg_position": 12.4 },
      "competitors": [
        { "domain": "glowlab.co.uk", "etv": 71200, "avg_position": 8.2, "intersections": 34 }
      ],
      "insight": "..."
    },
    "s4_backlinks": {
      "current":  { "dr": 51, "total_backlinks": 24310, "referring_domains": 1847,
                    "dofollow": 18900, "nofollow": 5410 },
      "previous": { "dr": 50, "total_backlinks": 23998, "referring_domains": 1833 },
      "timeline": [
        { "date": "2025-12", "referring_domains": 1788, "new": 9, "lost": 5 }
      ],
      "new_domains":  [{ "domain": "beautymag.co.uk", "dr": 68, "dofollow": true,
                         "anchor": "natural skincare", "first_seen": "2026-05-08" }],
      "lost_domains": [{ "domain": "makeupblog.co.uk", "dr": 41,
                         "lost_date": "2026-04-28", "reason": "Page removed" }],
      "insight": "..."
    },
    "s5_technical_health": {
      "pages": [
        { "url": "/", "label": "Homepage", "performance": 91, "seo_score": 98,
          "accessibility": 94, "lcp": "1.8s", "cls": "0.04", "status": "green" }
      ],
      "issues": [
        { "issue": "LCP > 4s on /spf-tinted-moisturiser", "severity": "CRITICAL",
          "pages_affected": 1, "impact": "Rankings + UX",
          "fix": "Compress hero image, enable lazy load" }
      ],
      "insight": "..."
    },
    "s_ai_llm": {
      "metrics": { "total_mentions": 14, "citations_count": 6,
                   "avg_position": 3.2, "models_count": 3 },
      "google_mentions": [
        { "query": "best organic moisturiser UK", "mention_type": "citation" }
      ],
      "chatgpt_mentions": [
        { "query": "natural face cream UK", "mention_type": "recommendation" }
      ],
      "ai_overview_keywords": ["organic moisturiser", "vegan foundation UK"],
      "insight": "..."
    },
    "s6_next_actions": {
      "actions": [
        { "title": "...", "why": "...", "actions": "1) ...", "effort": "Medium (3-5 hrs)",
          "impact": "High -- est. +340 sessions/mo", "owner": "SEO" }
      ]
    }
  }
}
```

---

## Appendix C -- V1 → V3 Call Translation

When `DFS_MODE=V3`, replace every V1 tool call with `api_request` using the table below.
V3 `data` is always an array of one task object containing the same parameters.

| V1 tool name | V3 path | Notes |
|---|---|---|
| `dataforseo_labs_google_domain_rank_overview` | `POST /v3/dataforseo_labs/google/domain_rank_overview/live` | |
| `dataforseo_labs_google_historical_rank_overview` | `POST /v3/dataforseo_labs/google/historical_rank_overview/live` | |
| `dataforseo_labs_google_ranked_keywords` | `POST /v3/dataforseo_labs/google/ranked_keywords/live` | |
| `dataforseo_labs_google_keyword_ideas` | `POST /v3/dataforseo_labs/google/keyword_ideas/live` | |
| `dataforseo_labs_google_keyword_suggestions` | `POST /v3/dataforseo_labs/google/keyword_suggestions/live` | |
| `dataforseo_labs_google_historical_serps` | `POST /v3/dataforseo_labs/google/historical_serps/live` | |
| `dataforseo_labs_google_competitors_domain` | `POST /v3/dataforseo_labs/google/competitors_domain/live` | |
| `dataforseo_labs_google_serp_competitors` | `POST /v3/dataforseo_labs/google/serp_competitors/live` | |
| `dataforseo_labs_bulk_keyword_difficulty` | `POST /v3/dataforseo_labs/google/bulk_keyword_difficulty/live` | |
| `dataforseo_labs_google_relevant_pages` | `POST /v3/dataforseo_labs/google/relevant_pages/live` | |
| `dataforseo_labs_google_historical_keyword_data` | `POST /v3/dataforseo_labs/google/historical_search_volume/live` | |
| `serp_organic_live_advanced` | `POST /v3/serp/google/organic/live/advanced` | |
| `serp_locations` | `GET /v3/serp/google/locations` | Pass `name` as query param |
| `kw_data_google_ads_search_volume` | `POST /v3/keywords_data/google_ads/search_volume/live` | |
| `kw_data_google_trends_explore` | `POST /v3/keywords_data/google_trends/explore/live` | |
| `backlinks_summary` | `POST /v3/backlinks/summary/live` | Field is `backlinks` (not `total_backlinks`); no `dofollow`/`nofollow` — use `referring_domains_nofollow`; `count` not `keywords_count` in domain_rank_overview |
| `backlinks_timeseries_new_lost_summary` | `POST /v3/backlinks/timeseries_new_lost_summary/live` | |
| `backlinks_referring_domains` | `POST /v3/backlinks/referring_domains/live` | |
| `on_page_lighthouse` | `POST /v3/on_page/lighthouse/live/json` | V3 returns `numericValue` (ms) not `displayValue`; format: LCP=`round(ms/1000,1)`s, CLS=3dp |
| `on_page_instant_pages` | `POST /v3/on_page/instant_pages` | |
| `business_data_business_listings_search` | `POST /v3/business_data/google/my_business_info/live` | |
| `ai_opt_llm_ment_agg_metrics` | `POST /v3/ai_optimization/llm_mentions/target_metrics/live` | |
| `ai_opt_llm_ment_search` | `POST /v3/ai_optimization/llm_mentions/search_mentions/live` | |
| `ai_opt_llm_ment_top_pages` | `POST /v3/ai_optimization/llm_mentions/top_pages/live` | |
| `ai_opt_llm_ment_top_domains` | `POST /v3/ai_optimization/llm_mentions/top_domains/live` | |
| `ai_optimization_llm_response` | `POST /v3/ai_optimization/llm_mentions/response/live` | |

**V3 call syntax example:**
```python
# V1:
backlinks_summary(target="bloom-cosmetics.com", include_subdomains=True)

# V3 equivalent:
api_request(
  method="POST",
  path="/v3/backlinks/summary/live",
  data=[{"target": "bloom-cosmetics.com", "include_subdomains": True}]
)
```

The response structure from V3 is the same as V1 — extract fields identically.

---

## Reference Files

- `references/endpoints.md` -- DataForSEO endpoint reference with request/response fields.
- `scripts/build_report.py` -- PDF generator. Call via subprocess, do not modify.
