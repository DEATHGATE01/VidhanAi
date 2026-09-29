"""
PRS India Acts Scraper
======================
Scrapes the PRS India Acts listing (https://prsindia.org/acts/parliament) and
per-bill status timelines from PRS BillTrack detail pages.

Conventions mirror PRSBillTrackScraper (same session / UA / timeout style).
Reconnaissance (verified 2026-09-29 by real HTTP fetch):

- Acts listing: ``div.views-row`` -> ``div.views-field-title-field a`` with a
  ``title`` attribute; the PDF lives under
  ``/files/bills_acts/acts_parliament/<year>/<File>.pdf``. A pager exists
  (``?page=N``) but may repeat content; pages are deduped by PDF href and the
  walk stops when a page adds nothing new.
- PRS has no per-Act detail page: Acts are PDFs only.
- Bill detail status timeline: one
  ``div.field-collection-item-field-own-status-details`` block per event,
  containing ``field-own-status`` (state), ``field-own-status-title`` (house)
  and ``field-own-status-date`` (``.date-display-single``, e.g. ``Aug 13, 2026``).
"""
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Local import so the module works both as a package and standalone.
try:
    from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper
except ImportError:  # pragma: no cover - only matters when run standalone
    from prs_billtrack_scraper import PRSBillTrackScraper


