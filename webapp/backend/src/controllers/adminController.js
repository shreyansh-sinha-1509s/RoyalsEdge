import bcrypt from 'bcryptjs';
import fs from 'node:fs';
import { appCache } from '../config/cache.js';
import { DATA_PROCESSED_DIR, OUTPUTS_DIR, SUBMISSION_DIR } from '../config/paths.js';
import { ADMIN_COOKIE_NAME, getAdminCookieOptions, signAdminToken } from '../middleware/auth.js';
import { isImportRunning, runAnalyticsImport } from '../services/importService.js';
import { runDataReconciliation } from '../services/reconcileService.js';
import { AppError, buildPaginationMeta, sendSuccess } from '../utils/response.js';

async function recordAudit(prisma, { adminUserId = null, actorEmail = null, action, status, req, detailsJson = null }) {
  try {
    await prisma.adminAuditLog.create({
      data: {
        adminUserId,
        actorEmail,
        action,
        status,
        ipAddress: req?.ip || null,
        detailsJson,
      },
    });
  } catch {
    // Audit logging should not mask primary error
  }
}

export function createAdminController(prisma, env) {
  return {
    async login(req, res, next) {
      try {
        const { email, password } = req.validatedBody;
        const normalizedEmail = email.trim().toLowerCase();

        const admin = await prisma.adminUser.findUnique({ where: { email: normalizedEmail } });
        const valid = admin && admin.isActive ? await bcrypt.compare(password, admin.passwordHash) : false;

        if (!valid) {
          await recordAudit(prisma, {
            adminUserId: admin?.id ?? null,
            actorEmail: normalizedEmail,
            action: 'ADMIN_LOGIN',
            status: 'FAILED',
            req,
            detailsJson: { reason: 'Invalid credentials or inactive account' },
          });
          throw new AppError(401, 'INVALID_CREDENTIALS', 'Invalid email or password.');
        }

        await prisma.adminUser.update({
          where: { id: admin.id },
          data: { lastLoginAt: new Date() },
        });

        const token = signAdminToken(admin, env);
        res.cookie(ADMIN_COOKIE_NAME, token, getAdminCookieOptions(env));

        await recordAudit(prisma, {
          adminUserId: admin.id,
          actorEmail: admin.email,
          action: 'ADMIN_LOGIN',
          status: 'SUCCESS',
          req,
        });

        return sendSuccess(res, {
          admin: {
            id: admin.id,
            email: admin.email,
            role: admin.role,
          },
        });
      } catch (err) {
        return next(err);
      }
    },

    async logout(req, res, next) {
      try {
        res.clearCookie(ADMIN_COOKIE_NAME, {
          ...getAdminCookieOptions(env),
          maxAge: undefined,
        });
        if (req.admin) {
          await recordAudit(prisma, {
            adminUserId: req.admin.id,
            actorEmail: req.admin.email,
            action: 'ADMIN_LOGOUT',
            status: 'SUCCESS',
            req,
          });
        }
        return sendSuccess(res, { loggedOut: true });
      } catch (err) {
        return next(err);
      }
    },

    async me(req, res) {
      return sendSuccess(res, { admin: req.admin });
    },

    async health(_req, res, next) {
      try {
        await prisma.$queryRaw`SELECT 1`;
        const [
          players,
          battingPerformance,
          bowlingPerformance,
          battingReliability,
          bowlingReliability,
          battingRankings,
          bowlingRankings,
          matches,
          innings,
          pressureSummaries,
          pressureCube,
          methodologySections,
          importLogsCount,
        ] = await Promise.all([
          prisma.player.count(),
          prisma.playerBattingPerformance.count(),
          prisma.playerBowlingPerformance.count(),
          prisma.playerBattingReliability.count(),
          prisma.playerBowlingReliability.count(),
          prisma.battingRanking.count(),
          prisma.bowlingRanking.count(),
          prisma.match.count(),
          prisma.innings.count(),
          prisma.pressureSummary.count(),
          prisma.pressureAnalyticsCube.count(),
          prisma.methodologySection.count(),
          prisma.dataImportLog.count(),
        ]);

        return sendSuccess(res, {
          status: 'healthy',
          database: 'connected',
          importInProgress: isImportRunning(),
          uptimeSeconds: Math.round(process.uptime()),
          memoryMb: Math.round(process.memoryUsage().rss / (1024 * 1024)),
          cache: appCache.stats(),
          sourceDirectories: {
            dataProcessedAvailable: fs.existsSync(DATA_PROCESSED_DIR),
            outputsAvailable: fs.existsSync(OUTPUTS_DIR),
            submissionAvailable: fs.existsSync(SUBMISSION_DIR),
          },
          tableCounts: {
            players,
            battingPerformance,
            bowlingPerformance,
            battingReliability,
            bowlingReliability,
            battingRankings,
            bowlingRankings,
            matches,
            innings,
            pressureSummaries,
            pressureCube,
            methodologySections,
            importLogsCount,
          },
        });
      } catch (err) {
        return next(err);
      }
    },

    async listImports(req, res, next) {
      try {
        const { page, limit } = req.validatedQuery;
        const skip = (page - 1) * limit;
        const [total, logs] = await Promise.all([
          prisma.dataImportLog.count(),
          prisma.dataImportLog.findMany({
            orderBy: { startedAt: 'desc' },
            skip,
            take: limit,
            include: {
              adminUser: { select: { id: true, email: true } },
            },
          }),
        ]);
        return sendSuccess(res, logs, buildPaginationMeta(page, limit, total));
      } catch (err) {
        return next(err);
      }
    },

    async runImport(req, res, next) {
      try {
        if (isImportRunning()) {
          throw new AppError(409, 'IMPORT_IN_PROGRESS', 'An analytics import is already running.');
        }

        const result = await runAnalyticsImport(prisma, {
          triggeredBy: 'ADMIN_API',
          adminUserId: req.admin.id,
        });
        appCache.clear();

        await recordAudit(prisma, {
          adminUserId: req.admin.id,
          actorEmail: req.admin.email,
          action: 'RUN_DATA_IMPORT',
          status: result.status,
          req,
          detailsJson: {
            batchId: result.batchId,
            insertedCount: result.insertedCount,
            reconcilePassed: result.reconcileReport.passed,
          },
        });

        return sendSuccess(res, result);
      } catch (err) {
        await recordAudit(prisma, {
          adminUserId: req.admin?.id ?? null,
          actorEmail: req.admin?.email ?? null,
          action: 'RUN_DATA_IMPORT',
          status: 'FAILED',
          req,
          detailsJson: { message: err.message },
        });
        return next(err);
      }
    },

    async reconcile(req, res, next) {
      try {
        const report = await runDataReconciliation(prisma);
        await recordAudit(prisma, {
          adminUserId: req.admin.id,
          actorEmail: req.admin.email,
          action: 'RUN_RECONCILIATION',
          status: report.passed ? 'PASS' : 'FAIL',
          req,
          detailsJson: {
            passed: report.passed,
            discrepancyCount: report.discrepancies.length,
          },
        });
        return sendSuccess(res, report);
      } catch (err) {
        return next(err);
      }
    },

    async refreshCache(req, res, next) {
      try {
        const clearedKeys = appCache.clear();
        await recordAudit(prisma, {
          adminUserId: req.admin.id,
          actorEmail: req.admin.email,
          action: 'CACHE_REFRESH',
          status: 'SUCCESS',
          req,
          detailsJson: { clearedKeys },
        });
        return sendSuccess(res, { clearedKeys, cache: appCache.stats() });
      } catch (err) {
        return next(err);
      }
    },

    async auditLogs(req, res, next) {
      try {
        const { page, limit } = req.validatedQuery;
        const skip = (page - 1) * limit;
        const [total, items] = await Promise.all([
          prisma.adminAuditLog.count(),
          prisma.adminAuditLog.findMany({
            orderBy: { createdAt: 'desc' },
            skip,
            take: limit,
          }),
        ]);
        return sendSuccess(res, items, buildPaginationMeta(page, limit, total));
      } catch (err) {
        return next(err);
      }
    },
  };
}

