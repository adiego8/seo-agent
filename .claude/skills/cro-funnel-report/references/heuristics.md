# CRO Heuristics — the scoring rubric

The rubric the analysis step scores every page against. It exists so two runs a month
apart reach the same verdict on the same page, and so a client can ask "why did you say
that?" and get a field name and a quote rather than an opinion.

Field paths below refer to the per-page objects in `pages.json`, produced by
`scripts/fetch_pages.py`.

---

## The prime directive

**Never report a finding without evidence.** Every finding carries:

| Key | Meaning |
|---|---|
| `dimension` | one of the six below |
| `stage` | the funnel stage of the page it was found on |
| `severity` | critical / high / medium / low — from the severity model, not from taste |
| `evidence` | a verbatim quote from the page, or a signal with its number |
| `finding` | what is wrong, in one sentence |
| `fix` | what to change, specifically enough to hand to a developer |

A finding you cannot evidence is a hypothesis. Hypotheses belong in the test backlog, not
in the friction inventory.

---

## D1 — Clarity

*Can a first-time visitor tell what is offered, to whom, and what happens next?*

| Signal | Field | Reads badly when |
|---|---|---|
| H1 states the offer | `structure.h1` | Missing, or a brand slogan with no noun for the product |
| One H1 | `structure.h1_count` | `0` (no anchor) or `>1` (competing claims) |
| Title matches H1 | `head.title` vs `structure.h1` | They describe different things |
| Meta description | `head.meta_description_len` | `0` on an entry page — the SERP snippet is the first impression |
| Copy depth | `structure.word_count` | `<80` on a value or offer page: nothing to persuade with |
| Jargon | `structure.text_sample` | Category terms a buyer would not search for |

Read `structure.text_sample` and judge the actual words. The H1 test is: *does this
sentence survive being read aloud to someone who has never heard of the company?*

## D2 — Action

*Is there one obvious next step, and does it name what happens?*

| Signal | Field | Reads badly when |
|---|---|---|
| A body CTA exists | `ctas.body_total` | `0` — the page is a dead end |
| Competing destinations | `ctas.distinct_destinations` | `>3` on a conversion or offer page |
| Vague wording | `ctas.generic_count` | Any "Submit", "Click here", "Learn more" on offer/conversion |
| Off-site leak | `ctas.items[].external` | A CTA on the conversion path leaves the domain |
| CTA is buried | `ctas.first_body_cta_index` | High relative to page length — nothing actionable early |
| Nav-only CTA | `ctas.nav_total > 0` and `body_total == 0` | The page relies on the header alone |

Strong CTA copy names the outcome ("Get my quote"), not the mechanism ("Submit"). First
person often outperforms second. Say so as a hypothesis, not as fact.

## D3 — Friction

*What does the visitor have to do, and how much of it is unnecessary?*

| Signal | Field | Reads badly when |
|---|---|---|
| Form length | `form_summary.max_fields` | `>5` on a lead form; `>3` for a first-touch enquiry |
| Required ratio | `forms[].required_count / field_count` | Near `1.0` — nothing is optional |
| Unlabelled fields | `forms[].unlabelled_count` | `>0` — placeholder-only labels vanish on focus |
| Field justification | `forms[].fields[].name` | Fields the business cannot act on today (VAT number at first contact) |
| Weak submit | `forms[].submit_text` | "Submit" |
| No form at all | `form_summary.count` | `0` on a page classified `conversion` |
| Contact fallback | `contact.phone`, `contact.email` | Both absent on a conversion page |

Every required field is a reason to leave. The question for each is: *does someone act on
this value within 24 hours of the form arriving?* If not, it is optional or it is gone.

## D4 — Trust

*Is proof present at the moment of decision, and is risk removed?*

| Signal | Field | Reads badly when |
|---|---|---|
| Social proof | `trust.social_proof` | `0` on offer or conversion |
| Risk reversal | `trust.risk_reversal` | `0` where money or commitment is asked for |
| Security cues | `trust.security` | `0` on checkout or a page taking personal data |
| Authority | `trust.authority` | `0` in regulated or high-consideration categories |
| Specific numbers | `proof_claims` | Empty — vague claims with no figures |
| False urgency | `trust.urgency` | High while `social_proof` is `0` — pressure without substance |

