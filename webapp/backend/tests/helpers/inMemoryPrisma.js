/**
 * Faithful in-memory Prisma test harness for Vitest + Supertest.
 * Supports transactional import, idempotent re-import, reconciliation, and all API queries
 * against real verified project CSVs without mutating any live Neon database.
 */

function matchesValue(recordVal, cond) {
  if (cond === undefined) return true;
  if (cond === null) return recordVal === null || recordVal === undefined;
  if (typeof cond !== 'object' || cond instanceof Date) {
    return recordVal === cond;
  }
  if ('equals' in cond) return recordVal === cond.equals;
  if ('not' in cond) {
    if (cond.not === null) return recordVal !== null && recordVal !== undefined;
    return recordVal !== cond.not;
  }
  if ('in' in cond) return Array.isArray(cond.in) && cond.in.includes(recordVal);
  if ('gte' in cond) return recordVal !== null && recordVal !== undefined && recordVal >= cond.gte;
  if ('lte' in cond) return recordVal !== null && recordVal !== undefined && recordVal <= cond.lte;
  if ('contains' in cond) {
    if (recordVal === null || recordVal === undefined) return false;
    const hay = cond.mode === 'insensitive' ? String(recordVal).toLowerCase() : String(recordVal);
    const needle = cond.mode === 'insensitive' ? String(cond.contains).toLowerCase() : String(cond.contains);
    return hay.includes(needle);
  }
  return true;
}

function getStore(state, name) {
  return state[name];
}

function attachRelations(state, modelName, row, includeOrSelect) {
  if (!row) return null;
  const base = { ...row };
  if (!includeOrSelect) return base;

  const isSelect = includeOrSelect.__mode === 'select';
  const spec = includeOrSelect.spec;

  if (modelName === 'player') {
    const pid = row.playerId;
    const resolveRel = (relKey, targetModel, mode, extraWhere = null) => {
      const list = getStore(state, targetModel).filter((r) => r.playerId === pid);
      const filtered = extraWhere ? list.filter((r) => matchesWhere(state, targetModel, r, extraWhere)) : list;
      if (mode === 'one') return filtered[0] ? { ...filtered[0] } : null;
      return filtered.map((r) => ({ ...r }));
    };

    const relMap = {
      battingPerformance: ['playerBattingPerformance', 'one'],
      bowlingPerformance: ['playerBowlingPerformance', 'one'],
      battingReliability: ['playerBattingReliability', 'one'],
      bowlingReliability: ['playerBowlingReliability', 'one'],
      battingRanking: ['battingRanking', 'one'],
      bowlingRanking: ['bowlingRanking', 'one'],
      pressureExposures: ['playerPressureExposure', 'many'],
      pressureBreakdowns: ['playerPressureBreakdown', 'many'],
      seasonPerformances: ['playerSeasonPerformance', 'many'],
    };

    for (const [k, [target, mode]] of Object.entries(relMap)) {
      if (spec[k]) {
        const sub = spec[k];
        let val = resolveRel(k, target, mode, typeof sub === 'object' ? sub.where : null);
        if (mode === 'many' && typeof sub === 'object' && sub.orderBy) {
          val = sortRows(val, sub.orderBy);
        }
        if (val && typeof sub === 'object' && sub.select) {
          val = Array.isArray(val)
            ? val.map((item) => pickSelect(item, sub.select))
            : pickSelect(val, sub.select);
        }
        base[k] = val;
      }
    }
  } else if (modelName === 'playerBattingPerformance' || modelName === 'playerBowlingPerformance') {
    if (spec.player) {
      const p = state.player.find((x) => x.playerId === row.playerId) || null;
      base.player = p
        ? attachRelations(state, 'player', p, {
            __mode: spec.player.select ? 'select' : 'include',
            spec: spec.player.select || spec.player.include || {},
          })
        : null;
    }
  } else if (modelName === 'match') {
    if (spec.innings) {
      let inns = state.innings.filter((i) => i.matchId === row.matchId).map((i) => ({ ...i }));
      if (typeof spec.innings === 'object' && spec.innings.orderBy) {
        inns = sortRows(inns, spec.innings.orderBy);
      }
      base.innings = inns;
    }
  } else if (modelName === 'dataImportLog') {
    if (spec.adminUser) {
      const u = row.adminUserId ? state.adminUser.find((x) => x.id === row.adminUserId) || null : null;
      base.adminUser = u && spec.adminUser.select ? pickSelect(u, spec.adminUser.select) : u;
    }
  }

  return isSelect ? pickSelect(base, spec) : base;
}

