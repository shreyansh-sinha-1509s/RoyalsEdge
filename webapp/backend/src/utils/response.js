export class AppError extends Error {
  constructor(statusCode, code, message, details = undefined) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export function sendSuccess(res, data, meta = undefined, statusCode = 200) {
  const payload = { success: true, data };
  if (meta !== undefined) payload.meta = meta;
  return res.status(statusCode).json(payload);
}

export function buildPaginationMeta(page, limit, total) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  return {
    page,
    limit,
    total,
    totalPages,
    hasNext: page < totalPages,
    hasPrev: page > 1,
  };
}

export function resolveSort(sortBy, sortOrder, allowedMap, defaultField, defaultDir = 'asc') {
  const field = sortBy && Object.prototype.hasOwnProperty.call(allowedMap, sortBy)
    ? allowedMap[sortBy]
    : defaultField;
  const dir = sortOrder === 'desc' ? 'desc' : sortOrder === 'asc' ? 'asc' : defaultDir;
  return { [field]: dir };
}

