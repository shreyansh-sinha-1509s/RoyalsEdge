import { useId } from 'react';
import {
  TAGLINE_PATH,
  TAGLINE_WIDTH,
  WORDMARK_EDGE_PATH,
  WORDMARK_ROYALS_PATH,
  WORDMARK_VIEWBOX_WIDTH,
} from './royalsedgeBrandPaths.js';

const OUTER_SHIELD =
  'M10 11 L21 18.2 L32 5.5 L43 18.2 L54 11 L52.2 35.5 L32 59 L11.8 35.5 Z';
const INNER_SHIELD =
  'M13.6 17.2 L21.4 22.3 L32 11.4 L42.6 22.3 L50.4 17.2 L48.8 34.2 L32 54.1 L15.2 34.2 Z';
const RIGHT_FACET =
  'M32 11.4 L42.6 22.3 L50.4 17.2 L48.8 34.2 L32 54.1 Z';
const PILLARS = [
  'M21.4 27.8 H24.5 V43.2 L21.4 39.7 Z',
  'M30.45 23.6 H33.55 V49.5 L32 51.3 L30.45 49.5 Z',
  'M39.5 27.8 H42.6 V39.7 L39.5 43.2 Z',
];
const CROWN_DIAMOND = 'M32 14.3 L34.6 17.3 L32 20.3 L29.4 17.3 Z';
const EDGE_RIM_KNOCKOUT = 'M49.2 24.4 L61.6 15.6';
const EDGE_PILLAR_KNOCKOUT = 'M17.4 42.2 Q36.0 33.6 61.2 15.6';
const EDGE_BLADE = 'M16.6 42.6 Q35.4 33.0 61.4 15.2 Q38.8 37.8 16.6 42.6 Z';
const SEAM_ARC = 'M22.2 44.6 Q39.5 37.8 56.8 22.8';

/**
 * Sovereign Vector Crest Emblem — internal SVG content in a 64x64 coordinate system.
 */
