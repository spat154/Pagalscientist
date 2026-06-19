# Made in India — News Automation Desk

An editorial pipeline that **senses** relevant news for the *Middle India*
audience, **verifies** it, **drafts** a customized story (with the connecting
angle drawn out), and **stages** it for review so an editor can do the final
pass and hit one button to **publish everywhere**.

It does *not* buy a wire from a paid third-party news service. The desk senses
the news itself from free, public RSS feeds and topic-targeted news queries.

```
ingest  ─►  cluster  ─►  verify  ─►  generate  ─►  review  ─►  publish
(sense)    (patterns)   (trust)     (Claude)     (human)    (one button)
```

A human approves every story before anything goes live. The AI gets it
*ready*; the editor hits the button.

---

## Why it is built this way

| Decision | Choice | Reason |
|---|---|---|
| News sourcing | Free public RSS + Google News RSS queries (`config/sources.yaml`) | No paid wire; we "tap and sense" the news ourselves |
| Audience | "Middle India" persona encoded in `config/settings.yaml` | Every story is rewritten for tier-2/tier-3, value-conscious, bilingual readers |
| Finding angles/patterns | Token-overlap clustering + cross-cluster theme detection | Same story from many sources collapses into one; recurring themes surface as "trending" |
| Verification | Transparent multi-signal score (source tier, corroboration, recency, hype flags) | Routes editor attention; it screens, it does not replace human judgment |
| Drafting | Claude, with a strict "only what sources support" brief | Customized for the audience without inventing facts |
| Publishing | Pluggable targets; staged as **draft** by default | "Have it ready, then hit a button" — WordPress adapter included, more are easy to add |
| Storage | SQLite | Zero-config, makes re-runs idempotent (no duplicate articles/stories) |

The pure logic (clustering, scoring, store, review) uses **only the standard
library**, so the test suite and a deterministic **dry-run mode** work with no
network and no API keys. `feedparser`, `anthropic`, `requests` and `PyYAML`
are imported lazily and only needed for the live integrations.

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your keys (optional for a dry run)

# Sense -> cluster -> verify -> draft. Stories land in the review queue.
python -m pagalscientist.cli run

# See what's waiting, with credibility score + recommendation.
python -m pagalscientist.cli queue

# Read a draft (and its sources + credibility report).
python -m pagalscientist.cli show <story-id>

# Editor tweaks, approves, and publishes everywhere.
python -m pagalscientist.cli edit <story-id> --headline "Better headline"
python -m pagalscientist.cli approve <story-id>
python -m pagalscientist.cli publish <story-id>

# What themes are trending across multiple stories right now?
python -m pagalscientist.cli patterns
```

Without `ANTHROPIC_API_KEY`, generation runs in **dry-run**: the pipeline still
ingests, clusters, verifies and produces a placeholder draft so you can see the
whole flow. Add the key to get real, audience-tuned stories.

---

## Configuration

- **`config/sources.yaml`** — the feeds the desk listens to. Each has a
  `trust_tier` (1 = official/paper-of-record, 3 = aggregator) and an
  `audience_weight` (how strongly it skews to Middle India). Add or remove
  feeds freely.
- **`config/settings.yaml`** — the audience persona, clustering sensitivity,
  verification thresholds, models, and publishing targets.
- **`.env`** — secrets and deployment paths (`ANTHROPIC_API_KEY`, `WP_*`,
  `PAGAL_DB`). Model ids can be overridden with `PAGAL_GENERATION_MODEL` /
  `PAGAL_VERIFY_MODEL`.

---

## Publishing targets

Targets implement a small `Publisher` interface (`pagalscientist/publish/`):

- **`console`** (default) — renders the story to `out/<id>.md` and prints a
  preview. No credentials. Great for review and demos.
- **`wordpress`** — posts to the WordPress REST API as a **draft** (set
  `WP_BASE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`; uses an Application
  Password). Flip `publishing.stage_as_draft: false` to publish live.

Enable targets in `config/settings.yaml` (`publishing.default_targets`) or per
command (`publish <id> --targets console,wordpress`). The publish step fans the
story out to **all** enabled targets at once — that's the "publish everywhere"
button. Adding WhatsApp, Instagram, or a newsletter is a new file in
`publish/`, no pipeline changes.

---

## How verification works (the trust score)

`score_cluster` blends four transparent signals into 0–100:

- **Source trust** (0–40): best source tier in the cluster.
- **Corroboration** (0–35): how many *distinct* sources report it.
- **Recency** (0–25): exponential decay with a configurable half-life.
- **Language penalty**: deductions for sensational/clickbait and
  unverified-claim markers ("viral", "sources say", "allegedly", ...).

It outputs a recommendation — `fast_review`, `review`, or `hold` — and raises
flags (`single_source`, `sensational_language`, ...) so editors know where to
look. Stories below `min_score_to_draft` are never drafted.

---

## Running automatically

`python -m pagalscientist.cli run` is safe to run on a schedule (cron, a
systemd timer, or a GitHub Action). It is idempotent: already-seen articles are
skipped and clusters that already have a story are not re-drafted. New verified
drafts simply accumulate in the review queue for an editor to clear.

---

## Tests

```bash
pip install pytest
python -m pytest
```

The suite covers tokenization, clustering and pattern detection, the
verification scorer, the SQLite store, and a full offline pipeline run through
to publish — all without network access or API keys.

---

## Project layout

```
config/                 sources.yaml + settings.yaml
pagalscientist/
  ingest.py             sense the news (RSS)
  cluster.py            group related stories + detect patterns/angles
  verify.py             credibility scoring
  llm.py                Claude wrapper (+ deterministic dry-run)
  generate.py           draft the India-customized story
  publish/              pluggable targets (console, wordpress, ...)
  pipeline.py           ingest -> cluster -> verify -> draft
  review.py             edit / approve / reject / publish-everywhere
  cli.py                command-line control
  store.py              SQLite persistence
tests/
```

## Roadmap / not yet built

- LLM-assisted fact-flagging as a second verification signal (the hook is
  there: `verify_model` in settings, `LLMClient` ready).
- Real social/newsletter publishers (Instagram, WhatsApp, Brevo email).
- A small web review UI on top of the same store and `review.py` functions.
- Image generation/selection for each story.