function pickSelect(obj, select) {
  const out = {};
  for (const [k, v] of Object.entries(select)) {
    if (v) out[k] = obj[k] !== undefined ? obj[k] : null;
  }
  return out;
}

function matchesWhere(state, modelName, row, where) {
  if (!where) return true;
  for (const [key, cond] of Object.entries(where)) {
    if (cond === undefined) continue;
    if (key === 'OR') {
      if (!cond.some((sub) => matchesWhere(state, modelName, row, sub))) return false;
      continue;
    }
    if (key === 'AND') {
      const list = Array.isArray(cond) ? cond : [cond];
      if (!list.every((sub) => matchesWhere(state, modelName, row, sub))) return false;
      continue;
    }

    // Relation filters on player
    if (modelName === 'player') {
      const relTargets = {
        battingPerformance: 'playerBattingPerformance',
        bowlingPerformance: 'playerBowlingPerformance',
        battingReliability: 'playerBattingReliability',
        bowlingReliability: 'playerBowlingReliability',
        battingRanking: 'battingRanking',
        bowlingRanking: 'bowlingRanking',
      };
      if (key in relTargets) {
        const relRow = state[relTargets[key]].find((r) => r.playerId === row.playerId) || null;
        if (cond && typeof cond === 'object' && 'isNot' in cond) {
          if (cond.isNot === null && relRow === null) return false;
          continue;
        }
        if (!relRow) return false;
        if (!matchesWhere(state, relTargets[key], relRow, cond)) return false;
        continue;
      }
    }

    if (!matchesValue(row[key], cond)) return false;
  }
  return true;
}

function sortRows(rows, orderBy) {
  if (!orderBy) return rows;
  const specs = Array.isArray(orderBy) ? orderBy : [orderBy];
  return [...rows].sort((a, b) => {
    for (const s of specs) {
      const [field, dir] = Object.entries(s)[0];
      const av = a[field];
      const bv = b[field];
      if (av === bv) continue;
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const cmp = av < bv ? -1 : 1;
      return dir === 'desc' ? -cmp : cmp;
    }
    return 0;
  });
}

function makeDelegate(state, modelName, pkField = 'id', autoInc = false) {
  let seq = 1;
  return {
    async count({ where } = {}) {
      return state[modelName].filter((r) => matchesWhere(state, modelName, r, where)).length;
    },
    async findMany({ where, orderBy, skip, take, include, select } = {}) {
      let rows = state[modelName].filter((r) => matchesWhere(state, modelName, r, where));
      if (orderBy) rows = sortRows(rows, orderBy);
      if (skip) rows = rows.slice(skip);
      if (take !== undefined) rows = rows.slice(0, take);
      const relOpt = select ? { __mode: 'select', spec: select } : include ? { __mode: 'include', spec: include } : null;
      return rows.map((r) => attachRelations(state, modelName, r, relOpt));
    },
    async findUnique({ where, include, select } = {}) {
      const row = state[modelName].find((r) => matchesWhere(state, modelName, r, where)) || null;
      if (!row) return null;
      const relOpt = select ? { __mode: 'select', spec: select } : include ? { __mode: 'include', spec: include } : null;
      return attachRelations(state, modelName, row, relOpt);
    },
    async findFirst({ where, orderBy, include, select } = {}) {
      let rows = state[modelName].filter((r) => matchesWhere(state, modelName, r, where));
      if (orderBy) rows = sortRows(rows, orderBy);
      const row = rows[0] || null;
      if (!row) return null;
      const relOpt = select ? { __mode: 'select', spec: select } : include ? { __mode: 'include', spec: include } : null;
      return attachRelations(state, modelName, row, relOpt);
    },
    async aggregate({ where, _sum } = {}) {
      const rows = state[modelName].filter((r) => matchesWhere(state, modelName, r, where));
      const out = {};
      if (_sum) {
        out._sum = {};
        for (const key of Object.keys(_sum)) {
          out._sum[key] = rows.reduce((acc, r) => acc + (Number(r[key]) || 0), 0);
        }
      }
      return out;
    },
    async create({ data }) {
      const rec = { ...data };
      if (autoInc && rec[pkField] === undefined) {
        rec[pkField] = seq++;
      }
      if (!rec.createdAt) rec.createdAt = new Date();
      if (modelName === 'dataImportLog' && !rec.startedAt) rec.startedAt = new Date();
      state[modelName].push(rec);
      return { ...rec };
    },
    async createMany({ data }) {
      for (const item of data) {
        const rec = { ...item };
        if (autoInc && rec[pkField] === undefined) {
          rec[pkField] = seq++;
        }
        state[modelName].push(rec);
      }
      return { count: data.length };
    },
    async update({ where, data }) {
      const idx = state[modelName].findIndex((r) => matchesWhere(state, modelName, r, where));
      if (idx === -1) throw Object.assign(new Error('Not found'), { code: 'P2025' });
      state[modelName][idx] = { ...state[modelName][idx], ...data, updatedAt: new Date() };
      return { ...state[modelName][idx] };
    },
    async upsert({ where, update, create }) {
      const idx = state[modelName].findIndex((r) => matchesWhere(state, modelName, r, where));
      if (idx >= 0) {
        state[modelName][idx] = { ...state[modelName][idx], ...update, updatedAt: new Date() };
        return { ...state[modelName][idx] };
      }
      return this.create({ data: create });
    },
    async deleteMany({ where } = {}) {
      const before = state[modelName].length;
      if (!where) {
        state[modelName] = [];
        return { count: before };
      }
      state[modelName] = state[modelName].filter((r) => !matchesWhere(state, modelName, r, where));
      return { count: before - state[modelName].length };
    },
  };
}

