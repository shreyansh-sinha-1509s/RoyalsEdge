/**
 * Formatting helpers honoring strict data-integrity rules:
 * - NULL values NEVER render as 0 (rendered explicitly as "N/A" or "Insufficient Evidence (NULL)").
 * - Tabular formatting for crisp leaderboard alignment.
 */

export function fmtNum(val, digits = 2, { sign = false, suffix = '' } = {}) {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return 'N/A';
  const n = Number(val);
  const prefix = sign && n > 0 ? '+' : '';
  return `${prefix}${n.toFixed(digits)}${suffix}`;
}

export function fmtInt(val) {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return 'N/A';
  return Math.trunc(Number(val)).toLocaleString('en-US');
}

export function fmtReliability(val) {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return 'Insufficient Evidence (NULL)';
  }
  return `${Number(val).toFixed(1)} / 100`;
}

export function fmtCi(low, high, digits = 1) {
  if (low === null || low === undefined || high === null || high === undefined) return 'N/A';
  return `[${fmtNum(low, digits, { sign: true })}, ${fmtNum(high, digits, { sign: true })}]`;
}

export function fmtBytes(bytes) {
  if (bytes === null || bytes === undefined) return 'N/A';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function fmtDate(iso) {
  if (!iso) return 'N/A';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function fmtDateTime(iso) {
  if (!iso) return 'N/A';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function stabilityBadgeClasses(tier) {
  switch (tier) {
    case 'CORE_CONSENSUS':
      return 'bg-rr-teal/15 text-rr-teal border-rr-teal/35';
    case 'MODERATELY_STABLE':
      return 'bg-rr-gold/15 text-rr-gold border-rr-gold/35';
    case 'ASSUMPTION_SENSITIVE':
      return 'bg-rr-coral/15 text-rr-coral border-rr-coral/35';
    default:
      return 'bg-rr-lavender/10 text-rr-lavender border-rr-lavender/25';
  }
}

export function evidenceBadgeClasses(tier) {
  switch (tier) {
    case 'HIGH_CONFIDENCE':
      return 'bg-rr-teal/15 text-rr-teal border-rr-teal/35';
    case 'MODERATE_CONFIDENCE':
      return 'bg-rr-blue/15 text-rr-blue border-rr-blue/35';
    case 'LOW_EVIDENCE':
      return 'bg-rr-gold/15 text-rr-gold border-rr-gold/35';
    case 'INSUFFICIENT_EVIDENCE':
      return 'bg-rr-coral/15 text-rr-coral border-rr-coral/35';
    default:
      return 'bg-rr-lavender/10 text-rr-lavender border-rr-lavender/25';
  }
}

export function humanizeEnum(val) {
  if (!val) return 'N/A';
  return String(val).replaceAll('_', ' ');
}

