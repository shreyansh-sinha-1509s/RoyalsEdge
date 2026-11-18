import { Router } from 'express';
import { z } from 'zod';
import { createAdminController } from '../controllers/adminController.js';
import { createBattingController } from '../controllers/battingController.js';
import { createBowlingController } from '../controllers/bowlingController.js';
import { createMatchesController } from '../controllers/matchesController.js';
import { createOverviewController } from '../controllers/overviewController.js';
import { createPlayersController } from '../controllers/playersController.js';
import { createPressureController } from '../controllers/pressureController.js';
import { createResearchController } from '../controllers/researchController.js';
import { createRequireAdmin } from '../middleware/auth.js';
import { createLoginRateLimiter } from '../middleware/rateLimiter.js';
import { validateBody, validateParams, validateQuery } from '../middleware/validate.js';

const boolQuery = z
  .union([z.boolean(), z.enum(['true', 'false', '1', '0'])])
  .optional()
  .transform((v) => (v === true || v === 'true' || v === '1' ? true : v === false || v === 'false' || v === '0' ? false : undefined));

const paginationSchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

const pressureFilterSchema = z.object({
  framework: z.enum(['ALL', 'CHASE', 'FIRST_INNINGS', 'BOWLING', 'BATTING_COMBINED']).optional(),
  format: z.enum(['ALL', 'IPL', 'T20I']).optional(),
  season: z.enum(['ALL', '2022', '2023', '2024', '2025', '2026']).optional(),
  pressureLevel: z
    .enum(['ALL', 'LOW PRESSURE', 'MODERATE PRESSURE', 'HIGH PRESSURE', 'EXTREME PRESSURE', 'UNAVAILABLE'])
    .optional(),
  innings: z.coerce.number().int().min(1).max(2).optional(),
  phase: z.enum(['ALL', 'Powerplay', 'Middle', 'Death', 'Unavailable']).optional(),
});

const disciplineSummarySchema = pressureFilterSchema.extend({
  role: z.string().max(80).optional(),
  paceOrSpin: z.enum(['ALL', 'Pace', 'Spin']).optional(),
  playerId: z.coerce.number().int().positive().optional(),
});

