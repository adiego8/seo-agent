# DataForSEO API -- Endpoint Reference for SEO Monthly Report

All data is fetched via the DataForSEO MCP. This file documents the exact endpoints,
request parameters, and response fields used by the skill.

---

## Section 01 -- Executive Summary

### `dataforseo_labs_google_domain_rank_overview`

**Purpose:** Current-period snapshot of a domain's organic visibility -- estimated
traffic, keyword counts by position bucket (top1, top3, top10 ... top100), and avg position.

**Key response fields:**
```json
{
  "metrics": {
    "organic": {
      "etv": 28400,
      "pos_1": 2,
      "pos_2_3": 9,
      "pos_4_10": 20,
      "pos_11_20": 18,
      "pos_21_30": 12,
      "pos_31_40": 9,
      "pos_41_50": 8,
      "pos_51_60": 5,
      "pos_61_70": 4,
      "pos_71_80": 3,
      "pos_81_90": 2,
      "pos_91_100": 1,
      "count": 87
    }
  }
}
```

**Visibility Index formula:**
```
VI = (pos_1*1.0 + pos_2_3*0.85 + pos_4_10*0.5 + pos_11_20*0.2 + pos_21_30*0.05)
     / max(keywords_count, 1) * 100
```

**Request:**
```json
{ "target": "bloom-cosmetics.com", "location_code": 2826, "language_code": "en" }
```

---

### `dataforseo_labs_google_historical_rank_overview`

**Purpose:** Same fields as `domain_rank_overview` but for a specific past date range.
Used to get the previous-period snapshot for MoM comparison.

**Request:**
```json
{
  "target": "bloom-cosmetics.com",
  "location_code": 2826,
  "language_code": "en",
  "date_from": "2026-04-01",
  "date_to": "2026-04-30"
}
```

**Note:** Extract `etv`, `pos_1`..`pos_100` for the previous period -> compute MoM delta
for Executive Summary.

---

## Section 02 -- Keyword Rankings

### `dataforseo_labs_google_ranked_keywords`

**Purpose:** Full list of keywords the domain ranks for in Google -- keyword text, URL,
position, SERP features, and search volume.

**Key response fields:**
```json
{
  "keyword": "organic moisturiser",
  "keyword_data": {
    "search_volume": 12100,
    "competition": 0.45
  },
  "ranked_serp_element": {
    "serp_item": {
      "rank_absolute": 6,
      "url": "bloom-cosmetics.com/organic-moisturiser",
      "type": "organic"
    }
  }
}
```

**Request:**
```json
{
  "target": "bloom-cosmetics.com",
  "location_code": 2826,
  "language_code": "en",
  "limit": 500
}
```

---

### `serp_organic_live_advanced`

**Purpose:** Live SERP for a specific keyword -- position of each domain in the results,
SERP features present (featured snippet, PAA, shopping, image pack, etc.).

**Used in Section 02:** For each tracked keyword to get current position and identify
which SERP features are present.

**Key response fields:**
```json
{
  "items": [
    {
      "type": "organic",
      "rank_absolute": 6,
      "domain": "bloom-cosmetics.com",
      "url": "...",
      "title": "Best Organic Moisturiser UK | Bloom Cosmetics"
    },
    { "type": "featured_snippet", "domain": "naturalbeauty.com" },
    { "type": "people_also_ask", "items": ["what is..."] }
  ]
}
```

**Request:**
```json
{
  "keyword": "organic moisturiser",
  "location_code": 2826,
  "language_code": "en",
  "depth": 30
}
```

> **Cost note:** 1 call = 1 keyword. 20 tracked keywords = 20 calls. No batching available.

---

### `kw_data_google_ads_search_volume`

**Purpose:** Search volume, Competition index, and CPC for a list of keywords.

**Request (bulk -- send all tracked keywords in one call):**
```json
{
  "keywords": ["organic moisturiser", "vegan foundation UK"],
  "location_code": 2826,
  "language_code": "en"
}
```

**Used for:** Populating the `Vol/mo` column in the keyword rankings table.

---

### `dataforseo_labs_google_historical_serps`

**Purpose:** SERP snapshots for specific keywords at a past date -- used to get
previous-period positions for the top tracked keywords.

**Request:**
```json
{
  "keyword": "organic moisturiser",
  "location_code": 2826,
  "language_code": "en",
  "date_from": "2026-04-01",
  "date_to": "2026-04-30"
}
```

**Used for:** Computing position delta (now vs previous period) in the keyword table.
Run only for the top 10 tracked terms by volume to limit call count.

---

## Section 03 -- Share of Voice

### `dataforseo_labs_google_competitors_domain`

**Purpose:** Discover organic competitors of a domain -- domains with the highest keyword
overlap, their avg position, estimated traffic, and intersection keyword count.

**Key response fields:**
```json
{
  "domain": "glowlab.co.uk",
  "avg_position": 8.2,
  "intersections": 34,
  "full_domain_metrics": {
    "organic": { "etv": 71200, "pos_1": 15, "pos_4_10": 42 }
  }
}
```

