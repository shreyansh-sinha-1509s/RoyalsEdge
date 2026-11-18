/**
 * High-contrast, lightweight CSS night-stadium visual fallback.
 * Used as instant LCP backdrop while 3D hydrates AND as full fallback on mobile / reduced-motion / non-WebGL devices.
 */
export function StadiumHeroFallback() {
  return (
    <div
      className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#13081B] via-[#24172C] to-[#1A0E23]"
      aria-hidden="true"
    >
      {/* Stadium floodlight radial cones */}
      <div
        className="stadium-beam absolute -left-24 -top-24 h-[520px] w-[520px] rounded-full opacity-50 blur-3xl"
        style={{ background: 'radial-gradient(circle, rgba(216,180,90,0.42) 0%, rgba(232,62,128,0.12) 45%, transparent 72%)' }}
      />
      <div
        className="stadium-beam absolute -right-24 -top-24 h-[520px] w-[520px] rounded-full opacity-50 blur-3xl"
        style={{
          background: 'radial-gradient(circle, rgba(232,62,128,0.42) 0%, rgba(216,180,90,0.14) 45%, transparent 72%)',
          animationDelay: '2.2s',
        }}
      />

      {/* Stadium horizon ring & pitch perspective */}
      <div className="absolute inset-x-0 bottom-0 h-[44%] bg-gradient-to-t from-[#120819] via-[#24172C]/70 to-transparent" />
      <div
        className="absolute bottom-[-22%] left-1/2 h-[340px] w-[140%] -translate-x-1/2 rounded-[50%] border-t-2 border-rr-pink/40"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(79, 209, 165, 0.14) 0%, rgba(36, 23, 44, 0.85) 65%)',
        }}
      />
      {/* Illuminated central pitch strip */}
      <div
        className="absolute bottom-0 left-1/2 h-44 w-24 -translate-x-1/2 opacity-40"
        style={{
          background: 'linear-gradient(to top, rgba(216,180,90,0.55), rgba(216,180,90,0.08))',
          clipPath: 'polygon(22% 0%, 78% 0%, 100% 100%, 0% 100%)',
        }}
      />

      {/* Subtle floating stadium particles */}
      {[
        { top: '24%', left: '18%', delay: '0s' },
        { top: '32%', left: '74%', delay: '1.5s' },
        { top: '48%', left: '34%', delay: '3s' },
        { top: '20%', left: '56%', delay: '2s' },
        { top: '58%', left: '82%', delay: '4.2s' },
      ].map((dot, idx) => (
        <span
          key={idx}
          className="stadium-particle absolute h-1.5 w-1.5 rounded-full bg-rr-gold/70 shadow-[0_0_10px_#D8B45A]"
          style={{ top: dot.top, left: dot.left, animationDelay: dot.delay }}
        />
      ))}
    </div>
  );
}

