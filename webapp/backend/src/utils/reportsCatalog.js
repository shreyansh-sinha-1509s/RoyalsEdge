import fs from 'node:fs';
import path from 'node:path';
import { OUTPUTS_DIR, SUBMISSION_DIR } from '../config/paths.js';

/**
 * Strictly allowlisted downloadable reports.
 * Prevents directory traversal and forbids access to .env, raw data, or source code.
 */
const ALLOWED_REPORTS = [
  {
    id: 'top-10-batters-csv',
    title: 'Final Top 10 Batters Under Pressure (CSV)',
    description: 'Official ordered Phase 6 Top 10 Batters shortlist with composite scores, EB impact, reliability, exposure, 95% CIs, and stability tiers.',
    category: 'Official Submission',
    fileType: 'CSV',
    mimeType: 'text/csv; charset=utf-8',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Top_10_Batters.csv',
  },
  {
    id: 'top-10-bowlers-csv',
    title: 'Final Top 10 Bowlers Under Pressure (CSV)',
    description: 'Official ordered Phase 6 Top 10 Bowlers shortlist with composite scores, EB impact, economy, reliability, exposure, 95% CIs, and stability tiers.',
    category: 'Official Submission',
    fileType: 'CSV',
    mimeType: 'text/csv; charset=utf-8',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Top_10_Bowlers.csv',
  },
  {
    id: 'final-rankings-xlsx',
    title: 'Final Rankings Multi-Sheet Workbook (Excel)',
    description: '7-sheet formatted workbook including Executive Summary, Top 10 Batters, Top 10 Bowlers, Full Eligible Pools (173/165), Robustness & Data Dictionary.',
    category: 'Official Submission',
    fileType: 'XLSX',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Final_Rankings.xlsx',
  },
  {
    id: 'methodology-report-pdf',
    title: 'RoyalsEdge — Methodology Report (PDF)',
    description: 'Publication-grade 4-page PDF documenting data controls, Model C pressure framework, Empirical Bayes shrinkage, reliability, Top 10 tables, robustness, and limitations.',
    category: 'Official Submission',
    fileType: 'PDF',
    mimeType: 'application/pdf',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Methodology_Report.pdf',
  },
  {
    id: 'executive-summary-pdf',
    title: 'RoyalsEdge — Executive Summary (PDF)',
    description: '2-page decision-maker brief presenting the Top 10 Batters & Bowlers, confidence intervals, strongest findings, and key decision risks.',
    category: 'Official Submission',
    fileType: 'PDF',
    mimeType: 'application/pdf',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Executive_Summary.pdf',
  },
  {
    id: 'methodology-report-md',
    title: 'Complete 20-Section Methodology Report (Markdown)',
    description: 'Full 20-section reproducible technical report matching the official competition brief.',
    category: 'Official Submission',
    fileType: 'Markdown',
    mimeType: 'text/markdown; charset=utf-8',
    baseDir: SUBMISSION_DIR,
    fileName: 'RR_Performance_Lab_Methodology_Report.md',
  },
  {
    id: 'ranking-robustness-csv',
    title: 'Ranking Robustness Across 7 Alternative Specifications (CSV)',
    description: 'Spearman rank correlations, Top-10 overlaps, and Top-15 shifts across Models A/B, ±3pt thresholds, Raw No-EB, Performance-Dominant, and Reliability-Dominant specs.',
    category: 'Analytical Appendix',
    fileType: 'CSV',
    mimeType: 'text/csv; charset=utf-8',
    baseDir: OUTPUTS_DIR,
    fileName: 'ranking_robustness.csv',
  },
  {
    id: 'pressure-model-comparison-csv',
    title: 'Pressure Model A vs B vs C Comparison (CSV)',
    description: 'Quantitative comparison of fixed-par Model A, pooled-ECDF Model B, and context-normalized LOMO Model C across IPL and T20I.',
    category: 'Analytical Appendix',
    fileType: 'CSV',
    mimeType: 'text/csv; charset=utf-8',
    baseDir: OUTPUTS_DIR,
    fileName: 'pressure_model_comparison.csv',
  },
  {
    id: 'shortlist-alternatives-csv',
    title: 'Narrow Misses & Unselected Candidate Audit (CSV)',
    description: 'Transparent audit of Ranks 11–15 narrow misses, high-raw/insufficient-evidence exclusions, high-reliability/lower-impact profiles, and volatile workhorses.',
    category: 'Analytical Appendix',
    fileType: 'CSV',
    mimeType: 'text/csv; charset=utf-8',
    baseDir: OUTPUTS_DIR,
    fileName: 'shortlist_alternatives.csv',
  },
];

const REPORT_MAP = new Map(ALLOWED_REPORTS.map((r) => [r.id, r]));

export function listAllowedReports() {
  return ALLOWED_REPORTS.map((entry) => {
    const resolvedPath = resolveSafeReportPath(entry);
    const exists = resolvedPath ? fs.existsSync(resolvedPath) : false;
    const stat = exists ? fs.statSync(resolvedPath) : null;
    return {
      id: entry.id,
      title: entry.title,
      description: entry.description,
      category: entry.category,
      fileType: entry.fileType,
      fileName: entry.fileName,
      available: exists,
      sizeBytes: stat ? stat.size : null,
      lastGeneratedAt: stat ? stat.mtime.toISOString() : null,
      downloadUrl: `/api/reports/${entry.id}/download`,
    };
  });
}

export function resolveSafeReportPath(entry) {
  if (!entry) return null;
  const normalizedBase = path.resolve(entry.baseDir);
  const resolved = path.resolve(normalizedBase, entry.fileName);
  if (!resolved.startsWith(normalizedBase + path.sep)) {
    return null;
  }
  return resolved;
}

export function getAllowedReportForDownload(reportId) {
  // Reject any path-like characters upfront
  if (!reportId || !/^[a-z0-9-]+$/i.test(reportId)) {
    return null;
  }
  const entry = REPORT_MAP.get(reportId);
  if (!entry) return null;
  const filePath = resolveSafeReportPath(entry);
  if (!filePath || !fs.existsSync(filePath)) return null;
  return { ...entry, filePath };
}

