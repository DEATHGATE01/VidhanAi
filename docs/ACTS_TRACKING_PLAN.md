# Acts Tracking & Bill → Act Lifecycle — Implementation Plan

Status: PLAN (ready to execute) · Author: hermes-session 2026-09-29 · Owner: overnight CTO loop

## 1. The review point (why this matters)

Reviewer feedback: *"Why are you not tracking the Acts too? The Bill is not the law — it is
the Act that is the law. Track Acts and link them to Bills so the lifecycle is visible."*

Correct, and the repo currently proves the gap rather than closing it:

- The only public objects in the product are **Bills**. There is no Act entity, no Act
  scraper, no Act page, no Bill→Act relationship (`grep -n "class .*Act" backend/models.py`
  → nothing).
- The bill "timeline" in `backend/routes.py:262-327` is **fabricated**: for a bill whose PRS
  status contains "passed" it invents an event dated `introduction_date + 30 days`
  (`routes.py:283-294`), and for withdrawn/lapsed states it stamps `datetime.utcnow()`.
  Those dates are not from any source. This is exactly the reviewer's complaint: the
  lifecycle is asserted, not tracked.
- PRS India — our data source — does publish Acts (`https://prsindia.org/acts/parliament`,
  verified HTTP 200, 549 Act PDF rows) and does publish the real per-bill status dates
  (Introduced / Passed Lok Sabha / Passed Rajya Sabha, each with a date). We are simply not
  collecting either.

Deliverable of this plan: Bills and Acts as first-class, linked objects with a merged,
**sourced** lifecycle; every date traceable to PRS HTML or left NULL.

## 2. Verified reconnaissance (measured 2026-09-29, do not re-guess)

All of the following was confirmed by real HTTP fetches with a browser User-Agent from this
machine. Selectors are exact.

**Acts listing** — `GET https://prsindia.org/acts/parliament` → 200, 549 `div.views-row`:
```html
<div class="views-row">
  <div class="views-field views-field-title-field">
    <div class="field-content row">
      <div class="col-1 pr-0"><img src="/images/pdf-smls.png" class="pdf-logo" /></div>
      <div class="col-11 pl-0" class="file">
        <a href="/files/bills_acts/acts_parliament/2026/Industrial_Relations_Code_(A)_Act_2026.pdf"
           title="The Industrial Relations Code (Amendment) Act, 2026" data-pjax="0">The Industrial Relations Code (Amendment) Act, 2026</a>
      </div>
    </div>
  </div>
</div>
```
- Act name = `<a>` `title` attribute (fallback: link text). Year = the path segment after
  `/acts_parliament/`. PDF URL = href, prefix `https://prsindia.org` when relative.
- A pager exists (`?page=N`) but `?page=1` returned the same 550 title nodes as page 0 —
  **the scraper must detect the pager, follow pages, and dedupe by PDF href**; do not assume
  one page, do not assume pagination works.
- PRS has **no per-Act detail page**: Acts are PDFs only. So Act metadata beyond
  name/year/PDF is enrichment, not baseline.

**Bills listing** — `GET https://prsindia.org/billtrack/category/billtrack` → 200, 975 rows.
`https://prsindia.org/billtrack/parliament` → **404** (do not use it); `https://prsindia.org/billtrack`
(root) serves a near-empty shell.
```html
<div class="views-row">
  <div class="views-field views-field-title-field"><span class="field-content">
    <h3 class="cate"><a href="/billtrack/the-tribunals-reforms-bill-2026">The Tribunals Reforms Bill, 2026</a></h3>
  </span></div>
  <div class="views-field views-field-field-bill-status">
    <span class="status-pending">Rules</span>
  </div>
</div>
```
Observed status vocabulary: `Passed`, `Pending`, `Lapsed`, `Withdrawn`, `Negatived`, `Rules`,
`Replaced by an Act`, `Ordinance: In force`, `In Committee`, `Model Act`,
`Introduced - Infructuous`, `Draft`, `Report`, `Repromulgated`.
`Replaced by an Act` and `Passed` are the two statuses that imply an Act exists.

