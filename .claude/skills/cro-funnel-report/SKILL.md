---
name: cro-funnel-report
description: >
  Audits a website's conversion funnel end to end and produces a markdown CRO report.
  Use this skill whenever a user wants to create, generate, produce or build a CRO report,
  conversion audit, funnel audit, conversion rate report, UX/conversion assessment, or
  landing page audit. Also triggers on: "why isn't this site converting", "audit the funnel
  for [domain]", "run a CRO report for [client]", "review our checkout flow", "conversion
  audit for [domain]", "where are we losing people", "what's wrong with our pricing page",
  "find the friction on [site]". Fetches the live pages, extracts conversion signals
  deterministically, scores them against a fixed rubric, and writes a markdown report.
  Free to run -- no paid API is used.
---

# CRO Funnel Report Skill

## What This Skill Does

Audits a funnel as a **system**, not as a pile of pages: it walks
`entry → value → proof → offer → conversion`, finds where the path breaks, and writes up
what to fix in severity order.

**Output:** `[report_dir]/[client-domain]_cro_[YYYY-MM-DD].md` — plus
`[report_dir]/[client-domain]_pages_[YYYY-MM-DD].json`, the raw evidence every finding is traceable to.

**Every file this skill writes goes inside the company's folder, `[report_dir]`** (e.g.
`mywelltax-report/`): candidates, plan, config, page evidence and the report. Never write to the
top level of the project. Later additions for the same company (Search Console data, positioning
notes) go into that company's existing report, not into a new loose file.

**Cost: zero.** Fetching live HTML and reading it is all this does. No DataForSEO, no
PageSpeed, no analytics API, nothing metered. Never add a paid call to this workflow without
asking the user first.

---

## Interaction Rules (apply to every question in this skill)

- Ask questions ONE AT A TIME. Do not combine questions. Wait for the reply before the next.
- For ALL questions with a fixed set of options: use the `AskUserQuestion` tool to render
  an interactive select or multiselect UI. Do NOT output a numbered text list for these.
- Optional text fields: ask in plain text, note "(optional -- press Enter or type '-' to skip)".
  Store null if skipped.
- For open-ended lists (URLs, competitors): ask in plain text. Never pre-fill.
- For yes/no: use AskUserQuestion single-select with "Yes" / "No" options.

---

## Reference Files

Read these before analysing. They hold the judgement; this file holds the process.

| File | Use |
|---|---|
| `references/heuristics.md` | The six scoring dimensions, the severity model, the readiness score, and what raw HTML cannot tell you |
| `references/page-roles.md` | What each funnel stage owes, and the stage-gap findings |
| `references/report-template.md` | The exact markdown skeleton of the report |

---

## Step 1 -- Configurator

Check for `[report_dir]/[client-domain]_cro_config.json` first (look inside every `*-report/`
folder, since an existing company folder may have a different name). If it exists and has
all five answers, skip to Step 2 and show one line:
"Using saved config: {business_model} / {primary_conversion} / {reader}."

Otherwise run Q1-Q5 one at a time. Save answers to the config file.

**Q1 -- Domain.** Always the first question. Ask it before anything else, with no preamble
and nothing alongside it. Plain text:

> Which domain should I analyze?

**Normalise whatever arrives** -- never make the user type a scheme. `acmebooks.co.uk`,
`www.acmebooks.co.uk`, `https://acmebooks.co.uk/en` and a pasted deep link are all the same
answer: prepend `https://` if absent, keep the host, and drop the path unless the user clearly
meant a sub-site.

Save the normalised URL as `site` and the bare host (no scheme, no `www.`) as `client_domain`.

Then set `report_dir`, the company's folder: the domain without `www.` or its ending, plus
`-report` (`mywelltax.com` → `mywelltax-report`). If a `*-report/` folder for this company already
exists under another name, reuse it (`numericosoftware.com` → `numerico-report`). Create it with
`mkdir -p` before the first file is written.
Discovery follows redirects, so `example.com` resolving to `www.example.com/en` is expected --
do not go back to the user about it.

**Then run Step 2 (discover) immediately -- before Q2.** It costs three requests and tells you
whether there is anything to audit. If its homepage gate stops the run (see Step 2), report
that and do not ask Q2-Q5. Four questions about a site that is down, or that raw HTML cannot
read, waste the user's time.

**Q2 -- Business model.** AskUserQuestion, single-select, header "Business model":
- Question: "What kind of business is this?"
- "Lead generation" — description "Enquiries, quotes or bookings -- the sale happens offline"
- "E-commerce" — description "Products sold directly on the site"
- "SaaS / subscription" — description "Trial, demo or self-serve signup"
- "Booking / appointment" — description "Calendar slots, consultations, reservations"