export function createInMemoryPrisma() {
  const state = {
    player: [],
    playerBattingPerformance: [],
    playerBowlingPerformance: [],
    playerBattingReliability: [],
    playerBowlingReliability: [],
    playerPressureExposure: [],
    playerSeasonPerformance: [],
    playerPressureBreakdown: [],
    battingRanking: [],
    bowlingRanking: [],
    match: [],
    innings: [],
    pressureSummary: [],
    methodologySection: [],
    adminUser: [],
    dataImportLog: [],
    pressureAnalyticsCube: [],
    rankingRobustnessAudit: [],
    adminAuditLog: [],
  };

  const client = {
    player: makeDelegate(state, 'player', 'playerId', false),
    playerBattingPerformance: makeDelegate(state, 'playerBattingPerformance', 'playerId', false),
    playerBowlingPerformance: makeDelegate(state, 'playerBowlingPerformance', 'playerId', false),
    playerBattingReliability: makeDelegate(state, 'playerBattingReliability', 'playerId', false),
    playerBowlingReliability: makeDelegate(state, 'playerBowlingReliability', 'playerId', false),
    playerPressureExposure: makeDelegate(state, 'playerPressureExposure', 'id', true),
    playerSeasonPerformance: makeDelegate(state, 'playerSeasonPerformance', 'id', true),
    playerPressureBreakdown: makeDelegate(state, 'playerPressureBreakdown', 'id', true),
    battingRanking: makeDelegate(state, 'battingRanking', 'playerId', false),
    bowlingRanking: makeDelegate(state, 'bowlingRanking', 'playerId', false),
    match: makeDelegate(state, 'match', 'matchId', false),
    innings: makeDelegate(state, 'innings', 'id', true),
    pressureSummary: makeDelegate(state, 'pressureSummary', 'id', true),
    methodologySection: makeDelegate(state, 'methodologySection', 'sectionNumber', false),
    adminUser: makeDelegate(state, 'adminUser', 'id', true),
    dataImportLog: makeDelegate(state, 'dataImportLog', 'id', true),
    pressureAnalyticsCube: makeDelegate(state, 'pressureAnalyticsCube', 'id', true),
    rankingRobustnessAudit: makeDelegate(state, 'rankingRobustnessAudit', 'id', true),
    adminAuditLog: makeDelegate(state, 'adminAuditLog', 'id', true),
    async $queryRaw() {
      return [{ '?column?': 1 }];
    },
    async $transaction(fn) {
      // Snapshot rollback on failure
      const snapshot = structuredClone(state);
      try {
        return await fn(client);
      } catch (err) {
        for (const k of Object.keys(snapshot)) {
          state[k] = snapshot[k];
        }
        throw err;
      }
    },
  };

  return client;
}