**Bill detail** — `GET https://prsindia.org/billtrack/<slug>` → 200. Fields:
- Ministry: `div.field-name-field-ministry div.field-item` (e.g. `Mines`).
- Real status timeline — one `div.entity.field-collection-item.field-collection-item-field-own-status-details`
  per event, inside `div.flexslider ul.bp-link-slides li`, containing:
  - `div.field-name-field-own-status div.field-item` → state, e.g. `Introduced`, `Passed`
  - `div.field-name-field-own-status-title div.field-item` → house, e.g. `Lok Sabha`, `Rajya Sabha`
  - `div.field-name-field-own-status-date .date-display-single` → e.g. `Aug 13, 2026`
- Bill text PDF: `../files/bills_acts/bills_parliament/<year>/<Slug>.pdf`.
- Body text `div.field-name-body` sometimes names the resulting Act in prose (usable, weak signal).

**No bill→act hyperlink exists on PRS.** The relationship must be derived. That is why the
schema below carries `match_method`, `match_confidence`, `evidence`, `verified` — a guess must
be visibly a guess.

**India Code (indiacode.nic.in)** — `GET https://www.indiacode.nic.in/...` timed out
(curl HTTP 000, 30s) from this machine. India Code is the authoritative source for
**Act Number** and **assent/Gazette date** (`No. 12 of 2026`, "Assented to on ..."). Treat it
as **optional P2 enrichment** with a browser fallback; if unreachable, `act_number` and
`assent_date` stay NULL with a recorded reason. **Never invent them.**

## 3. Data model (backend/models.py — additive, no destructive change)

Three new tables. Existing `bills`, `bill_versions`, `amendment_service` are untouched.

```python
class Act(db.Model):
    __tablename__ = 'acts'
    id              = Integer, pk
    act_id          = String(200), unique, index      # slug from PRS PDF path
    title           = String(500), index              # "The Tribunals Reforms Act, 2026"
    short_title     = String(300)                     # normalized, no leading "The"/year
    year            = Integer, index                  # from PDF path segment
    act_number      = String(50), nullable            # "No. 12 of 2026" — only if sourced
    assent_date     = DateTime, nullable              # only if sourced
    commencement_date = DateTime, nullable            # only if sourced
    status          = String(50), default 'unknown'   # in_force | repealed | spent | unknown
    source          = String(50)                      # 'prs_acts' | 'indiacode'
    source_url      = String(500)
    pdf_url         = String(500)
    full_text       = Text, nullable
    date_scraped    = DateTime
    last_updated    = DateTime

class BillActLink(db.Model):
    __tablename__ = 'bill_act_links'
    id               = Integer, pk
    bill_id          = FK bills.id, index, not null
    act_id           = FK acts.id, index, not null
    link_type        = String(50)     # enacted_as | replaced_by_act | amended_by_act | repealed_by
    match_method     = String(50)     # prs_status | title_match | body_mention | manual
    match_confidence = Float          # 0..1
    evidence         = Text           # the exact scraped string / URL that justifies the link
    verified         = Boolean, default False
    created_at       = DateTime
    UniqueConstraint(bill_id, act_id, link_type)

class LifecycleEvent(db.Model):
    __tablename__ = 'lifecycle_events'
    id          = Integer, pk
    bill_id     = FK bills.id, nullable, index
    act_id      = FK acts.id,  nullable, index
    event_type  = String(50)   # introduced | referred_to_committee | committee_report |
                               # passed_lok_sabha | passed_rajya_sabha | passed_both_houses |
                               # president_assent | act_notified | commencement | amendment | repeal
    event_date  = DateTime, nullable   # NULL when the source does not state one
    house       = String(50), nullable
    source      = String(50)   # prs_billtrack | prs_acts | indiacode | manual
    source_url  = String(500)
    notes       = Text
    is_estimated= Boolean, default False   # must be False for everything this work creates
    extracted_at= DateTime
    UniqueConstraint(bill_id, act_id, event_type, event_date)
```

Rule enforced by review: **`is_estimated=False` implies `source` and `source_url` are set.**
The UI must render an explicit "estimated" badge when `is_estimated=True`, and there must be
no new estimated rows.

## 4. Scraper (new file: `backend/src/scraping/prs_acts_scraper.py`)

`class PRSActsScraper` mirroring `PRSBillTrackScraper` (same session/UA/timeout conventions):

- `fetch_acts_list(house='parliament', max_items=None)` — walk the pager on
  `/acts/parliament`, parse `div.views-row` per §2, dedupe by PDF href, return
  `[{title, year, pdf_url, act_id, source_url}]`. `act_id` = slugified PDF basename
  (stable, unique, re-scrapable).
