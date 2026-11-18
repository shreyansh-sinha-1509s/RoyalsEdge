import { AppError } from '../utils/response.js';

export function validateQuery(schema) {
  return (req, _res, next) => {
    const parsed = schema.safeParse(req.query);
    if (!parsed.success) {
      return next(parsed.error);
    }
    req.validatedQuery = parsed.data;
    return next();
  };
}

export function validateParams(schema) {
  return (req, _res, next) => {
    const parsed = schema.safeParse(req.params);
    if (!parsed.success) {
      return next(parsed.error);
    }
    req.validatedParams = parsed.data;
    return next();
  };
}

export function validateBody(schema) {
  return (req, _res, next) => {
    if (!req.body || typeof req.body !== 'object') {
      return next(new AppError(400, 'VALIDATION_ERROR', 'JSON request body is required.'));
    }
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) {
      return next(parsed.error);
    }
    req.validatedBody = parsed.data;
    return next();
  };
}

