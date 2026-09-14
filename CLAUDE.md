# website-analyzer

A workspace for auditing client websites. No application code — it holds a Claude Code agent
and the skills it uses, plus the reports they produce.

## What's here

```
.claude/agents/cro.md                  The CRO consultant persona
.claude/skills/cro-funnel-report/      Conversion audit -> markdown report
.claude/skills/seo-visibility-report/  SEO visibility audit -> PDF report
```

**Each company gets its own folder, `<company>-report/`, and every file for that company lives
there** — candidates, plan, config, page evidence, the CRO report (`[domain]_cro_[YYYY-MM-DD].md`),
any SEO PDF (`[domain]_SEO_[YYYY-MM].pdf`), and later additions such as Search Console findings,
which go into that company's report rather than a new loose file. Nothing is written to the top
level of this folder.

`<company>` is the domain without `www.` or its ending (`mywelltax.com` → `mywelltax-report/`). If
a folder for that company already exists under another name, reuse it
(`numericosoftware.com` → `numerico-report/`).

## The two skills

| | `cro-funnel-report` | `seo-visibility-report` |
|---|---|---|
| Question | Why don't visitors convert? | Why don't visitors arrive? |
| Data | Live HTML, fetched directly | DataForSEO MCP |
| Cost | **Free** | **Paid per run** |
| Output | Markdown | PDF (reportlab) |

They pair: if a CRO audit finds a healthy funnel, the problem is upstream — hand off to the
SEO skill, and vice versa.

## How a session starts

Opening Claude in this folder means one thing: a site needs analyzing. The first question,
before any preamble, is **"Which domain should I analyze?"** — then the `cro` agent takes it
from there. A bare domain is enough; the tooling normalises and follows redirects.

## Running the CRO audit

Ask for it in plain language ("run a CRO report for example.com") and the `cro` agent picks
up the skill. The skill drives the rest: it interviews you, discovers the funnel, shows you
the page shortlist for confirmation, fetches, scores, and writes the report.

The scripts can also be run on their own:

```bash
cd .claude/skills/cro-funnel-report

# homepage + robots.txt + sitemap.xml only -> candidate URLs with guessed funnel roles
python3 scripts/fetch_pages.py discover https://example.com --out candidates.json

# fetch a confirmed page list -> structured conversion signals
python3 scripts/fetch_pages.py fetch plan.json --out pages.json

# sites built in JavaScript: load pages in local headless Chrome ("render": true in plan.json too)
python3 scripts/fetch_pages.py discover https://example.com --out candidates.json --render

# offline tests, no network, no cost
python3 scripts/tests/test_extract.py     # 67/67 -- signal extraction, embeds and role guessing
python3 scripts/tests/test_pipeline.py    # 44/44 -- discover + fetch against localhost sites: a down site, a JS shell, rendering
```

Stdlib only — no pip install, no API key, nothing metered. `--render` uses the Google Chrome
already on the machine (or `CHROME_PATH`).

## Conventions that matter

- **Confirm the page list before fetching.** The skill never crawls a list the user hasn't seen.
- **Findings cite evidence.** A quote from the page or a signal with its number, or it isn't a
  finding — it's a backlog hypothesis.
- **No promised lifts.** Nothing has been A/B tested; recommendations are evidenced
  hypotheses.
- **Raw HTML by default; Chrome when needed.** JavaScript isn't run unless discovery flags the
  site as client-rendered — then pages are loaded in the local headless Chrome (`--render`,
  free, nothing installed). A page that fails to render is an error, never audited from the
  empty shell.
- **The report is for the client.** Plain language, no internal vocabulary, scores and
  quotes kept. `SKILL.md` Step 6 holds the binding word-for-word mapping.
- **Ask before spending.** The CRO path is free by design. Adding a paid API (PageSpeed,
  DataForSEO, analytics) to it needs the user's go-ahead.

## Source of truth

`seo-visibility-report` is a **copy**. Its canonical version lives in
`~/Projects/my-skills/seo-visibility-report` — edit it there, then re-copy, or the two drift.

`cro-funnel-report` is authored here and has no upstream yet. Promoting it — to `my-skills/`
or to `~/.claude/skills/` for use across projects — is a deliberate next step, not done.