- `fetch_bill_status_timeline(bill_url)` — return the **real** events list
  `[{event_type, house, date}]` from the status collection blocks (§2). Map
  state+house → `event_type`: `Introduced`+house → `introduced`;
  `Passed`+`Lok Sabha` → `passed_lok_sabha`; `Passed`+`Rajya Sabha` → `passed_rajya_sabha`;
  `Referred to Committee`/`In Committee` → `referred_to_committee`. Unknown state → keep the
  raw label in `notes` with `event_type='other'`, never guess a date.
- `fetch_act_number_from_pdf(pdf_url)` — **optional, P2**: pypdf/pdfplumber first page for
  `No. X of YYYY` and `Assented to`. If the library is missing, return
  `{'act_number': None, 'assent_date': None, 'reason': 'no pdf parser'}` and move on —
  do not fall back to regex on the filename.

Add `PRSBillTrackScraper.fetch_bill_status_timeline` as an alias/delegate so both entry
points share one implementation.

## 5. Linker (new file: `backend/services/act_linker.py`)

Deterministic, explainable, no LLM:

1. `normalize(title)`: lowercase; strip leading `the`; strip all punctuation; drop the trailing
   year; map the head noun `bill` ↔ `act`; collapse `(amendment)`/`(amendment) act`/`(a)` to a
   single token; strip whitespace. `The Industrial Relations Code (Amendment) Bill, 2026` and
   `The Industrial Relations Code (Amendment) Act, 2026` must normalize equal.
2. Candidate generation:
   - bills whose PRS `status` ∈ {`Passed`, `Replaced by an Act`} (strong class),
   - acts from `acts` with `year ∈ {bill_year, bill_year+1}`,
   - all pairs whose normalized titles are equal, or whose normalized *base* titles
     (amendment markers removed) are equal.
3. Scoring (0..1): exact normalized equality `.95`; base-title equality `.70`; `+0.05` same
   ministry string; `+0.05` PRS status is `Passed`/`Replaced by an Act`; `−0.15` conflicting
   year. Clamp to 1.0.
4. Write policy: `≥0.90` → `verified=True`, `match_method='title_match'`;
   `0.60–0.90` → `verified=False` with `evidence` = both titles + source URLs;
   `<0.60` → **no row written** (a missing link beats a wrong link).
5. `evidence` must always quote the actual scraped text; `verified=True` is only ever set for
   an exact normalized match or a direct PRS status derivation.
6. Idempotent: upsert on `(bill_id, act_id, link_type)`; re-running changes nothing.

## 6. Sync script (`backend/scripts/setup/sync_acts.py`)

Follows `fetch_all_bill_data.py` conventions (`argparse`, `create_app()`, batching, `--delay`
between requests, progress prints, idempotent):

```
python backend/scripts/setup/sync_acts.py --limit 50            # acts + timeline + links
python backend/scripts/setup/sync_acts.py --bills-only          # refresh status timelines
python backend/scripts/setup/sync_acts.py --dry-run             # print, write nothing
```

Steps: (1) upsert Acts from PRS; (2) for every bill, fetch its status timeline and upsert
`LifecycleEvent` rows with real dates; (3) run the linker; (4) print a summary —
`acts: N new / M total · timeline events: N · links: N verified / N candidate`.

## 7. API (backend/routes.py — envelope `{success, ...}` / `{error}` per CLAUDE.md §7)

| Method | Route | Behaviour |
|---|---|---|
| GET | `/api/acts` | list, filters `q`, `year`, `status`, `page`, `per_page` |
| GET | `/api/acts/<act_id>` | act + its linked bills + its lifecycle events |
| GET | `/api/bills/<bill_id>/lifecycle` | merged, **sourced** timeline: PRS status events + Act chain (enacted as → assent if known → commencement if known); every event carries `source`, `source_url`, `is_estimated` |
| GET | `/api/bills/<bill_id>` | add an `act` block (`{title, act_id, year, pdf_url, verified}`) when linked |
| POST | `/api/admin/sync-acts` | trigger the sync (same shape as `/api/admin/index-all-bills`) |
| GET | `/api/analytics/lifecycle-stats` | bill→act conversion counts by year and ministry (real counts only) |

**Delete the fabrication** at `routes.py:283-294` (and the `utcnow()` stamps at 300-322):
`/api/bills/<bill_id>` must emit lifecycle events only from `LifecycleEvent` rows, or none.
`grep -n "timedelta(days=30)" backend/routes.py` must return nothing when done.