Proof is positional. Testimonials on `/about` do not help someone hesitating on
`/pricing`. Score *proof density at the point of decision*, not site-wide.

## D5 — Relevance

*Does each step continue the promise made by the one before?*

Cross-page, so it cannot be scored from a single page object:

- **Message match** — the offer page's H1 against the entry page's H1 and the CTA text that
  leads there. A CTA reading "Start free trial" landing on a page headed "Our Plans" is a
  break.
- **Stage continuity** — walk `entry → value → proof → offer → conversion`. Each hop should
  be reachable by a CTA found on the previous page (`ctas.items[].href`).
- **Orphan pages** — a stage present in the site but unreachable from the funnel.
- **Missing stage** — see `page-roles.md`. Usually the single most valuable finding.

## D6 — Mobile & technical

Conversion friction that happens to be technical. Raw HTML supports only proxies — say so.

| Signal | Field | Reads badly when |
|---|---|---|
| Viewport | `head.has_viewport` | `false` — the page is not mobile-ready at all |
| Blocking scripts | `weight.scripts_head_blocking` | `>2` — delays first paint |
| Third-party weight | `stack.third_party_count` | `>10` |
| HTML weight | `http.html_bytes` | `>500000` before any asset loads |
| Server latency | `http.elapsed_ms` | `>1500` |
| Alt coverage | `media.images_missing_alt` | A large share of `media.images` |
| Measurement | `stack.has_analytics` | `false` — nothing can be tested or proven |

`stack.has_analytics == false` is a **critical process finding** regardless of page: without
measurement no recommendation here can ever be validated. Always report it.

---

## Severity model

Severity is *dimension weight × stage position*. Not taste.

**Stage multiplier** — the closer to the money, the worse the same defect:

| Stage | × |
|---|---|
| conversion | 3.0 |
| offer | 2.5 |
| entry | 2.0 |
| value | 1.5 |
| proof | 1.5 |
| trust / support | 1.0 |
| content | 0.5 |

**Base weight** — D3 Friction 3 · D2 Action 3 · D1 Clarity 2.5 · D4 Trust 2 · D5 Relevance 2 ·
D6 Mobile/technical 1.5.

`score = base × multiplier` → **critical** ≥ 7 · **high** 5–6.9 · **medium** 3–4.9 · **low** < 3.

Overrides, applied after the arithmetic:
- No analytics anywhere → **critical**.
- A conversion page with no form, no phone/email and no booking or form embed
  (`embeds.booking` / `embeds.form`) → **critical**. When an embed is how the page converts,
  name the provider and say its inside couldn't be checked — never score what you can't see.
- No viewport meta → **critical**.
- Anything on a `render_risk` page → cap at **medium**, and say why.

## Readiness score

Per page: start at 100, subtract 15 per critical, 8 per high, 4 per medium, 1 per low,
floor 0.

Site score: take the stage-multiplier-weighted mean of the page scores, **then subtract the
funnel-level findings** (stage gaps, broken paths, message-match breaks) at the same rates.
Those findings belong to no single page, so a weighted mean of page scores alone will read
far too high on a site whose pages are individually fine and whose funnel has a hole in it.
Show both numbers when they diverge.

Bands: **80–100** solid, fix the detail · **60–79** competent, leaking · **40–59** material
problems on the money pages · **0–39** the funnel is broken, not underperforming.

The score orders work. It is not a conversion-rate prediction, and must never be presented
as one.

---

## What raw HTML cannot tell you

State these limits in the report rather than guessing past them:

- **Anything below the fold.** DOM order is not visual position. No layout, no CSS applied.
- **Real conversion rates**, traffic, bounce, or drop-off. No analytics is connected.
- **JS-rendered content.** Never executed. See `render_risk` per page.
- **Actual mobile rendering**, tap-target size, or thumb reach.
- **Page speed as experienced.** `http.elapsed_ms` is server response, not load or LCP.
- **A/B results.** Nothing here has been tested. Every recommendation is a hypothesis with
  evidence behind it — never a promised lift. Do not attach a percentage to an untested change.