Save as `business_model`. It sets which stages are mandatory: e-commerce must have `offer`
and `conversion`; lead generation must have `conversion` with a form or a phone number.

**Q3 -- Primary conversion.** Plain text: "What is the ONE action a visitor should take?
(e.g. 'request a quote', 'start free trial', 'add to cart')"
Save as `primary_conversion`. Everything is judged against this. If the user names more than
one, ask which matters most this quarter — a funnel with two primary actions has neither.

**Q4 -- Reader.** AskUserQuestion, single-select, header "Primary reader":
- "Business owner / exec" — description "Wants the money impact and the decision"
- "Marketing / product team" — description "Wants the mechanism and a ticket they can action"

Save as `reader`: "exec" or "manager".

**Q5 -- Modules.** AskUserQuestion, multiSelect: true, header "Report modules".
Pre-tag the recommended set with "[Recommended] " in the description.

Recommended by model:
```
lead_gen:   funnel_map, page_audits, friction_inventory, trust_credibility, form_analysis, test_backlog
ecommerce:  funnel_map, page_audits, friction_inventory, trust_credibility, mobile_experience, test_backlog
saas:       funnel_map, page_audits, friction_inventory, form_analysis, test_backlog
booking:    funnel_map, page_audits, friction_inventory, form_analysis, trust_credibility, test_backlog
```

- Question: "Which sections should the report include?"
- "Funnel Map" — "Stage-by-stage coverage and the gaps between them"
- "Page Audits" — "Per-page scoring across six dimensions with evidence"
- "Friction Inventory" — "Every finding in one severity-ordered list"
- "Trust & Credibility" — "Proof density at the point of decision"

Second AskUserQuestion, multiSelect: true, header "More modules":
- "Mobile & Technical" — "Viewport, script weight, server response, measurement"
- "Form Analysis" — "Field-by-field friction on every lead form"
- "Test Backlog" — "ICE-scored hypotheses to run next"
- "None -- that's all" — "Skip, I've selected everything I need"

Merge both. Save as `enabled_modules`.
Keys: `funnel_map`, `page_audits`, `friction_inventory`, `trust_credibility`,
`mobile_experience`, `form_analysis`, `test_backlog`.

`funnel_map` and `page_audits` are always included even if deselected — without them there is
no audit. Say so if the user drops them.

---

## Step 2 -- Discover the funnel

```bash
python3 "[skill_dir]/scripts/fetch_pages.py" discover "[site]" --out "[report_dir]/[domain]_candidates.json"
```

Runs right after Q1 (see Step 1). Fetches at most three documents: the homepage, `robots.txt`
and `sitemap.xml`. It returns internal URLs with anchor text and a **guessed** funnel role.

**Homepage gate -- read `homepage` in the output first:**

| `homepage` says | Exit code | Do this |
|---|---|---|
| `failed: true` | 2 | Stop. No candidates were collected. Tell the user the status from `notes` (e.g. HTTP 500) and that there is nothing to audit until the site is back. Offer to re-run later. |
| `render_risk: true`, `rendered: false` | 0 | The site is built in JavaScript. Tell the user in one line ("This site is built in JavaScript -- rendering it in Chrome, about 3 s per page") and re-run discover with `--render`. Use that output from here on, and set `"render": true` in the plan (Step 3). |
| `render_risk: true`, `rendered: true` | 0 | Stop before Q2. Even rendered, the homepage is empty (login wall, bot blocking, or very late loading). Say so with the numbers from `notes`, and offer: paste the visible copy manually. |
| (no JSON written) | 3 | `--render` found no Chrome. Stop. Tell the user to install Google Chrome, or set `CHROME_PATH`. |
| neither | 0 | Continue. |

Read the rest of the output. Build a shortlist of **6-12 pages** covering as many stages as exist:

- Always include `entry` (the homepage).
- Include every `conversion` and `offer` page found — these carry the most weight.
- Include the best-linked `value` and `proof` page (highest `count`).
- Include `trust` and `support` only if the model makes them load-bearing.
- For `content`, take at most one representative page — audit the pattern, not the blog.

If a stage has no candidate, note it now. A missing stage is a finding, not an error.

---

## Step 3 -- Confirm before fetching

Show the shortlist as a **box-drawn table** -- three columns, in this order, no others.
This table is required. It is how the user sees your reasoning before you act on it, and the
same table goes into the report (Step 6).

```
┌────────────┬───────────────────────────┬───────────────────────────────────────────────────────┐
│   Stage    │            URL            │                          Why                          │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ entry      │ /en                       │ The homepage                                          │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ value      │ /en/services              │ Best-linked value page (5 inbound)                    │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ offer      │ /en/products              │ Product hub                                           │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ conversion │ /en/contact               │ The money page (4 inbound, "Let's work together")     │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ trust      │ /en/about                 │ Lead-gen consultancy — who you are is load-bearing    │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ orphan     │ /en/miami-tech-consulting │ Unreachable landing page — worth seeing what it's for │
└────────────┴───────────────────────────┴───────────────────────────────────────────────────────┘
```

