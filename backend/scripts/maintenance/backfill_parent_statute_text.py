"""Backfill statute_history.full_text — the parent statute's own text, from India Code.

WHY: the diff screen could compare a Bill with the Act it became, but not an Act with
the statute it amends, so "the 2026 Act vs the 2014 Act it changes" was answered with
an apology. The parent's text is the missing half of the feature.

READING, not guessing. For a parent statute India Code holds:
  - an "ACT" collection record for the principal Act (amendment records are separate),
  - and, attached to it, a text sidecar (``a<year>-<no>.pdf.txt``) that is the whole
    Act in English — 206k characters for the Andhra Pradesh Reorganisation Act, 2014,
    against 800 KB for the PDF it was extracted from.
So the sidecar is preferred over running pdftotext on the PDF: it is the same source's
own text, it is complete rather than the first N pages, and it avoids pulling 19-41 MB
PDFs. The Hindi sidecars (``H2014-06H.pdf.txt``) sit beside the English ones in the
same record, so the text is checked for Devanagari before being accepted.

The principal Act is matched as: collection == ACT, the title carries every significant
word of the parent's name, and the title is NOT an amendment/ordinance/order/repeal —
the same rule the statute-history chain needed, for the same reason (amending records
outnumber and outrank the principal one in India Code's search).

Provenance is written with the text (URL + label + timestamp) because the page claims
"this is the statute, as India Code holds it" and has to be able to show that.

Nothing is written unless real text came back: a failed read is counted and reported,
never stored as an empty string that would later read as "this statute has no text".

Usage:
    python scripts/maintenance/backfill_parent_statute_text.py [--refresh] [--delay 0.8]
                                                              [--limit N] [--keys a,b]
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import StatuteHistory, db  # noqa: E402
from services.statute_history import SOURCE_LABEL, USER_AGENT_FALLBACK  # noqa: E402

API = "https://indiacode.gov.in/server/api"
ITEM_URL = "https://indiacode.gov.in/handle/"

# An amending instrument's title must never be mistaken for the principal Act.
_NOT_PRINCIPAL = re.compile(
    r"amend|ordinance|removal of dif|repeal|second|third|validat|extension|modificat",
    re.I,
)
_STOPWORDS = {"the", "act", "of", "and", "a", "an"}
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")

MAX_TEXT_CHARS = 600_000       # one statute's text; observed maximum is ~206k
MAX_PDF_BYTES = 30 * 1024 * 1024
PDF_MAX_PAGES = 150            # a statute, not just its commencement clause
MIN_TEXT_CHARS = 200           # below this it is not a statute's text
MAX_RECORDS_TRIED = 4          # duplicate records worth trying when a copy is empty/truncated


def _words(value: str):
    """Identifying words, tolerant of singular/plural.

    India Code spells some titles differently from the Act that names them — the
    Indian Institutes of Management Act, 2017 becomes "The Indian Institute of
    Management Act, 2017" — so a plain subset test misses the statute entirely.
    """
    out = set()
    for word in re.findall(r"[a-z]+", (value or "").lower()):
        if word in _STOPWORDS:
            continue
        out.add(word[:-1] if len(word) > 3 and word.endswith("s") else word)
    return out


def _is_devanagari(text: str) -> bool:
    if not text:
        return True
    sample = text[:5000]
    return len(_DEVANAGARI.findall(sample)) / max(len(sample), 1) > 0.2


def _looks_truncated(text: str) -> bool:
    """True when the text stops at the source's own cap.

    India Code's text sidecars are themselves capped: the Central Excise Act, 1944 ends
    at EXACTLY 100,000 characters, mid-word ("...which are wholly ex"), and so does the
    Industrial Relations Code, 2020. A round length in the ten-thousands is that cap's
    signature, and it is the only signal used — an earlier version also flagged any text
    not ending in punctuation, which cried wolf on three statutes that simply end with a
    dash rule or a list of links (RBI, J&K Panchayati Raj, Waqf). Claiming truncation
    where there is none is worse than staying quiet.
    """
    length = len((text or "").rstrip())
    return length >= 10_000 and length % 10_000 == 0


def find_principal_records(session, parent_title: str):
    """Every principal-Act record carrying the parent's name, best first. (list)"""
    want = _words(parent_title)
    if not want:
        return []
    try:
        resp = session.get(
            API + "/discover/search/objects",
            params={"query": f'dc.title:"{parent_title}"', "size": 20},
            timeout=45,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    candidates = []
    for obj in resp.json().get("_embedded", {}).get("searchResult", {}).get("_embedded", {}).get("objects", []):
        item = obj.get("_embedded", {}).get("indexableObject", {})
        md = item.get("metadata", {})
        title = str((md.get("dc.title") or [{}])[0].get("value") or "")
        collection = (md.get("dc.identifier.collection") or [{}])[0].get("value")
        if collection != "ACT" or _NOT_PRINCIPAL.search(title):
            continue
        if want <= _words(title):          # every word of the parent's name is present
            candidates.append({"uuid": item.get("uuid"), "title": title,
                               "handle": item.get("handle")})
    # Most specific title first. Duplicates are kept: India Code often holds the same
    # Act several times and only one copy has the files attached (Registration of
    # Births and Deaths Act, 1969 returns six records; five carry nothing).
    candidates.sort(key=lambda c: len(c["title"]))
    return candidates


def bitstreams(session, uuid: str):
    out = []
    try:
        resp = session.get(f"{API}/core/items/{uuid}/bundles", timeout=60)
        resp.raise_for_status()
        for bundle in resp.json().get("_embedded", {}).get("bundles", []):
            inner = session.get(f"{API}/core/bundles/{bundle['uuid']}/bitstreams", timeout=60)
            inner.raise_for_status()
            for bs in inner.json().get("_embedded", {}).get("bitstreams", []):
                out.append({"name": str(bs.get("name") or ""), "size": bs.get("sizeBytes"),
                            "url": (bs.get("_links") or {}).get("content", {}).get("href")})
    except requests.RequestException:
        return []
    return out


def read_text(session, streams):
    """(text, source_url, note) — the English sidecar if present, else the PDF."""
    sidecars = [s for s in streams if s["name"].lower().endswith(".pdf.txt")]
    # English sidecars are named for the English PDF (a2014-6.pdf.txt); the Hindi set is
    # prefixed H. Name first, then verify by script, since the naming is not a contract.
    sidecars.sort(key=lambda s: (not s["name"].lower().startswith("a"), -(s["size"] or 0)))
    for s in sidecars:
        try:
            text = session.get(s["url"], timeout=120).text
        except requests.RequestException:
            continue
        if not _is_devanagari(text) and text.strip():
            return text, s["url"], f"text sidecar {s['name']}"

    pdfs = [s for s in streams if s["name"].lower().endswith(".pdf")]
    pdfs.sort(key=lambda s: (not s["name"].lower().startswith("a"), s["size"] or 0))
    for s in pdfs:
        if (s["size"] or 0) > MAX_PDF_BYTES:
            return None, s["url"], f"PDF larger than cap ({s['size'] / 1_048_576:.0f} MB)"
        try:
            blob = session.get(s["url"], timeout=180).content[:MAX_PDF_BYTES]
        except requests.RequestException as exc:
            return None, s["url"], f"download failed ({type(exc).__name__})"
        if not blob.startswith(b"%PDF"):
            return None, s["url"], "not a PDF"
        pdftotext = shutil.which("pdftotext")
        if not pdftotext:
            return None, s["url"], "pdftotext not installed"
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
                fh.write(blob)
                tmp = fh.name
            out = subprocess.run(
                [pdftotext, "-f", "1", "-l", str(PDF_MAX_PAGES), "-layout", tmp, "-"],
                capture_output=True, text=True, errors="replace", timeout=300,
            )
            text = re.sub(r"[ \t]+", " ", out.stdout or "")
            if text.strip():
                return text, s["url"], f"PDF {s['name']} (first {PDF_MAX_PAGES} pages)"
            return None, s["url"], "PDF has no text layer (scanned?)"
        except (subprocess.TimeoutExpired, OSError) as exc:
            return None, s["url"], f"pdf handling failed ({type(exc).__name__})"
        finally:
            if tmp and Path(tmp).exists():
                try:
                    Path(tmp).unlink()
                except OSError:
                    pass
    return None, None, "no text sidecar and no PDF attached"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-read even when text is stored")
    ap.add_argument("--delay", type=float, default=0.8, help="seconds between parents")
    ap.add_argument("--limit", type=int, help="stop after N parents")
    ap.add_argument("--keys", help="comma-separated parent keys (default: all)")
    args = ap.parse_args()

    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT_FALLBACK})

    with app.app_context():
        query = StatuteHistory.query
        if args.keys:
            keys = [k.strip() for k in args.keys.split(",") if k.strip()]
            query = query.filter(StatuteHistory.parent_key.in_(keys))
        parents = query.order_by(StatuteHistory.id).all()
        if args.limit:
            parents = parents[:args.limit]

        stored = skipped = no_record = failed = 0
        total_chars = 0
        for i, parent in enumerate(parents, 1):
            label = str(parent.parent_title or parent.parent_key)[:38]
            if (parent.full_text or "").strip() and not args.refresh:
                skipped += 1
                continue
            candidates = find_principal_records(session, parent.parent_title or "")
            if not candidates:
                no_record += 1
                print(f"  {i:3d} {label:38s} | no principal-Act record in India Code")
                time.sleep(args.delay)
                continue

            # Try records until one yields a text that looks complete. India Code holds
            # duplicates and only some carry files; its sidecars can also stop mid-
            # sentence, in which case a longer copy elsewhere is worth the look.
            best = None
            attempts = 0
            for record in candidates[:MAX_RECORDS_TRIED]:
                attempts += 1
                streams = bitstreams(session, record["uuid"])
                text, url, note = read_text(session, streams)
                if text and len(text.strip()) >= MIN_TEXT_CHARS:
                    if best is None or len(text) > len(best[0]):
                        best = (text, url, note, record)
                    if not _looks_truncated(text):
                        break                      # complete text, no need to keep looking
                time.sleep(0.3)

            if best is None:
                failed += 1
                print(f"  {i:3d} {label:38s} | READ FAILED: {note} "
                      f"({candidates[0]['title'][:30]}, {attempts} record(s) tried)")
                time.sleep(args.delay)
                continue

            text, url, note, record = best
            truncated_at_source = _looks_truncated(text)
            clipped = len(text) > MAX_TEXT_CHARS
            parent.full_text = text[:MAX_TEXT_CHARS]
            parent.text_source_url = url or (ITEM_URL + str(record["handle"]))
            detail = []
            if note:
                detail.append(note)
            if truncated_at_source:
                # Say it plainly: this is where the SOURCE's text stops, not the statute.
                detail.append(f"source text stops at {len(text):,} characters (source's own cap)")
            if clipped:
                detail.append(f"clipped to {MAX_TEXT_CHARS:,} chars")
            if attempts > 1:
                detail.append(f"{attempts} records tried")
            parent.text_source_label = (
                f"{SOURCE_LABEL} — {record['title']}"
                + (f" [{' · '.join(detail)}]" if detail else "")
            )[:200]
            parent.text_checked_at = datetime.utcnow()
            db.session.commit()
            stored += 1
            total_chars += len(parent.full_text)
            mark = " (source-truncated)" if truncated_at_source else ""
            print(f"  {i:3d} {label:38s} | stored {len(parent.full_text):>8,} chars{mark} · {record['title'][:30]}")
            time.sleep(args.delay)

        print(f"\nSUMMARY stored={stored} skipped={skipped} no_record={no_record} "
              f"read_failed={failed}")
        have = StatuteHistory.query.filter(StatuteHistory.full_text.isnot(None)).count()
        chars = db.session.query(db.func.sum(db.func.length(StatuteHistory.full_text))).scalar() or 0
        print(f"parents with stored text: {have} / {StatuteHistory.query.count()} ({chars:,} chars)")


if __name__ == "__main__":
    main()