const rankingsQuerySchema = paginationSchema.extend({
  top10Only: boolQuery,
  search: z.string().trim().max(80).optional(),
  role: z.string().max(80).optional(),
  paceOrSpin: z.enum(['ALL', 'Pace', 'Spin']).optional(),
  competition: z.enum(['ALL', 'IPL + T20I', 'IPL Only', 'T20I Only']).optional(),
  stabilityTier: z.enum(['ALL', 'CORE_CONSENSUS', 'MODERATELY_STABLE', 'ASSUMPTION_SENSITIVE']).optional(),
  evidenceTier: z.enum(['ALL', 'HIGH_CONFIDENCE', 'MODERATE_CONFIDENCE']).optional(),
  sortBy: z.string().max(40).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

const playersListSchema = paginationSchema.extend({
  discipline: z.enum(['all', 'batting', 'bowling']).default('all'),
  search: z.string().trim().max(80).optional(),
  role: z.string().max(80).optional(),
  competition: z.enum(['ALL', 'IPL', 'T20I']).optional(),
  evidenceTier: z
    .enum(['ALL', 'HIGH_CONFIDENCE', 'MODERATE_CONFIDENCE', 'LOW_EVIDENCE', 'INSUFFICIENT_EVIDENCE'])
    .optional(),
  eligibleOnly: boolQuery,
  sortBy: z.string().max(40).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

const playerIdParamSchema = z.object({
  playerId: z.coerce.number().int().positive(),
});

const playerSubQuerySchema = z.object({
  discipline: z.enum(['all', 'batting', 'bowling']).optional(),
});

const compareQuerySchema = z.object({
  discipline: z.enum(['batting', 'bowling']),
  playerIds: z
    .string()
    .min(1)
    .transform((raw) => raw.split(',').map((s) => Number(s.trim())))
    .refine((arr) => arr.every((n) => Number.isInteger(n) && n > 0), 'playerIds must be comma-separated positive integers')
    .refine((arr) => arr.length >= 2 && arr.length <= 4, 'Provide between 2 and 4 player IDs'),
});

const matchesListSchema = paginationSchema.extend({
  search: z.string().trim().max(80).optional(),
  format: z.enum(['ALL', 'IPL', 'T20I']).optional(),
  season: z.enum(['ALL', '2022', '2023', '2024', '2025', '2026']).optional(),
  completionType: z.string().max(60).optional(),
  minPressure: z.coerce.number().min(0).max(100).optional(),
  sortBy: z.string().max(40).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional(),
});

const matchIdParamSchema = z.object({
  matchId: z.coerce.number().int().positive(),
});

const pressureModelsSchema = z.object({
  framework: z.string().max(40).optional(),
});

const loginBodySchema = z.object({
  email: z.string().email().max(160),
  password: z.string().min(1).max(200),
});

export function createApiRouter(prisma, env) {
  const router = Router();

  const overviewCtrl = createOverviewController(prisma);
  const pressureCtrl = createPressureController(prisma);
  const battingCtrl = createBattingController(prisma);
  const bowlingCtrl = createBowlingController(prisma);
  const playersCtrl = createPlayersController(prisma);
  const matchesCtrl = createMatchesController(prisma);
  const researchCtrl = createResearchController(prisma);
  const adminCtrl = createAdminController(prisma, env);

  const requireAdmin = createRequireAdmin(prisma, env);
  const loginLimiter = createLoginRateLimiter();

  // Health & Overview
  router.get('/health', overviewCtrl.health);
  router.get('/overview', overviewCtrl.overview);

  // Pressure Intelligence
  router.get('/pressure/summary', validateQuery(pressureFilterSchema), pressureCtrl.summary);
  router.get('/pressure/distribution', validateQuery(pressureFilterSchema), pressureCtrl.distribution);
  router.get('/pressure/models', validateQuery(pressureModelsSchema), pressureCtrl.models);

  // Batting Analytics
  router.get('/batting/summary', validateQuery(disciplineSummarySchema), battingCtrl.summary);
  router.get('/batting/rankings', validateQuery(rankingsQuerySchema), battingCtrl.rankings);

  // Bowling Analytics
  router.get('/bowling/summary', validateQuery(disciplineSummarySchema), bowlingCtrl.summary);
  router.get('/bowling/rankings', validateQuery(rankingsQuerySchema), bowlingCtrl.rankings);

  // Players & Comparison
  router.get('/players', validateQuery(playersListSchema), playersCtrl.list);
  router.get('/players/:playerId', validateParams(playerIdParamSchema), playersCtrl.profile);
  router.get(
    '/players/:playerId/performance',
    validateParams(playerIdParamSchema),
    validateQuery(playerSubQuerySchema),
    playersCtrl.performance
  );
  router.get(
    '/players/:playerId/reliability',
    validateParams(playerIdParamSchema),
    validateQuery(playerSubQuerySchema),
    playersCtrl.reliability
  );
  router.get(
    '/players/:playerId/trends',
    validateParams(playerIdParamSchema),
    validateQuery(playerSubQuerySchema),
    playersCtrl.trends
  );
  router.get('/compare', validateQuery(compareQuerySchema), playersCtrl.compare);

  // Historical Matches
  router.get('/matches', validateQuery(matchesListSchema), matchesCtrl.list);
  router.get('/matches/:matchId', validateParams(matchIdParamSchema), matchesCtrl.detail);

  // Methodology & Reports
  router.get('/methodology', researchCtrl.methodology);
  router.get('/reports', researchCtrl.reports);
  router.get('/reports/:reportId/download', researchCtrl.downloadReport);

  // Admin Auth (No public registration)
  router.post('/admin/auth/login', loginLimiter, validateBody(loginBodySchema), adminCtrl.login);
  router.post('/admin/auth/logout', adminCtrl.logout);
  router.get('/admin/auth/me', requireAdmin, adminCtrl.me);

  // Protected Admin Operations (No manual ranking edits permitted)
  router.get('/admin/health', requireAdmin, adminCtrl.health);
  router.get('/admin/imports', requireAdmin, validateQuery(paginationSchema), adminCtrl.listImports);
  router.post('/admin/imports/run', requireAdmin, adminCtrl.runImport);
  router.post('/admin/reconcile', requireAdmin, adminCtrl.reconcile);
  router.post('/admin/cache/refresh', requireAdmin, adminCtrl.refreshCache);
  router.get('/admin/audit-logs', requireAdmin, validateQuery(paginationSchema), adminCtrl.auditLogs);

  return router;
}

