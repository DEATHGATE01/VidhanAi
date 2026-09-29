"""
Act Linker Service
==================
Deterministic, explainable, no LLM. Links Bills to the Acts they came from by
normalized-title matching plus PRS status, storing match confidence and the
exact scraped evidence for every link. A missing link beats a wrong link:
nothing is written below the 0.60 confidence floor, and `verified=True` is only
ever set for an exact normalized match.

Rule (enforced by review): is_estimated=False implies source and source_url are
set. This module never writes estimated rows at all.
"""
import re
from datetime import datetime

from models import db, Act, Bill, BillActLink, LifecycleEvent

# PRS list statuses that imply an Act exists (verified 2026-09-29: the live
# status vocabulary includes both, and PRS has no bill->act hyperlink, so the
# relationship is derived).
ACT_IMPLYING_STATUSES = ('Passed', 'Replaced by an Act')


def normalize(title):
    """Normalize a bill/act title for matching.

    lowercase; strip leading `the`; strip punctuation; drop the trailing year;
    map the head noun bill <-> act; collapse whitespace.
    'The Industrial Relations Code (Amendment) Bill, 2026' and
    'The Industrial Relations Code (Amendment) Act, 2026' normalize equal.
    """
    t = str(title or '').lower().strip()
    t = re.sub(r'^the\s+', '', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\b(19|20)\d{2}\b', ' ', t)   # drop the trailing year
    t = re.sub(r'\bbill\b', 'act', t)          # map head noun
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def base_title(normalized_title):
    """Strip amendment markers and the head noun: the *base* title.

    Used for a weaker match class when exact normalized equality fails.
    """
    t = re.sub(r'\bamendment\b', ' ', normalized_title)
    t = re.sub(r'\bact\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def _year_of(title):
    match = re.search(r'\b((?:19|20)\d{2})\b', str(title or ''))
    return int(match.group(1)) if match else None


def _link_type_for(bill_status):
    """Link type from the PRS bill status ('Replaced by an Act' wins)."""
    status = (bill_status or '').lower()
    if 'replaced' in status:
        return 'replaced_by_act'
    return 'enacted_as'


def score_pair(bill, act):
    """Score a (bill, act) pair 0..1 per plan §5.3.

    exact normalized equality .95; base-title equality .70; +0.05 same
    ministry string; +0.05 PRS status implies an Act; -0.15 conflicting year.
    Clamped to 1.0.
    """
    nb = normalize(bill.title)
    na = normalize(act.title)
    if not nb or not na:
        return 0.0

    if nb == na:
        score = 0.95
    elif base_title(nb) == base_title(na):
        score = 0.70
    else:
        return 0.0  # no row below base-title equality is even considered

    # Acts scraped from the PRS listing carry no ministry; apply the bonus
    # only when both sides actually have a ministry string to compare.
    bill_ministry = getattr(bill, 'ministry', None)
    act_ministry = getattr(act, 'ministry', None)
    if bill_ministry and act_ministry and \
            bill_ministry.strip().lower() == act_ministry.strip().lower():
        score += 0.05
    if (bill.status or '').strip() in ACT_IMPLYING_STATUSES:
        score += 0.05

    by = _year_of(bill.title)
    ay = act.year or _year_of(act.title)
    if by and ay and by != ay:
        score -= 0.15

    return max(0.0, min(1.0, score))


def link_bill_to_act(bill, act, dry_run=False):
    """Upsert one BillActLink for a (bill, act) pair that scored >= 0.60.

    >= 0.90 -> verified=True, match_method='title_match', evidence quotes both
    titles; 0.60-0.90 -> verified=False with evidence = both titles + source
    URLs. < 0.60 -> no row written. Idempotent on (bill_id, act_id, link_type).
    Returns (link_or_None, action) where action is 'verified' | 'candidate' | 'skipped'.
    """
    score = score_pair(bill, act)
    if score < 0.60:
        return None, 'skipped'

    verified = score >= 0.90
    link_type = _link_type_for(bill.status)
    evidence = (
        f"Bill: \"{bill.title}\" ({bill.url or 'no url'}) | "
        f"Act: \"{act.title}\" ({act.source_url or 'no url'}) | "
        f"normalized match, score {score:.2f}"
    )

    if dry_run:
        return (BillActLink(bill_id=bill.id, act_id=act.id, link_type=link_type,
                            match_method='title_match', match_confidence=score,
                            evidence=evidence, verified=verified), 'dry-run')

    link = BillActLink.query.filter_by(
        bill_id=bill.id, act_id=act.id, link_type=link_type
    ).first()
    if link:
        changed = (link.match_confidence != score or link.verified != verified
                   or link.evidence != evidence)
        if changed:
            link.match_method = 'title_match'
            link.match_confidence = score
            link.evidence = evidence
            link.verified = verified
        return link, ('kept' if not changed else 'updated')

    link = BillActLink(
        bill_id=bill.id,
        act_id=act.id,
        link_type=link_type,
        match_method='title_match',
        match_confidence=score,
        evidence=evidence,
        verified=verified,
        created_at=datetime.utcnow(),
    )
    db.session.add(link)
    return link, ('verified' if verified else 'candidate')


def run_linker(dry_run=False, bills_query=None, acts_query=None):
    """Run the full linker over the candidate space (plan §5.2).

    Candidates: bills whose PRS status implies an Act, matched against all
    acts. Returns a summary dict; idempotent (re-running changes nothing).
    """
    strong_bills = bills_query if bills_query is not None else Bill.query.filter(
        Bill.status.in_(ACT_IMPLYING_STATUSES)
    ).all()
    all_acts = acts_query if acts_query is not None else Act.query.all()

    verified = 0
    candidates = 0
    skipped = 0
    total_links = 0

    for bill in strong_bills:
        nb = normalize(bill.title)
        if not nb:
            continue
        bill_year = _year_of(bill.title)
        for act in all_acts:
            # Candidate generation: same normalized title, same normalized
            # base title, or year within {bill_year, bill_year+1}.
            na = normalize(act.title)
            ay = act.year or _year_of(act.title)
            year_window = bill_year and ay and ay in (bill_year, bill_year + 1)
            if not (nb == na or base_title(nb) == base_title(na) or year_window):
                continue
            link, action = link_bill_to_act(bill, act, dry_run=dry_run)
            if action == 'skipped':
                skipped += 1
            elif action in ('verified', 'candidate'):
                verified += 1 if action == 'verified' else 0
                candidates += 1
            elif action in ('kept', 'updated'):
                # Re-runs count existing links by their current flag.
                total_links += 1
                if link is not None and link.verified:
                    verified += 1
            else:  # dry-run probe
                if link is not None and link.verified:
                    verified += 1
                candidates += 1

    return {
        'bills_considered': len(strong_bills),
        'acts_considered': len(all_acts),
        'links_verified': verified,
        'links_candidate': candidates,
        'pairs_skipped': skipped,
        'existing_links_seen': total_links,
    }
