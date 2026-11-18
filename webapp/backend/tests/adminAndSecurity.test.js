import bcrypt from 'bcryptjs';
import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';
import { loadEnv } from '../src/config/env.js';
import { runAnalyticsImport } from '../src/services/importService.js';
import { createInMemoryPrisma } from './helpers/inMemoryPrisma.js';

describe('Admin Security, Authentication & Report Download Allowlisting', () => {
  let app;
  let prisma;
  const testAdminEmail = 'security-test-admin@rrlab.local';
  const testAdminPassword = 'TestOnlyStrongPassword!2027';

  beforeAll(async () => {
    process.env.NODE_ENV = 'test';
    prisma = createInMemoryPrisma();
    await runAnalyticsImport(prisma, { triggeredBy: 'VITEST_ADMIN' });
    const passwordHash = await bcrypt.hash(testAdminPassword, 4);
    await prisma.adminUser.create({
      data: {
        email: testAdminEmail,
        passwordHash,
        role: 'ADMIN',
        isActive: true,
      },
    });
    app = createApp({ prismaClient: prisma, envOverride: loadEnv() });
  }, 30000);

  it('blocks unauthenticated access to all protected admin endpoints', async () => {
    const endpoints = [
      ['get', '/api/admin/auth/me'],
      ['get', '/api/admin/health'],
      ['get', '/api/admin/imports'],
      ['post', '/api/admin/reconcile'],
      ['post', '/api/admin/cache/refresh'],
      ['get', '/api/admin/audit-logs'],
    ];
    for (const [method, url] of endpoints) {
      const res = await request(app)[method](url);
      expect(res.status).toBe(401);
      expect(res.body.success).toBe(false);
    }
  });

  it('rejects invalid admin password and records failed audit entry', async () => {
    const res = await request(app)
      .post('/api/admin/auth/login')
      .send({ email: testAdminEmail, password: 'WrongPassword123!' });
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe('INVALID_CREDENTIALS');
  });

  it('authenticates admin via HttpOnly cookie, allows health/reconcile/cache/audit, and logs out cleanly', async () => {
    const agent = request.agent(app);
    const login = await agent
      .post('/api/admin/auth/login')
      .send({ email: testAdminEmail, password: testAdminPassword });

    expect(login.status).toBe(200);
    expect(login.headers['set-cookie'][0]).toContain('HttpOnly');
    expect(login.body.data.admin.email).toBe(testAdminEmail);
    expect(login.body.data.admin.passwordHash).toBeUndefined();

    const me = await agent.get('/api/admin/auth/me');
    expect(me.status).toBe(200);
    expect(me.body.data.admin.email).toBe(testAdminEmail);

    const health = await agent.get('/api/admin/health');
    expect(health.status).toBe(200);
    expect(health.body.data.tableCounts.battingRankings).toBe(173);
    expect(health.body.data.tableCounts.bowlingRankings).toBe(165);

    const reconcile = await agent.post('/api/admin/reconcile');
    expect(reconcile.status).toBe(200);
    expect(reconcile.body.data.passed).toBe(true);

    const cacheRes = await agent.post('/api/admin/cache/refresh');
    expect(cacheRes.status).toBe(200);

    const audits = await agent.get('/api/admin/audit-logs');
    expect(audits.status).toBe(200);
    expect(audits.body.data.length).toBeGreaterThanOrEqual(3);

    const logout = await agent.post('/api/admin/auth/logout');
    expect(logout.status).toBe(200);

    const afterLogout = await agent.get('/api/admin/auth/me');
    expect(afterLogout.status).toBe(401);
  });

  it('enforces strict report download allowlisting and blocks path traversal / secret access', async () => {
    const list = await request(app).get('/api/reports');
    expect(list.status).toBe(200);
    expect(list.body.data.length).toBeGreaterThanOrEqual(6);
    expect(list.body.data.every((r) => r.available)).toBe(true);

    // Valid allowlisted download
    const ok = await request(app).get('/api/reports/top-10-batters-csv/download');
    expect(ok.status).toBe(200);
    expect(ok.headers['content-disposition']).toContain('RR_Performance_Lab_Top_10_Batters.csv');
    expect(ok.text).toContain('Matthew Wade');

    // Blocked arbitrary/traversal targets
    const badIds = ['..%2F.env', '.env', 'ball_by_ball.csv', 'non-existent-report'];
    for (const bad of badIds) {
      const res = await request(app).get(`/api/reports/${bad}/download`);
      expect(res.status).toBe(404);
      expect(res.body.success).toBe(false);
    }
  });
});

