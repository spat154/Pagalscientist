# SEO & AEO Gap Audit — madeinindiamagazine.com.au

_Prepared: 19 June 2026. Sources: live technical crawl (4,974 pages), organic
traffic/keyword estimates, and a PageSpeed/Core Web Vitals audit. Estimates are
directional; confirm against Google Search Console._

## Technical SEO crawl summary

- **Health score:** 80/100 · **Pages crawled:** 4,974 (3,500 OK, 1,407 blocked,
  59 broken, 8 redirected) · **Total issues:** 7,394.
- SSL and XML sitemap checks **passed** — the foundation is sound; it's the
  volume of small on-page issues holding rankings down.

### High-impact issues (fix first)

| Issue | Pages | Why it matters |
|---|---|---|
| Broken internal link anchors | ~3,002 | Wastes link equity, hurts UX and crawl |
| Duplicate meta descriptions | ~2,701 | Google ignores/rewrites them; lost click-through |
| Pages returning 4xx | 55 | Dead ends; crawl waste |
| Thin content (low word count) | 154 | Won't rank; dilutes topical authority |
| Missing H1 heading | 91 | Weakens topic signals (SEO + AEO) |
| Empty meta descriptions | 100 | No snippet control |
| Titles too long | 614 | Truncated in results |
| Titles too short | 602 | Under-optimised |
| Duplicate titles | 8 | Cannibalisation |
| Non-SEO-friendly URLs (`?p=123`) | 45 | Weak relevance signal |

### Already known (from earlier analysis)
- **Toxic backlink profile:** ~145,000 backlinks from only ~528 referring
  domains — audit/disavow candidate.
- **Poor mobile speed:** LCP 8.9s, TTI 27.6s, 764 KB unused JS, 197 KB unused
  CSS. Hurts rankings and UX (Google is mobile-first).
- **Off-brand filler** (pets, "fake person", acid reflux) dilutes authority.
- **Title inconsistency** — mix of Title Case and ALL CAPS; needs a house rule.
- **1,407 "blocked" pages** in the crawl — confirm these are intentionally
  noindexed (tag/pagination) and not accidental.

---

## AEO — what's missing to be cited by AI answer engines

AEO (Answer Engine Optimization) wins citations in Google AI Overviews, ChatGPT,
Perplexity, and voice assistants. The category barely does this, so it is the
biggest leapfrog opportunity. Gaps:

1. **Structured data / schema markup** — the #1 gap. Needed: `Article`,
   `FAQPage`, `HowTo`, `Event` (garba/concerts), `LocalBusiness` (temples,
   restaurants), `Organization`, `BreadcrumbList`. Schema is how AI engines
   parse and quote a page.
2. **Answer-first formatting** — lead each section with a short, extractable
   answer; use **question-style H2s** ("When is Diwali in Australia in 2026?").
3. **FAQ blocks** on every guide — the format AI engines quote most often.
4. **E-E-A-T / author signals** — named authors with bios and credentials, an
   editorial-standards page, and visible publish/updated dates.
5. **Citable, sourced facts** — the brief's 3-references-per-quote/date rule is a
   real advantage; lean into it.
6. **AI-crawler access** — decide in robots.txt whether to allow GPTBot,
   Google-Extended, PerplexityBot, ClaudeBot, OAI-SearchBot. You can't be cited
   by engines you block. Optionally add an `llms.txt`.
7. **Entity clarity & internal linking** — link related pieces (temple hub →
   each temple) so engines map you as the authority on Indian-Australian topics.

---

## Priority roadmap

**Now (content engine handles these per article):** correct titles, unique
meta descriptions, H1s, keyword placement, depth, AU English, 3-reference
sourcing → plus the new **schema + FAQ generation** being added to the engine.

**Developer/host (site-wide):** fix broken links and 4xx, prune/redirect thin
filler, deduplicate meta site-wide, mobile-speed optimisation (LiteSpeed Cache),
backlink audit/disavow, robots.txt AI-crawler policy.

**Editorial standard going forward:** every new piece ships answer-first, with a
FAQ block, author byline, sources, and `Article` + `FAQPage` (+ `Event` where
relevant) JSON-LD.