Rules for the table:

- **Paths, not full URLs.** `/en/contact`, never `https://www.example.com/en/contact`.
- **"Why" is evidence, not a category.** "Best-linked value page (5 inbound)" and "Unreachable
  landing page" are reasons. "Value page" is not -- that just repeats the stage column.
- **`orphan` is its own stage label** for any page nothing links to, whatever role it was
  guessed as. It is usually the most interesting row in the table.
- Order rows by funnel position: entry → value → proof → offer → conversion → trust → support
  → content, with `orphan` last.
- Name any stage that has **no** candidate directly beneath the table.

Then ask, plain text: "Here's the funnel I'd audit. Add or remove anything, or say 'go'."

Respect edits exactly — the user knows which page is the real money page. If they add a URL
not in the candidate list, accept it and guess its role.

Write the confirmed list to `[report_dir]/[domain]_plan.json`:

```json
{
  "site": "https://example.com",
  "delay_seconds": 1.0,
  "pages": [
    {"url": "https://example.com/", "role": "entry", "label": "Home"},
    {"url": "https://example.com/pricing", "role": "offer", "label": "Pricing"}
  ]
}
```

If discovery ran with `--render`, add `"render": true` to the plan -- every page is then loaded
in Chrome the same way. A page that fails to render comes back as an error, not as an empty page.

**Never fetch a page list the user has not seen.**

---

## Step 4 -- Fetch

```bash
python3 "[skill_dir]/scripts/fetch_pages.py" fetch "[report_dir]/[domain]_plan.json" --out "[report_dir]/[domain]_pages_[YYYY-MM-DD].json"
```

One request per page, 1s apart. The script reports `ok_count`, `render_risk_count` and any
errors.

Handle what comes back:
- **A page errored** — report it, audit the rest, and list it as not audited. Do not retry
  more than once.
- **`render_risk` is true** — the page is client-rendered and the signals understate it. Tell
  the user which pages, and offer: paste the visible copy manually, or accept a capped audit
  for those pages. Never quietly score a hollow page.
- **Every page is at render risk** — on a raw run, re-run fetch with `"render": true` (see the
  homepage gate in Step 2). On a rendered run, stop: the site is still empty in a real browser
  (login wall, bot blocking, very late loading). Say so and offer manual copy.

---

## Step 5 -- Analyse

Read `references/heuristics.md` and `references/page-roles.md` in full before starting.

For each page in the fetch output:

1. Read `structure.text_sample`, `structure.h1`, and `ctas.items[].text` as **words**, not as
   data. The numbers locate the problem; the copy is the problem.
2. Score each of the six dimensions 0-100 against the rubric.
3. Write findings. Every one needs `dimension`, `stage`, `severity`, `evidence`, `finding`,
   `fix`. Severity comes from the model in `heuristics.md` — base weight × stage multiplier —
   not from how strongly you feel about it.
4. Apply the overrides: no analytics anywhere → critical; conversion page with no form, no
   phone/email and no booking or form embed (`embeds.booking` / `embeds.form`) → critical; no
   viewport → critical; anything on a `render_risk` page → capped at medium. When an embed is
   how a page converts, name the provider and say its inside couldn't be checked.

Then, across pages:

5. Trace the path. Follow `ctas.items[].href` from entry toward the primary conversion. Note
   where it breaks, loops, or leaves the domain.
6. Check message match between each CTA's text and the H1 of the page it lands on.
7. Check stage coverage against `page-roles.md` and raise the stage-gap findings. **Report
   these first** — they outrank any single-page finding.
8. Compute page scores and the weighted site score.

Discipline:
- No finding without evidence. Anything you believe but cannot evidence becomes a test
  backlog hypothesis instead.
- No percentage lifts. Nothing here has been tested.
- Do not pad. Six real findings beat twenty restatements of the same one.
- Name the page and quote the words. "The CTA is weak" is not a finding; "the only body CTA
  on /pricing reads 'Submit'" is.

---

## Step 6 -- Write the report

Follow `references/report-template.md` exactly. Fill placeholders, drop sections whose module
is off, delete every instruction comment.

On a rendered run (`"rendered": true` in the pages JSON), "What this audit could not see" says the
pages were loaded in a browser before reading, and names any booking or form tool embedded from
another site (`embeds.*_providers`) whose inside could not be checked.

Save as `[report_dir]/[client-domain]_cro_[YYYY-MM-DD].md`.