class PRSActsScraper:
    """Scraper for PRS India Acts and BillTrack status timelines."""

    # States that map to a lifecycle event_type; anything else keeps its raw
    # label in `notes` with event_type='other' -- never guessed.
    STATE_EVENT_MAP = {
        'introduced': 'introduced',
        'passed': None,  # resolved with the house (passed_lok_sabha / passed_rajya_sabha)
        'referred to committee': 'referred_to_committee',
        'in committee': 'referred_to_committee',
        'committee report': 'committee_report',
        'withdrawn': 'withdrawn',
        'negatived': 'negatived',
        'lapsed': 'lapsed',
    }

    def __init__(self):
        self.base_url = "https://prsindia.org"
        self.acts_url = f"{self.base_url}/acts/parliament"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        })

    # ------------------------------------------------------------------ #
    # Acts listing
    # ------------------------------------------------------------------ #

    def fetch_acts_list(self, house='parliament', max_items=None, max_pages=30,
                        delay=0.5):
        """Walk the pager on /acts/<house> and return deduped Act entries.

        Returns a list of dicts: {title, year, pdf_url, act_id, source_url}.
        act_id is the slugified PDF basename (stable, unique, re-scrapable).
        Pages are deduped by PDF href; the walk stops when a page adds no new
        hrefs, so a repeating pager cannot create duplicates.
        """
        try:
            list_url = f"{self.base_url}/acts/{house}"
            acts = {}
            page = 0
            pages_fetched = 0

            while page < max_pages:
                url = f"{list_url}?page={page}" if page else list_url
                print(f"Fetching acts page {page}: {url}")
                response = self.session.get(url, timeout=30)
                if response.status_code == 403 or response.status_code == 429:
                    print(f"WARNING: PRS returned {response.status_code} on page {page}; stopping pager walk.")
                    break
                response.raise_for_status()

                new_on_page = self._parse_acts_page(response.content, acts)
                pages_fetched += 1

                if new_on_page == 0:
                    print(f"Page {page} added no new acts; stopping pager walk.")
                    break

                if max_items and len(acts) >= max_items:
                    print(f"Reached max_items={max_items}; stopping pager walk.")
                    break

                page += 1
                if delay:
                    time.sleep(delay)

            items = list(acts.values())
            if max_items:
                items = items[:max_items]
            print(f"Successfully fetched {len(items)} acts across {pages_fetched} page(s)")
            return items

        except Exception as e:
            print(f"Error fetching acts list: {e}")
            return []

    def _parse_acts_page(self, content, acts):
        """Parse one acts-listing page into `acts` (keyed by PDF href).

        Returns the number of NEW hrefs added by this page.
        """
        soup = BeautifulSoup(content, 'html.parser')
        bill_rows = soup.find_all('div', class_='views-row')
        added = 0

        for row in bill_rows:
            try:
                title_field = row.find('div', class_='views-field-title-field')
                if not title_field:
                    continue
                title_link = title_field.find('a')
                if not title_link:
                    continue

                href = title_link.get('href', '')
                # Only PDF rows under /files/bills_acts/ are Act entries.
                if not href or '/files/bills_acts/' not in href or '.pdf' not in href.lower():
                    continue

                if href in acts:
                    continue  # dedupe by PDF href
                added += 1

                title = title_link.get('title') or title_link.get_text(strip=True)
                year_match = re.search(r'/acts_parliament/(\d{4})/', href)
                year = int(year_match.group(1)) if year_match else None
                pdf_url = href if href.startswith('http') else self.base_url + href
                act_id = self._slugify_pdf_basename(pdf_url)

                acts[href] = {
                    'title': title,
                    'year': year,
                    'pdf_url': pdf_url,
                    'act_id': act_id,
                    'source_url': f"{self.base_url}/acts/parliament",
                }
            except Exception as e:
                print(f"Error parsing act row: {e}")
                continue

        return added

    @staticmethod
    def _slugify_pdf_basename(pdf_url):
        """Stable act_id: slugified PDF basename without extension/year.

        e.g. https://prsindia.org/files/bills_acts/acts_parliament/2021/
             The_Tribunals_Reforms_Act_2021.pdf  ->  the-tribunals-reforms-act-2021
        The trailing year is kept in the slug (it is part of the unique
        basename), so re-runs are stable and two different-year files of the
        same Act remain distinct act_ids.
        """
        basename = pdf_url.rstrip('/').split('/')[-1]
        basename = re.sub(r'\.pdf$', '', basename, flags=re.IGNORECASE)
        slug = re.sub(r'[^A-Za-z0-9]+', '-', basename).strip('-').lower()
        return slug or 'unknown-act'

    # ------------------------------------------------------------------ #
    # Bill status timeline
    # ------------------------------------------------------------------ #

    def fetch_bill_status_timeline(self, bill_url):
        """Return the REAL status events from a PRS bill page.

        Returns a list of dicts: {event_type, house, date (datetime|None),
        raw_label}. Only states that map cleanly produce a typed event_type;
        unknown states keep their raw label with event_type='other'. A date is
        returned only when the source states one -- never guessed.
        """
        try:
            if not bill_url:
                return []
            response = self.session.get(bill_url, timeout=30)
            response.raise_for_status()
            return self.parse_bill_status_html(response.content)
        except Exception as e:
            print(f"Error fetching bill status timeline for {bill_url}: {e}")
            return []

    def parse_bill_status_html(self, content):
        """Parse status-collection blocks out of PRS bill page HTML."""
        soup = BeautifulSoup(content, 'html.parser')

        # The plan's strict selector does not match the live markup (the class
        # string is '... field-collection-item-field-own-status-details' on the
        # same element, not 'field-collection-item.' + suffix); match on the
        # shared class token instead. Verified against the live page 2026-09-29.
        blocks = soup.select('div.field-collection-item-field-own-status-details')
        if not blocks:
            # Older fallback used by fetch_bill_content in the bills scraper.
            blocks = soup.find_all('div', class_='entity-field-collection-item')

        events = []
        for block in blocks:
            try:
                state_el = block.select_one('div.field-name-field-own-status div.field-item')
                house_el = block.select_one('div.field-name-field-own-status-title div.field-item')
                date_el = block.select_one('div.field-name-field-own-status-date .date-display-single')

                if not state_el and not date_el:
                    continue

                raw_label = state_el.get_text(strip=True) if state_el else ''
                house = house_el.get_text(strip=True) if house_el else None

                event_date = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    for fmt in ('%b %d, %Y', '%B %d, %Y', '%d %B, %Y', '%d %b, %Y'):
                        try:
                            event_date = datetime.strptime(date_text, fmt)
                            break
                        except ValueError:
                            continue
                    # The source states a date we cannot parse: keep the raw
                    # string as the label rather than inventing a datetime.
                    if event_date is None and date_text:
                        raw_label = (raw_label + ' — ' + date_text).strip(' —')

                state_key = raw_label.lower().strip()
                event_type = self.STATE_EVENT_MAP.get(state_key, 'other')
                if event_type is None:  # 'passed' + house
                    house_lower = (house or '').lower()
                    if 'lok sabha' in house_lower:
                        event_type = 'passed_lok_sabha'
                    elif 'rajya sabha' in house_lower:
                        event_type = 'passed_rajya_sabha'
                    elif 'both' in house_lower:
                        event_type = 'passed_both_houses'
                    else:
                        event_type = 'passed'
                        if not house:
                            house = None

                events.append({
                    'event_type': event_type,
                    'house': house,
                    'date': event_date,
                    'raw_label': raw_label or None,
                })
            except Exception as e:
                print(f"Error parsing status block: {e}")
                continue

        return events

    # ------------------------------------------------------------------ #
    # Optional P2: Act number / assent date from the Act PDF
    # ------------------------------------------------------------------ #

    def fetch_act_number_from_pdf(self, pdf_url):
        """OPTIONAL (P2 enrichment): parse the Act PDF's first page.

        Requires pypdf or pdfplumber; if neither is importable, returns Nones
        with a reason and moves on -- never a regex guess on the filename.
        """
        parser = None
        try:
            import pypdf  # noqa: F401
            parser = 'pypdf'
        except ImportError:
            try:
                import pdfplumber  # noqa: F401
                parser = 'pdfplumber'
            except ImportError:
                return {'act_number': None, 'assent_date': None,
                        'reason': 'no pdf parser'}

        try:
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()
            import io
            first_page_text = ''
            if parser == 'pypdf':
                reader = pypdf.PdfReader(io.BytesIO(response.content))
                if reader.pages:
                    first_page_text = reader.pages[0].extract_text() or ''
            else:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    if pdf.pages:
                        first_page_text = pdf.pages[0].extract_text() or ''

            act_number = None
            assent_date = None
            num_match = re.search(r'No\.\s*(\d+)\s*of\s*((?:19|20)\d{2})', first_page_text)
            if num_match:
                act_number = f"No. {num_match.group(1)} of {num_match.group(2)}"
            assent_match = re.search(r'Assented\s+to\s+on\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', first_page_text)
            if assent_match:
                for fmt in ('%B %d, %Y', '%b %d, %Y'):
                    try:
                        assent_date = datetime.strptime(assent_match.group(1).replace(',', ', '), fmt)
                        break
                    except ValueError:
                        continue
            return {'act_number': act_number, 'assent_date': assent_date,
                    'reason': None if act_number else 'no match on first page'}
        except Exception as e:
            return {'act_number': None, 'assent_date': None, 'reason': str(e)}


class PRSBillTrackScraperWithTimeline(PRSBillTrackScraper):
    """PRSBillTrackScraper variant that also exposes the real status timeline.

    Shares one implementation with PRSActsScraper (single source of truth for
    the timeline selectors), so both entry points return identical events.
    """

    def fetch_bill_status_timeline(self, bill_url):
        return PRSActsScraper.fetch_bill_status_timeline(self, bill_url)

    def parse_bill_status_html(self, content):
        return PRSActsScraper.parse_bill_status_html(self, content)


# Convenience alias so the bills scraper entry point also carries the method
# without changing the original class contract (plan §4).
PRSBillTrackScraper.fetch_bill_status_timeline = (
    lambda self, bill_url: PRSActsScraper.fetch_bill_status_timeline(self, bill_url)
)
PRSBillTrackScraper.parse_bill_status_html = (
    lambda self, content: PRSActsScraper.parse_bill_status_html(self, content)
)
