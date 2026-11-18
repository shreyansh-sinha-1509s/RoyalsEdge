import { describe, expect, it } from 'vitest';
import { EXPECTED_COUNTS, runAnalyticsImport, validateAllSourceFiles } from '../src/services/importService.js';
import { runDataReconciliation } from '../src/services/reconcileService.js';
import { createInMemoryPrisma } from './helpers/inMemoryPrisma.js';

describe('CSV Import Validation, Idempotency & Reconciliation (Real Project Data)', () => {
  it('validates all required Phase 2–6 source CSV files and mandatory headers', () => {
    const res = validateAllSourceFiles();
    expect(res.validatedFiles).toBe(30);
  });

  it('imports all verified datasets, reconciles exact Top 10 against submission CSVs, and is idempotent on re-run', async () => {
    const prisma = createInMemoryPrisma();

    // First import
    const first = await runAnalyticsImport(prisma, { triggeredBy: 'VITEST_FIRST' });
    expect(first.status).toBe('SUCCESS');
    expect(first.reconcileReport.passed).toBe(true);
    expect(first.reconcileReport.battingTop10Check.exactMatch).toBe(true);
    expect(first.reconcileReport.bowlingTop10Check.exactMatch).toBe(true);
    expect(first.reconcileReport.nullReliabilityPreserved).toBe(true);
    expect(first.reconcileReport.sharedPlayerIdsPreserved).toBe(true);

    expect(first.tableCounts.players).toBe(EXPECTED_COUNTS.players);
    expect(first.tableCounts.batting_rankings).toBe(EXPECTED_COUNTS.battingRankings);
    expect(first.tableCounts.bowling_rankings).toBe(EXPECTED_COUNTS.bowlingRankings);
    expect(first.tableCounts.matches).toBe(EXPECTED_COUNTS.matches);
    expect(first.tableCounts.innings).toBe(EXPECTED_COUNTS.innings);
    expect(first.tableCounts.source_deliveries_aggregated).toBe(EXPECTED_COUNTS.primaryDeliveries);

    // Second import (idempotency check — zero duplicates)
    const second = await runAnalyticsImport(prisma, { triggeredBy: 'VITEST_SECOND' });
    expect(second.status).toBe('SUCCESS');
    expect(second.reconcileReport.passed).toBe(true);

    expect(await prisma.player.count()).toBe(1217);
    expect(await prisma.battingRanking.count()).toBe(173);
    expect(await prisma.bowlingRanking.count()).toBe(165);
    expect(await prisma.match.count()).toBe(853);
    expect(await prisma.innings.count()).toBe(1652);
    expect(await prisma.dataImportLog.count()).toBe(2);

    // Standalone reconciliation check
    const rec = await runDataReconciliation(prisma);
    expect(rec.passed).toBe(true);
    expect(rec.discrepancies).toHaveLength(0);
  }, 30000);
});

