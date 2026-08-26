// Smart bill search — dependency-free scoring search for the BillPicker.
//
// Pipeline: normalize -> synonym expansion -> per-token scoring
// (exact word > prefix > substring > fuzzy subsequence) with field weights
// (title > ministry > status) -> AND semantics, OR fallback when AND is empty.

const SYNONYMS = {
  gst: 'goods and services tax',
  dpdp: 'digital personal data protection',
  bns: 'bharatiya nyaya sanhita',
  bnss: 'bharatiya nagarik suraksha sanhita',
  bsa: 'bharatiya sakshya',
  jk: 'jammu kashmir',
  jandk: 'jammu kashmir',
  it: 'income tax information technology',
  income: 'income tax',
  onc: 'one nation election',
  ut: 'union territory',
  msp: 'minimum support price',
  caa: 'citizenship amendment',
  anrf: 'anusandhan national research foundation',
}

export function normalize(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[()[\]{}.,/\\'"“”‘’—–-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

// Filler words never carry meaning on their own — matching "and" would
// pull in every bill title in existence.
const STOP_WORDS = new Set(['and', 'the', 'of', 'for', 'in', 'to', 'a', 'an', 'or'])

function expandToken(tok) {
  return SYNONYMS[tok] ? `${tok} ${SYNONYMS[tok]}` : tok
}

function isSubsequence(needle, haystack) {
  let i = 0
  for (let j = 0; j < haystack.length && i < needle.length; j++) {
    if (haystack[j] === needle[i]) i++
  }
  return i === needle.length
}

// Score one token against one field's normalized text.
function scoreTokenInField(tok, text, weights) {
  if (!text) return 0
  if (text.includes(tok)) {
    const words = text.split(' ')
    if (words.includes(tok)) return weights.exact
    if (words.some((w) => w.startsWith(tok))) return weights.prefix
    return weights.substring
  }
  // Fuzzy subsequence — only for tokens >=4 chars, heavily discounted
  // (3-char tokens like "gst" subsequence-match far too much noise).
  if (tok.length >= 4 && isSubsequence(tok, text.replace(/ /g, ''))) {
    return weights.fuzzy
  }
  return 0
}

const TITLE_W = { exact: 100, prefix: 75, substring: 55, fuzzy: 25 }
const MINISTRY_W = { exact: 70, prefix: 50, substring: 35, fuzzy: 0 }
const STATUS_W = { exact: 45, prefix: 35, substring: 25, fuzzy: 0 }

function scoreBill(bill, rawTokens) {
  const title = normalize(bill.title)
  const ministry = normalize(bill.ministry)
  const status = normalize(bill.status)

  let total = 0
  let allMatched = true

  for (const raw of rawTokens) {
    const variants = expandToken(raw).split(' ').filter((v) => v !== raw && !STOP_WORDS.has(v))
    let best = scoreTokenInField(raw, title, TITLE_W)
    best = Math.max(best, scoreTokenInField(raw, ministry, MINISTRY_W))
    best = Math.max(best, scoreTokenInField(raw, status, STATUS_W))
    if (variants.length > 0) {
      // Sum across synonym words: a bill matching MORE expansion words
      // (e.g. "goods" + "services" + "tax" for "gst") ranks higher than
      // one matching just a single common word.
      let variantSum = 0
      for (const v of variants) {
        variantSum += Math.max(
          scoreTokenInField(v, title, TITLE_W),
          scoreTokenInField(v, ministry, MINISTRY_W),
          scoreTokenInField(v, status, STATUS_W)
        )
      }
      best = Math.max(best, variantSum * 0.9)
    }
    if (best === 0) allMatched = false
    total += best
  }

  return { score: total, matchedAll: allMatched }
}

/**
 * Filter + rank bills for a query.
 * @param {Array} bills  bill objects ({title, ministry, status, ...})
 * @param {string} query raw user input
 * @returns {Array} bills sorted best-first (empty query -> original order)
 */
export function smartFilterBills(bills, query) {
  const q = normalize(query)
  if (!q) return bills
  const tokens = q.split(' ').filter((t) => t && !STOP_WORDS.has(t))
  if (tokens.length === 0) return bills

  // AND pass: every token must match somewhere in the bill.
  const scored = []
  for (const bill of bills) {
    const { score, matchedAll } = scoreBill(bill, tokens)
    if (matchedAll && score > 0) scored.push({ bill, score })
  }

  // OR fallback: if AND matched nothing, keep bills that matched at least
  // one token so the user still sees near-misses, ranked.
  if (scored.length === 0) {
    for (const bill of bills) {
      let any = 0
      for (const raw of tokens) {
        const variants = expandToken(raw).split(' ')
        let best = scoreTokenInField(raw, normalize(bill.title), TITLE_W)
        best = Math.max(best, scoreTokenInField(raw, normalize(bill.ministry), MINISTRY_W))
        for (const v of variants) {
          if (v === raw) continue
          best = Math.max(best, scoreTokenInField(v, normalize(bill.title), TITLE_W) * 0.9)
        }
        any += best
      }
      if (any > 0) scored.push({ bill, score: any * 0.5 })
    }
  }

  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 50)
    .map((s) => s.bill)
}
