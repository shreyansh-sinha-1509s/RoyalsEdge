import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';
import { loadEnv } from '../src/config/env.js';
import { runAnalyticsImport } from '../src/services/importService.js';
import { createInMemoryPrisma } from './helpers/inMemoryPrisma.js';

describe('Public Analytics REST API (Verified Project Data)', () => {
  let app;
  let prisma;

  beforeAll(async () => {
    process.env.NODE_ENV = 'test';
    prisma = createInMemoryPrisma();
    await runAnalyticsImport(prisma, { triggeredBy: 'VITEST_PUBLIC' });
    app = createApp({ prismaClient: prisma, envOverride: loadEnv() });
  }, 30000);

  it('GET /api/health returns database connected and last import info', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.data.database).toBe('connected');
    expect(res.body.data.lastSuccessfulImport.reconcilePassed).toBe(true);
  });

  it('GET /api/overview returns exact verified dataset counts and Top 10 lists', async () => {
    const res = await request(app).get('/api/overview');
    expect(res.status).toBe(200);
    expect(res.body.data.snapshot.deliveries).toBe(193988);
    expect(res.body.data.snapshot.matchesWithBallData).toBe(837);
    expect(res.body.data.snapshot.innings).toBe(1652);
    expect(res.body.data.snapshot.battersAnalyzed).toBe(824);
    expect(res.body.data.snapshot.bowlersAnalyzed).toBe(596);
    expect(res.body.data.top10Batters).toHaveLength(10);
    expect(res.body.data.top10Bowlers).toHaveLength(10);
  });

  it('GET /api/batting/rankings returns exact ordered Top 10 batters and full 173 eligible pool with pagination', async () => {
    const top10 = await request(app).get('/api/batting/rankings?top10Only=true');
    expect(top10.status).toBe(200);
    expect(top10.body.data).toHaveLength(10);
    expect(top10.body.data[0].rank).toBe(1);
    expect(top10.body.data[0].playerId).toBe(796);
    expect(top10.body.data[0].playerName).toBe('Matthew Wade');
    expect(top10.body.data[9].rank).toBe(10);
    expect(top10.body.data[9].playerId).toBe(6726);
    expect(top10.body.data[9].playerName).toBe('Romario Shepherd');

    const paged = await request(app).get('/api/batting/rankings?page=2&limit=15');
    expect(paged.status).toBe(200);
    expect(paged.body.meta.total).toBe(173);
    expect(paged.body.meta.page).toBe(2);
    expect(paged.body.data).toHaveLength(15);
    expect(paged.body.data[0].rank).toBe(16);
  });

  it('GET /api/bowling/rankings returns exact ordered Top 10 bowlers and full 165 eligible pool', async () => {
    const top10 = await request(app).get('/api/bowling/rankings?top10Only=true');
    expect(top10.status).toBe(200);
    expect(top10.body.data).toHaveLength(10);
    expect(top10.body.data[0].rank).toBe(1);
    expect(top10.body.data[0].playerId).toBe(4658);
    expect(top10.body.data[0].playerName).toBe('Nasum Ahmed');
    expect(top10.body.data[1].playerId).toBe(2876);
    expect(top10.body.data[1].playerName).toBe('Axar Patel');

    const allMeta = await request(app).get('/api/bowling/rankings?page=1&limit=10');
    expect(allMeta.body.meta.total).toBe(165);
  });

  it('preserves shared player names under distinct player_ids (Rashid Khan 4722 vs 20172)', async () => {
    const search = await request(app).get('/api/players?search=Rashid%20Khan');
    expect(search.status).toBe(200);
    const ids = search.body.data.map((p) => p.playerId).sort((a, b) => a - b);
    expect(ids).toContain(4722);
    expect(ids).toContain(20172);

    const p1 = await request(app).get('/api/players/4722');
    const p2 = await request(app).get('/api/players/20172');
    expect(p1.status).toBe(200);
    expect(p2.status).toBe(200);
    expect(p1.body.data.overview.playerId).toBe(4722);
    expect(p2.body.data.overview.playerId).toBe(20172);
    expect(p1.body.data.overview.sharesNameWithOtherId).toBe(true);
    expect(p1.body.data.rankings.bowling.rank).toBe(4);
    expect(p2.body.data.rankings.bowling).toBeNull();
  });

  it('preserves NULL reliability for INSUFFICIENT_EVIDENCE players (never 0)', async () => {
    const sparseRel = await prisma.playerBattingReliability.findFirst({
      where: { evidenceTier: 'INSUFFICIENT_EVIDENCE' },
    });
    expect(sparseRel).not.toBeNull();
    expect(sparseRel.reliabilityScore).toBeNull();

    const res = await request(app).get(`/api/players/${sparseRel.playerId}/reliability?discipline=batting`);
    expect(res.status).toBe(200);
    expect(res.body.data.batting.reliability.evidenceTier).toBe('INSUFFICIENT_EVIDENCE');
    expect(res.body.data.batting.reliability.reliabilityScore).toBeNull();
  });

  it('preserves UNAVAILABLE pressure context separately from LOW PRESSURE (1,551 deliveries)', async () => {
    const sum = await request(app).get('/api/pressure/summary');
    expect(sum.status).toBe(200);
    expect(sum.body.data.frameworks.BATTING_COMBINED.totalDeliveries).toBe(193988);
    expect(sum.body.data.frameworks.BATTING_COMBINED.unavailableDeliveries).toBe(1551);
    expect(sum.body.data.frameworks.BOWLING.unavailableDeliveries).toBe(1551);

    const dist = await request(app).get('/api/pressure/distribution?framework=BATTING_COMBINED');
    expect(dist.status).toBe(200);
    const unavail = dist.body.data.byLevel.find((l) => l.pressureLevel === 'UNAVAILABLE');
    expect(unavail.deliveries).toBe(1551);
    expect(unavail.meanPressureIndex).toBeNull();
  });

  it('GET /api/pressure/models marks Model C as the primary pressure framework', async () => {
    const res = await request(app).get('/api/pressure/models');
    expect(res.status).toBe(200);
    const primaryRows = res.body.data.modelComparison.filter((m) => m.isPrimaryFramework);
    expect(primaryRows.length).toBe(3);
  });

  it('GET /api/compare enforces same-discipline comparison and flags sample-size gaps', async () => {
    // Compare Ravindra Jadeja (550b) vs Matthew Wade (172b) -> >2x sample gap warning
    const ok = await request(app).get('/api/compare?discipline=batting&playerIds=152,796');
    expect(ok.status).toBe(200);
    expect(ok.body.data.players).toHaveLength(2);
    expect(ok.body.data.sampleSizeWarning).toContain('Substantial sample-size difference');

    // Pure batter / non-bowler rejected in bowling mode (Matthew Wade 796 has no bowling performance)
    const mismatch = await request(app).get('/api/compare?discipline=bowling&playerIds=796,2876');
    expect(mismatch.status).toBe(400);
    expect(mismatch.body.error.code).toBe('DISCIPLINE_MISMATCH');

    // Invalid discipline rejected by Zod
    const badDisc = await request(app).get('/api/compare?discipline=mixed&playerIds=152,796');
    expect(badDisc.status).toBe(400);
  });

  it('rejects invalid query parameters cleanly with 400 and no stack trace', async () => {
    const badPage = await request(app).get('/api/matches?page=-5&limit=999');
    expect(badPage.status).toBe(400);
    expect(badPage.body.success).toBe(false);
    expect(badPage.body.error.code).toBe('VALIDATION_ERROR');
    expect(badPage.body.stack).toBeUndefined();

    const badId = await request(app).get('/api/players/not-an-integer');
    expect(badId.status).toBe(400);
  });

  it('supports matches pagination, match detail, methodology, and batting/bowling summaries', async () => {
    const matches = await request(app).get('/api/matches?format=IPL&page=1&limit=5');
    expect(matches.status).toBe(200);
    expect(matches.body.data).toHaveLength(5);

    const firstId = matches.body.data[0].matchId;
    const detail = await request(app).get(`/api/matches/${firstId}`);
    expect(detail.status).toBe(200);
    expect(detail.body.data.matchId).toBe(firstId);

    const meth = await request(app).get('/api/methodology');
    expect(meth.status).toBe(200);
    expect(meth.body.data.sections).toHaveLength(20);

    const batSum = await request(app).get('/api/batting/summary?format=IPL');
    expect(batSum.status).toBe(200);
    expect(batSum.body.data.byPressureCategory).toHaveLength(4);

    const bowlSum = await request(app).get('/api/bowling/summary?format=T20I');
    expect(bowlSum.status).toBe(200);
    expect(bowlSum.body.data.byPressureCategory).toHaveLength(4);
  });
});

