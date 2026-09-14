# Funnel stages — what each page owes

Used twice: to classify discovered URLs into a funnel, and — more valuably — to notice a
stage that **is not there at all**. A missing stage is invisible when auditing pages one at
a time, and is usually the largest finding a funnel audit produces.

The role keys match `ROLE_PATTERNS` in `scripts/fetch_pages.py`. Roles are guessed from URL
and anchor text, then **confirmed by the user** before any audit is built on them.

---

## The path

```
entry  →  value  →  proof  →  offer  →  conversion
              ↖  trust / support feed every stage  ↗
```

Not every business needs all five as separate pages — a single strong landing page can carry
value, proof and offer at once. What matters is that **every job gets done somewhere before
the ask**, not that every job gets its own URL.

---

## `entry` — the arrival page

Usually the homepage; often a campaign landing page.

**Owes:** who this is for and what it does, in the H1 · one primary next step · enough proof
to be credible on first contact · a route to the offer.

**Fails when:** the H1 is a slogan · several equally weighted CTAs · the visitor must
navigate to understand the product.

**Weight ×2.0** — everything downstream depends on it.

## `value` — what it is and why it is better

`/features`, `/services`, `/how-it-works`, `/solutions`.

**Owes:** benefits before mechanics · the objection a competitor raises, answered · a CTA
continuing to offer or conversion.

**Fails when:** feature lists with no outcome · no CTA (a dead end) · written for the
industry rather than the buyer.

**Weight ×1.5**

## `proof` — evidence that it works

`/case-studies`, `/testimonials`, `/reviews`, `/portfolio`, `/customers`.

**Owes:** specifics — names, numbers, before/after · proof resembling the reader's situation ·
a CTA while conviction is high.

**Fails when:** unattributed quotes · logos with no story · proof that exists only here and
never appears at the point of decision.

**Weight ×1.5** — note the cross-page finding when proof is quarantined on this page.

## `offer` — what it costs and what is included

`/pricing`, `/plans`, `/packages`, product and collection pages.

**Owes:** a price, or an honest reason there is not one · clear differences between options ·
objections handled *in situ* — contract length, refunds, what happens after signup ·
risk reversal beside the price · proof beside the price.

**Fails when:** price is hidden behind a form with no justification · options differ in ways
a buyer cannot evaluate · guarantee lives on another page.

**Weight ×2.5** — where intent is highest and doubt is loudest.

## `conversion` — the ask

`/contact`, `/signup`, `/book`, `/checkout`, `/demo`, `/quote`, `/apply`.

**Owes:** the shortest form that still lets the business act · a restatement of what the
visitor gets · what happens next, and when ("we reply within one working day") · security and
privacy cues where personal data is asked for · an alternative channel — phone or email · no
distractions: nav and secondary CTAs should thin out here.

**Fails when:** the form asks for data nobody uses · no expectation is set · no fallback
contact · the page still carries full site navigation competing with the submit button.

**Weight ×3.0** — the most expensive place to be wrong.

## `trust` — the background check

`/about`, `/team`, `/privacy`, `/terms`, `/guarantee`, `/security`.

**Owes:** real people and a real address · policies findable from the conversion page.

**Fails when:** no human presence anywhere · a guarantee that exists but is never mentioned
where money is asked for.

**Weight ×1.0**

## `support` — the objection handler

`/faq`, `/help`, `/docs`.

**Owes:** the questions that actually block a purchase, answered plainly · a route back to
the offer.

**Weight ×1.0**

## `content` — the top of funnel

`/blog`, `/resources`, `/guides`.

**Owes:** a relevant next step toward value or offer. A post with no route into the funnel is
traffic that cannot convert.

**Weight ×0.5** — audit the *pattern* across a sample, not every post.

---

## Stage-gap findings

Report these at the funnel level, above any page-level finding:

| Gap | Typical severity | Why |
|---|---|---|
| No `conversion` page reachable from the funnel | critical | There is no way to buy |
| No `offer` page and price appears nowhere | critical | Price anxiety goes unresolved |
| No `proof` anywhere on the path | high | Claims rest on assertion alone |
| Proof exists but is absent from `offer` and `conversion` | high | Evidence is not where doubt is |
| `value` present but with no CTA onward | high | The funnel stops mid-path |
| No `trust` signals and personal data is collected | high | Nothing earns the disclosure |
| More than 3 stages collapsed onto one page | medium | Judge by whether each job is done |
| `content` with no route into the funnel | medium | Traffic that cannot convert |

## Coverage note for the report

State plainly how many URLs were discovered, how many were audited, and which stages went
unrepresented. A funnel audit of 6 of 400 pages is a funnel audit — but only if it says so.