**Request:**
```json
{
  "target": "bloom-cosmetics.com",
  "location_code": 2826,
  "language_code": "en",
  "limit": 10
}
```

---

### `dataforseo_labs_google_serp_competitors`

**Purpose:** For a defined keyword set, returns every competing domain's position metrics
across those keywords. Core endpoint for SOV calculation.

**Request:**
```json
{
  "keywords": ["organic moisturiser", "vegan foundation UK"],
  "location_code": 2826,
  "language_code": "en"
}
```

**Key response fields:**
```json
{
  "domain": "glowlab.co.uk",
  "avg_position": 5.1,
  "metrics": {
    "organic": { "etv": 8200, "pos_1": 3, "pos_4_10": 7 }
  },
  "intersections": 14
}
```

**SOV formula per domain:**
```
SOV% = domain_etv_on_tracked_kws / sum_etv_all_domains_on_tracked_kws * 100
```

---

## Section 04 -- Backlink Profile

### `backlinks_summary`

**Purpose:** Full snapshot of a domain's link profile -- DR, total backlinks, referring
domains, dofollow/nofollow split, referring IPs.

**Key response fields:**
```json
{
  "rank": 339,
  "backlinks": 24310,
  "referring_domains": 1847,
  "referring_domains_nofollow": 1064,
  "referring_domains_noindex": 23,
  "broken_backlinks": 12,
  "broken_pages": 8,
  "referring_ips": 1402
}
```
Note: there is no top-level `dofollow`/`nofollow` count field. Use `backlinks - referring_pages_nofollow` to approximate dofollow count if needed. Field is `backlinks` (not `total_backlinks`).

**Important — DR normalization:** The `rank` field is on a 0-1000 scale, not 0-100.
Convert to Domain Rating (0-100) with:
```python
dr = round(math.sin(rank / 636.62) * 100, 1)
```
The MCP has no `rank_scale` parameter; apply this formula manually.

**Request:**
```json
{ "target": "bloom-cosmetics.com", "include_subdomains": true }
```

---

### `backlinks_timeseries_new_lost_summary`

**Purpose:** Monthly trend of new and lost backlinks and referring domains over a date range.

**Request:**
```json
{
  "target": "bloom-cosmetics.com",
  "date_from": "2025-12-01",
  "date_to": "2026-05-31",
  "group_by": "month"
}
```

**Key response fields:**
```json
[
  {
    "date": "2026-05-01",
    "new_backlinks": 312,
    "lost_backlinks": 89,
    "new_referring_domains": 18,
    "lost_referring_domains": 4
  }
]
```

**Used for:** 6-month trend table in Section 4A.

---

### `backlinks_referring_domains`

**Purpose:** Detailed list of referring domains with DR, UR, backlink count, dofollow flag,
first_seen and lost_date. Used for both new and lost domain tables.

**Request -- new domains (current period):**
```json
{
  "target": "bloom-cosmetics.com",
  "filters": [
    ["first_seen", ">=", "2026-05-01"],
    ["first_seen", "<=", "2026-05-31"]
  ],
  "order_by": [["rank", "desc"]],
  "limit": 100
}
```

**Request -- lost domains:**
```json
{
  "target": "bloom-cosmetics.com",
  "filters": [
    ["lost_date", ">=", "2026-05-01"],
    ["is_lost", "=", true]
  ]
}
```

**Key response fields (per domain):**
```json
{
  "domain": "beautymag.co.uk",
  "rank": 68,
  "backlinks": 3,
  "referring_domains": 1240,
  "dofollow": true,
  "is_lost": false,
  "first_seen": "2026-05-08",
  "lost_date": null
}
```

---

## Section 05 -- Technical Health

### `on_page_lighthouse`

**Purpose:** Google Lighthouse audit for a URL -- Performance, SEO, Accessibility, and
Best Practices scores, plus Core Web Vitals (LCP, CLS, TBT).

**Request:**
```json
{
  "url": "https://bloom-cosmetics.com/organic-moisturiser",
  "for_mobile": true
}
```

**V3 path:** `POST /v3/on_page/lighthouse/live/json`

**Key response fields:**
```json
{
  "categories": {
    "performance":    { "score": 0.51 },
    "seo":            { "score": 0.85 },
    "accessibility":  { "score": 0.74 },
    "best-practices": { "score": 0.54 }
  },
  "audits": {
    "largest-contentful-paint": { "numericValue": 7379 },
    "total-blocking-time":      { "numericValue": 397 },
    "cumulative-layout-shift":  { "numericValue": 0.001 }
  }
}
```

**Important:** V3 returns `numericValue` (raw numbers in ms for time metrics, ratio for CLS),
not `displayValue`. Format manually: LCP = `round(ms/1000, 1)` → "7.4 s"; CLS = round to 3dp.
Category scores are 0–1; multiply by 100 for display.

**Note:** Run for homepage + top landing pages (max 6). 1 call per URL.

---

### `on_page_instant_pages`

