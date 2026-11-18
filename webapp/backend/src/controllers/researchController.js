import { appCache } from '../config/cache.js';
import { getAllowedReportForDownload, listAllowedReports } from '../utils/reportsCatalog.js';
import { AppError, sendSuccess } from '../utils/response.js';

export function createResearchController(prisma) {
  return {
    async methodology(_req, res, next) {
      try {
        const data = await appCache.getOrSet('methodology', async () => {
          const [sections, audits, pressureModels] = await Promise.all([
            prisma.methodologySection.findMany({ orderBy: { sectionNumber: 'asc' } }),
            prisma.rankingRobustnessAudit.findMany(),
            prisma.pressureSummary.findMany({
              where: { summaryType: 'MODEL_COMPARISON' },
            }),
          ]);

          return {
            sections,
            modelComparison: pressureModels.map((r) => r.payloadJson),
            rankingMethodComparison: audits
              .filter((a) => a.auditType === 'METHOD_COMPARISON')
              .map((a) => a.payloadJson),
            robustnessTests: audits
              .filter((a) => a.auditType === 'ROBUSTNESS_TEST')
              .map((a) => a.payloadJson),
            thresholdSensitivity: audits
              .filter((a) => a.auditType === 'THRESHOLD_SENSITIVITY')
              .map((a) => a.payloadJson),
            shortlistAlternatives: audits
              .filter((a) => a.auditType === 'SHORTLIST_ALTERNATIVE')
              .map((a) => a.payloadJson),
            downloadPdfUrl: '/api/reports/methodology-report-pdf/download',
          };
        });

        return sendSuccess(res, data);
      } catch (err) {
        return next(err);
      }
    },

    async reports(_req, res, next) {
      try {
        const catalog = listAllowedReports();
        return sendSuccess(res, catalog);
      } catch (err) {
        return next(err);
      }
    },

    async downloadReport(req, res, next) {
      try {
        const { reportId } = req.params;
        const report = getAllowedReportForDownload(reportId);
        if (!report) {
          throw new AppError(404, 'REPORT_NOT_FOUND', 'Requested report ID is not approved or does not exist.');
        }

        res.setHeader('Content-Type', report.mimeType);
        res.setHeader('Content-Disposition', `attachment; filename="${report.fileName}"`);
        res.setHeader('X-Content-Type-Options', 'nosniff');
        return res.sendFile(report.filePath, (err) => {
          if (err && !res.headersSent) {
            next(new AppError(500, 'DOWNLOAD_ERROR', 'Unable to stream report file.'));
          }
        });
      } catch (err) {
        return next(err);
      }
    },
  };
}

