// Elegant SVG bottle used until real product photos are available.
// To use a real photo: if product.imageUrl is set, an <img> is rendered instead.
export default function PerfumeBottle({ color = '#b5651d', size = 220, variant = 0, imageUrl, alt = '' }) {
  if (imageUrl) return <img src={imageUrl} alt={alt} style={{ height: size, objectFit: 'contain' }} />;
  const id = `g-${color.replace('#', '')}-${variant}`;
  const shapes = [
    // 0: classic rectangular bottle
    <rect key="b" x="40" y="80" width="120" height="150" rx="14" fill={`url(#${id})`} />,
    // 1: round bottle
    <ellipse key="b" cx="100" cy="160" rx="72" ry="72" fill={`url(#${id})`} />,
    // 2: tall slim bottle
    <rect key="b" x="58" y="70" width="84" height="165" rx="40" fill={`url(#${id})`} />,
  ];
  return (
    <svg viewBox="0 0 200 250" height={size} aria-label={alt} role="img">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.55" />
          <stop offset="55%" stopColor={color} stopOpacity="0.9" />
          <stop offset="100%" stopColor={color} />
        </linearGradient>
      </defs>
      <rect x="82" y="22" width="36" height="38" rx="4" fill="#1d1a17" />
      <rect x="90" y="58" width="20" height="16" fill="#c9a96e" />
      {shapes[variant % 3]}
      <rect x="50" y="95" width="14" height="110" rx="7" fill="#fff" opacity="0.22" />
      <rect x="70" y="140" width="60" height="26" rx="2" fill="#f7f3ec" opacity="0.85" />
      <line x1="78" y1="153" x2="122" y2="153" stroke="#1d1a17" strokeWidth="1.2" opacity="0.6" />
    </svg>
  );
}