**Purpose:** Fast on-page audit -- HTTP status, meta tags, headings, canonical, schema,
images without alt text, broken internal links, duplicate content signals.

**Request:**
```json
{
  "url": "https://bloom-cosmetics.com/organic-moisturiser",
  "load_resources": true,
  "enable_javascript": true
}
```

**Key response fields for issue detection:**
```json
{
  "meta": {
    "title": "...",
    "description": null,
    "htags": { "h1": ["..."], "h2": ["...", "..."] }
  },
  "checks": {
    "no_image_alt": true,
    "no_description": true,
    "duplicate_meta_tags": false,
    "has_render_blocking_resources": true
  },
  "images": [
    { "src": "hero.jpg", "alt": null, "size": 1240000 }
  ],
  "internal_links": [
    { "url": "...", "status_code": 301 }
  ]
}
```

---

## Section 06 -- Local SEO

### `business_data_business_listings_search`

**Purpose:** Fetch Google Business Profile (GBP) data — rating, review count, category,
address, claimed status, and basic visibility signals.

**Request:**
```json
{
  "keyword": "Bloom Cosmetics",
  "location_code": 2826,
  "language_code": "en"
}
```

**Key response fields:**
```json
{
  "title": "Bloom Cosmetics",
  "rating": { "value": 4.7, "votes_count": 312 },
  "category": "Cosmetics store",
  "address": "14 King St, London",
  "is_claimed": true,
  "work_hours": { "timetable": { "monday": [{ "open": { "hour": 9 }, "close": { "hour": 18 } }] } }
}
```

---

### `serp_organic_live_advanced` (local pack)

**Purpose:** Detect whether the client appears in the Local Pack (top-3 map results) for
target keywords, and capture competitors shown in that pack.

**Request:**
```json
{
  "keyword": "organic moisturiser london",
  "location_code": 2826,
  "language_code": "en",
  "depth": 10
}
```

**Key response fields for local pack detection:**
```json
{
  "items": [
    {
      "type": "local_pack",
      "items": [
        {
          "title": "Bloom Cosmetics",
          "rating": 4.7,
          "rating_count": 312,
          "url": "bloom-cosmetics.com",
          "rank_group": 1
        }
      ]
    }
  ]
}
```

Filter `items` where `type == "local_pack"` to extract pack positions. Run for each
local tracking keyword (configured under `local_pack_keywords` in the client config).

---

## Endpoint Summary

| # | Section | Endpoint | Module | Calls |
|---|---------|----------|--------|-------|
| 1 | Executive Summary | `dataforseo_labs_google_domain_rank_overview` | Labs | 1 |
| 2 | Executive Summary | `dataforseo_labs_google_historical_rank_overview` | Labs | 1 |
| 3 | Keyword Rankings | `dataforseo_labs_google_ranked_keywords` | Labs | 1 |
| 4 | Keyword Rankings | `serp_organic_live_advanced` | SERP Live | 1 per keyword |
| 5 | Keyword Rankings | `kw_data_google_ads_search_volume` | KW Data | 1 bulk |
| 6 | Keyword Rankings | `dataforseo_labs_google_historical_serps` | Labs | up to 10 |
| 7 | Share of Voice | `dataforseo_labs_google_competitors_domain` | Labs | 1 |
| 8 | Share of Voice | `dataforseo_labs_google_serp_competitors` | Labs | 1 |
| 9 | Share of Voice | `dataforseo_labs_google_historical_rank_overview` | Labs | 1 per competitor |
| 10 | Backlink Profile | `backlinks_summary` | Backlinks | 1 |
| 11 | Backlink Profile | `backlinks_timeseries_new_lost_summary` | Backlinks | 1 |
| 12 | Backlink Profile | `backlinks_referring_domains` | Backlinks | 2 (new + lost) |
| 13 | Technical Health | `on_page_lighthouse` | On-Page | 1 per URL |
| 14 | Technical Health | `on_page_instant_pages` | On-Page | 1 per URL |
| 15 | Local SEO | `business_data_business_listings_search` | Business Data | 1 per location |
| 16 | Local SEO | `serp_organic_live_advanced` (local pack) | SERP Live | 1 per local keyword |

**Typical total:** ~30-40 base calls + 1 per tracked keyword (SERP live).
For 20 keywords, 4 competitors, 5 pages, 2 locations, 5 local keywords: ~70-85 calls.

---

## Common Parameters

### location_code / language_code

| Country | location_code | language_code |
|---------|--------------|---------------|
| United Kingdom | 2826 | en |
| United States | 2840 | en |
| Ukraine | 2804 | uk |
| Germany | 2276 | de |
| France | 2250 | fr |
| Australia | 2036 | en |

Full list: use `serp_locations` MCP tool to search by country name.

### Labs vs Live

- `dataforseo_labs_*` -- cached data (days/weeks old). Fast, lower cost. Use for
  domain overviews, competitor discovery, historical positions.
- `serp_organic_live_advanced` -- real-time SERP. Use for current tracked keyword
  positions and SERP feature detection.
