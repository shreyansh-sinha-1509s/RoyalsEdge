import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App.jsx';
import { fmtNum, fmtReliability } from '../utils/formatters.js';

function mockFetchMap(handlers) {
  globalThis.fetch = vi.fn(async (url) => {
    const strUrl = String(url);
    for (const [pattern, response] of handlers) {
      if (strUrl.includes(pattern)) {
        const status = response.status ?? 200;
        return {
          ok: status >= 200 && status < 300,
          status,
          json: async () => response.body,
        };
      }
    }
    return {
      ok: false,
      status: 404,
      json: async () => ({ success: false, error: { code: 'NOT_FOUND', message: 'Not mocked' } }),
    };
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('RoyalsEdge Frontend Verification', () => {
  it('never formats NULL reliability or missing metrics as zero', () => {
    expect(fmtReliability(null)).toBe('Insufficient Evidence (NULL)');
    expect(fmtReliability(undefined)).toBe('Insufficient Evidence (NULL)');
    expect(fmtReliability(50.1)).toBe('50.1 / 100');
    expect(fmtNum(null)).toBe('N/A');
    expect(fmtNum(undefined)).toBe('N/A');
  });

  it('renders cinematic homepage with brand, tagline, CTA, and verified snapshot from API', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
      [
        '/api/overview',
        {
          body: {
            success: true,
            data: {
              snapshot: {
                deliveries: 193988,
                matchesWithBallData: 837,
                totalEligibleMatches: 853,
                innings: 1652,
                totalPlayers: 1217,
                battersAnalyzed: 824,
                bowlersAnalyzed: 596,
                eligibleBatters: 173,
                eligibleBowlers: 165,
                seasonsCoverage: '2022–2026',
              },
              top10Batters: [
                {
                  rank: 1,
                  playerId: 796,
                  playerName: 'Matthew Wade',
                  role: 'Finisher / Lower-Middle',
                  competitionContext: 'IPL + T20I',
                  finalRankingScore: 80.51,
                  reliabilityScore: 50.1,
                  evidenceScore: 57.69,
                },
              ],
              top10Bowlers: [
                {
                  rank: 1,
                  playerId: 4658,
                  playerName: 'Nasum Ahmed',
                  role: 'Powerplay Specialist (Spin)',
                  competitionContext: 'T20I Only',
                  finalRankingScore: 76.11,
                  reliabilityScore: 55.85,
                  evidenceScore: 45.89,
                },
              ],
              pressureLevels: [],
              pipelineStages: [],
            },
          },
        },
      ],
    ]);

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /RoyalsEdge/i })).toBeInTheDocument();
    expect(screen.getAllByText(/BEYOND THE NUMBERS\. INSIDE THE PRESSURE\./i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('link', { name: /ENTER ANALYTICS/i })).toHaveAttribute('href', '/overview');

    await waitFor(() => {
      expect(screen.getByText('Matthew Wade')).toBeInTheDocument();
      expect(screen.getByText('Nasum Ahmed')).toBeInTheDocument();
    });
  });

  it('shows honest error state when backend API fails (no fabricated demo data)', async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    });

    render(
      <MemoryRouter initialEntries={['/overview']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/never substitutes fabricated demo data/i)).toBeInTheDocument();
    });
  });

  it('redirects unauthenticated visitors on /admin to /admin/login', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
    ]);

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Admin Console Login/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/No Public Registration/i)).toBeInTheDocument();
  });

  it('renders Player Profile keyed by player_id with explicit NULL reliability notice', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
      [
        '/api/players/20172/performance',
        { body: { success: true, data: { playerId: 20172, displayName: 'Rashid Khan', batting: null, bowling: { summary: null, pressureBreakdown: [] } } } },
      ],
      [
        '/api/players/20172/reliability',
        {
          body: {
            success: true,
            data: {
              playerId: 20172,
              displayName: 'Rashid Khan',
              nullPolicyNote: 'reliabilityScore is intentionally NULL (never imputed as 0).',
              batting: null,
              bowling: { reliability: { evidenceTier: 'INSUFFICIENT_EVIDENCE', reliabilityScore: null, pressureBalls: 12, pressureMatches: 2 } },
            },
          },
        },
      ],
      ['/api/players/20172/trends', { body: { success: true, data: { seasonTrends: [], highAndExtremeSplits: [] } } }],
      [
        '/api/players/20172',
        {
          body: {
            success: true,
            data: {
              overview: {
                playerId: 20172,
                displayName: 'Rashid Khan',
                disciplines: ['bowling'],
                competitionExposure: 'T20I Only',
                seasonsRepresented: [2024],
                sharesNameWithOtherId: true,
              },
              rankings: { batting: null, bowling: null },
              explanations: {
                bowling: {
                  status: 'INSUFFICIENT_EVIDENCE',
                  headline: 'Insufficient bowling pressure sample.',
                  strengths: [],
                  limitations: ['Reliability score is NULL.'],
                },
              },
            },
          },
        },
      ],
    ]);

    render(
      <MemoryRouter initialEntries={['/players/20172']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/player_id: 20172/i)).toBeInTheDocument();
      expect(screen.getByText(/Shared Name — Strictly Keyed on ID 20172/i)).toBeInTheDocument();
      expect(screen.getByText(/Reliability Score is NULL \(Never Imputed as 0\)/i)).toBeInTheDocument();
    });
  });

  it('renders Batting Rankings Top 10 table and Pressure UNAVAILABLE disclosure cleanly', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
      [
        '/api/batting/summary',
        {
          body: {
            success: true,
            data: {
              kpis: { battersAnalyzed: 824, eligibleBatters: 173, totalPressureRuns: 48000, totalPressureBallsFaced: 35000, medianPressureStrikeRate: 137.3, highExtremeExposures: 58739 },
              byPressureCategory: [],
              pressureVsNonPressure: null,
              performanceVsReliabilityScatter: [],
              seasonalTrends: [],
            },
          },
        },
      ],
      [
        '/api/batting/rankings',
        {
          body: {
            success: true,
            data: [
              {
                rank: 1,
                playerId: 796,
                playerName: 'Matthew Wade',
                role: 'Finisher / Lower-Middle',
                competitionContext: 'IPL + T20I',
                finalRankingScore: 80.51,
                ebPressureImpact: 68.88,
                pressureStrikeRate: 169.19,
                pressureAverage: 58.2,
                reliabilityScore: 50.1,
                evidenceScore: 57.69,
                pressureBallsFaced: 172,
                uniqueMatches: 16,
                impactCi95Low: 51.5,
                impactCi95High: 132.6,
                mcProbTop10Pct: 98.7,
                stabilityTier: 'CORE_CONSENSUS',
              },
            ],
            meta: { page: 1, limit: 10, total: 10, totalPages: 1 },
          },
        },
      ],
    ]);

    render(
      <MemoryRouter initialEntries={['/batting']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Matthew Wade')).toBeInTheDocument();
      expect(screen.getByText('80.51')).toBeInTheDocument();
      expect(screen.getByText('ID 796')).toBeInTheDocument();
    });
  });

  it('renders Pressure Analytics with Model C Primary badge and 1,551 UNAVAILABLE notice', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
      [
        '/api/pressure/summary',
        {
          body: {
            success: true,
            data: {
              unavailablePolicy: 'Missing DLS deliveries remain UNAVAILABLE and never treated as LOW PRESSURE.',
              frameworks: {
                CHASE: { meanPressureIndex: 42.68, highExtremeSharePct: 30.18, contextMetrics: { meanRequiredRunRate: 9.8 } },
                FIRST_INNINGS: { meanPressureIndex: 37.9, highExtremeSharePct: 30.84, validPressureDeliveries: 101288, contextMetrics: {} },
                BOWLING: { meanPressureIndex: 51.46, highExtremeSharePct: 29.88, validPressureDeliveries: 192437, contextMetrics: {}, outcomes: { bowlingEconomy: 8.7 } },
                BATTING_COMBINED: { unavailableDeliveries: 1551 },
              },
            },
          },
        },
      ],
      ['/api/pressure/distribution', { body: { success: true, data: { histogram: [], byLevel: [], byPhase: [], bySeason: [] } } }],
      [
        '/api/pressure/models',
        {
          body: {
            success: true,
            data: {
              modelComparison: [
                { framework: 'Chase (Inn 2)', model: 'Model C (Context-Normalized LOMO - Primary)', isPrimaryFramework: true, mean: 42.68, std: 20.37, ipl_mean: 42.04, t20i_mean: 43.22, ipl_minus_t20i_mean: -1.18, spearman_corr_with_model_c: 1.0, top30_agreement_with_c_pct: 100.0 },
              ],
            },
          },
        },
      ],
    ]);

    render(
      <MemoryRouter initialEntries={['/pressure']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/1,551 UNAVAILABLE Deliveries Preserved/i)).toBeInTheDocument();
      expect(screen.getByText('PRIMARY')).toBeInTheDocument();
    });
  });

  it('renders Reports download catalog wired to backend allowlisted URLs', async () => {
    mockFetchMap([
      ['/api/admin/auth/me', { status: 401, body: { success: false, error: { code: 'UNAUTHORIZED', message: 'Auth required' } } }],
      [
        '/api/reports',
        {
          body: {
            success: true,
            data: [
              {
                id: 'methodology-report-pdf',
                title: 'RoyalsEdge — Methodology Report (PDF)',
                description: '4-page PDF report',
                category: 'Official Submission',
                fileType: 'PDF',
                available: true,
                sizeBytes: 598473,
                lastGeneratedAt: '2026-11-18T11:52:00.000Z',
              },
            ],
          },
        },
      ],
    ]);

    render(
      <MemoryRouter initialEntries={['/reports']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Methodology Report \(PDF\)/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Download PDF/i })).toHaveAttribute(
        'href',
        'http://localhost:5000/api/reports/methodology-report-pdf/download'
      );
    });
  });
});
