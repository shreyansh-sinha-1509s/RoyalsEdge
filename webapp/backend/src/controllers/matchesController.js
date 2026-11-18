import { AppError, buildPaginationMeta, resolveSort, sendSuccess } from '../utils/response.js';

const MATCH_SORTS = {
  matchDate: 'matchDate',
  matchId: 'matchId',
  meanChasePressure: 'meanChasePressure',
  meanI1Pressure: 'meanI1Pressure',
  meanBowlingPressure: 'meanBowlingPressure',
  highOrExtremeBattingBalls: 'highOrExtremeBattingBalls',
  regularDeliveries: 'regularDeliveries',
};

export function createMatchesController(prisma) {
  return {
    async list(req, res, next) {
      try {
        const q = req.validatedQuery;
        const where = {};

        if (q.format && q.format !== 'ALL') where.matchFormat = q.format;
        if (q.season && q.season !== 'ALL') where.season = q.season;
        if (q.completionType && q.completionType !== 'ALL') {
          where.matchCompletionClassification = q.completionType;
        }
        if (q.minPressure !== undefined) {
          where.OR = [
            { meanChasePressure: { gte: q.minPressure } },
            { meanI1Pressure: { gte: q.minPressure } },
            { meanBowlingPressure: { gte: q.minPressure } },
          ];
        }
        if (q.search) {
          const maybeId = Number(q.search);
          where.AND = [
            ...(where.AND || []),
            {
              OR: [
                { compName: { contains: q.search, mode: 'insensitive' } },
                { homeTeam: { contains: q.search, mode: 'insensitive' } },
                { awayTeam: { contains: q.search, mode: 'insensitive' } },
                { venueCountry: { contains: q.search, mode: 'insensitive' } },
                { result: { contains: q.search, mode: 'insensitive' } },
                ...(Number.isInteger(maybeId) ? [{ matchId: maybeId }] : []),
              ],
            },
          ];
        }

        const orderBy = resolveSort(q.sortBy, q.sortOrder, MATCH_SORTS, 'matchDate', 'desc');
        const skip = (q.page - 1) * q.limit;

        const [total, items] = await Promise.all([
          prisma.match.count({ where }),
          prisma.match.findMany({
            where,
            orderBy,
            skip,
            take: q.limit,
          }),
        ]);

        return sendSuccess(res, items, {
          ...buildPaginationMeta(q.page, q.limit, total),
          dataScopeNotice: 'Historical verified IPL & T20I matches (2022–2026). No live scores.',
        });
      } catch (err) {
        return next(err);
      }
    },

    async detail(req, res, next) {
      try {
        const { matchId } = req.validatedParams;
        const match = await prisma.match.findUnique({
          where: { matchId },
          include: {
            innings: {
              orderBy: { innings: 'asc' },
            },
          },
        });

        if (!match) {
          throw new AppError(404, 'MATCH_NOT_FOUND', `No match found with match_id=${matchId}.`);
        }

        return sendSuccess(res, {
          ...match,
          historicalNotice: 'Historical verified match record (2022–2026).',
        });
      } catch (err) {
        return next(err);
      }
    },
  };
}