## 8. Frontend (frontend_new/ — React 19 + Vite, existing `.container/.page-title/.btn` classes, CSS vars from `index.css`)

- `src/pages/ActsPage.jsx` → route `/acts`: filter bar (search, year, status) + Act rows
  (title, year, Act No. when known else "—", PDF link, linked-bill count). Monospace for
  identifiers (`var(--font-mono)` if present, else a mono stack).
- `src/pages/ActDetailPage.jsx` → route `/acts/:actId`: Act header, PDF link, the bill(s) it
  came from, and the shared lifecycle timeline.
- `src/components/LifecycleTimeline.jsx`: shared component rendering `LifecycleEvent`s —
  real dates, per-event source link, an explicit `estimated` badge when `is_estimated`;
  states with no date render as undated milestones, never as a made-up date.
- `src/pages/ExplorePage.jsx` + `src/components/BillCard.jsx`: an "Enacted as: <Act>" chip
  linking to `/acts/:actId` when the bill has a verified link.
- `src/services/api.js`: add `getActs`, `getActById`, `getBillLifecycle`, `syncActs` following
  the existing function style.
- `src/App.jsx` + `src/components/Sidebar.jsx`: add the `/acts` route and nav entry.

## 9. Migration / backfill

- New tables are created by `db.create_all()` (the app and `init_db.py` already do this) —
  no destructive `drop_all` run against the live DB.
- Add `backend/scripts/maintenance/migrate_acts_tables.py`: idempotent `create_all` for just
  the three new tables, following `add_bill_status_column.py` conventions.
- Then `sync_acts.py --limit 50` for a real, reviewable slice (fast, bounded, demonstrable).

## 10. Acceptance criteria (all must be provable with pasted output)

1. `python -m py_compile` clean on every changed `.py` file.
2. `python backend/scripts/setup/sync_acts.py --limit 50` runs against the live DB and reports
   `acts: ≥1`, `timeline events: ≥1`, `links: ≥1`.
3. `GET /api/acts` (Flask on :5000) returns `{success: true}` with a non-empty list;
   `GET /api/acts/<act_id>` returns a linked bill for a known enactment.
4. `GET /api/bills/<bill_id>/lifecycle` for ≥5 bills with PRS status `Passed` /
   `Replaced by an Act` returns events whose dates match that bill's PRS page, each with
   `source` + `source_url`; **zero** returned events have `is_estimated=true`.
5. `grep -rn "timedelta(days=30)" backend/` returns nothing.
6. `cd frontend_new && npm run build` passes; `/acts` renders Act rows (a browser check of the
   dev server is welcome but the build passing is the gate).
7. `python backend/scripts/verify_acts.py` prints `PASS` for checks 1–5, and its output is
   pasted into the report.

## 11. Phasing (one pass per phase; stop early if a phase is blocked)

- **P0 — data spine:** models + `PRSActsScraper` + `act_linker` + `sync_acts.py` +
  `migrate_acts_tables.py` + `verify_acts.py` + routes (`/api/acts`, `/api/acts/<id>`,
  `/api/bills/<id>/lifecycle`, removal of the fake timeline).
- **P1 — UI:** `ActsPage`, `ActDetailPage`, `LifecycleTimeline`, BillCard chip, router/sidebar,
  `api.js`.
- **P2 — enrichment (optional):** India Code act number/assent date via browser fallback;
  state-legislature Acts (`/acts/states`); `lifecycle-stats` analytics.

## 12. Risks / honest limits

- PRS does not link Bills to Acts → link quality is bounded by title matching. Mitigation:
  confidence + evidence columns, `verified` only on exact matches, no row below 0.60.
- Assent and commencement dates are **not on PRS bill pages** and India Code was unreachable
  from this machine. Those fields stay NULL rather than being estimated. If a later phase
  cannot source them, say so in the report — do not fill them in.
- Acts page paging behaviour is unverified beyond page 0; the scraper dedupes by href and
  stops when a page adds nothing new.
- Scraping volume: keep `--delay ≥ 0.5s` and bounded `--limit` runs; PRS is a small NGO site.

## 13. Definition of done

Criteria 1–7 green with evidence in `docs/cto-report-acts.md`, a reflective paragraph written
into the report on *what the lifecycle now proves that it did not before*, and a closing
SESSION_LOG.md entry. Then `touch .cto-stop` and stop — do not invent P3 work.
