/**
 * Centralized API client for RR PERFORMANCE LAB backend.
 * Uses VITE_API_BASE_URL (default http://localhost:5000) and HttpOnly cookie credentials.
 * Never fabricates fallback data when backend calls fail.
 */

const rawApiBase = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = (
  rawApiBase !== undefined
    ? rawApiBase
    : import.meta.env.PROD
      ? ''
      : 'http://localhost:5000'
).replace(/\/+$/, '');

export class ApiClientError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function buildQueryString(params = {}) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === 'ALL') continue;
    qs.set(key, String(value));
  }
  const str = qs.toString();
  return str ? `?${str}` : '';
}

export async function apiRequest(path, { method = 'GET', params, body, signal } = {}) {
  const url = `${API_BASE_URL}${path}${params ? buildQueryString(params) : ''}`;
  const headers = { Accept: 'application/json' };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (networkErr) {
    if (networkErr.name === 'AbortError') throw networkErr;
    throw new ApiClientError(
      0,
      'NETWORK_ERROR',
      `Unable to reach RR PERFORMANCE LAB API at ${API_BASE_URL}. Confirm the backend server is running.`
    );
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || !payload?.success) {
    const errObj = payload?.error || {};
    throw new ApiClientError(
      response.status,
      errObj.code || `HTTP_${response.status}`,
      errObj.message || `API request failed with status ${response.status}.`,
      errObj.details || null
    );
  }

  return payload;
}

export const api = {
  getHealth: (signal) => apiRequest('/api/health', { signal }),
  getOverview: (signal) => apiRequest('/api/overview', { signal }),

  getPressureSummary: (params, signal) => apiRequest('/api/pressure/summary', { params, signal }),
  getPressureDistribution: (params, signal) => apiRequest('/api/pressure/distribution', { params, signal }),
  getPressureModels: (params, signal) => apiRequest('/api/pressure/models', { params, signal }),

  getBattingSummary: (params, signal) => apiRequest('/api/batting/summary', { params, signal }),
  getBattingRankings: (params, signal) => apiRequest('/api/batting/rankings', { params, signal }),

  getBowlingSummary: (params, signal) => apiRequest('/api/bowling/summary', { params, signal }),
  getBowlingRankings: (params, signal) => apiRequest('/api/bowling/rankings', { params, signal }),

  getPlayers: (params, signal) => apiRequest('/api/players', { params, signal }),
  getPlayerProfile: (playerId, signal) => apiRequest(`/api/players/${playerId}`, { signal }),
  getPlayerPerformance: (playerId, params, signal) => apiRequest(`/api/players/${playerId}/performance`, { params, signal }),
  getPlayerReliability: (playerId, params, signal) => apiRequest(`/api/players/${playerId}/reliability`, { params, signal }),
  getPlayerTrends: (playerId, params, signal) => apiRequest(`/api/players/${playerId}/trends`, { params, signal }),

  comparePlayers: (discipline, playerIds, signal) =>
    apiRequest('/api/compare', {
      params: { discipline, playerIds: playerIds.join(',') },
      signal,
    }),

  getMatches: (params, signal) => apiRequest('/api/matches', { params, signal }),
  getMatchDetail: (matchId, signal) => apiRequest(`/api/matches/${matchId}`, { signal }),

  getMethodology: (signal) => apiRequest('/api/methodology', { signal }),
  getReports: (signal) => apiRequest('/api/reports', { signal }),
  getReportDownloadUrl: (reportId) => `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/download`,

  // Admin endpoints (HttpOnly cookie authenticated)
  adminLogin: (email, password) => apiRequest('/api/admin/auth/login', { method: 'POST', body: { email, password } }),
  adminLogout: () => apiRequest('/api/admin/auth/logout', { method: 'POST' }),
  adminMe: (signal) => apiRequest('/api/admin/auth/me', { signal }),
  adminHealth: (signal) => apiRequest('/api/admin/health', { signal }),
  adminImports: (params, signal) => apiRequest('/api/admin/imports', { params, signal }),
  adminRunImport: () => apiRequest('/api/admin/imports/run', { method: 'POST' }),
  adminReconcile: () => apiRequest('/api/admin/reconcile', { method: 'POST' }),
  adminRefreshCache: () => apiRequest('/api/admin/cache/refresh', { method: 'POST' }),
  adminAuditLogs: (params, signal) => apiRequest('/api/admin/audit-logs', { params, signal }),
};

