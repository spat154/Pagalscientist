# Start here (next session)

This project is the **Made in India Magazine content engine** plus research
docs. Work happens on branch `claude/india-news-automation-qpcfcy` (PR #1).

## The one blocker that needs a fresh session

Connecting to the live WordPress site (`madeinindiamagazine.com.au`) is blocked
by the environment's **network egress allowlist**. A running session does NOT
pick up allowlist changes — they only load when a session starts. If you're
reading this in a session opened *after* the host was added to the allowlist,
run the access check below; it should now work.

## First action: verify site access (read-only)

Set these as environment secrets (not committed):
`WP_BASE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` (an Editor-scoped Application
Password), and `ANTHROPIC_API_KEY` (for real article generation).

Then:

```bash
pip install -r requirements.txt
python3 scripts/wp_check.py
```

- If it lists recent posts → access works. Proceed.
- If it says "Host not in allowlist" → the allowlist still isn't loaded;
  the host must be added to THIS environment and a new session started.

## What's already built

- Full content engine: ingest → cluster → verify → write → SEO → social,
  staged as drafts for approval. AU English + banned-words/em-dash linter +
  3-references-per-quote/date rule + RankMath SEO + JSON-LD schema + FAQ (AEO).
- `commission` flow: create an article from supplied sources + a direction.
- WordPress publisher posts drafts via REST (embeds FAQ + JSON-LD).
- 30 passing tests (`python -m pytest`).

## Research docs (in `docs/`)

- `competitor-analysis.md` — five Australian competitors, where to compete.
- `content-calendar.md` — pillar-mapped plan to Nov 2026 (verified dates).
- `seo-aeo-audit.md` — live crawl findings + AEO gaps.

## Recommended first work once connected

1. Read-only audit of installed plugins (ask the user to paste the list; the
   Editor key can't enumerate plugins) for the LiteSpeed + de-dupe cleanup plan.
2. Commission flagship drafts (highest-confidence ranking wins):
   - Sydney Hindu temple hub
   - Melbourne Hindu temple hub
   - "Best Indian food trucks in Australia" (rebuild of the page ranking #49)
   All staged as WordPress drafts for human approval before publishing.

## Guardrails to honour

- Never publish without human approval; stage as draft.
- No invented facts/dates; 3 references per quote/date; label unverified.
- Editor-scoped access only does content/SEO — plugin/theme/server work is for
  the host/developer on the Acronis-backed staging copy.
