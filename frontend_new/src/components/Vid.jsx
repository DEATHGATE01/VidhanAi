// Vid — the VidhanAI mascot. A friendly AI bot with the scales of justice
// balanced on its head, tiny arms and legs so it can wave and walk.
// Two big sparkly eyes + a wide smile read as a cute character at a glance;
// the ⚖️ says "law". The body is a lavender orb outlined in accent purple so
// it pops on both the white canvas and AMOLED black — every fill is a CSS
// variable from index.css, so the same SVG flips themes automatically.
//
// Expressions: 'cheerful' | 'wink' | 'curious'.
// Movement (class-gated so small/logo instances stay still):
//   lively  → gentle bob + right arm wave (greeting, hero, empty states)
//   walking → swinging legs + arms, bobbing (the AI "searching" state)
// Render multiple times freely — all shapes are inlined (no shared ids).

const SCALES = (
  <>
    <line x1="100" y1="28" x2="100" y2="62" stroke="var(--gold)" strokeWidth="6" strokeLinecap="round" />
    <circle cx="100" cy="20" r="5" fill="var(--gold)" />
    <line x1="64" y1="30" x2="136" y2="30" stroke="var(--gold)" strokeWidth="6" strokeLinecap="round" />
    <line x1="67" y1="30" x2="67" y2="42" stroke="var(--gold)" strokeWidth="3" strokeLinecap="round" />
    <line x1="133" y1="30" x2="133" y2="42" stroke="var(--gold)" strokeWidth="3" strokeLinecap="round" />
    <path d="M56 42 Q68 56 80 42 Z" fill="var(--gold)" />
    <path d="M120 42 Q132 56 144 42 Z" fill="var(--gold)" />
  </>
)

const BODY = (
  <>
    {/* Lavender orb with an accent outline — the silhouette reads on any bg */}
    <circle cx="100" cy="118" r="58" fill="var(--orb)" stroke="var(--accent)" strokeWidth="4" />
    <ellipse cx="100" cy="82" rx="26" ry="15" fill="var(--orb-hi)" />
    <path d="M48 126 C48 152 64 176 100 176 C136 176 152 152 152 126 L152 118 C152 114 145 112 135 112 L65 112 C55 112 48 114 48 118 Z" fill="var(--coat)" />
    <path d="M80 126 L120 126 L119 118 C116 112 84 112 81 118 Z" fill="var(--coat-collar)" />
    <line x1="100" y1="124" x2="100" y2="164" stroke="var(--coat-collar)" strokeWidth="3" strokeLinecap="round" />
    <circle cx="100" cy="144" r="4" fill="var(--gold)" />
  </>
)

// Tiny arms + legs. Each limb is its own group so the walking/wave animations
// (gated by .vid-walking / .vid-lively on the <svg>) can swing them.
const LIMBS = (
  <>
    <g className="vid-arm-l">
      <line x1="50" y1="122" x2="40" y2="138" stroke="var(--coat)" strokeWidth="9" strokeLinecap="round" />
    </g>
    <g className="vid-arm-r">
      <line x1="150" y1="122" x2="160" y2="138" stroke="var(--coat)" strokeWidth="9" strokeLinecap="round" />
    </g>
    <g className="vid-leg-l">
      <line x1="86" y1="173" x2="83" y2="188" stroke="var(--coat)" strokeWidth="10" strokeLinecap="round" />
      <ellipse cx="82" cy="191" rx="6.5" ry="3" fill="var(--coat)" />
    </g>
    <g className="vid-leg-r">
      <line x1="114" y1="173" x2="117" y2="188" stroke="var(--coat)" strokeWidth="10" strokeLinecap="round" />
      <ellipse cx="118" cy="191" rx="6.5" ry="3" fill="var(--coat)" />
    </g>
  </>
)

// Big sparkly eyes: main eye + a large highlight plus a tiny secondary sparkle.
const EYES = (lCx, rCx, cy) => (
  <>
    <circle cx={lCx} cy={cy} r="11.5" fill="var(--eye)" />
    <circle cx={rCx} cy={cy} r="11.5" fill="var(--eye)" />
    <circle cx={lCx - 3.4} cy={cy - 3.4} r="3.8" fill="var(--bg)" />
    <circle cx={rCx - 3.4} cy={cy - 3.4} r="3.8" fill="var(--bg)" />
    <circle cx={lCx + 3.5} cy={cy + 3.5} r="1.7" fill="var(--bg)" opacity="0.7" />
    <circle cx={rCx + 3.5} cy={cy + 3.5} r="1.7" fill="var(--bg)" opacity="0.7" />
  </>
)

const BLUSH = (
  <>
    <ellipse cx="73" cy="100" rx="9.5" ry="5.5" fill="var(--blush)" />
    <ellipse cx="127" cy="100" rx="9.5" ry="5.5" fill="var(--blush)" />
  </>
)

const FACES = {
  cheerful: (
    <>
      {BLUSH}
      {EYES(83, 117, 82)}
      <path d="M71 71 Q82 63 93 71" fill="none" stroke="var(--eye)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M107 71 Q118 63 129 71" fill="none" stroke="var(--eye)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M82 99 Q100 114 118 99" fill="none" stroke="var(--eye)" strokeWidth="4.5" strokeLinecap="round" />
    </>
  ),
  wink: (
    <>
      {BLUSH}
      <path d="M73 84 Q83 92 93 84" fill="none" stroke="var(--eye)" strokeWidth="4.5" strokeLinecap="round" />
      <circle cx="117" cy="82" r="11.5" fill="var(--eye)" />
      <circle cx="113.6" cy="78.6" r="3.8" fill="var(--bg)" />
      <circle cx="120.5" cy="85.5" r="1.7" fill="var(--bg)" opacity="0.7" />
      <path d="M107 71 Q118 63 129 71" fill="none" stroke="var(--eye)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M86 99 Q100 112 114 99" fill="none" stroke="var(--eye)" strokeWidth="4.5" strokeLinecap="round" />
    </>
  ),
  curious: (
    <>
      {BLUSH}
      {EYES(83, 117, 82)}
      <path d="M71 69 Q82 61 93 69" fill="none" stroke="var(--eye)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M107 71 Q118 63 129 71" fill="none" stroke="var(--eye)" strokeWidth="3.5" strokeLinecap="round" />
      <circle cx="100" cy="106" r="4" fill="none" stroke="var(--eye)" strokeWidth="3.4" />
    </>
  ),
}

/**
 * @param {{ size?: number, expression?: 'cheerful'|'wink'|'curious', className?: string, label?: string, style?: object, lively?: boolean, walking?: boolean }} props
 */
export default function Vid({ size = 48, expression = 'cheerful', className = '', label, style, lively = false, walking = false }) {
  const face = FACES[expression] || FACES.cheerful
  const motion = walking ? 'vid-walking' : lively ? 'vid-lively' : ''
  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      className={`${className} ${motion}`.trim()}
      role={label ? 'img' : 'presentation'}
      aria-label={label}
      style={{ display: 'block', flexShrink: 0, ...style }}
    >
      <g className="vid-bob">
        {SCALES}
        {BODY}
        {LIMBS}
        {face}
      </g>
    </svg>
  )
}
