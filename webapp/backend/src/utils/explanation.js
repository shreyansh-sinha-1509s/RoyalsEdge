/**
 * Builds deterministic, strictly data-grounded analytical explanations from actual DB fields.
 * Never invents statistics, never calls external AI APIs, and always discloses insufficient evidence.
 */

function fmt(val, digits = 1, sign = false) {
  if (val === null || val === undefined || Number.isNaN(val)) return 'N/A';
  const num = Number(val);
  const prefix = sign && num > 0 ? '+' : '';
  return `${prefix}${num.toFixed(digits)}`;
}

export function buildBattingExplanation(perf, rel, ranking) {
  if (!perf) {
    return {
      status: 'NO_DATA',
      headline: 'No primary IPL/T20I batting exposure recorded (2022–2026).',
      strengths: [],
      limitations: ['No eligible regular-innings deliveries faced in the 2022–2026 IPL + T20I cohort.'],
      evidenceNotice: 'Insufficient batting data.',
    };
  }

  const strengths = [];
  const limitations = [];
  const tier = rel?.evidenceTier || 'INSUFFICIENT_EVIDENCE';

  if (ranking?.isTop10) {
    strengths.push(
      `Shortlisted at Rank #${ranking.rank} overall (Composite Score ${fmt(ranking.finalRankingScore, 2)}/100; ${ranking.methodsInTop10OutOf8 ?? 'N/A'}/8 robustness methods; ${fmt(ranking.mcProbTop10Pct, 1)}% Monte Carlo Top-10 probability).`
    );
  } else if (ranking) {
    strengths.push(
      `Eligible primary batting cohort Rank #${ranking.rank} of 173 (Composite Score ${fmt(ranking.finalRankingScore, 2)}/100).`
    );
  }

  if (perf.pressureBallsFaced > 0) {
    strengths.push(
      `Under HIGH + EXTREME pressure: ${perf.pressureRuns} runs off ${perf.pressureBallsFaced} balls (SR ${fmt(perf.pressureStrikeRate, 1)}, Avg ${fmt(perf.pressureAverage, 1)}, Boundary ${fmt(perf.pressureBoundaryPct, 1)}%, Dot ${fmt(perf.pressureDotBallPct, 1)}%) across ${perf.pressureInnings} innings (${perf.pressureMatches} matches).`
    );
  }

  if (rel?.ebPressureImpact !== null && rel?.ebPressureImpact !== undefined) {
    strengths.push(
      `Context-adjusted EB-shrunk pressure impact: ${fmt(rel.ebPressureImpact, 2, true)} runs/100b (raw ${fmt(rel.rawPressureImpact, 2, true)}; shrinkage weight ${fmt((rel.ebShrinkageWeight ?? 0) * 100, 1)}%).`
    );
  }

  if (rel?.reliabilityScore !== null && rel?.reliabilityScore !== undefined) {
    strengths.push(
      `Volume-free Reliability Score: ${fmt(rel.reliabilityScore, 1)}/100 (Evidence Strength ${fmt(rel.evidenceStrengthScore, 1)}/100).`
    );
  } else {
    limitations.push(
      `Reliability score is intentionally NULL (${tier}): fewer than 5 pressure innings or below minimum pressure-ball evidence; never imputed as 0.`
    );
  }

  if (rel?.impactCi95Low !== null && rel?.impactCi95High !== null && rel?.impactCi95Low !== undefined) {
    limitations.push(
      `Match-clustered 95% bootstrap CI spans [${fmt(rel.impactCi95Low, 1, true)}, ${fmt(rel.impactCi95High, 1, true)}] runs/100b.`
    );
  }

  if (ranking?.mainLimitation) {
    limitations.push(ranking.mainLimitation);
  } else if (!rel?.isPrimaryEligible) {
    limitations.push(
      `Not eligible for primary final rankings (requires >=80 pressure balls faced and >=10 pressure innings/matches; recorded ${perf.pressureBallsFaced}b / ${perf.pressureMatches}m).`
    );
  }

  const headline = ranking?.isTop10
    ? `Top-10 Pressure Batter (#${ranking.rank}) — ${perf.battingRole} delivering ${fmt(rel?.ebPressureImpact, 1, true)} EB runs/100b under pressure.`
    : rel?.isPrimaryEligible
      ? `Primary-Eligible ${perf.battingRole} (${tier.replaceAll('_', ' ')}) with ${perf.pressureBallsFaced} pressure balls across ${perf.pressureMatches} matches.`
      : `${perf.battingRole} with ${tier.replaceAll('_', ' ')} (${perf.pressureBallsFaced} pressure balls across ${perf.pressureMatches} matches).`;

  return {
    status: tier,
    headline,
    strengths,
    limitations,
    evidenceNotice:
      rel?.reliabilityScore === null || rel?.reliabilityScore === undefined
        ? 'Insufficient evidence to estimate cross-match reliability (stored as NULL).'
        : `Evidence tier: ${tier} (${perf.pressureBallsFaced} pressure BF, ${perf.pressureMatches} matches, ${perf.pressureSeasons} seasons).`,
  };
}

