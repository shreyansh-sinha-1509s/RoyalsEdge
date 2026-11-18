import { loadEnv } from '../src/config/env.js';
import { disconnectPrisma, getPrismaClient } from '../src/config/prisma.js';
import { runDataReconciliation } from '../src/services/reconcileService.js';

async function main() {
  loadEnv({ requireDatabase: true, requireJwt: false });
  const prisma = getPrismaClient();

  console.log('=== RR PERFORMANCE LAB — Database Reconciliation ===');
  const report = await runDataReconciliation(prisma);

  console.log(`Status                      : ${report.passed ? 'PASS' : 'FAIL'}`);
  console.log(`NULL Reliability Preserved  : ${report.nullReliabilityPreserved}`);
  console.log(`Shared Player IDs Preserved : ${report.sharedPlayerIdsPreserved}`);
  console.log(`Batting Top 10 Exact Match  : ${report.battingTop10Check.exactMatch}`);
  console.log(`Bowling Top 10 Exact Match  : ${report.bowlingTop10Check.exactMatch}`);
  console.log('Database Counts             :', JSON.stringify(report.counts, null, 2));

  if (!report.passed) {
    console.error('\nDiscrepancies detected:');
    for (const d of report.discrepancies) {
      console.error(`  - ${d}`);
    }
    process.exitCode = 1;
  }
}

main()
  .catch((err) => {
    console.error('\n[RECONCILE FAILED]', err.message);
    process.exitCode = 1;
  })
  .finally(async () => {
    await disconnectPrisma();
  });