function SovereignCrestContent({ uid, theme = 'dark', simplified = false, includeSheen = true }) {
  const isMono = theme === 'mono-dark' || theme === 'mono-light';
  const monoColor = theme === 'mono-dark' ? '#F5F1F5' : '#24172C';
  const isLight = theme === 'light';

  const goldTop = isLight ? '#E5C36E' : '#F5DF9E';
  const goldMid = isLight ? '#C99F3D' : '#D8B45A';
  const goldBot = isLight ? '#96701B' : '#A67E26';

  if (simplified) {
    if (isMono) {
      return (
        <>
          <defs>
            <mask id={`re-m-${uid}`}>
              <rect width="64" height="64" fill="white" />
              <path
                d="M48.4 25.0 L61.6 15.4"
                stroke="black"
                strokeWidth="5.6"
                strokeLinecap="butt"
                fill="none"
              />
            </mask>
          </defs>
          <path d={OUTER_SHIELD} fill={monoColor} mask={`url(#re-m-${uid})`} />
          <path className="re-logo-blade" d={EDGE_BLADE} fill={monoColor} />
        </>
      );
    }

    return (
      <>
        <defs>
          <linearGradient id={`re-g-${uid}`} x1="10" y1="6" x2="54" y2="59" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor={goldTop} />
            <stop offset="52%" stopColor={goldMid} />
            <stop offset="100%" stopColor={goldBot} />
          </linearGradient>
          <linearGradient id={`re-e-${uid}`} x1="17" y1="44" x2="61" y2="15" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#D12D6E" />
            <stop offset="62%" stopColor="#E83E80" />
            <stop offset="100%" stopColor="#FF6BA6" />
          </linearGradient>
          <mask id={`re-cut-${uid}`}>
            <rect width="64" height="64" fill="white" />
            <path d="M48.4 25.0 L61.6 15.4" stroke="black" strokeWidth="5.4" strokeLinecap="butt" fill="none" />
          </mask>
        </defs>
        <path d={OUTER_SHIELD} fill={`url(#re-g-${uid})`} mask={`url(#re-cut-${uid})`} />
        <path
          d="M14.8 18.6 L21.8 23.2 L32 13.0 L42.2 23.2 L49.2 18.6 L47.8 33.8 L32 52.4 L16.2 33.8 Z"
          fill="#24172C"
        />
        <path
          d="M32 13.0 L42.2 23.2 L49.2 18.6 L47.8 33.8 L32 52.4 Z"
          fill="#160D1C"
          fillOpacity="0.72"
        />
        <path d="M32 15.4 L35.0 18.7 L32 22.0 L29.0 18.7 Z" fill="#E83E80" />
        <path className="re-logo-blade" d={EDGE_BLADE} fill={`url(#re-e-${uid})`} />
      </>
    );
  }

  if (isMono) {
    return (
      <>
        <defs>
          <mask id={`re-mc-${uid}`}>
            <rect width="64" height="64" fill="white" />
            <path d={INNER_SHIELD} fill="black" />
            <path d={EDGE_RIM_KNOCKOUT} stroke="black" strokeWidth="5.2" strokeLinecap="butt" fill="none" />
          </mask>
          <mask id={`re-pc-${uid}`}>
            <rect width="64" height="64" fill="white" />
            <path d={EDGE_PILLAR_KNOCKOUT} stroke="black" strokeWidth="5.4" strokeLinecap="round" fill="none" />
          </mask>
        </defs>
        <path d={OUTER_SHIELD} fill={monoColor} mask={`url(#re-mc-${uid})`} />
        <g mask={`url(#re-pc-${uid})`}>
          {PILLARS.map((d, i) => (
            <path key={i} d={d} fill={monoColor} fillOpacity="0.78" />
          ))}
        </g>
        <path d={CROWN_DIAMOND} fill={monoColor} />
        <path className="re-logo-blade" d={EDGE_BLADE} fill={monoColor} />
      </>
    );
  }

  return (
    <>
      <defs>
        <linearGradient id={`re-g-${uid}`} x1="10" y1="6" x2="54" y2="59" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={goldTop} />
          <stop offset="48%" stopColor={goldMid} />
          <stop offset="100%" stopColor={goldBot} />
        </linearGradient>
        <linearGradient id={`re-p-${uid}`} x1="32" y1="23" x2="32" y2="51" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={goldTop} stopOpacity="0.95" />
          <stop offset="100%" stopColor={goldMid} stopOpacity="0.34" />
        </linearGradient>
        <linearGradient id={`re-e-${uid}`} x1="17" y1="44" x2="61" y2="15" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#C92867" />
          <stop offset="62%" stopColor="#E83E80" />
          <stop offset="100%" stopColor="#FF6AA5" />
        </linearGradient>
        <linearGradient id={`re-sh-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
          <stop offset="50%" stopColor="#FFF7DC" stopOpacity="0.65" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
        </linearGradient>
        <clipPath id={`re-clip-${uid}`}>
          <path d={OUTER_SHIELD} />
        </clipPath>
        <mask id={`re-rc-${uid}`}>
          <rect width="64" height="64" fill="white" />
          <path d={EDGE_RIM_KNOCKOUT} stroke="black" strokeWidth="4.8" strokeLinecap="butt" fill="none" />
        </mask>
        <mask id={`re-pc-${uid}`}>
          <rect width="64" height="64" fill="white" />
          <path d={EDGE_PILLAR_KNOCKOUT} stroke="black" strokeWidth="5.4" strokeLinecap="round" fill="none" />
        </mask>
      </defs>

      {/* Outer Gold Crown-Crest Frame (Notched cleanly at upper-right breakout) */}
      <path d={OUTER_SHIELD} fill={`url(#re-g-${uid})`} mask={`url(#re-rc-${uid})`} />

      {/* Restrained Metallic Gold Light Sweep (triggered on reveal or hover) */}
      {includeSheen && (
        <g clipPath={`url(#re-clip-${uid})`} mask={`url(#re-rc-${uid})`}>
          <rect
            className="re-logo-sheen"
            x="-24"
            y="0"
            width="20"
            height="64"
            fill={`url(#re-sh-${uid})`}
            opacity="0"
          />
        </g>
      )}

      {/* Recessed Deep Plum Shield & Sculpted Right Half-Facet */}
      <path d={INNER_SHIELD} fill="#24172C" />
      <path d={RIGHT_FACET} fill="#160D1C" fillOpacity="0.78" />

      {/* Three Precision Stump / Telemetry Columns */}
      <g mask={`url(#re-pc-${uid})`}>
        {PILLARS.map((d, i) => (
          <path key={i} d={d} fill={`url(#re-p-${uid})`} />
        ))}
      </g>

      {/* Sovereign Crown Apex Diamond */}
      <path d={CROWN_DIAMOND} fill="#E83E80" />

      {/* Cricket Seam Secondary Precision Filament */}
      <path
        className="re-logo-seam"
        d={SEAM_ARC}
        stroke={`url(#re-g-${uid})`}
        strokeWidth="1.35"
        strokeLinecap="round"
        fill="none"
        opacity="0.92"
      />

      {/* Signature Ascending Trajectory / Edge Blade */}
      <path className="re-logo-blade" d={EDGE_BLADE} fill={`url(#re-e-${uid})`} />
    </>
  );
}

/**
 * Custom Geometric Wordmark SVG ("RoyalsEdge") with engineered 'R' and 3-tier beveled 'E'.
 * Works standalone or composed inside RoyalsEdgeLogo horizontal/stacked lockups.
 */
export function RoyalsEdgeWordmark({
  height = 20,
  theme = 'auto',
  className = '',
}) {
  const uid = useId().replace(/:/g, '');
  const vbWidth = Math.ceil(WORDMARK_VIEWBOX_WIDTH + 2);
  const vbHeight = 44;
  const computedWidth = Math.round((height * vbWidth) / vbHeight);

  const isAuto = theme === 'auto';
  const isMonoDark = theme === 'mono-dark';
  const isMonoLight = theme === 'mono-light';

  let royalsFill;
  let edgeFill;
  let royalsClass = '';
  let edgeClass = '';

  if (isAuto) {
    royalsClass = 're-wm-royals-auto';
    edgeClass = 're-wm-edge-auto';
  } else if (isMonoDark) {
    royalsFill = '#F5F1F5';
    edgeFill = '#F5F1F5';
  } else if (isMonoLight) {
    royalsFill = '#24172C';
    edgeFill = '#24172C';
  } else if (theme === 'light') {
    royalsFill = '#24172C';
    edgeFill = `url(#re-wmg-${uid})`;
  } else {
    royalsFill = '#F5F1F5';
    edgeFill = `url(#re-wmg-${uid})`;
  }

  return (
    <svg
      width={computedWidth}
      height={height}
      viewBox={`0 0 ${vbWidth} ${vbHeight}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      {!isAuto && !isMonoDark && !isMonoLight && (
        <defs>
          <linearGradient id={`re-wmg-${uid}`} x1="0" y1="0" x2="0" y2="34" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor={theme === 'light' ? '#C89D38' : '#F5DF9E'} />
            <stop offset="55%" stopColor={theme === 'light' ? '#A87E22' : '#D8B45A'} />
            <stop offset="100%" stopColor={theme === 'light' ? '#876315' : '#B99136'} />
          </linearGradient>
        </defs>
      )}
      <g transform="translate(1 1)">
        <path d={WORDMARK_ROYALS_PATH} fill={royalsFill} className={royalsClass} fillRule="evenodd" />
        <path d={WORDMARK_EDGE_PATH} fill={edgeFill} className={edgeClass} fillRule="evenodd" />
      </g>
    </svg>
  );
}

/**
 * Official RoyalsEdge Brand Logo ("The Sovereign Vector").
 *
 * Variants:
 * - "icon"       : Sovereign Vector crest emblem only (auto-simplifies at size <= 24)
 * - "micro"      : Forced small-size simplified emblem
 * - "horizontal" : Primary horizontal lockup (crest + bespoke RoyalsEdge wordmark + optional tagline)
 * - "stacked"    : Compact stacked lockup (crest above centered wordmark + gold divider + optional tagline)
 *
 * Themes: "auto" | "dark" | "light" | "mono-dark" | "mono-light"
 */
export function RoyalsEdgeLogo({
  variant = 'icon',
  theme = 'auto',
  size = 38,
  showTagline = false,
  animated = false,
  interactive = true,
  className = '',
}) {
  const uid = useId().replace(/:/g, '');
  const motionClasses = [
    animated ? 're-logo-reveal' : '',
    interactive ? 're-logo-interactive' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const resolvedCrestTheme = theme === 'auto' ? 'dark' : theme;

  if (variant === 'icon' || variant === 'micro') {
    const simplified = variant === 'micro' || size <= 24;
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`shrink-0 ${motionClasses}`}
        aria-hidden="true"
      >
        <SovereignCrestContent
          uid={uid}
          theme={resolvedCrestTheme}
          simplified={simplified}
          includeSheen={!simplified}
        />
      </svg>
    );
  }

  if (variant === 'stacked') {
    const vbW = 296;
    const vbH = showTagline ? 194 : 156;
    const width = Math.round((size * vbW) / vbH);
    const wmScale = 0.88;
    const wmX = (vbW - WORDMARK_VIEWBOX_WIDTH * wmScale) / 2;
    const tagScale = 0.88;
    const tagX = (vbW - TAGLINE_WIDTH * tagScale) / 2;
    const isAuto = theme === 'auto';
    const isMonoDark = theme === 'mono-dark';
    const isMonoLight = theme === 'mono-light';
    const royalsFill = isAuto ? undefined : isMonoLight || theme === 'light' ? '#24172C' : '#F5F1F5';
    const edgeFill = isAuto
      ? undefined
      : isMonoDark
        ? '#F5F1F5'
        : isMonoLight
          ? '#24172C'
          : theme === 'light'
            ? '#A87E22'
            : '#D8B45A';
    const tagFill = isAuto ? undefined : isMonoLight || theme === 'light' ? '#5B4867' : '#C9B9D3';

    return (
      <svg
        width={width}
        height={size}
        viewBox={`0 0 ${vbW} ${vbH}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`shrink-0 ${motionClasses}`}
        aria-hidden="true"
      >
        <g transform="translate(103.8 4) scale(1.38)">
          <SovereignCrestContent uid={uid} theme={resolvedCrestTheme} />
        </g>
        <g transform={`translate(${wmX.toFixed(2)} 104) scale(${wmScale})`}>
          <path
            d={WORDMARK_ROYALS_PATH}
            fill={royalsFill}
            className={isAuto ? 're-wm-royals-auto' : ''}
            fillRule="evenodd"
          />
          <path
            d={WORDMARK_EDGE_PATH}
            fill={edgeFill}
            className={isAuto ? 're-wm-edge-auto' : ''}
            fillRule="evenodd"
          />
        </g>
        {showTagline && (
          <>
            <rect
              x="112"
              y="154"
              width="72"
              height="1.6"
              rx="0.8"
              fill={isMonoDark ? '#F5F1F5' : isMonoLight ? '#24172C' : '#D8B45A'}
              opacity="0.7"
            />
            <g transform={`translate(${tagX.toFixed(2)} 166) scale(${tagScale})`} opacity="0.92">
              <path d={TAGLINE_PATH} fill={tagFill} className={isAuto ? 're-wm-tag-auto' : ''} />
            </g>
          </>
        )}
      </svg>
    );
  }

  // Primary horizontal lockup (crest + custom geometric wordmark + optional tagline)
  const vbW = 336;
  const vbH = showTagline ? 84 : 72;
  const width = Math.round((size * vbW) / vbH);
  const isAuto = theme === 'auto';
  const isMonoDark = theme === 'mono-dark';
  const isMonoLight = theme === 'mono-light';
  const royalsFill = isAuto ? undefined : isMonoLight || theme === 'light' ? '#24172C' : '#F5F1F5';
  const edgeFill = isAuto
    ? undefined
    : isMonoDark
      ? '#F5F1F5'
      : isMonoLight
        ? '#24172C'
        : theme === 'light'
          ? '#A87E22'
          : '#D8B45A';
  const tagFill = isAuto ? undefined : isMonoLight || theme === 'light' ? '#5B4867' : '#C9B9D3';

  return (
    <svg
      width={width}
      height={size}
      viewBox={`0 0 ${vbW} ${vbH}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${motionClasses}`}
      aria-hidden="true"
    >
      <g transform={showTagline ? 'translate(2 6) scale(1.125)' : 'translate(2 2) scale(1.06)'}>
        <SovereignCrestContent uid={uid} theme={resolvedCrestTheme} />
      </g>
      <g transform={showTagline ? 'translate(84 14)' : 'translate(82 17)'}>
        <path
          d={WORDMARK_ROYALS_PATH}
          fill={royalsFill}
          className={isAuto ? 're-wm-royals-auto' : ''}
          fillRule="evenodd"
        />
        <path
          d={WORDMARK_EDGE_PATH}
          fill={edgeFill}
          className={isAuto ? 're-wm-edge-auto' : ''}
          fillRule="evenodd"
        />
      </g>
      {showTagline && (
        <g transform="translate(84 66.5)" opacity="0.92">
          <path d={TAGLINE_PATH} fill={tagFill} className={isAuto ? 're-wm-tag-auto' : ''} />
        </g>
      )}
    </svg>
  );
}
