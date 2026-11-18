import { useId } from 'react';

/**
 * Custom RoyalsEdge brand emblem:
 * Stylized cricket ball with precision diagonal seam stitching and integrated minimal royal crown.
 * Clean geometric silhouette with transparent background; crisp from 24px favicon up to large hero marks.
 */
export function RoyalsEdgeLogo({ size = 34, className = '' }) {
  const uid = useId().replace(/:/g, '');
  const ballGrad = `re-ball-${uid}`;
  const goldGrad = `re-gold-${uid}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      <defs>
        <radialGradient id={ballGrad} cx="35%" cy="30%" r="72%">
          <stop offset="0%" stopColor="#F55B98" />
          <stop offset="52%" stopColor="#E83E80" />
          <stop offset="100%" stopColor="#8A1544" />
        </radialGradient>
        <linearGradient id={goldGrad} x1="10" y1="4" x2="38" y2="42" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#F5DC93" />
          <stop offset="55%" stopColor="#D8B45A" />
          <stop offset="100%" stopColor="#B38932" />
        </linearGradient>
      </defs>

      {/* Minimal geometric royal crown integrated along upper rim */}
      <path
        d="M14.5 14.5L16.2 7.4L21.2 11.4L24 4.8L26.8 11.4L31.8 7.4L33.5 14.5C30.6 13.4 27.4 12.8 24 12.8C20.6 12.8 17.4 13.4 14.5 14.5Z"
        fill={`url(#${goldGrad})`}
      />
      {/* Precision apex diamond accent */}
      <circle cx="24" cy="3.2" r="1.4" fill="#E83E80" />

      {/* Stylized cricket ball sphere */}
      <circle
        cx="24"
        cy="29.5"
        r="15.2"
        fill={`url(#${ballGrad})`}
        stroke={`url(#${goldGrad})`}
        strokeWidth="1.6"
      />

      {/* Subtle upper-left specular sheen */}
      <path
        d="M13.6 24.5C14.8 20.1 18.4 17.1 22.8 16.5"
        stroke="#FFFFFF"
        strokeOpacity="0.28"
        strokeWidth="1.6"
        strokeLinecap="round"
      />

      {/* Diagonal twin cricket seam arcs */}
      <path
        d="M12.2 37.8C17.2 31.6 25.4 24.4 34.4 19.6"
        stroke={`url(#${goldGrad})`}
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M14.6 40.3C19.6 34.1 27.8 26.9 36.8 22.1"
        stroke={`url(#${goldGrad})`}
        strokeWidth="1.7"
        strokeLinecap="round"
      />

      {/* Precision angled cricket seam stitches */}
      <g stroke="#F5F1F5" strokeOpacity="0.9" strokeWidth="1.15" strokeLinecap="round">
        <line x1="15.8" y1="36.2" x2="17.2" y2="37.4" />
        <line x1="19.6" y1="32.4" x2="21.0" y2="33.7" />
        <line x1="23.5" y1="28.9" x2="24.9" y2="30.2" />
        <line x1="27.6" y1="25.6" x2="29.0" y2="27.0" />
        <line x1="31.8" y1="22.5" x2="33.1" y2="23.9" />
      </g>
    </svg>
  );
}

