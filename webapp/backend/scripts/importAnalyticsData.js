import { loadEnv } from '../src/config/env.js';
import { disconnectPrisma, getPrismaClient } from '../src/config/prisma.js';
import { runAnalyticsImport } from '../src/services/importService.js';

async function main() {
  loadEnv({ requireDatabase: true, requireJwt: false });
  const prisma = getPrismaClient();

  console.log('=== RoyalsEdge — Analytics Data Import ===');
  console.log('Validating source CSV headers and loading verified Phase 2–6 outputs...');

  const result = await runAnalyticsImport(prisma, { triggeredBy: 'CLI' });

  console.log('\nImport completed successfully:');
  console.log(`  Batch ID        : ${result.batchId}`);
  console.log(`  Status          : ${result.status}`);
  console.log(`  Duration        : ${result.durationMs} ms`);
  console.log(`  Total Inserted  : ${result.insertedCount}`);
  console.log('  Table Counts    :', JSON.stringify(result.tableCounts, null, 2));
  console.log(`  Reconciliation  : ${result.reconcileReport.passed ? 'PASS (Exact Top 10 & Count Match)' : 'FAIL'}`);
}

main()
  .catch((err) => {
    console.error('\n[IMPORT FAILED]', err.message);
    process.exitCode = 1;
  })
  .finally(async () => {
    await disconnectPrisma();
  });