**The report is written for the client, not for you.** No internal vocabulary reaches it. If
a term only makes sense to someone who has read `heuristics.md`, it does not ship:

| Never write | Write instead |
|---|---|
| "D5 Relevance", "D2 Action" | Clarity · Next step · Effort asked · Proof & trust · Continuity · Speed & mobile |
| "render_risk is true" | "I couldn't read this page fully -- it's built in JavaScript" |
| "`ctas.body_total` = 1" | "one call-to-action in the body of the page" |
| "`trust.social_proof` = 0" | "no proof of any kind on the page" |
| "stage-multiplier-weighted mean" | "pages closest to the sale count for more" |
| "ICE 7.3" alone | Keep the number, add one line saying what Impact / Confidence / Ease mean |

Keep the readiness score, the severity labels and the ranked test list -- the numbers are what
make it a report rather than an opinion. Keep every evidence quote **verbatim**: quoting the
site's own words back is what makes the findings impossible to argue with, and it is already
plain English.

Write for the reader chosen in Q4:
- **exec** — lead with the money and the decision. Keep per-page detail short; the funnel
  section and the top three fixes carry the report.
- **manager** — keep the mechanism. The friction inventory and test backlog are the
  deliverable; they should be actionable without reading the prose.

---

## Step 7 -- Deliver

```
Conversion audit complete.

Report:   [report_path]
Evidence: [pages_json_path]

  Readiness: [score]/100 -- [band]
  [n] pages audited across [n] stages ([n] of [n] discovered URLs)
  [n] critical, [n] high, [n] medium, [n] low
  Biggest gap: [the one-line headline finding]
  Top fix: [the #1 action]
```

Then offer follow-ups via AskUserQuestion (multiSelect), header "Go deeper?", question
"Want me to take any of these further?".

Pick 3-5 that actually fire against this report's findings, ordered strongest signal first,
and always append "No thanks -- the report is enough".

| Offer | Fires when | Action |
|---|---|---|
| "Rewrite the copy on {worst_page} — headline, subhead and CTA, three variants each" | Any clarity or action finding rated high+ | Write it inline, grounded in the extracted copy |
| "Redesign the {page} form — the shortest version that still lets you act" | A lead form with >5 fields or unlabelled fields | Field-by-field keep/cut/merge with reasons |
| "Map the full path from every entry point to {primary_conversion}" | Path break or orphan stage found | Re-run discover, widen to all entry candidates |
| "Draft the {missing_stage} page that isn't there" | A stage-gap finding | Outline: sections, proof needed, CTA |
| "Turn the backlog into a 90-day test plan, sequenced" | test_backlog module ran | Sequence by ICE and dependency |
| "Set up the measurement this site is missing" | `stack.has_analytics` false anywhere | What to install and which events to define |
| "Audit a competitor's funnel the same way, side by side" | Always available | Re-run this skill on their domain, compare |
| "Check whether the traffic problem is upstream of conversion" | Always available | → Run the `seo-visibility-report` skill |

---

## Error Handling

| Situation | Do this |
|---|---|
| Homepage fetch fails (discover exits 2, `homepage.failed`) | Stop before Q2. Report the status verbatim. A 5xx on every path means the site is down -- say so. A 403 may be Cloudflare or geo-blocking -- check the domain with the user. |
| Homepage looks client-rendered (`homepage.render_risk`) | Stop before Q2. See the homepage gate in Step 2. |
| `robots.txt` disallows crawling | Tell the user, and ask before fetching anyway. Their own site is their call; a competitor's is not. |
| Sitemap missing | Fine. Discovery falls back to homepage links. Note the reduced coverage in the report. |
| Some pages 404 | Audit the rest. List the failures. A 404 on a linked conversion page is itself a critical finding. |
| Every page at render risk | Stop before analysing. See Step 4. |
| The user asks for real conversion rates | Say plainly that no analytics is connected and this audit cannot measure them. Offer the measurement follow-up. |
| The user asks for a PDF | The report is markdown by design. Offer to convert it if they have a converter, but do not add a PDF dependency to this skill. |

---

## Appendix -- Config schema (`[client-domain]_cro_config.json`)

```json
{
  "site": "https://example.com",
  "client_domain": "example.com",
  "report_dir": "example-report",
  "client_name": "Example Ltd",
  "business_model": "lead_gen",
  "primary_conversion": "request a quote",
  "reader": "exec",
  "enabled_modules": [
    "funnel_map", "page_audits", "friction_inventory",
    "trust_credibility", "form_analysis", "test_backlog"
  ],
  "last_run": "2026-09-12"
}
```

On a re-run, keep the same page list where the URLs still resolve so scores are comparable,
and report what changed since `last_run`.
