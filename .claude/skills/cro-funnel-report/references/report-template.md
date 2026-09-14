# CRO report template

The skeleton every report follows. Fill it in; do not restructure it. Consistency is what lets
a client compare this month's report to last month's, and what stops an audit turning into an
essay.

**Who reads this:** the business owner or the marketer, not you. They have not read the
rubric and will not ask what a word means — they will just trust the report less. Every
section below is already written in the register it should ship in. Match it.

Rules:

- **Every finding cites evidence** — a verbatim quote from the page, or a plain-English count
  ("one call-to-action in the body"). No evidence, no finding; it goes to the test list instead.
- **Quote the site's own words exactly.** That is what makes a finding impossible to argue with.
- **No internal vocabulary.** Not `render_risk`, not `D5 Relevance`, not `ctas.body_total`. The
  mapping table in `SKILL.md` Step 6 is binding.
- **Never state a percentage lift.** Nothing here has been tested.
- Drop any section whose module was not enabled. Do not leave an empty heading.
- Name the strengths too. Inventing problems to look thorough is how audits lose credibility.

Placeholders read `{like_this}`. Delete every instruction line in `<!-- comments -->`.

---

```markdown
# Conversion Audit — {client_name}

**Site:** {site_url}
**What we want visitors to do:** {primary_conversion}
**Date:** {YYYY-MM-DD}

---

## The short version

**Conversion readiness: {score}/100 — {band}**

{Two or three sentences in plain language. What is working, what is costing the most, and
where. Name the page. No hedging, no preamble, no jargon.}

| | |
|---|---|
| Serious problems | {n} |
| Worth fixing | {n} |
| Minor | {n} |
| Missing from the journey | {stage list in plain words, or "nothing"} |

<!-- Severity labels in the report are plain: "Serious" (critical/high), "Worth fixing"
     (medium), "Minor" (low). Use those words in every table below too. -->

### Fix these three first

| # | Fix | Page | Why it matters | Effort |
|---|---|---|---|---|
| 1 | {specific change} | {page} | {the evidence, in one line} | {Small / Medium / Large} |
| 2 | | | | |
| 3 | | | | |

<!-- Ordered by how much they cost, not by how easy they are. If the top fix is hard, say so. -->

---

## What I looked at

<!-- REQUIRED. The same box-drawn table shown before the audit ran. It tells the client this
     was reasoned, not scraped, and it makes the coverage honest. -->

```
┌────────────┬───────────────────────────┬───────────────────────────────────────────────────────┐
│   Stage    │            URL            │                          Why                          │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ entry      │ /                         │ The homepage                                          │
├────────────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ conversion │ /contact                  │ The money page (4 inbound, "Let's work together")     │
└────────────┴───────────────────────────┴───────────────────────────────────────────────────────┘
```

{n_audited} of {n_discovered} pages found on the site. {Which stages had no page at all.}

---

## The journey

<!-- Module: funnel_map. The whole point — do this before any page detail.
     Stage names in the report are plain English, not the internal keys:
     entry = "Arriving" · value = "What you do" · proof = "Proof it works" ·
     offer = "What it costs" · conversion = "Getting in touch" · trust = "Who you are" ·
     support = "Questions" · content = "Articles" -->

| Step | Page | How it's doing | Score | What's missing |
|---|---|---|---|---|
| Arriving | {label} ({url}) | ✅ Working / ⚠️ Partly / ❌ Missing | {n}/100 | {one line} |
| What you do | | | | |
| Proof it works | | | | |
| What it costs | | | | |
| Getting in touch | | | | |

**Gaps in the journey**

{For each gap: what is missing, how serious, and what it costs the business. If nothing is
missing, say so plainly — it is a real strength and worth naming.}

**The path a visitor actually walks:** {Trace it using the real links. Name where it breaks,
loops, or sends someone off the site. Write it as a walk, not as data.}

---

## Page by page

<!-- Module: page_audits. Repeat per page, money pages first. -->

### {label} — {url}
*{Plain stage name} · Score: {n}/100*

> ⚠️ **I couldn't read this page fully.** Most of it is built in JavaScript, which this audit
> doesn't run, so only part of the page was visible to me. The notes below understate it —
> worth a manual look.
> {Delete this block unless the page was flagged.}

| Clarity | Next step | Effort asked | Proof & trust | Continuity | Speed & mobile |
|---|---|---|---|---|---|
| {n} | {n} | {n} | {n} | {n} | {n} |

<!-- Plain names, always. Clarity = is the offer obvious. Next step = is there one clear
     action. Effort asked = how much work the visitor must do. Proof & trust = is there
     evidence. Continuity = does this page keep the promise the last one made.
     Speed & mobile = technical friction. -->

{One paragraph: what this page is trying to do and whether it does it.}

| How serious | Area | What I found | The evidence | What to do |
|---|---|---|---|---|
| Serious | Effort asked | {finding} | "{quote from the page}" | {fix} |

---

## Everything worth fixing

<!-- Module: friction_inventory. The full list, most serious first. -->

| # | How serious | Page | What I found | What to do |
|---|---|---|---|---|
| 1 | Serious | | | |

---

## Proof and credibility

<!-- Module: trust_credibility. Proof WHERE THE DECISION HAPPENS, not site-wide. -->

| Step | Page | Proof on the page | Verdict |
|---|---|---|---|
| What it costs | | {plain description — "none", "two client names, no results"} | {one line} |

**Specific claims found on the site:** {numeric claims, verbatim — or "none"}

{Where proof is missing at the moment someone decides, and which proof the site already has
that could simply be moved there rather than created from scratch.}

---

## Speed and mobile

<!-- Module: mobile_experience. Say plainly that these are indicators, not a full test. -->

| Page | Mobile-ready | Slow-loading scripts | Page size | Server response |
|---|---|---|---|---|
| {label} | ✅/❌ | {n} | {n} KB | {n} ms |

**Measurement:** {What analytics are installed — or, critically, that nothing is. If nothing
is measuring, say that no change to this site can be proven to work until it is.}

---

## Forms

<!-- Module: form_analysis. -->

### {page}

| Fields | Required | Submit button reads |
|---|---|---|
| {n} | {n} | "{text}" |

**What it asks for:** {list in plain words}

**Assessment:** {Shortest set that still lets the business act. For each field to cut, say why
— usually "nobody acts on this within 24 hours". If the form is already good, say that and
leave it alone.}

---

## What to try next

<!-- Module: test_backlog. Explicitly untested ideas, best first. -->

Each idea is scored on three things out of 10 — **Impact** (how much it could move the
needle), **Confidence** (how sure I am, based on what's on the page), and **Ease** (how quickly
it can be done). The final column averages them, so the top row is the best use of your time.

| # | The idea | Page | What to watch | Impact | Confidence | Ease | Score |
|---|---|---|---|---|---|---|---|
| 1 | Because {evidence}, changing {X} should {expected outcome}. | {page} | {metric} | 8 | 7 | 9 | 8.0 |

{If nothing is measuring the site, open this section by saying none of these can be proven
until that is fixed — and that installing measurement is therefore the first job.}

---

## What this audit could not see

Worth knowing, so you can weigh the findings properly:

- **{Raw run: "I read the pages as they arrive, and don't run their JavaScript." Rendered run:
  "Your site is built in JavaScript, so I loaded each page in a browser first and read what a
  visitor sees."}** {Name any page that was still incomplete, or say all pages arrived complete.}
- {Only if a booking or form tool is embedded from another site: "**Your {booking calendar /
  form} comes from {provider}.** I could see it's there, but not test what happens inside it."}
- **No traffic or sales data.** I don't know your conversion rate or where people drop off —
  these findings come from what the pages say and ask, not from measured losses. Nothing here
  claims a percentage improvement.
- **I can't see the design.** Where things sit on the screen, how it looks on a phone, and how
  big the buttons are were not assessed.
- **Server response time was measured; real-world loading speed was not.**
- **{n_audited} of {n_discovered} pages were reviewed.** {Which stages weren't covered.}
```
