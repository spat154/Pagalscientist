# Made in India Magazine — content engine

An editorial engine for **Made in India Magazine** (Australia). It **senses**
news relevant to the Indian-Australian community, **verifies** it against the
magazine's strict fact standards, **writes** a finished article in the
magazine's voice (Australian English, hook-first, properly sourced), then
produces the **SEO package** and the **social story post** so a piece is ready
to review and publish.

It does *not* buy a wire from a paid news service. The engine senses the news
itself from free, public feeds and topic queries.

```
ingest  ─►  cluster  ─►  verify  ─►  write  ─►  SEO  ─►  social  ─►  review  ─►  publish
(sense)    (patterns)   (trust)    (step 1)  (step 2) (step 3)    (human)    (one button)
```

A human approves every story before anything goes live.

## Inputs: what you give it

You mostly **tell it to start** — `run` senses the news, decides what is worth
covering, drafts it, and queues it for you. Day to day, the only input it needs
from you is the final approval before publishing.

There are two ways stories enter the engine:

1. **Autonomous** — `run` finds and drafts stories on its own.
2. **Commissioned** — you hand it sources and a direction (the "Create Article"
   function): `commission --sources sources.json --direction "..."`. Use this
   when you already have the material and an angle.

Beyond that, four one-time setup inputs make it *your* magazine's engine:
your **feeds** (`config/sources.yaml`), your **audience + voice**
(`config/settings.yaml` + `config/style_rules.yaml`), your **Claude API key**,
and your **publishing destinations**.

## The three pillars

Every story must clearly serve at least one, and the writer names which:

1. Adds value to **Indians living in Australia**.
2. Adds value to **Australians interested in Indian culture**.
3. **Global news with direct Australian impact**, especially for the diaspora.

## What the brief enforces (mechanically, not just by prompting)

- **Australian English.** US spellings are auto-corrected (`optimized` →
  `optimised`) and any remaining ones are flagged.
- **Banned words and phrases.** The full list from the brief lives in
  `config/style_rules.yaml`; `style.py` flags every occurrence.
- **No em dash** and **no "it's not X, it's Y"** structure.
- **Fact standards.** The writer is instructed never to invent facts and to
  supply **at least 3 reference URLs for every quote and every date**. The
  engine then scans the article and flags any quote/date that is not backed by
  enough references, and surfaces any `I cannot verify…` notes.
- **Hook-first, subheadings, depth** (5–7 lines per person/org/case study), and
  a closing takeaway.

All of this is attached to each story as a `compliance` report so the editor
sees exactly what to fix.

## Step 2 — SEO (`seo.py`)

Produces a focus keyword, secondary keywords, an SEO title, a meta description
and a slug, then runs a **RankMath-style on-page checklist** (focus keyword in
title/intro/slug/meta, title and meta lengths, content length) and scores it
out of 100. Live keyword volumes can be enriched with the SEO MCP tools
(`keyword_metrics`, `serp_analysis`) by the editor.

## Step 3 — social story post (`social.py`)

A scroll-stopping but professional hook + caption (at most 3 lines, the word
"sibling" is banned, house-style applies), plus an approved CTA
("Explore the full story" / "Discover what happened next" /
"Read the full article") and hashtags.

## Answer Engine Optimisation (AEO)

Every draft is built to be *cited* by AI answer engines (Google AI Overviews,
ChatGPT, Perplexity), not just ranked:

- **Answer-first writing** with question-style subheadings.
- An **FAQ block** (3–5 sourced Q&A pairs) on every article.
- **JSON-LD structured data** (`schema.py`): `Organization` + `NewsArticle`
  (+ `FAQPage` when an FAQ exists), embedded on publish. Event-like stories are
  *flagged* for an editor to add a verified date/venue rather than auto-emitting
  invalid `Event` markup.
- Citations from the story's sources are attached to the Article schema to
  strengthen E-E-A-T.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # add your keys (optional for a dry run)

python -m pagalscientist.cli run            # sense → cluster → verify → draft
python -m pagalscientist.cli queue          # what's awaiting review (+ score)
python -m pagalscientist.cli show <id>      # full draft, compliance, SEO, social
python -m pagalscientist.cli package <id>   # run step 2 + step 3
python -m pagalscientist.cli approve <id>
python -m pagalscientist.cli publish <id>   # the "publish everywhere" button
```

Commission a piece from your own material:

```bash
python -m pagalscientist.cli commission \
  --sources sources.json \
  --direction "What the trade deal means for Indian-owned small businesses here"
```

`sources.json` is a list of `{source, title, summary, link, tier}`.

Without `ANTHROPIC_API_KEY`, generation runs in **dry-run**: the pipeline still
senses, clusters, verifies, runs every compliance/SEO/social check and produces
a clearly-labelled placeholder, so the whole flow is demonstrable offline.

## Configuration

- **`config/sources.yaml`** — the feeds (Australia, India, and diaspora/
  intersection queries), each with a trust tier and audience weight.
- **`config/settings.yaml`** — publication, audience persona, the three
  pillars, clustering/verification thresholds, models, SEO and social options.
- **`config/style_rules.yaml`** — Australian-English map, banned words/phrases,
  em-dash and structure bans, hedge-trigger words, approved CTAs, caption rules.
- **`.env`** — `ANTHROPIC_API_KEY`, `WP_*`, `PAGAL_DB`, model overrides.

## Publishing targets

Pluggable (`pagalscientist/publish/`): **`console`** renders to `out/<id>.md`
(default, no credentials); **`wordpress`** posts a draft via the REST API
(set `WP_*`). The publish step fans out to all enabled targets at once. Social
and newsletter adapters are a new file each.

## Tests

```bash
pip install pytest && python -m pytest
```

26 tests cover tokenization, clustering/pattern detection, the verification
scorer, the SQLite store, the house-style linter (banned words, em dash,
AU English, the not-X-its-Y structure), SEO/RankMath checks, social caption
rules, the commission path, and a full offline pipeline run through to publish.

## Project layout

```
config/                 sources.yaml · settings.yaml · style_rules.yaml
pagalscientist/
  ingest.py             sense the news (RSS)
  cluster.py            group related stories + detect patterns
  verify.py             credibility scoring
  llm.py                Claude wrapper (+ deterministic dry-run)
  style.py              Australian-English + banned-content linter
  generate.py           step 1: write the article (+ fact/style checks)
  seo.py                step 2: SEO package (RankMath-aligned)
  schema.py             AEO: JSON-LD structured data (Article/FAQ/Org)
  social.py             step 3: social story post
  publish/              pluggable targets (console, wordpress, ...)
  pipeline.py           ingest → cluster → verify → draft, and commission
  review.py             edit / approve / SEO / social / publish-everywhere
  cli.py                command-line control
  store.py              SQLite persistence
tests/
```

## Roadmap

- LLM-assisted fact-flagging as a second verification signal.
- Real social/newsletter publishers (Instagram, WhatsApp, email).
- Live SEO keyword enrichment wired through the SEO MCP tools.
- A small web review UI on the same store and `review.py` functions.
- Per-story image generation/selection.