export function buildBowlingExplanation(perf, rel, ranking) {
  if (!perf) {
    return {
      status: 'NO_DATA',
      headline: 'No primary IPL/T20I bowling exposure recorded (2022–2026).',
      strengths: [],
      limitations: ['No eligible regular-innings deliveries bowled in the 2022–2026 IPL + T20I cohort.'],
      evidenceNotice: 'Insufficient bowling data.',
    };
  }

  const strengths = [];
  const limitations = [];
  const tier = rel?.evidenceTier || 'INSUFFICIENT_EVIDENCE';

  if (ranking?.isTop10) {
    strengths.push(
      `Shortlisted at Rank #${ranking.rank} overall (Composite Score ${fmt(ranking.finalRankingScore, 2)}/100; ${ranking.methodsInTop10OutOf8 ?? 'N/A'}/8 robustness methods; ${fmt(ranking.mcProbTop10Pct, 1)}% Monte Carlo Top-10 probability).`
    );
  } else if (ranking) {
    strengths.push(
      `Eligible primary bowling cohort Rank #${ranking.rank} of 165 (Composite Score ${fmt(ranking.finalRankingScore, 2)}/100).`
    );
  }

  if (perf.pressureLegalBalls > 0) {
    strengths.push(
      `Under HIGH + EXTREME pressure: Econ ${fmt(perf.pressureEconomy, 2)} with ${perf.pressureWickets} wickets in ${perf.pressureLegalBalls} legal balls (RSAE ${fmt(perf.pressureRsaePerOver, 2, true)}/ov, Dot ${fmt(perf.pressureDotBallPct, 1)}%, Boundary conceded ${fmt(perf.pressureBoundaryConcededPct, 1)}%) across ${perf.pressureInnings} innings (${perf.pressureMatches} matches).`
    );
  }

  if (rel?.ebPressureImpact !== null && rel?.ebPressureImpact !== undefined) {
    strengths.push(
      `Context-adjusted EB-shrunk pressure impact: ${fmt(rel.ebPressureImpact, 2, true)} runs/24b (raw ${fmt(rel.rawPressureImpact, 2, true)}; shrinkage weight ${fmt((rel.ebShrinkageWeight ?? 0) * 100, 1)}%).`
    );
  }

  if (rel?.reliabilityScore !== null && rel?.reliabilityScore !== undefined) {
    strengths.push(
      `Volume-free Reliability Score: ${fmt(rel.reliabilityScore, 1)}/100 (Evidence Strength ${fmt(rel.evidenceStrengthScore, 1)}/100).`
    );
  } else {
    limitations.push(
      `Reliability score is intentionally NULL (${tier}): fewer than 5 pressure innings or below minimum pressure-ball evidence; never imputed as 0.`
    );
  }

  if (rel?.impactCi95Low !== null && rel?.impactCi95High !== null && rel?.impactCi95Low !== undefined) {
    limitations.push(
      `Match-clustered 95% bootstrap CI spans [${fmt(rel.impactCi95Low, 1, true)}, ${fmt(rel.impactCi95High, 1, true)}] runs/24b.`
    );
  }

  if (ranking?.mainLimitation) {
    limitations.push(ranking.mainLimitation);
  } else if (!rel?.isPrimaryEligible) {
    limitations.push(
      `Not eligible for primary final rankings (requires >=90 pressure legal balls and >=10 pressure innings/matches; recorded ${perf.pressureLegalBalls}b / ${perf.pressureMatches}m).`
    );
  }

  const headline = ranking?.isTop10
    ? `Top-10 Pressure Bowler (#${ranking.rank}) — ${perf.bowlingRole} delivering ${fmt(rel?.ebPressureImpact, 2, true)} EB runs/24b under pressure.`
    : rel?.isPrimaryEligible
      ? `Primary-Eligible ${perf.bowlingRole} (${tier.replaceAll('_', ' ')}) with ${perf.pressureLegalBalls} pressure legal balls across ${perf.pressureMatches} matches.`
      : `${perf.bowlingRole} with ${tier.replaceAll('_', ' ')} (${perf.pressureLegalBalls} pressure legal balls across ${perf.pressureMatches} matches).`;

  return {
    status: tier,
    headline,
    strengths,
    limitations,
    evidenceNotice:
      rel?.reliabilityScore === null || rel?.reliabilityScore === undefined
        ? 'Insufficient evidence to estimate cross-match reliability (stored as NULL).'
        : `Evidence tier: ${tier} (${perf.pressureLegalBalls} pressure LB, ${perf.pressureMatches} matches, ${perf.pressureSeasons} seasons).`,
  };
}

